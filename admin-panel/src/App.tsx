import { Navigate, Route, Routes } from 'react-router-dom';

import ProtectedRoute from './components/ProtectedRoute';
import AdminShell from './components/layout/AdminShell';
import AnalyticsPage from './pages/Analytics';
import BlogPage from './pages/Blog';
import DashboardPage from './pages/Dashboard';
import LoginPage from './pages/Login';
import NotificationsPage from './pages/Notifications';
import OrganizationsPage from './pages/Organizations';
import PaymentsPage from './pages/Payments';
import TeamsProjectsPage from './pages/TeamsProjects';
import UsersPage from './pages/Users';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/panel/login" replace />} />
      <Route path="/panel/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AdminShell />}>
          <Route path="/panel" element={<Navigate to="/panel/dashboard" replace />} />
          <Route path="/panel/dashboard" element={<DashboardPage />} />
          <Route path="/panel/users" element={<UsersPage />} />
          <Route path="/panel/organizations" element={<OrganizationsPage />} />
          <Route path="/panel/teams-projects" element={<TeamsProjectsPage />} />
          <Route path="/panel/payments" element={<PaymentsPage />} />

          <Route element={<ProtectedRoute allowedScopes={['system']} />}>
            <Route path="/panel/analytics" element={<AnalyticsPage />} />
            <Route path="/panel/blog" element={<BlogPage />} />
            <Route path="/panel/notifications" element={<NotificationsPage />} />
          </Route>

          <Route path="/panel/*" element={<Navigate to="/panel/dashboard" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/panel/login" replace />} />
    </Routes>
  );
}
