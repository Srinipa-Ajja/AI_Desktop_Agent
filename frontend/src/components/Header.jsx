import React from 'react';
import { Menu, RefreshCw, Trash2, Cpu, CheckCircle2, ShieldCheck, Terminal } from 'lucide-react';

export default function Header({
  title,
  agentStatus,
  onOpenMobileSidebar,
  onClearChat,
  onRefreshHealth,
  isTaskRunning,
}) {
  const getStatusColor = (status) => {
    const s = (status || '').toLowerCase();
    if (s.includes('ready') || s.includes('completed')) return 'var(--status-ready)';
    if (s.includes('fail') || s.includes('error')) return 'var(--status-error)';
    if (s.includes('cancel')) return 'var(--status-warn)';
    return 'var(--status-busy)';
  };

  const isAnimated = isTaskRunning || ['understanding', 'executing', 'waiting'].some(k =>
    (agentStatus || '').toLowerCase().includes(k)
  );

  return (
    <header
      style={{
        height: '60px',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-main)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Menu size={20} />
        </button>

        <div>
          <h1
            style={{
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              letterSpacing: '-0.2px',
            }}
          >
            {title || 'Desktop Assistant'}
          </h1>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Agent Status Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '5px 12px',
            borderRadius: '16px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getStatusColor(agentStatus),
              display: 'inline-block',
              boxShadow: `0 0 8px ${getStatusColor(agentStatus)}`,
            }}
            className={isAnimated ? 'animate-pulse-glow' : ''}
          />
          <span style={{ color: 'var(--text-secondary)' }}>
            {agentStatus || 'Ready'}
          </span>
        </div>

        {/* Clear chat button */}
        {onClearChat && (
          <button
            onClick={onClearChat}
            title="Clear this chat"
            style={{
              background: 'none',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px 8px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '12px',
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseOut={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <Trash2 size={14} />
          </button>
        )}

        {/* Refresh health button */}
        {onRefreshHealth && (
          <button
            onClick={onRefreshHealth}
            title="Refresh connection status"
            style={{
              background: 'none',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px 8px',
              display: 'flex',
              alignItems: 'center',
              fontSize: '12px',
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseOut={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <RefreshCw size={14} />
          </button>
        )}
      </div>
    </header>
  );
}
