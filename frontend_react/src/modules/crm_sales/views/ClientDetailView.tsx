import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, User, Phone, Mail, Trash2, FolderOpen, MessageSquare, FileText, Send, Loader2 } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import type { Client } from './ClientsView';
import DriveExplorer from '../components/drive/DriveExplorer';

const CRM_CLIENTS_BASE = '/admin/core/crm/clients';

export default function ClientDetailView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'data' | 'notes' | 'calls' | 'whatsapp' | 'drive'>('data');
  const [clientNotes, setClientNotes] = useState<any[]>([]);
  const [clientCalls, setClientCalls] = useState<any[]>([]);
  const [tabLoading, setTabLoading] = useState(false);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    status: 'active' as 'active' | 'inactive',
  });

  useEffect(() => {
    if (id) fetchClient();
  }, [id]);

  useEffect(() => {
    if (client) {
      setFormData({
        first_name: client.first_name || '',
        last_name: client.last_name || '',
        email: client.email || '',
        status: (client.status === 'active' || client.status === 'inactive' ? client.status : 'active'),
      });
    }
  }, [client]);

  const fetchClient = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<Client>(`${CRM_CLIENTS_BASE}/${id}`);
      setClient(response.data);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_load');
      setError(String(message));
      setClient(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !client) return;
    try {
      setSaving(true);
      setError(null);
      await api.put(`${CRM_CLIENTS_BASE}/${id}`, {
        first_name: formData.first_name || null,
        last_name: formData.last_name || null,
        email: formData.email || null,
        status: formData.status,
      });
      setClient((prev) => prev ? { ...prev, ...formData } : null);
    } catch (err: unknown) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_save');
      setError(String(message));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm(t('clients.confirm_delete'))) return;
    try {
      await api.delete(`${CRM_CLIENTS_BASE}/${id}`);
      navigate('/crm/clientes', { replace: true });
    } catch (err) {
      const message = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : t('clients.error_delete');
      setError(String(message));
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-white/40">{t('common.loading')}</div>
    );
  }

  if (!client && !loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-white/40">
        <p className="mb-4">{t('clients.not_found')}</p>
        <button onClick={() => navigate('/crm/clientes')} className="text-primary hover:underline font-medium">
          {t('clients.back_to_list')}
        </button>
      </div>
    );
  }

  const displayName = client ? [client.first_name, client.last_name].filter(Boolean).join(' ') || client.phone_number || '—' : '—';

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center justify-between gap-4 p-4 lg:p-6 border-b border-white/[0.06] bg-white/[0.03] shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <button
            type="button"
            onClick={() => navigate('/crm/clientes')}
            className="p-2 rounded-lg hover:bg-white/[0.04] text-white/50 shrink-0"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-white truncate">{displayName}</h1>
            {client && <p className="text-sm text-white/40 truncate">{client.phone_number}</p>}
          </div>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          className="p-2 rounded-lg hover:bg-red-500/10 text-red-400 shrink-0 flex items-center gap-2"
          title={t('common.delete')}
        >
          <Trash2 size={18} />
          <span className="hidden sm:inline text-sm font-medium">{t('common.delete')}</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="shrink-0 flex border-b border-white/[0.06] px-4 lg:px-6">
        <button
          onClick={() => setActiveTab('data')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'data'
              ? 'border-primary text-white'
              : 'border-transparent text-white/50 hover:text-white/70'
          }`}
        >
          <User size={14} className="inline mr-1.5" />
          {t('clients.personal_data')}
        </button>
        <button
          onClick={() => setActiveTab('notes')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'notes' ? 'border-primary text-white' : 'border-transparent text-white/50 hover:text-white/70'
          }`}
        >
          <FileText size={14} className="inline mr-1.5" />
          {t('client360.notes')}
        </button>
        <button
          onClick={() => setActiveTab('calls')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'calls' ? 'border-primary text-white' : 'border-transparent text-white/50 hover:text-white/70'
          }`}
        >
          <Phone size={14} className="inline mr-1.5" />
          {t('client360.calls')}
        </button>
        <button
          onClick={() => setActiveTab('whatsapp')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'whatsapp' ? 'border-primary text-white' : 'border-transparent text-white/50 hover:text-white/70'
          }`}
        >
          <MessageSquare size={14} className="inline mr-1.5" />
          WhatsApp
        </button>
        <button
          onClick={() => setActiveTab('drive')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'drive' ? 'border-primary text-white' : 'border-transparent text-white/50 hover:text-white/70'
          }`}
        >
          <FolderOpen size={14} className="inline mr-1.5" />
          {t('drive.title')}
        </button>
      </div>

      {activeTab === 'notes' && client ? (
        <ClientNotesTab clientPhone={client.phone_number} />
      ) : activeTab === 'calls' && client ? (
        <ClientCallsTab clientPhone={client.phone_number} />
      ) : activeTab === 'whatsapp' && client ? (
        <ClientWhatsAppTab clientPhone={client.phone_number} />
      ) : activeTab === 'drive' && client ? (
        <div className="flex-1 min-h-0">
          <DriveExplorer clientId={client.id} />
        </div>
      ) : (
      <div className="flex-1 min-h-0 overflow-y-auto p-4 lg:p-6">
        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        <form onSubmit={handleSave} className="max-w-lg space-y-6">
          <div>
            <h2 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
              <User size={18} />
              {t('clients.personal_data')}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">{t('clients.first_name')}</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData((f) => ({ ...f, first_name: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">{t('clients.last_name')}</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData((f) => ({ ...f, last_name: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                />
              </div>
              <div className="sm:col-span-2 flex items-center gap-2 text-sm text-white/40">
                <Phone size={16} />
                {client?.phone_number}
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-white/70 mb-1 flex items-center gap-1">
                  <Mail size={14} />
                  {t('clients.email')}
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
                />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-white/70 mb-1">{t('clients.status')}</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData((f) => ({ ...f, status: e.target.value as 'active' | 'inactive' }))}
              className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/50 placeholder:text-white/30"
            >
              <option value="active">{t('clients.status_active')}</option>
              <option value="inactive">{t('clients.status_inactive')}</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 font-medium"
            >
              <Save size={18} />
              {saving ? t('common.saving') : t('common.save_changes')}
            </button>
            <button
              type="button"
              onClick={() => navigate('/crm/clientes')}
              className="px-4 py-2 text-white/70 bg-white/[0.04] rounded-lg hover:bg-white/[0.06] font-medium"
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      </div>
      )}
    </div>
  );
}

// ─── Tab Components ──────────────────────────────────────────────────────────

function ClientNotesTab({ clientPhone }: { clientPhone: string }) {
  const { t } = useTranslation();
  const [notes, setNotes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState('');
  const [leadId, setLeadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        // Find linked lead by phone
        const res = await api.get('/admin/core/crm/leads', { params: { search: clientPhone, limit: 1 } });
        const leads = res.data?.leads || res.data || [];
        if (leads.length > 0) {
          const lid = leads[0].id;
          setLeadId(lid);
          const notesRes = await api.get(`/admin/core/crm/leads/${lid}/notes`);
          setNotes(Array.isArray(notesRes.data) ? notesRes.data : notesRes.data?.notes || []);
        }
      } catch { setError(t('client360.error_loading')); }
      setLoading(false);
    })();
  }, [clientPhone]);

  const handleAddNote = async () => {
    if (!newNote.trim() || !leadId) return;
    try {
      await api.post(`/admin/core/crm/leads/${leadId}/notes`, { content: newNote.trim(), note_type: 'internal' });
      setNewNote('');
      const res = await api.get(`/admin/core/crm/leads/${leadId}/notes`);
      setNotes(Array.isArray(res.data) ? res.data : res.data?.notes || []);
    } catch {}
  };

  if (loading) return <div className="flex-1 flex items-center justify-center p-4"><Loader2 className="animate-spin text-violet-400" size={24} /></div>;
  if (error) return <div className="flex-1 p-4 text-red-400 text-sm">{error}</div>;
  if (!leadId) return <div className="flex-1 p-4 text-white/40 text-sm">{t('client360.no_linked_lead')}</div>;

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {notes.length === 0 ? (
          <p className="text-white/30 text-sm">{t('client360.no_notes')}</p>
        ) : notes.map((note: any, i: number) => (
          <div key={note.id || i} className="p-3 bg-white/[0.03] border border-white/[0.06] rounded-lg">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-violet-400">{note.author_name || note.author_email || 'Sistema'}</span>
              <span className="text-[10px] text-white/30">{new Date(note.created_at).toLocaleString()}</span>
            </div>
            <p className="text-sm text-white/70">{note.content}</p>
          </div>
        ))}
      </div>
      <div className="shrink-0 px-4 py-3 border-t border-white/[0.06] flex gap-2">
        <input value={newNote} onChange={e => setNewNote(e.target.value)} placeholder={t('client360.add_note')}
          onKeyDown={e => e.key === 'Enter' && handleAddNote()}
          className="flex-1 px-3 py-2 bg-white/[0.05] text-white text-sm border border-white/[0.08] rounded-lg" />
        <button onClick={handleAddNote} disabled={!newNote.trim()} className="px-3 py-2 bg-primary text-white rounded-lg disabled:opacity-30"><Send size={16} /></button>
      </div>
    </div>
  );
}

function ClientCallsTab({ clientPhone }: { clientPhone: string }) {
  const { t } = useTranslation();
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/admin/core/team-activity/feed', { params: { limit: 50 } });
        const feed = Array.isArray(res.data) ? res.data : res.data?.items || [];
        setEvents(feed.filter((e: any) => e.event_type?.includes('call') || e.event_type === 'appointment_created'));
      } catch {}
      setLoading(false);
    })();
  }, [clientPhone]);

  if (loading) return <div className="flex-1 flex items-center justify-center p-4"><Loader2 className="animate-spin text-violet-400" size={24} /></div>;

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-2">
      {events.length === 0 ? (
        <p className="text-white/30 text-sm">{t('client360.no_calls')}</p>
      ) : events.map((ev: any, i: number) => (
        <div key={ev.id || i} className="flex items-center gap-3 p-3 bg-white/[0.03] border border-white/[0.06] rounded-lg">
          <Phone size={16} className="text-amber-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white/70">{ev.description || ev.event_type}</p>
            <p className="text-[10px] text-white/30">{ev.actor_name || ''} - {new Date(ev.created_at).toLocaleString()}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function ClientWhatsAppTab({ clientPhone }: { clientPhone: string }) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/admin/core/chat/messages/${clientPhone}`);
        setMessages(Array.isArray(res.data) ? res.data : res.data?.messages || []);
      } catch {}
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [clientPhone]);

  if (loading) return <div className="flex-1 flex items-center justify-center p-4"><Loader2 className="animate-spin text-violet-400" size={24} /></div>;

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-2">
      {messages.length === 0 ? (
        <p className="text-white/30 text-sm">{t('client360.no_whatsapp')}</p>
      ) : messages.map((msg: any, i: number) => (
        <div key={msg.id || i} className={`flex ${msg.role === 'user' || msg.direction === 'inbound' ? '' : 'justify-end'}`}>
          <div className={`max-w-[70%] px-3 py-2 rounded-lg text-sm ${
            msg.role === 'user' || msg.direction === 'inbound'
              ? 'bg-white/[0.04] text-white/70'
              : 'bg-primary/20 text-white/80'
          }`}>
            <p>{msg.content || msg.text || msg.body || ''}</p>
            <p className="text-[10px] text-white/30 mt-1">{new Date(msg.created_at || msg.timestamp).toLocaleTimeString()}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
