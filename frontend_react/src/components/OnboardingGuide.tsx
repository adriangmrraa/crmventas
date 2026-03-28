import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import {
  X, ChevronRight, ChevronLeft, CheckCircle, Sparkles,
  Home, Users, MessageSquare, ShieldCheck, BarChart3,
  Calendar, User, Megaphone, Settings, Target, BookOpen, Search, Layout
} from 'lucide-react';

interface GuideStep {
  title: string;
  description: string;
  benefit: string;
  tip?: string;
}

interface PageGuide {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  steps: GuideStep[];
}

const GUIDES: Record<string, PageGuide> = {
  '/': {
    icon: <Home size={20} />,
    title: 'Dashboard CRM',
    subtitle: 'Tu centro de mando de ventas',
    steps: [
      { title: 'KPIs de ventas', description: 'Conversaciones IA, turnos agendados, urgencias y revenue confirmado. Todo actualizado en tiempo real.', benefit: 'Toma decisiones sin buscar en multiples pantallas.', tip: 'Usa los filtros Semanal/Mensual/Historico para comparar periodos.' },
      { title: 'Eficiencia de IA', description: 'Ve cuantas derivaciones vs citas concretadas genera la IA. Mide si el agente esta convirtiendo.', benefit: 'Optimiza el prompt del agente basandote en datos reales.' },
      { title: 'Tabla de actividad', description: 'Ultimos leads, citas y acciones del equipo. Cada fila es clickeable para ir al detalle.', benefit: 'Nunca te pierdas lo que paso mientras no estabas.' },
    ],
  },
  '/crm/leads': {
    icon: <Users size={20} />,
    title: 'Leads',
    subtitle: 'Pipeline de prospectos',
    steps: [
      { title: 'Lista de leads', description: 'Todos tus prospectos con nombre, telefono, estado, vendedor asignado y fecha de creacion. Busqueda instantanea.', benefit: 'Encontra cualquier lead en segundos.' },
      { title: 'Estados del pipeline', description: 'Cada lead tiene un estado: Nuevo, Contactado, Interesado, Negociacion, Cerrado Ganado, Cerrado Perdido. Filtra por estado.', benefit: 'Visualiza tu embudo de ventas.' },
      { title: 'Asignacion de vendedores', description: 'Asigna leads a vendedores manualmente o con reglas automaticas (round-robin, performance, carga).', benefit: 'Distribucion justa y eficiente del trabajo.' },
      { title: 'Acciones masivas', description: 'Selecciona multiples leads y cambia su estado de una vez con el boton de acciones bulk.', benefit: 'Ahorra tiempo en actualizaciones repetitivas.', tip: 'Podes cambiar estado de hasta 50 leads a la vez.' },
    ],
  },
  '/crm/clientes': {
    icon: <Users size={20} />,
    title: 'Clientes',
    subtitle: 'Leads convertidos',
    steps: [
      { title: 'Base de clientes', description: 'Todos los leads que cerraron como "ganado". Historial completo de interacciones.', benefit: 'Contexto completo para upselling y retencion.' },
      { title: 'Ficha del cliente', description: 'Click en un cliente para ver datos, historial de conversaciones, notas y actividad.', benefit: 'Todo en un solo lugar antes de cada llamada.' },
    ],
  },
  '/crm/agenda': {
    icon: <Calendar size={20} />,
    title: 'Agenda de Ventas',
    subtitle: 'Calendario de llamadas y reuniones',
    steps: [
      { title: 'Vista de calendario', description: 'Todas las citas y llamadas agendadas por la IA o manualmente. Vista diaria, semanal, mensual y lista.', benefit: 'Planifica tu dia de ventas de un vistazo.' },
      { title: 'Crear evento', description: 'Click en un horario vacio para crear una llamada, demo o reunion. Asigna a un vendedor.', benefit: 'Agenda rapida sin salir del calendario.' },
      { title: 'Google Calendar sync', description: 'Si esta configurado, los eventos se sincronizan con el calendario del vendedor.', benefit: 'El vendedor ve sus llamadas en el celular.' },
    ],
  },
  '/chats': {
    icon: <MessageSquare size={20} />,
    title: 'Conversaciones',
    subtitle: 'WhatsApp con IA integrada',
    steps: [
      { title: 'Bandeja de chats', description: 'Todas las conversaciones de WhatsApp en un solo lugar. La IA responde automaticamente a los leads.', benefit: 'Atencion 24/7 sin que vos tengas que estar.' },
      { title: 'Modo manual', description: 'Toma control de cualquier conversacion. La IA se silencia por 24h para ese lead.', benefit: 'Interveni cuando lo necesites.' },
      { title: 'Derivacion humana', description: 'Cuando la IA detecta urgencia o el lead pide hablar con alguien, te llega una notificacion.', benefit: 'Nunca pierdas un lead caliente.' },
    ],
  },
  '/crm/prospeccion': {
    icon: <Search size={20} />,
    title: 'Prospeccion',
    subtitle: 'Busqueda activa de leads',
    steps: [
      { title: 'Scraping de prospectos', description: 'Busca negocios en Google Maps por zona y rubro. Importa datos automaticamente.', benefit: 'Genera leads sin publicidad.' },
      { title: 'Datos enriquecidos', description: 'Cada prospecto trae direccion, reviews, sitio web y telefono.', benefit: 'Leads pre-calificados con info real.' },
    ],
  },
  '/crm/vendedores': {
    icon: <ShieldCheck size={20} />,
    title: 'Vendedores',
    subtitle: 'Gestion del equipo de ventas',
    steps: [
      { title: 'Metricas por vendedor', description: 'Conversaciones, leads asignados, tasa de conversion, tiempo de respuesta promedio.', benefit: 'Identifica quien rinde mas y quien necesita coaching.' },
      { title: 'Leaderboard', description: 'Ranking en tiempo real del equipo. Compara por periodo.', benefit: 'Motivacion competitiva para el equipo.' },
      { title: 'Reglas de asignacion', description: 'Configura como se distribuyen los leads: round-robin, por performance o por carga.', benefit: 'Automatiza la distribucion justa.' },
    ],
  },
  '/crm/marketing': {
    icon: <Megaphone size={20} />,
    title: 'Marketing Hub',
    subtitle: 'Meta Ads + atribucion',
    steps: [
      { title: 'Conexion con Meta', description: 'Conecta tu cuenta de Meta Ads para importar campanas, gastos y leads automaticamente.', benefit: 'Datos de marketing sin carga manual.' },
      { title: 'ROI por campana', description: 'Ve cuanto invertiste, cuantos leads llegaron y cuanto revenue genero cada campana.', benefit: 'Sabe que anuncio convierte mejor.' },
      { title: 'Atribucion', description: 'Cada lead queda vinculado al anuncio que lo trajo. First-touch attribution permanente.', benefit: 'Retorno real por peso invertido.' },
    ],
  },
  '/crm/meta-leads': {
    icon: <Target size={20} />,
    title: 'Meta Leads',
    subtitle: 'Leads de formularios Meta',
    steps: [
      { title: 'Leads automaticos', description: 'Los leads que llegan por formularios de Meta Ads aparecen aca automaticamente.', benefit: 'No pierdas ningun prospecto de publicidad.' },
      { title: 'Estado y conversion', description: 'Cada lead tiene estado y se puede asignar a un vendedor para seguimiento.', benefit: 'Pipeline desde el primer contacto.' },
    ],
  },
  '/crm/hsm': {
    icon: <Layout size={20} />,
    title: 'Automatizacion',
    subtitle: 'Plantillas y reglas HSM',
    steps: [
      { title: 'Templates HSM', description: 'Plantillas aprobadas por Meta para enviar mensajes fuera de la ventana de 24h.', benefit: 'Comunicate con leads inactivos.' },
      { title: 'Reglas automaticas', description: 'Recordatorios de cita, recuperacion de leads y seguimiento post-venta.', benefit: 'Reduce no-shows y recupera leads automaticamente.' },
    ],
  },
  '/perfil': {
    icon: <User size={20} />,
    title: 'Mi Perfil',
    subtitle: 'Datos personales',
    steps: [
      { title: 'Datos y Google Calendar', description: 'Nombre, email, contraseña y ID de Google Calendar para sincronizar tu agenda.', benefit: 'Mantene tus datos actualizados.' },
    ],
  },
  '/configuracion': {
    icon: <Settings size={20} />,
    title: 'Configuracion',
    subtitle: 'Integraciones y ajustes',
    steps: [
      { title: 'WhatsApp (YCloud)', description: 'Conecta tu numero de WhatsApp Business para que la IA reciba y envie mensajes.', benefit: 'Atencion automatica por WhatsApp.' },
      { title: 'Meta Ads', description: 'Conecta Meta Business para importar campanas y leads.', benefit: 'Marketing con datos reales.' },
      { title: 'Google Calendar', description: 'Sincroniza la agenda con Google Calendar de cada vendedor.', benefit: 'Vendedores ven sus citas en el celular.' },
    ],
  },
};

interface OnboardingGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

const OnboardingGuide: React.FC<OnboardingGuideProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState<'next' | 'prev'>('next');
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [swipeX, setSwipeX] = useState(0);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const [completedPages, setCompletedPages] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('onboarding_completed') || '[]'); } catch { return []; }
  });

  const currentPath = Object.keys(GUIDES).find(path => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  }) || '/';

  const guide = GUIDES[currentPath];
  useEffect(() => { setCurrentStep(0); }, [currentPath]);

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 8;
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * -8;
    setTilt({ x, y });
  };
  const handlePointerLeave = () => setTilt({ x: 0, y: 0 });

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    setSwipeX(0);
  };
  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const dx = e.touches[0].clientX - touchStartRef.current.x;
    const dy = e.touches[0].clientY - touchStartRef.current.y;
    if (Math.abs(dx) > Math.abs(dy)) setSwipeX(dx * 0.4);
  };
  const handleTouchEnd = () => {
    if (!touchStartRef.current) return;
    if (swipeX < -50) {
      if (currentStep < (guide?.steps.length || 1) - 1) { setDirection('next'); setCurrentStep(s => s + 1); }
      else handleComplete();
    } else if (swipeX > 50 && currentStep > 0) { setDirection('prev'); setCurrentStep(s => s - 1); }
    setSwipeX(0);
    touchStartRef.current = null;
  };

  if (!isOpen || !guide) return null;

  const step = guide.steps[currentStep];
  const isLastStep = currentStep === guide.steps.length - 1;
  const progress = ((currentStep + 1) / guide.steps.length) * 100;

  const goNext = () => { if (!isLastStep) { setDirection('next'); setCurrentStep(s => s + 1); } };
  const goPrev = () => { if (currentStep > 0) { setDirection('prev'); setCurrentStep(s => s - 1); } };
  const handleComplete = () => {
    const updated = [...new Set([...completedPages, currentPath])];
    setCompletedPages(updated);
    localStorage.setItem('onboarding_completed', JSON.stringify(updated));
    onClose();
  };

  const animClass = direction === 'next' ? 'animate-[cardSlideLeft_0.3s_ease-out]' : 'animate-[cardSlideRight_0.3s_ease-out]';

  return (
    <>
      <style>{`
        @keyframes modalIn { from { opacity:0; transform: scale(0.92) translateY(20px); } to { opacity:1; transform: scale(1) translateY(0); } }
        @keyframes cardSlideLeft { from { opacity:0; transform: translateX(40px); } to { opacity:1; transform: translateX(0); } }
        @keyframes cardSlideRight { from { opacity:0; transform: translateX(-40px); } to { opacity:1; transform: translateX(0); } }
      `}</style>

      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[200]" onClick={onClose} />

      <div className="fixed inset-0 z-[201] flex items-center justify-center p-4 pointer-events-none">
        <div
          ref={cardRef}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          className="pointer-events-auto w-full max-w-md bg-[#0c1018]/95 backdrop-blur-2xl border border-white/[0.08] rounded-3xl shadow-2xl shadow-black/40 overflow-hidden"
          style={{
            animation: 'modalIn 0.35s cubic-bezier(0.16,1,0.3,1)',
            transform: `perspective(800px) rotateY(${tilt.x}deg) rotateX(${tilt.y}deg)`,
            transition: 'transform 0.15s ease-out',
          }}
        >
          <div className="px-5 pt-5 pb-3">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400">{guide.icon}</div>
                <div>
                  <h2 className="text-base font-bold text-white leading-tight">{guide.title}</h2>
                  <p className="text-[11px] text-white/35">{guide.subtitle}</p>
                </div>
              </div>
              <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-full bg-white/[0.04] text-white/30 hover:bg-white/[0.08] hover:text-white/60 transition-all active:scale-90">
                <X size={16} />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
              </div>
              <span className="text-[10px] font-bold text-white/25 tabular-nums">{currentStep + 1}/{guide.steps.length}</span>
            </div>
          </div>

          <div className="px-5 pb-2 min-h-[240px] touch-pan-y select-none" onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}>
            <div key={`${currentPath}-${currentStep}`} className={swipeX === 0 ? animClass : ''} style={{ transform: swipeX !== 0 ? `translateX(${swipeX}px)` : undefined, opacity: swipeX !== 0 ? Math.max(0.3, 1 - Math.abs(swipeX) / 200) : undefined, transition: swipeX !== 0 ? 'none' : undefined }}>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-md bg-blue-500 text-white flex items-center justify-center text-xs font-black shadow-md shadow-blue-500/25">{currentStep + 1}</div>
                <h3 className="text-sm font-bold text-white">{step.title}</h3>
              </div>
              <p className="text-[13px] text-white/55 leading-relaxed mb-3">{step.description}</p>
              <div className="bg-emerald-500/[0.06] border border-emerald-500/15 rounded-xl p-3 mb-2 hover:bg-emerald-500/[0.10] transition-colors">
                <div className="flex items-start gap-2">
                  <Sparkles size={14} className="text-emerald-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-emerald-300/70 leading-relaxed">{step.benefit}</p>
                </div>
              </div>
              {step.tip && (
                <div className="bg-amber-500/[0.06] border border-amber-500/15 rounded-xl p-3 hover:bg-amber-500/[0.10] transition-colors">
                  <div className="flex items-start gap-2">
                    <BookOpen size={14} className="text-amber-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-amber-300/70 leading-relaxed">{step.tip}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="px-5 pb-5 pt-2">
            <div className="flex items-center justify-center gap-1 mb-4">
              {guide.steps.map((_, i) => (
                <button key={i} onClick={() => { setDirection(i > currentStep ? 'next' : 'prev'); setCurrentStep(i); }}
                  className={`h-1 rounded-full transition-all duration-300 active:scale-90 ${i === currentStep ? 'w-5 bg-blue-500' : i < currentStep ? 'w-1.5 bg-blue-500/30' : 'w-1.5 bg-white/[0.08]'}`} />
              ))}
            </div>
            <div className="flex items-center justify-between">
              <button onClick={goPrev} disabled={currentStep === 0} className="flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-medium text-white/35 hover:bg-white/[0.04] transition-all disabled:opacity-0 disabled:pointer-events-none active:scale-95">
                <ChevronLeft size={14} /> Anterior
              </button>
              {isLastStep ? (
                <button onClick={handleComplete} className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 transition-all active:scale-95">
                  <CheckCircle size={14} /> Entendido
                </button>
              ) : (
                <button onClick={goNext} className="flex items-center gap-1 px-4 py-2 rounded-xl text-xs font-semibold bg-white/[0.06] text-white/70 border border-white/[0.08] hover:bg-white/[0.10] transition-all active:scale-95">
                  Siguiente <ChevronRight size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default OnboardingGuide;
