import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AppLayout } from './components/AppLayout';
import { RequireAuth } from './components/RequireAuth';
import { ChatPage } from './pages/ChatPage';
import { DashboardPage } from './pages/DashboardPage';
import { SkillAdminPage } from './pages/SkillAdminPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { LlmConfigPage } from './pages/LlmConfigPage';
import { LoginPage } from './pages/LoginPage';
import { UserAdminPage } from './pages/UserAdminPage';
import { MultiAgentsAdminPage } from './pages/MultiAgentsAdminPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<ChatPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/multi-agents" element={<MultiAgentsAdminPage />} />
              <Route path="/skills" element={<SkillAdminPage />} />
              <Route path="/data-sources" element={<DataSourcesPage />} />
              <Route path="/llm" element={<LlmConfigPage />} />
              <Route path="/users" element={<UserAdminPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
