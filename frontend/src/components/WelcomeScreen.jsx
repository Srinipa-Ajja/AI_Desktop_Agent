import React from 'react';
import { Monitor, Camera, AppWindow, Play, Terminal, HelpCircle, Layers } from 'lucide-react';

export default function WelcomeScreen({ onSelectPrompt }) {
  const examplePrompts = [
    {
      title: 'Inspect Open Windows',
      prompt: 'What windows are currently open on my desktop?',
      icon: <AppWindow size={18} color="#60a5fa" />,
      desc: 'Queries the AT-SPI2 accessibility tree for all active application windows',
    },
    {
      title: 'Capture Desktop Screenshot',
      prompt: 'Take a screenshot of the desktop and describe what you see.',
      icon: <Camera size={18} color="#a78bfa" />,
      desc: 'Captures full X11 display and uses Gemini multimodal vision to analyze it',
    },
    {
      title: 'Launch an Application',
      prompt: 'Open the Firefox browser',
      icon: <Play size={18} color="#34d399" />,
      desc: 'Executes desktop application launcher and checks the updated window list',
    },
    {
      title: 'System & Window Inspection',
      prompt: 'List the active applications and tell me what the focused window is',
      icon: <Layers size={18} color="#f59e0b" />,
      desc: 'Inspects window hierarchy, accessibility state, and active focus',
    },
  ];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        maxWidth: '720px',
        margin: 'auto',
        padding: '30px 20px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-active)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          boxShadow: '0 8px 24px rgba(46,73,144,0.35)',
        }}
      >
        <Monitor size={32} color="#9cadd4" />
      </div>

      <h2
        style={{
          fontSize: '24px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.4px',
          marginBottom: '8px',
        }}
      >
        AI Desktop Assistant
      </h2>

      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          maxWidth: '540px',
          marginBottom: '32px',
        }}
      >
        Perceive and operate your Linux desktop using Google Gemini paired with Microsoft Hybrid Computer Use (HCU). Type a natural language command below or try one of the examples.
      </p>

      {/* Grid of example cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '12px',
          width: '100%',
        }}
      >
        {examplePrompts.map((item, idx) => (
          <div
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            style={{
              padding: '16px',
              borderRadius: '10px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              textAlign: 'left',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
              e.currentTarget.style.borderColor = 'var(--border-active)';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--bg-card)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              {item.icon}
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                {item.title}
              </div>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
              {item.desc}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
