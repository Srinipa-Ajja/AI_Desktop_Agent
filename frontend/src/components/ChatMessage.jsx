import React, { useState } from 'react';
import {
  User,
  Bot,
  Terminal,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Eye,
  Sliders,
  Maximize2
} from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const [toolsExpanded, setToolsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [previewImage, setPreviewImage] = useState(null);

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  // Helper to format text with paragraphs, bullet points, and code blocks
  const renderFormattedContent = (content) => {
    if (!content) return null;

    // Check for markdown code blocks ```lang ... ```
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          text: content.substring(lastIndex, match.index),
        });
      }
      parts.push({
        type: 'code',
        language: match[1] || 'bash',
        code: match[2],
      });
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        text: content.substring(lastIndex),
      });
    }

    return parts.map((part, idx) => {
      if (part.type === 'code') {
        return (
          <div
            key={idx}
            style={{
              margin: '10px 0',
              borderRadius: '6px',
              backgroundColor: '#0a0e17',
              border: '1px solid var(--border-subtle)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 12px',
                backgroundColor: 'rgba(255,255,255,0.03)',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: '11px',
                color: 'var(--text-muted)',
              }}
            >
              <span>{part.language}</span>
              <button
                onClick={() => handleCopy(part.code)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                }}
              >
                {copied ? <Check size={12} color="var(--status-ready)" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre
              style={{
                padding: '12px',
                fontSize: '12px',
                lineHeight: '1.5',
                overflowX: 'auto',
                color: '#e2e8f0',
              }}
            >
              <code>{part.code}</code>
            </pre>
          </div>
        );
      }

      // Format text lines
      const lines = part.text.split('\n');
      return (
        <div key={idx} style={{ lineHeight: '1.6' }}>
          {lines.map((line, lidx) => {
            if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
              return (
                <div key={lidx} style={{ paddingLeft: '14px', margin: '3px 0' }}>
                  • {line.trim().substring(2)}
                </div>
              );
            }
            if (!line.trim()) {
              return <div key={lidx} style={{ height: '8px' }} />;
            }
            return <div key={lidx}>{line}</div>;
          })}
        </div>
      );
    });
  };

  const toolCalls = message.tool_calls || [];
  const hasScreenshot = message.screenshot_url || toolCalls.some(t => t.image_url);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: '12px',
        maxWidth: '850px',
        margin: '0 auto 20px',
        width: '100%',
        alignItems: 'flex-start',
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          backgroundColor: isUser ? 'var(--bubble-user)' : 'var(--bg-card)',
          border: `1px solid ${isUser ? 'var(--border-active)' : 'var(--border-subtle)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          color: isUser ? '#ffffff' : 'var(--text-secondary)',
          boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
        }}
      >
        {isUser ? <User size={18} /> : <Terminal size={18} />}
      </div>

      {/* Message Body */}
      <div
        style={{
          maxWidth: 'calc(100% - 50px)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
        }}
      >
        {/* Author & Timestamp */}
        <div
          style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>
            {isUser ? 'You' : 'Desktop Agent'}
          </span>
          <span>{formatTimestamp(message.timestamp)}</span>
          {message.status && (
            <span
              style={{
                fontSize: '10px',
                padding: '1px 6px',
                borderRadius: '4px',
                backgroundColor: 'rgba(255,255,255,0.05)',
                color: message.status === 'completed' ? 'var(--status-ready)' : 'var(--text-muted)',
              }}
            >
              {message.status}
            </span>
          )}
        </div>

        {/* Bubble */}
        <div
          style={{
            padding: '14px 18px',
            borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
            backgroundColor: isUser ? 'var(--bubble-user)' : 'var(--bubble-bot)',
            border: `1px solid ${isUser ? 'rgba(46,73,144,0.4)' : 'var(--border-subtle)'}`,
            color: 'var(--text-primary)',
            fontSize: '14px',
            wordBreak: 'break-word',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          }}
        >
          {renderFormattedContent(message.content)}

          {/* Desktop Actions / Tool Executions Accordion */}
          {toolCalls.length > 0 && (
            <div
              style={{
                marginTop: '12px',
                paddingTop: '10px',
                borderTop: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              <button
                onClick={() => setToolsExpanded(!toolsExpanded)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  padding: 0,
                }}
              >
                {toolsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <span>
                  Executed {toolCalls.length} desktop {toolCalls.length === 1 ? 'action' : 'actions'}
                </span>
              </button>

              {toolsExpanded && (
                <div
                  style={{
                    marginTop: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  {toolCalls.map((tc, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '10px',
                        borderRadius: '6px',
                        backgroundColor: '#0c111e',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '12px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: '4px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span
                            style={{
                              fontFamily: 'monospace',
                              fontWeight: 600,
                              color: tc.tool === 'hcu_ax' ? '#60a5fa' : tc.tool === 'hcu_gui' ? '#a78bfa' : '#34d399',
                            }}
                          >
                            {tc.tool}
                          </span>
                          <span style={{ color: 'var(--text-muted)' }}>({tc.summary})</span>
                        </div>
                      </div>

                      {/* Tool Output Snippet */}
                      {tc.output && (
                        <div
                          style={{
                            marginTop: '6px',
                            padding: '6px 8px',
                            backgroundColor: 'rgba(0,0,0,0.3)',
                            borderRadius: '4px',
                            fontFamily: 'monospace',
                            fontSize: '11px',
                            color: 'var(--text-secondary)',
                            maxHeight: '120px',
                            overflowY: 'auto',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {tc.output}
                        </div>
                      )}

                      {/* Attached Screenshot */}
                      {(tc.image_url || tc.image_path) && (
                        <div style={{ marginTop: '8px' }}>
                          <div
                            style={{
                              fontSize: '11px',
                              color: 'var(--text-muted)',
                              marginBottom: '4px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Eye size={12} />
                            <span>Desktop Screenshot</span>
                          </div>
                          <img
                            src={tc.image_url || `/api/screenshots/${tc.image_path.split('/').pop()}`}
                            alt="Desktop screenshot"
                            onClick={() => setPreviewImage(tc.image_url || `/api/screenshots/${tc.image_path.split('/').pop()}`)}
                            style={{
                              maxWidth: '100%',
                              maxHeight: '200px',
                              borderRadius: '4px',
                              border: '1px solid var(--border-subtle)',
                              cursor: 'zoom-in',
                              objectFit: 'contain',
                            }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Direct Screenshot on Message */}
          {message.screenshot_url && !toolsExpanded && (
            <div style={{ marginTop: '12px' }}>
              <img
                src={message.screenshot_url}
                alt="Desktop Screenshot"
                onClick={() => setPreviewImage(message.screenshot_url)}
                style={{
                  maxWidth: '100%',
                  maxHeight: '260px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'zoom-in',
                  objectFit: 'contain',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen Image Modal Preview */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.85)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            cursor: 'zoom-out',
          }}
        >
          <img
            src={previewImage}
            alt="Enlarged screenshot"
            style={{
              maxWidth: '95vw',
              maxHeight: '95vh',
              objectFit: 'contain',
              borderRadius: '8px',
              border: '1px solid var(--border-active)',
              boxShadow: '0 10px 40px rgba(0,0,0,0.7)',
            }}
          />
        </div>
      )}
    </div>
  );
}
