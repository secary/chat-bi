import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { ChatPage } from './pages/ChatPage';
import { SkillAdminPage } from './pages/SkillAdminPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { LlmConfigPage } from './pages/LlmConfigPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/skills" element={<SkillAdminPage />} />
          <Route path="/data-sources" element={<DataSourcesPage />} />
          <Route path="/llm" element={<LlmConfigPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
