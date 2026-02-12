import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import DashboardView from './views/DashboardView';
import AgendaView from './modules/dental/views/AgendaView';
import PatientsView from './modules/dental/views/PatientsView';
import PatientDetail from './modules/dental/views/PatientDetail';
import ProfessionalAnalyticsView from './modules/dental/views/ProfessionalAnalyticsView';
import ChatsView from './views/ChatsView';
import TreatmentsView from './modules/dental/views/TreatmentsView';
import LoginView from './views/LoginView';
import LandingView from './views/LandingView';
import UserApprovalView from './views/UserApprovalView';
import ProfileView from './views/ProfileView';
import ClinicsView from './views/ClinicsView';
import ConfigView from './views/ConfigView';
import LeadsView from './modules/crm_sales/views/LeadsView';
import LeadDetailView from './modules/crm_sales/views/LeadDetailView';
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
                    <Route path="agenda" element={<AgendaView />} />
                    <Route path="pacientes" element={<PatientsView />} />
                    <Route path="pacientes/:id" element={<PatientDetail />} />
                    <Route path="chats" element={<ChatsView />} />
                    <Route path="profesionales" element={<Navigate to="/aprobaciones" replace />} />
                    <Route path="analytics/professionals" element={
                      <ProtectedRoute allowedRoles={['ceo']}>
                        <ProfessionalAnalyticsView />
                      </ProtectedRoute>
                    } />
                    <Route path="tratamientos" element={<TreatmentsView />} />
                    <Route path="perfil" element={<ProfileView />} />
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
                    <Route path="crm/leads" element={<LeadsView />} />
                    <Route path="crm/leads/:id" element={<LeadDetailView />} />
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
