import React, { useState, useEffect } from 'react';
import {
  Filter, Search, Download, Upload, UserPlus, MessageSquare,
  Phone, Mail, Calendar, Target, TrendingUp, Users,
  CheckCircle, XCircle, Clock, AlertCircle, Loader2,
  BarChart3, Facebook, ExternalLink, RefreshCw
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { useTranslation } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import SellerBadge from '../components/SellerBadge';
import SellerSelector from '../components/SellerSelector';

interface MetaLead {
  id: string;
  first_name?: string;
  last_name?: string;
  phone_number: string;
  email?: string;
  status: string;
  lead_source: string;
  campaign_name?: string;
  adset_name?: string;
  ad_name?: string;
  form_name?: string;
  created_at: string;
  assigned_seller_id?: string;
  assigned_seller_name?: string;
  assigned_seller_role?: string;
  notes?: string;
  is_demo?: boolean;
}

const DEMO_LEADS: MetaLead[] = [
  {
    id: 'demo-1',
    first_name: 'Juan',
    last_name: 'Pérez',
    phone_number: '+5491112345678',
    email: 'juanperez@example.com',
    status: 'new',
    lead_source: 'META_ADS',
    campaign_name: 'Campaña Dental Invierno',
    form_name: 'Formulario de Contacto Directo',
    created_at: new Date().toISOString(),
    is_demo: true
  },
  {
    id: 'demo-2',
    first_name: 'María',
    last_name: 'García',
    phone_number: '+5491187654321',
    email: 'mariagarcia@example.com',
    status: 'contacted',
    lead_source: 'META_ADS',
    campaign_name: 'Ortodoncia Invisible',
    form_name: 'Consulta Gratuita',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    is_demo: true
  },
  {
    id: 'demo-3',
    first_name: 'Carlos',
    last_name: 'López',
    phone_number: '+5491100001111',
    email: 'carloslopez@example.com',
    status: 'qualified',
    lead_source: 'META_ADS',
    campaign_name: 'Implantes Demo',
    form_name: 'Interés en Implantes',
    created_at: new Date(Date.now() - 172800000).toISOString(),
    is_demo: true
  }
];

const MetaLeadsView: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [leads, setLeads] = useState<MetaLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [showSellerSelector, setShowSellerSelector] = useState(false);
  const [selectedLeadForAssignment, setSelectedLeadForAssignment] = useState<string | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    new: 0,
    contacted: 0,
    converted: 0,
    today: 0
  });

  useEffect(() => {
    fetchMetaLeads();
  }, [statusFilter, dateFilter]);

  const fetchMetaLeads = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        lead_source: 'META_ADS'
      };

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      if (dateFilter !== 'all') {
        if (dateFilter === 'today') {
          params.created_after = new Date().toISOString().split('T')[0];
        } else if (dateFilter === 'week') {
          const weekAgo = new Date();
          weekAgo.setDate(weekAgo.getDate() - 7);
          params.created_after = weekAgo.toISOString();
        } else if (dateFilter === 'month') {
          const monthAgo = new Date();
          monthAgo.setMonth(monthAgo.getMonth() - 1);
          params.created_after = monthAgo.toISOString();
        }
      }

      const response = await api.get('/admin/core/crm/leads', { params });

      // Robust handling of different API response formats
      let rawLeads: any[] = [];
      if (Array.isArray(response.data)) {
        rawLeads = response.data;
      } else if (response.data && response.data.success) {
        rawLeads = response.data.leads || [];
      } else if (response.data && response.data.leads) {
        rawLeads = response.data.leads;
      } else if (response.data) {
        // Handle single object response if happens
        rawLeads = [response.data];
      }

      const metaLeads = rawLeads.filter((lead: any) =>
        (lead.lead_source === 'META_ADS' || lead.lead_source === 'meta_ads') &&
        (lead.status !== 'deleted')
      );

      // If no real leads and no active filters/search, show demo leads
      if (metaLeads.length === 0 && searchQuery === '' && statusFilter === 'all' && dateFilter === 'all') {
        setLeads(DEMO_LEADS);
        calculateStats(DEMO_LEADS);
      } else {
        setLeads(metaLeads);
        calculateStats(metaLeads);
      }
    } catch (err: any) {
      console.error('Error fetching Meta leads:', err);
      // Don't show technical error if we can fallback to demo data
      if (leads.length === 0) {
        setLeads(DEMO_LEADS);
        calculateStats(DEMO_LEADS);
      } else {
        setError(err.response?.data?.detail || 'Error de conexión con el servidor');
      }
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (leadsData: MetaLead[]) => {
    const today = new Date().toISOString().split('T')[0];

    const statsData = {
      total: leadsData.length,
      new: leadsData.filter(lead => lead.status === 'new').length,
      contacted: leadsData.filter(lead => lead.status === 'contacted').length,
      converted: leadsData.filter(lead => lead.status === 'converted' || lead.status === 'closed_won').length,
      today: leadsData.filter(lead => lead.created_at.startsWith(today)).length
    };

    setStats(statsData);
  };

  const handleAssignSeller = async (leadId: string, sellerId: string, sellerName: string) => {
    try {
      const response = await api.put(`/admin/core/crm/leads/${leadId}`, {
        assigned_seller_id: sellerId
      });

      if (response.data.success) {
        // Actualizar localmente
        setLeads(prev => prev.map(lead =>
          lead.id === leadId
            ? {
              ...lead,
              assigned_seller_id: sellerId,
              assigned_seller_name: sellerName
            }
            : lead
        ));

        setSelectedLeadForAssignment(null);
        setShowSellerSelector(false);

        // Mostrar notificación
        // showToast({ type: 'success', message: `Lead asignado a ${sellerName}` });
      }
    } catch (err: any) {
      console.error('Error assigning seller to lead:', err);
      // showToast({ type: 'error', message: 'Error al asignar lead' });
    }
  };

  const handleBulkAssign = async (sellerId: string, sellerName: string) => {
    if (selectedLeads.length === 0) return;

    try {
      const promises = selectedLeads.map(leadId =>
        api.put(`/admin/core/crm/leads/${leadId}`, {
          assigned_seller_id: sellerId
        })
      );

      await Promise.all(promises);

      // Actualizar localmente
      setLeads(prev => prev.map(lead =>
        selectedLeads.includes(lead.id)
          ? {
            ...lead,
            assigned_seller_id: sellerId,
            assigned_seller_name: sellerName
          }
          : lead
      ));

      setSelectedLeads([]);
      // showToast({ type: 'success', message: `${selectedLeads.length} leads asignados a ${sellerName}` });
    } catch (err: any) {
      console.error('Error in bulk assign:', err);
      // showToast({ type: 'error', message: 'Error en asignación masiva' });
    }
  };

  const handleStatusChange = async (leadId: string, newStatus: string) => {
    try {
      const response = await api.put(`/admin/core/crm/leads/${leadId}`, {
        status: newStatus
      });

      if (response.data.success) {
        setLeads(prev => prev.map(lead =>
          lead.id === leadId ? { ...lead, status: newStatus } : lead
        ));
      }
    } catch (err: any) {
      console.error('Error updating lead status:', err);
    }
  };

  const handleExportCSV = () => {
    const csvContent = [
      ['Nombre', 'Teléfono', 'Email', 'Estado', 'Campaña', 'Formulario', 'Asignado a', 'Fecha'],
      ...leads.map(lead => [
        `${lead.first_name || ''} ${lead.last_name || ''}`.trim() || 'Sin nombre',
        lead.phone_number,
        lead.email || '',
        lead.status,
        lead.campaign_name || '',
        lead.form_name || '',
        lead.assigned_seller_name || 'Sin asignar',
        new Date(lead.created_at).toLocaleDateString()
      ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meta-leads-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const filteredLeads = leads.filter(lead => {
    const matchesSearch = !searchQuery ||
      (lead.first_name?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (lead.last_name?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      lead.phone_number.includes(searchQuery) ||
      (lead.email?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (lead.campaign_name?.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-blue-100 text-blue-700';
      case 'contacted': return 'bg-yellow-100 text-yellow-700';
      case 'qualified': return 'bg-purple-100 text-purple-700';
      case 'converted': return 'bg-green-100 text-green-700';
      case 'closed_won': return 'bg-green-100 text-green-700';
      case 'lost': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'new': return <AlertCircle size={14} />;
      case 'contacted': return <MessageSquare size={14} />;
      case 'qualified': return <Target size={14} />;
      case 'converted': return <CheckCircle size={14} />;
      case 'closed_won': return <CheckCircle size={14} />;
      case 'lost': return <XCircle size={14} />;
      default: return <Clock size={14} />;
    }
  };

  if (loading && leads.length === 0) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="animate-spin mx-auto text-gray-400" size={32} />
        <p className="text-gray-500 text-sm mt-3">Cargando leads de Meta Ads...</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <Facebook size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">FORMULARIO META</h1>
              <p className="text-gray-600">Leads generados desde Meta Ads</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchMetaLeads}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              title="Actualizar"
            >
              <RefreshCw size={20} />
            </button>

            <button
              onClick={handleExportCSV}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <Download size={18} />
              <span className="hidden sm:inline">Exportar CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Leads</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <BarChart3 className="text-blue-500" size={20} />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Nuevos</p>
              <p className="text-2xl font-bold text-gray-900">{stats.new}</p>
            </div>
            <AlertCircle className="text-blue-500" size={20} />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Contactados</p>
              <p className="text-2xl font-bold text-gray-900">{stats.contacted}</p>
            </div>
            <MessageSquare className="text-yellow-500" size={20} />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Convertidos</p>
              <p className="text-2xl font-bold text-gray-900">{stats.converted}</p>
            </div>
            <CheckCircle className="text-green-500" size={20} />
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Hoy</p>
              <p className="text-2xl font-bold text-gray-900">{stats.today}</p>
            </div>
            <Calendar className="text-purple-500" size={20} />
          </div>
        </div>
      </div>

      {/* Filters and Actions */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Buscar por nombre, teléfono, email o campaña..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="all">Todos los estados</option>
                <option value="new">Nuevo</option>
                <option value="contacted">Contactado</option>
                <option value="qualified">Calificado</option>
                <option value="converted">Convertido</option>
                <option value="lost">Perdido</option>
              </select>
            </div>

            <select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              <option value="all">Todo el tiempo</option>
              <option value="today">Hoy</option>
              <option value="week">Esta semana</option>
              <option value="month">Este mes</option>
            </select>

            {selectedLeads.length > 0 && (
              <button
                onClick={() => setShowSellerSelector(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <UserPlus size={18} />
                <span>Asignar ({selectedLeads.length})</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {error ? (
          <div className="p-8 text-center">
            <AlertCircle className="mx-auto text-red-400" size={32} />
            <p className="text-red-500 text-sm mt-3">{error}</p>
            <button
              onClick={fetchMetaLeads}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Reintentar
            </button>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="mx-auto text-gray-300" size={48} />
            <p className="text-gray-500 text-sm mt-3">
              {searchQuery || statusFilter !== 'all' || dateFilter !== 'all'
                ? 'No hay leads que coincidan con los filtros'
                : 'No hay leads de Meta Ads aún'}
            </p>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="mt-3 text-blue-600 hover:text-blue-700"
              >
                Limpiar búsqueda
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedLeads.length === filteredLeads.length && filteredLeads.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedLeads(filteredLeads.map(lead => lead.id));
                        } else {
                          setSelectedLeads([]);
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Campaña
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Asignado a
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedLeads.includes(lead.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedLeads(prev => [...prev, lead.id]);
                          } else {
                            setSelectedLeads(prev => prev.filter(id => id !== lead.id));
                          }
                        }}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900 flex items-center gap-2">
                          {lead.first_name || lead.last_name
                            ? `${lead.first_name || ''} ${lead.last_name || ''}`.trim()
                            : 'Sin nombre'}
                          {lead.is_demo && (
                            <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 text-[10px] font-bold rounded uppercase">
                              Demo
                            </span>
                          )}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Phone size={12} className="text-gray-400" />
                          <span className="text-sm text-gray-500">{lead.phone_number}</span>
                        </div>
                        {lead.email && (
                          <div className="flex items-center gap-2 mt-1">
                            <Mail size={12} className="text-gray-400" />
                            <span className="text-sm text-gray-500">{lead.email}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                          {lead.campaign_name || 'Sin campaña'}
                        </p>
                        <p className="text-xs text-gray-500 truncate max-w-[200px]">
                          {lead.form_name || 'Sin formulario'}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(lead.status)}`}>
                          {getStatusIcon(lead.status)}
                          <span className="ml-1">
                            {lead.status === 'new' ? 'Nuevo' :
                              lead.status === 'contacted' ? 'Contactado' :
                                lead.status === 'qualified' ? 'Calificado' :
                                  lead.status === 'converted' ? 'Convertido' :
                                    lead.status === 'closed_won' ? 'Cerrado' :
                                      lead.status === 'lost' ? 'Perdido' : lead.status}
                          </span>
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {lead.assigned_seller_id ? (
                        <SellerBadge
                          sellerId={lead.assigned_seller_id}
                          sellerName={lead.assigned_seller_name}
                          sellerRole={lead.assigned_seller_role}
                          size="sm"
                          showLabel={true}
                          onClick={() => {
                            setSelectedLeadForAssignment(lead.id);
                            setShowSellerSelector(true);
                          }}
                        />
                      ) : (
                        <button
                          onClick={() => {
                            setSelectedLeadForAssignment(lead.id);
                            setShowSellerSelector(true);
                          }}
                          className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                        >
                          Asignar
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Calendar size={12} className="text-gray-400" />
                        <span className="text-sm text-gray-500">
                          {new Date(lead.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {new Date(lead.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/chats?phone=${encodeURIComponent(lead.phone_number)}`)}
                          className="p-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded"
                          title="Ir al chat"
                        >
                          <MessageSquare size={16} />
                        </button>

                        <button
                          onClick={() => handleStatusChange(lead.id, 'contacted')}
                          className="p-1.5 text-green-600 hover:text-green-700 hover:bg-green-50 rounded"
                          title="Marcar como contactado"
                        >
                          <CheckCircle size={16} />
                        </button>

                        <select
                          value={lead.status}
                          onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                          className="px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                          <option value="new">Nuevo</option>
                          <option value="contacted">Contactado</option>
                          <option value="qualified">Calificado</option>
                          <option value="converted">Convertido</option>
                          <option value="lost">Perdido</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {filteredLeads.length > 0 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Mostrando {filteredLeads.length} de {leads.length} leads
          </p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50">
              Anterior
            </button>
            <span className="px-3 py-1 text-sm bg-blue-600 text-white rounded">1</span>
            <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50">
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Seller Selector Modal */}
      {showSellerSelector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="relative max-w-md w-full">
            <SellerSelector
              phone={selectedLeadForAssignment ?
                leads.find(l => l.id === selectedLeadForAssignment)?.phone_number || '' : ''}
              currentSellerId={selectedLeadForAssignment ?
                leads.find(l => l.id === selectedLeadForAssignment)?.assigned_seller_id : undefined}
              currentSellerName={selectedLeadForAssignment ?
                leads.find(l => l.id === selectedLeadForAssignment)?.assigned_seller_name : undefined}
              currentSellerRole={selectedLeadForAssignment ?
                leads.find(l => l.id === selectedLeadForAssignment)?.assigned_seller_role : undefined}
              onSellerSelected={(sellerId, sellerName) => {
                if (selectedLeadForAssignment) {
                  handleAssignSeller(selectedLeadForAssignment, sellerId, sellerName);
                } else if (selectedLeads.length > 0) {
                  handleBulkAssign(sellerId, sellerName);
                }
              }}
              onCancel={() => {
                setShowSellerSelector(false);
                setSelectedLeadForAssignment(null);
              }}
              showAssignToMe={true}
              showAutoAssign={true}
            />
          </div>
        </div>
      )}

      {/* Info Panel */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-3">
          <Facebook size={20} className="text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-800">Leads de Meta Ads</h3>
            <p className="text-sm text-blue-700 mt-1">
              Esta vista muestra exclusivamente los leads generados desde formularios de Meta Ads.
              Puedes asignarlos a vendedores, cambiar su estado y exportar los datos.
            </p>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="text-xs">
                <span className="font-medium text-blue-800">Total:</span> {stats.total} leads
              </div>
              <div className="text-xs">
                <span className="font-medium text-blue-800">Sin asignar:</span> {leads.filter(l => !l.assigned_seller_id).length}
              </div>
              <div className="text-xs">
                <span className="font-medium text-blue-800">Tasa conversión:</span> {stats.total > 0 ? ((stats.converted / stats.total) * 100).toFixed(1) : 0}%
              </div>
              <div className="text-xs">
                <span className="font-medium text-blue-800">Última actualización:</span> Ahora
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetaLeadsView;
