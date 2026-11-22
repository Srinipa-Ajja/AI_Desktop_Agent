import React, { useRef, useEffect } from 'react';
import { Send, Square, Loader2, Sparkles, AlertCircle } from 'lucide-react';

export default function MessageInput({
  input,
  setInput,
  onSendMessage,
  onCancelTask,
  isTaskRunning,
  agentStatus,
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = Math.min(scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isTaskRunning && input.trim()) {
        onSendMessage();
      }
    }
  };

  return (
    <div
      style={{
        padding: '12px 20px 20px',
        backgroundColor: 'var(--bg-main)',
        borderTop: '1px solid var(--border-subtle)',
        maxWidth: '850px',
        margin: '0 auto',
        width: '100%',
        boxSizing: 'border-box',
      }}
    >
      {/* Live status bar when task is active */}
      {isTaskRunning && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 12px',
            marginBottom: '8px',
            borderRadius: '6px',
            backgroundColor: 'rgba(46,73,144,0.15)',
            border: '1px solid rgba(46,73,144,0.3)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Loader2 size={14} className="animate-spin-slow" color="#60a5fa" />
            <span>{agentStatus || 'Executing task on desktop...'}</span>
          </div>

          <button
            onClick={onCancelTask}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(239,68,68,0.2)',
              border: '1px solid var(--status-error)',
              color: '#fca5a5',
              fontSize: '11px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <Square size={10} fill="#fca5a5" />
            <span>Stop</span>
          </button>
        </div>
      )}

      {/* Input container */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: '8px',
          padding: '8px 12px',
          backgroundColor: 'var(--bg-card)',
          borderRadius: '12px',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
          transition: 'border-color 0.15s ease',
        }}
        onFocus={() => {}}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isTaskRunning
              ? 'Agent is operating desktop... (press Stop to cancel)'
              : 'Ask the agent to open apps, take screenshots, inspect windows, or operate desktop... (Enter to send)'
          }
          disabled={isTaskRunning}
          rows={1}
          style={{
            flex: 1,
            backgroundColor: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '14px',
            lineHeight: '1.4',
            resize: 'none',
            maxHeight: '160px',
            fontFamily: 'inherit',
          }}
        />

        {isTaskRunning ? (
          <button
            onClick={onCancelTask}
            title="Stop running task"
            style={{
              padding: '8px',
              borderRadius: '8px',
              backgroundColor: 'var(--status-error)',
              border: 'none',
              color: '#ffffff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.15s ease',
            }}
          >
            <Square size={16} fill="#ffffff" />
          </button>
        ) : (
          <button
            onClick={onSendMessage}
            disabled={!input.trim()}
            title="Send request"
            style={{
              padding: '8px',
              borderRadius: '8px',
              backgroundColor: input.trim() ? 'var(--accent-primary)' : 'var(--border-subtle)',
              border: 'none',
              color: input.trim() ? '#ffffff' : 'var(--text-muted)',
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.15s ease',
            }}
            onMouseOver={(e) => {
              if (input.trim()) e.currentTarget.style.backgroundColor = 'var(--accent-hover)';
            }}
            onMouseOut={(e) => {
              if (input.trim()) e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
            }}
          >
            <Send size={16} />
          </button>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '6px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          padding: '0 4px',
        }}
      >
        <span>Press <kbd style={{ padding: '1px 4px', background: 'var(--border-subtle)', borderRadius: '3px' }}>Enter</kbd> to send, <kbd style={{ padding: '1px 4px', background: 'var(--border-subtle)', borderRadius: '3px' }}>Shift+Enter</kbd> for new line</span>
        <span>Powered by Gemini &amp; Hybrid Computer Use</span>
      </div>
    </div>
  );
}
