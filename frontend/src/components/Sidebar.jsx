import React, { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  Monitor,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  Layers,
  ChevronLeft,
  X
} from 'lucide-react';

export default function Sidebar({
  conversations,
  currentConvId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  health,
  isOpen,
  onCloseMobile
}) {
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const getStatusIcon = () => {
    if (!health) return <Activity size={14} className="text-gray-400 animate-spin" />;
    if (health.status === 'healthy') {
      return <CheckCircle2 size={14} style={{ color: 'var(--status-ready)' }} />;
    }
    if (health.status === 'degraded') {
      return <AlertTriangle size={14} style={{ color: 'var(--status-warn)' }} />;
    }
    return <XCircle size={14} style={{ color: 'var(--status-error)' }} />;
  };

  const getStatusText = () => {
    if (!health) return 'Checking connection...';
    if (health.desktop_session?.accessible) return 'Desktop Connected';
    if (!health.gemini?.key_configured) return 'Gemini Key Missing';
    return 'Desktop Degraded';
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onCloseMobile}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            zIndex: 40,
            display: 'block',
          }}
          className="md:hidden"
        />
      )}

      <aside
        style={{
          width: '280px',
          backgroundColor: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          flexShrink: 0,
          zIndex: 50,
          transition: 'transform 0.25s ease',
        }}
        className={`fixed md:static inset-y-0 left-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Header / Brand */}
        <div
          style={{
            padding: '18px 16px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                backgroundColor: 'var(--border-active)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 2px 8px rgba(46,73,144,0.3)',
              }}
            >
              <Monitor size={18} style={{ color: '#ffffff' }} />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', letterSpacing: '-0.2px' }}>
                HCU Assistant
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Gemini Desktop Agent
              </div>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="md:hidden"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Action: New Chat */}
        <div style={{ padding: '14px 16px' }}>
          <button
            onClick={() => {
              onNewChat();
              if (onCloseMobile) onCloseMobile();
            }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '10px 14px',
              backgroundColor: 'var(--accent-primary)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 500,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'background-color 0.15s ease',
            }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'var(--accent-hover)')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'var(--accent-primary)')}
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversations List */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '4px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
          }}
        >
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: 'var(--text-muted)',
              padding: '8px 10px 4px',
              letterSpacing: '0.5px',
            }}
          >
            Conversations
          </div>

          {conversations.length === 0 ? (
            <div
              style={{
                padding: '24px 12px',
                textAlign: 'center',
                fontSize: '12px',
                color: 'var(--text-muted)',
              }}
            >
              No conversations yet. Start typing to create one.
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = conv.id === currentConvId;
              const isConfirming = confirmDeleteId === conv.id;

              return (
                <div
                  key={conv.id}
                  onClick={() => {
                    onSelectConversation(conv.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    backgroundColor: isSelected ? 'var(--bg-card)' : 'transparent',
                    border: isSelected ? '1px solid var(--border-active)' : '1px solid transparent',
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseOver={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(23, 34, 59, 0.5)';
                  }}
                  onMouseOut={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <MessageSquare size={14} style={{ flexShrink: 0, opacity: isSelected ? 1 : 0.6 }} />
                    <span
                      style={{
                        fontSize: '13px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: '170px',
                      }}
                    >
                      {conv.title || 'Untitled Chat'}
                    </span>
                  </div>

                  {/* Delete Button / Confirmation */}
                  <div style={{ display: 'flex', alignItems: 'center' }} onClick={(e) => e.stopPropagation()}>
                    {isConfirming ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <button
                          onClick={() => {
                            onDeleteConversation(conv.id);
                            setConfirmDeleteId(null);
                          }}
                          style={{
                            padding: '2px 6px',
                            fontSize: '10px',
                            backgroundColor: 'var(--status-error)',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          Del
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          style={{
                            padding: '2px 6px',
                            fontSize: '10px',
                            backgroundColor: 'var(--border-subtle)',
                            color: 'var(--text-secondary)',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(conv.id)}
                        title="Delete chat"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          opacity: isSelected ? 0.8 : 0.4,
                        }}
                        onMouseOver={(e) => (e.currentTarget.style.opacity = '1')}
                        onMouseOut={(e) => (e.currentTarget.style.opacity = isSelected ? '0.8' : '0.4')}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer: Live Agent & Desktop Connection Status */}
        <div
          style={{
            padding: '14px 16px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(11, 15, 25, 0.4)',
            fontSize: '12px',
          }}
        >
          {/* Status badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {getStatusIcon()}
              <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>
                {getStatusText()}
              </span>
            </div>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor: 'var(--border-subtle)',
                color: 'var(--text-muted)',
              }}
            >
              {health?.desktop_session?.display || ':0'}
            </span>
          </div>

          {/* Model info */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Cpu size={12} />
              <span>Model</span>
            </div>
            <span
              style={{
                color: 'var(--text-secondary)',
                fontWeight: 500,
              }}
            >
              {health?.gemini?.default_model || 'gemini-3.1-flash-lite'}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
