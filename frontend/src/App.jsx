import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ChatMessage from './components/ChatMessage';
import MessageInput from './components/MessageInput';
import WelcomeScreen from './components/WelcomeScreen';

export default function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [health, setHealth] = useState(null);
  const [agentStatus, setAgentStatus] = useState('Ready');
  const [isTaskRunning, setIsTaskRunning] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [liveToolCalls, setLiveToolCalls] = useState([]);

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, liveToolCalls, agentStatus]);

  // Fetch health
  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (err) {
      console.warn('Health check failed:', err);
    }
  };

  // Fetch conversations
  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (res.ok) {
        const list = await res.json();
        setConversations(list);
        if (list.length > 0 && !currentConvId) {
          selectConversation(list[0].id);
        }
      }
    } catch (err) {
      console.warn('Failed to load conversations:', err);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchConversations();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Select a conversation and load its messages
  const selectConversation = async (convId) => {
    setCurrentConvId(convId);
    try {
      const res = await fetch(`/api/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    }
  };

  // Create a new conversation
  const handleNewChat = () => {
    setCurrentConvId(null);
    setMessages([]);
    setLiveToolCalls([]);
    setAgentStatus('Ready');
  };

  // Delete a conversation
  const handleDeleteConversation = async (convId) => {
    try {
      await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
      const updated = conversations.filter((c) => c.id !== convId);
      setConversations(updated);
      if (currentConvId === convId) {
        if (updated.length > 0) {
          selectConversation(updated[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Clear current chat
  const handleClearChat = async () => {
    if (!currentConvId) {
      setMessages([]);
      return;
    }
    if (window.confirm('Clear all messages in this conversation?')) {
      handleDeleteConversation(currentConvId);
    }
  };

  // Cancel running task
  const handleCancelTask = async () => {
    if (!currentTaskId) return;
    try {
      setAgentStatus('Cancelling desktop task...');
      await fetch(`/api/tasks/${currentTaskId}/cancel`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  // Send message
  const handleSendMessage = async (textToSend) => {
    const messageText = (textToSend !== undefined ? textToSend : input).trim();
    if (!messageText || isTaskRunning) return;

    setInput('');
    setIsTaskRunning(true);
    setAgentStatus('Understanding request');
    setLiveToolCalls([]);

    const userMessage = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Use SSE streaming endpoint for live desktop execution feedback
    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: currentConvId,
          message: messageText,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let receivedFinal = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop(); // Keep partial event in buffer

        for (const evtStr of events) {
          if (!evtStr.trim()) continue;
          const lines = evtStr.split('\n');
          let eventType = 'message';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.substring(6).trim();
            }
          }

          if (!eventData) continue;
          let parsedData;
          try {
            parsedData = JSON.parse(eventData);
          } catch {
            continue;
          }

          if (eventType === 'task_created') {
            setCurrentTaskId(parsedData.task_id);
            if (!currentConvId && parsedData.conversation_id) {
              setCurrentConvId(parsedData.conversation_id);
            }
          } else if (eventType === 'status') {
            setAgentStatus(parsedData.status);
          } else if (eventType === 'tool_call') {
            setLiveToolCalls((prev) => [
              ...prev,
              {
                tool: parsedData.tool,
                summary: parsedData.summary,
                args: parsedData.args,
                output: 'Executing...',
              },
            ]);
          } else if (eventType === 'tool_result') {
            setLiveToolCalls((prev) => {
              if (prev.length === 0) return prev;
              const copy = [...prev];
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                output: parsedData.output,
                image_url: parsedData.image_url,
              };
              return copy;
            });
          } else if (eventType === 'final_response') {
            receivedFinal = true;
            const assistantMsg = parsedData.message;
            setMessages((prev) => [...prev, assistantMsg]);
            setAgentStatus(parsedData.cancelled ? 'Task cancelled' : 'Task completed');
            if (parsedData.conversation_id) {
              setCurrentConvId(parsedData.conversation_id);
              fetchConversations();
            }
          } else if (eventType === 'error') {
            receivedFinal = true;
            const errorMsg = {
              id: 'err-' + Date.now(),
              role: 'assistant',
              content: `Error: ${parsedData.error}`,
              status: 'error',
              timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, errorMsg]);
            setAgentStatus('Task failed');
          }
        }
      }

      if (!receivedFinal) {
        setAgentStatus('Task completed');
      }
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        id: 'err-' + Date.now(),
        role: 'assistant',
        content: `Connection error: ${err.message}. Make sure backend is running.`,
        status: 'error',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      setAgentStatus('Task failed');
    } finally {
      setIsTaskRunning(false);
      setCurrentTaskId(null);
      setLiveToolCalls([]);
      setTimeout(() => {
        setAgentStatus((current) => (current === 'Task completed' ? 'Ready' : current));
      }, 3500);
    }
  };

  const currentTitle = conversations.find((c) => c.id === currentConvId)?.title || 'Desktop Assistant';

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: 'var(--bg-main)',
      }}
    >
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        currentConvId={currentConvId}
        onSelectConversation={selectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        health={health}
        isOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main chat column */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          height: '100%',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Header
          title={currentTitle}
          agentStatus={agentStatus}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
          onClearChat={messages.length > 0 ? handleClearChat : null}
          onRefreshHealth={fetchHealth}
          isTaskRunning={isTaskRunning}
        />

        {/* Message Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 20px 0',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {messages.length === 0 ? (
            <WelcomeScreen onSelectPrompt={(p) => handleSendMessage(p)} />
          ) : (
            <>
              {messages.map((msg, index) => (
                <ChatMessage key={msg.id || index} message={msg} />
              ))}

              {/* In-progress streaming tool calls */}
              {isTaskRunning && liveToolCalls.length > 0 && (
                <div
                  style={{
                    maxWidth: '850px',
                    margin: '0 auto 20px',
                    width: '100%',
                    padding: '12px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(23, 34, 59, 0.5)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    Active Desktop Operations:
                  </div>
                  {liveToolCalls.map((tc, idx) => (
                    <div key={idx} style={{ marginBottom: '6px', fontFamily: 'monospace' }}>
                      <span style={{ color: '#60a5fa' }}>{tc.tool}</span> ({tc.summary}):{' '}
                      <span style={{ color: 'var(--text-muted)' }}>{tc.output?.substring(0, 100)}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <MessageInput
          input={input}
          setInput={setInput}
          onSendMessage={() => handleSendMessage()}
          onCancelTask={handleCancelTask}
          isTaskRunning={isTaskRunning}
          agentStatus={agentStatus}
        />
      </div>
    </div>
  );
}
