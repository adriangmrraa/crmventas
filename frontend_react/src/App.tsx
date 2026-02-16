import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import DashboardView from './views/DashboardView';
import ChatsView from './views/ChatsView';
import LoginView from './views/LoginView';
import LandingView from './views/LandingView';
import UserApprovalView from './views/UserApprovalView';
import ProfileView from './views/ProfileView';
import ClinicsView from './views/ClinicsView';
import ConfigView from './views/ConfigView';
import LeadsView from './modules/crm_sales/views/LeadsView';
import LeadDetailView from './modules/crm_sales/views/LeadDetailView';
import SellersView from './modules/crm_sales/views/SellersView';
import ClientsView from './modules/crm_sales/views/ClientsView';
import ClientDetailView from './modules/crm_sales/views/ClientDetailView';
import CrmAgendaView from './modules/crm_sales/views/CrmAgendaView';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <Router>
      <AuthProvider>
        <LanguageProvider>
          <Routes>
            <Route path="/login" element={<LoginView />} />
            <Route path="/demo" element={<LandingView />} />

            <Route path="/*" element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route index element={<DashboardView />} />
                    <Route path="agenda" element={<Navigate to="/crm/agenda" replace />} />
                    <Route path="pacientes" element={<Navigate to="/crm/clientes" replace />} />
                    <Route path="pacientes/:id" element={<Navigate to="/crm/clientes" replace />} />
                    <Route path="chats" element={<ChatsView />} />
                    <Route path="aprobaciones" element={
                      <ProtectedRoute allowedRoles={['ceo']}>
                        <UserApprovalView />
                      </ProtectedRoute>
                    } />
                    <Route path="sedes" element={
                      <ProtectedRoute allowedRoles={['ceo']}>
                        <ClinicsView />
                      </ProtectedRoute>
                    } />
                    <Route path="configuracion" element={
                      <ProtectedRoute allowedRoles={['ceo']}>
                        <ConfigView />
                      </ProtectedRoute>
                    } />
                    <Route path="crm/agenda" element={<CrmAgendaView />} />
                    <Route path="crm/leads" element={<LeadsView />} />
                    <Route path="crm/leads/:id" element={<LeadDetailView />} />
                    <Route path="crm/clientes" element={<ClientsView />} />
                    <Route path="crm/clientes/:id" element={<ClientDetailView />} />
                    <Route path="crm/vendedores" element={
                      <ProtectedRoute allowedRoles={['ceo']}>
                        <SellersView />
                      </ProtectedRoute>
                    } />
                    <Route path="perfil" element={<ProfileView />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            } />
          </Routes>
        </LanguageProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
