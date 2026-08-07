import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { CallPage } from "./pages/CallPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { SessionsPage } from "./pages/SessionsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TrazaPage } from "./pages/TrazaPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/call" replace />} />
        <Route path="/call" element={<CallPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/traza" element={<TrazaPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
