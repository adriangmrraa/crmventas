import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import CrmDashboardView from './views/CrmDashboardView';
import ChatsView from './views/ChatsView';
import LoginView from './views/LoginView';
import LandingView from './views/LandingView';
import UserApprovalView from './views/UserApprovalView';
import ProfileView from './views/ProfileView';
import CompaniesView from './views/CompaniesView';
import ConfigView from './views/ConfigView';
import LeadsView from './modules/crm_sales/views/LeadsView';
import LeadDetailView from './modules/crm_sales/views/LeadDetailView';
import MetaLeadsView from './views/MetaLeadsView';
import SellersView from './modules/crm_sales/views/SellersView';
import ClientsView from './modules/crm_sales/views/ClientsView';
import ClientDetailView from './modules/crm_sales/views/ClientDetailView';
import CrmAgendaView from './modules/crm_sales/views/CrmAgendaView';
import ProspectingView from './modules/crm_sales/views/ProspectingView';
import KanbanPipelineView from './modules/crm_sales/views/KanbanPipelineView';
import SalesAnalyticsView from './modules/crm_sales/views/SalesAnalyticsView';
import FollowUpQueueView from './modules/crm_sales/views/FollowUpQueueView';
import SetterQueueView from './modules/crm_sales/views/SetterQueueView';
import CloserPanelView from './modules/crm_sales/views/CloserPanelView';
import TeamActivityView from './modules/crm_sales/views/TeamActivityView';
import AuditLogView from './modules/crm_sales/views/AuditLogView';
import SellerPerformanceView from './modules/crm_sales/views/SellerPerformanceView';
import SupervisorDashboard from './modules/crm_sales/views/SupervisorDashboard';
import MarketingHubView from './views/marketing/MarketingHubView';
import MetaTemplatesView from './views/marketing/MetaTemplatesView';
import IntegrationsView from './components/integrations/IntegrationsView';
// Optional Notifications Pages
import NotificationsView from './views/NotificationsView';
// Legal Pages
import PrivacyTermsView from './views/PrivacyTermsView';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { SocketProvider } from './context/SocketContext';
import ProtectedRoute from './components/ProtectedRoute';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <LanguageProvider>
            <SocketProvider>
              <Routes>
                <Route path="/login" element={<LoginView />} />
                <Route path="/demo" element={<LandingView />} />
                <Route path="/legal" element={<PrivacyTermsView />} />
                <Route path="/privacy" element={<PrivacyTermsView />} />
                <Route path="/terms" element={<PrivacyTermsView />} />

                <Route path="/*" element={
                  <ProtectedRoute>
                    <Layout>
                      <Routes>
                        <Route index element={<CrmDashboardView />} />
                        <Route path="agenda" element={<Navigate to="/crm/agenda" replace />} />
                        <Route path="pacientes" element={<Navigate to="/crm/clientes" replace />} />
                        <Route path="pacientes/:id" element={<Navigate to="/crm/clientes" replace />} />
                        <Route path="chats" element={<ChatsView />} />
                        <Route path="aprobaciones" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <UserApprovalView />
                          </ProtectedRoute>
                        } />
                        <Route path="empresas" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <CompaniesView />
                          </ProtectedRoute>
                        } />
                        <Route path="configuracion" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <ConfigView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/agenda" element={<CrmAgendaView />} />
                        <Route path="crm/leads" element={<LeadsView />} />
                        <Route path="crm/pipeline" element={<KanbanPipelineView />} />
                        <Route path="crm/analytics" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <SalesAnalyticsView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/leads/:id" element={<LeadDetailView />} />
                        <Route path="crm/meta-leads" element={
                          <ProtectedRoute allowedRoles={['ceo', 'setter', 'closer', 'secretary']}>
                            <MetaLeadsView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/clientes" element={<ClientsView />} />
                        <Route path="crm/clientes/:id" element={<ClientDetailView />} />
                        <Route path="crm/setter-queue" element={
                          <ProtectedRoute allowedRoles={['ceo', 'setter']}>
                            <SetterQueueView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/closer-panel" element={
                          <ProtectedRoute allowedRoles={['ceo', 'closer']}>
                            <CloserPanelView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/seguimientos" element={
                          <ProtectedRoute allowedRoles={['ceo', 'setter', 'closer']}>
                            <FollowUpQueueView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/prospeccion" element={
                          <ProtectedRoute allowedRoles={['ceo', 'setter', 'closer']}>
                            <ProspectingView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/actividad-equipo" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <TeamActivityView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/auditoria" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <AuditLogView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/vendedores/:userId/performance" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <SellerPerformanceView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/vendedores" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <SellersView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/supervisor" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <SupervisorDashboard />
                          </ProtectedRoute>
                        } />
                        {/* Marketing Routes */}
                        <Route path="crm/marketing" element={
                          <ProtectedRoute allowedRoles={['ceo', 'admin', 'marketing']}>
                            <MarketingHubView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/hsm" element={
                          <ProtectedRoute allowedRoles={['ceo', 'admin', 'setter', 'closer']}>
                            <MetaTemplatesView />
                          </ProtectedRoute>
                        } />
                        <Route path="crm/integraciones" element={
                          <ProtectedRoute allowedRoles={['ceo']}>
                            <IntegrationsView />
                          </ProtectedRoute>
                        } />
                        <Route path="notificaciones" element={<NotificationsView />} />
                        <Route path="perfil" element={<ProfileView />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </Layout>
                  </ProtectedRoute>
                } />
              </Routes>
            </SocketProvider>
          </LanguageProvider>
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
