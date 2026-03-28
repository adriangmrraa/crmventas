import MetaConnectionPanel from '../components/integrations/MetaConnectionPanel';
import { Plug } from 'lucide-react';

export default function IntegrationsView() {
  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto space-y-8">
      {/* Page header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center text-blue-400">
          <Plug size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Integraciones</h1>
          <p className="text-sm text-white/40">
            Conecta tus canales de comunicacion y plataformas externas al CRM.
          </p>
        </div>
      </div>

      {/* Meta section */}
      <section className="p-6 rounded-3xl bg-[#0d1117] border border-white/[0.06]">
        <MetaConnectionPanel />
      </section>

      {/* Placeholder for future integrations */}
      <section className="p-6 rounded-3xl bg-[#0d1117] border border-white/[0.06] opacity-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-white/20">
            <Plug size={20} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white/40">More integrations coming soon</h3>
            <p className="text-sm text-white/20">Google, Mercado Libre, Shopify, and more.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
