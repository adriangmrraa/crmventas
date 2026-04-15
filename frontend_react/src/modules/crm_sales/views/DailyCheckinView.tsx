/**
 * DailyCheckinView — SPEC-05: Daily check-in/check-out for sellers + CEO panel.
 */
import { useState, useEffect } from 'react';
import { Clock, CheckCircle, BarChart3 } from 'lucide-react';
import api from '../../../api/axios';
import { useTranslation } from '../../../context/LanguageContext';
import { useAuth } from '../../../context/AuthContext';

const API = '/admin/core/checkin';

export default function DailyCheckinView() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isCeo = user?.role === 'ceo' || user?.role === 'admin';
  const [checkin, setCheckin] = useState<any>(null);
  const [ceoData, setCeoData] = useState<any>(null);
  const [planeadas, setPlaneadas] = useState(15);
  const [logradas, setLogradas] = useState(0);
  const [contactos, setContactos] = useState(0);
  const [notas, setNotas] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        if (isCeo) {
          const res = await api.get(`${API}/ceo/today`);
          setCeoData(res.data);
        } else {
          const res = await api.get(`${API}/today`);
          if (res.data?.id) setCheckin(res.data);
        }
      } catch {}
      setLoading(false);
    })();
  }, [isCeo]);

  const handleCheckin = async () => {
    try {
      const res = await api.post(`${API}/`, { llamadas_planeadas: planeadas });
      setCheckin(res.data);
    } catch {}
  };

  const handleCheckout = async () => {
    if (!checkin?.id) return;
    try {
      const res = await api.post(`${API}/${checkin.id}/checkout`, { llamadas_logradas: logradas, contactos_logrados: contactos, notas });
      setCheckin(res.data);
    } catch {}
  };

  const pctColor = (pct: number | null) => {
    if (pct === null || pct === undefined) return 'text-white/30';
    if (pct >= 80) return 'text-green-400';
    if (pct >= 50) return 'text-amber-400';
    return 'text-red-400';
  };

  if (loading) return <div className="h-full flex items-center justify-center text-white/40">{t('common.loading')}</div>;

  // CEO Panel
  if (isCeo && ceoData) {
    return (
      <div className="flex flex-col h-full">
        <div className="shrink-0 px-4 py-4 border-b border-white/[0.06]">
          <h1 className="text-lg font-semibold text-white">{t('checkin.ceo_panel')}</h1>
          <div className="flex gap-4 mt-2 text-sm">
            <span className="text-white/50">{t('checkin.total')}: {ceoData.total_sellers}</span>
            <span className="text-blue-400">{t('checkin.active')}: {ceoData.con_checkin}</span>
            <span className="text-green-400">{t('checkin.completed')}: {ceoData.completados}</span>
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-2">
          {ceoData.vendedores.map((v: any) => (
            <div key={v.seller_id} className="flex items-center justify-between px-4 py-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <div>
                <p className="text-sm font-medium text-white">{v.nombre}</p>
                <p className="text-xs text-white/40">{v.estado === 'sin_checkin' ? t('checkin.no_checkin') : v.estado}</p>
              </div>
              {v.llamadas_planeadas && (
                <div className="text-right">
                  <p className="text-sm text-white/70">{v.llamadas_logradas ?? '—'}/{v.llamadas_planeadas}</p>
                  <p className={`text-xs font-medium ${pctColor(v.cumplimiento_pct)}`}>
                    {v.cumplimiento_pct != null ? `${v.cumplimiento_pct}%` : '—'}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Seller View
  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 px-4 py-4 border-b border-white/[0.06]">
        <h1 className="text-lg font-semibold text-white">{t('checkin.title')}</h1>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {!checkin ? (
          <div className="max-w-sm mx-auto space-y-4">
            <p className="text-white/60 text-sm">{t('checkin.start_day')}</p>
            <div>
              <label className="block text-sm text-white/70 mb-1">{t('checkin.planned_calls')}</label>
              <input type="number" value={planeadas} onChange={e => setPlaneadas(Number(e.target.value))} min={1}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm" />
            </div>
            <button onClick={handleCheckin} className="w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2">
              <Clock size={16} /> {t('checkin.do_checkin')}
            </button>
          </div>
        ) : checkin.estado === 'active' ? (
          <div className="max-w-sm mx-auto space-y-4">
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-center">
              <p className="text-blue-400 text-sm font-medium">{t('checkin.in_progress')}</p>
              <p className="text-white/50 text-xs mt-1">{t('checkin.planned')}: {checkin.llamadas_planeadas}</p>
            </div>
            <div>
              <label className="block text-sm text-white/70 mb-1">{t('checkin.achieved_calls')}</label>
              <input type="number" value={logradas} onChange={e => setLogradas(Number(e.target.value))} min={0}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm text-white/70 mb-1">{t('checkin.contacts')}</label>
              <input type="number" value={contactos} onChange={e => setContactos(Number(e.target.value))} min={0}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm text-white/70 mb-1">{t('checkin.notes')}</label>
              <textarea value={notas} onChange={e => setNotas(e.target.value)} rows={3}
                className="w-full px-3 py-2 bg-white/[0.05] text-white border border-white/[0.08] rounded-lg text-sm resize-none" />
            </div>
            <button onClick={handleCheckout} className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2">
              <CheckCircle size={16} /> {t('checkin.do_checkout')}
            </button>
          </div>
        ) : (
          <div className="max-w-sm mx-auto p-4 bg-white/[0.03] border border-white/[0.06] rounded-lg space-y-3">
            <p className="text-green-400 font-medium text-sm flex items-center gap-2"><CheckCircle size={16} /> {t('checkin.day_completed')}</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-white/50">{t('checkin.planned')}:</span> <span className="text-white">{checkin.llamadas_planeadas}</span></div>
              <div><span className="text-white/50">{t('checkin.achieved')}:</span> <span className="text-white">{checkin.llamadas_logradas}</span></div>
              <div><span className="text-white/50">{t('checkin.contacts')}:</span> <span className="text-white">{checkin.contactos_logrados}</span></div>
              <div><span className="text-white/50">{t('checkin.compliance')}:</span> <span className={pctColor(checkin.cumplimiento_pct)}>{checkin.cumplimiento_pct}%</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
