import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Sparkles, X, Mic, MicOff, Send } from 'lucide-react';
import { BACKEND_URL, getCurrentTenantId } from '../api/axios';

// ============================================
// TYPES
// ============================================

type VoiceState = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
}

interface ToolResult {
  name: string;
  result: string;
  type?: string;
  page?: string;
}

// ============================================
// HELPERS
// ============================================

const HIDDEN_PATHS = ['/login', '/demo', '/privacy', '/terms', '/legal'];

const detectCurrentPage = (pathname: string): string => {
  if (pathname === '/') return 'dashboard';
  if (pathname.includes('agenda')) return 'agenda';
  if (pathname.includes('leads')) return 'leads';
  if (pathname.includes('pipeline')) return 'pipeline';
  if (pathname.includes('clientes')) return 'clientes';
  if (pathname.includes('chats')) return 'chats';
  if (pathname.includes('analytics')) return 'analytics';
  if (pathname.includes('config')) return 'configuracion';
  if (pathname.includes('marketing')) return 'marketing';
  if (pathname.includes('vendedores')) return 'vendedores';
  if (pathname.includes('empresas')) return 'empresas';
  return 'dashboard';
};

const msgId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

// ============================================
// COMPONENT
// ============================================

export const NovaWidget: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // UI state
  const [isOpen, setIsOpen] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [lastTool, setLastTool] = useState<ToolResult | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const transcriptBufferRef = useRef('');
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);

  const currentPage = detectCurrentPage(location.pathname);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ============================================
  // AUDIO PLAYBACK
  // ============================================

  const playAudioChunk = useCallback((arrayBuffer: ArrayBuffer) => {
    if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
      playbackCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      nextPlayTimeRef.current = 0;
    }
    const ctx = playbackCtxRef.current;
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});

    const pcm16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 32768;

    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);

    const startTime = Math.max(ctx.currentTime, nextPlayTimeRef.current);
    src.start(startTime);
    nextPlayTimeRef.current = startTime + buffer.duration;
  }, []);

  // ============================================
  // WEBSOCKET + MIC
  // ============================================

  const disconnect = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    recorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (playbackCtxRef.current && playbackCtxRef.current.state !== 'closed') {
      try { playbackCtxRef.current.close(); } catch (_) { /* ignore */ }
    }
    playbackCtxRef.current = null;
    nextPlayTimeRef.current = 0;
    setVoiceState('idle');
  }, []);

  const connect = useCallback(async () => {
    try {
      setVoiceState('connecting');

      // Get mic access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Build WS URL
      const wsBase = BACKEND_URL.replace(/^http/, 'ws');
      const tenantId = getCurrentTenantId() || '1';
      const token = localStorage.getItem('access_token') || '';
      const wsUrl = `${wsBase}/public/nova/voice?tenant_id=${tenantId}&token=${token}&page=${currentPage}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setVoiceState('listening');

        // Start MediaRecorder to capture audio chunks
        const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
        recorderRef.current = recorder;

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            e.data.arrayBuffer().then(buf => ws.send(buf));
          }
        };

        recorder.start(250); // Send chunks every 250ms
      };

      ws.onmessage = (evt) => {
        // Binary = audio from Nova
        if (evt.data instanceof ArrayBuffer) {
          setVoiceState('speaking');
          playAudioChunk(evt.data);
          return;
        }

        // Text = JSON control messages
        try {
          const msg = JSON.parse(evt.data as string);

          if (msg.type === 'transcript') {
            if (msg.role === 'user') {
              setMessages(prev => [...prev, {
                id: msgId(), role: 'user', text: msg.text, timestamp: Date.now(),
              }]);
            } else if (msg.role === 'assistant') {
              transcriptBufferRef.current += msg.text;
            }
          }

          if (msg.type === 'thinking' || msg.type === 'processing') {
            setVoiceState('thinking');
          }

          if (msg.type === 'tool_result') {
            setLastTool({ name: msg.name, result: msg.result, type: msg.result_type, page: msg.page });
            // Navigation tool
            if (msg.result_type === 'navigation' && msg.page) {
              navigate(msg.page);
            }
          }

          if (msg.type === 'nova_audio_done' || msg.type === 'response_done') {
            if (transcriptBufferRef.current) {
              setMessages(prev => [...prev, {
                id: msgId(), role: 'assistant', text: transcriptBufferRef.current, timestamp: Date.now(),
              }]);
              transcriptBufferRef.current = '';
            }
            setTimeout(() => setVoiceState('listening'), 500);
          }

          if (msg.type === 'user_speech_started') {
            setVoiceState('listening');
          }

          if (msg.type === 'error') {
            console.error('[Nova] Server error:', msg.message);
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onerror = () => {
        console.error('[Nova] WebSocket error');
        disconnect();
      };

      ws.onclose = () => disconnect();

    } catch (err) {
      console.error('[Nova] Failed to start:', err);
      disconnect();
    }
  }, [currentPage, playAudioChunk, disconnect, navigate]);

  // ============================================
  // TEXT CHAT (fallback)
  // ============================================

  const sendTextMessage = useCallback((text: string) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, { id: msgId(), role: 'user', text: text.trim(), timestamp: Date.now() }]);
    setInputText('');

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'conversation.item.create',
        item: { type: 'message', role: 'user', content: [{ type: 'input_text', text: text.trim() }] },
      }));
      wsRef.current.send(JSON.stringify({ type: 'response.create' }));
      setVoiceState('thinking');
    }
  }, []);

  // Toggle voice
  const toggleVoice = () => {
    if (voiceState !== 'idle') {
      disconnect();
    } else {
      connect();
    }
  };

  // Auto-connect when panel opens, disconnect on close
  useEffect(() => {
    if (isOpen && voiceState === 'idle') {
      const t = setTimeout(() => connect(), 400);
      return () => clearTimeout(t);
    }
    if (!isOpen && voiceState !== 'idle') {
      disconnect();
    }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => () => disconnect(), [disconnect]);

  // ============================================
  // RENDER
  // ============================================

  if (HIDDEN_PATHS.some(p => location.pathname.startsWith(p))) return null;

  // Voice state indicator
  const renderVoiceIndicator = () => {
    if (voiceState === 'idle' || voiceState === 'connecting') return null;

    return (
      <div className="px-4 py-2 border-t border-white/5 flex items-center gap-3 flex-shrink-0">
        {voiceState === 'listening' && (
          <div className="flex items-center gap-2 text-violet-300 text-xs">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet-500" />
            </span>
            Escuchando...
          </div>
        )}
        {voiceState === 'thinking' && (
          <div className="flex items-center gap-2 text-amber-300 text-xs">
            <span className="animate-spin w-3 h-3 border border-amber-300 border-t-transparent rounded-full" />
            Procesando...
          </div>
        )}
        {voiceState === 'speaking' && (
          <div className="flex items-center gap-2 text-cyan-300 text-xs">
            <span className="flex gap-[2px] items-end h-3">
              {[1, 2, 3, 4, 5].map(i => (
                <span
                  key={i}
                  className="w-[3px] bg-cyan-400 rounded-full animate-pulse"
                  style={{
                    height: `${6 + Math.random() * 8}px`,
                    animationDelay: `${i * 100}ms`,
                    animationDuration: '0.6s',
                  }}
                />
              ))}
            </span>
            Nova hablando...
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="nova-btn fixed bottom-6 right-6 z-[9998] w-14 h-14 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/25 flex items-center justify-center text-white hover:scale-110 active:scale-90 transition-all duration-200"
          style={{ bottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}
        >
          <Sparkles className="w-6 h-6 nova-icon" />
          <span className="absolute inset-0 rounded-full border-2 border-violet-400/40 animate-[novaPing_3s_ease-out_infinite]" />
        </button>
      )}

      {/* Panel */}
      {isOpen && (
        <>
          {/* Mobile backdrop */}
          <div
            className="lg:hidden fixed inset-0 bg-black/60 z-[9997] backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />

          <div className="fixed inset-0 lg:inset-auto lg:bottom-6 lg:right-6 z-[9998] lg:w-[420px] lg:h-[560px] bg-[#0f0f17] lg:border lg:border-violet-500/20 lg:rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 flex-shrink-0">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-400" />
                <span className="text-sm font-semibold text-white">Nova</span>
                {voiceState === 'connecting' && (
                  <span className="text-[10px] text-slate-500">conectando...</span>
                )}
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
              {messages.length === 0 && (
                <div className="bg-white/5 border border-white/5 rounded-lg p-3 text-sm text-slate-200">
                  Hola, soy Nova. Preguntame lo que necesites sobre tu CRM.
                </div>
              )}
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[80%] rounded-lg p-2.5 text-sm whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-violet-600 text-white rounded-br-sm'
                        : 'bg-white/5 border border-white/5 text-slate-200 rounded-bl-sm'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}

              {/* Tool result card */}
              {lastTool && (
                <div className="bg-violet-500/5 border border-violet-500/15 rounded-lg p-3">
                  <p className="text-[10px] text-violet-400 uppercase tracking-wider mb-1">{lastTool.name}</p>
                  <p className="text-xs text-slate-300 line-clamp-4">{lastTool.result}</p>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Voice state indicator */}
            {renderVoiceIndicator()}

            {/* Input bar */}
            <div className="p-3 border-t border-white/5 flex items-center gap-2 flex-shrink-0">
              <button
                onClick={toggleVoice}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
                  voiceState !== 'idle'
                    ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                    : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                }`}
                title={voiceState !== 'idle' ? 'Detener voz' : 'Activar voz'}
              >
                {voiceState !== 'idle' ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTextMessage(inputText); } }}
                placeholder="Preguntale a Nova..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              />
              <button
                onClick={() => sendTextMessage(inputText)}
                disabled={!inputText.trim()}
                className="w-9 h-9 rounded-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:hover:bg-violet-600 flex items-center justify-center transition-colors flex-shrink-0"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default NovaWidget;
