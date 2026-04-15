import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./Layout";
import RequireAuth from "./components/RequireAuth";
import CreateTask from "./pages/CreateTask";
import LoginPage from "./pages/Login";
import TaskList from "./pages/TaskList";
import ReviewEditor from "./pages/ReviewEditor";
import SettingsConfig from "./pages/SettingsConfig";
import ChatPage from "./pages/Chat";
import MaterialsPage from "./pages/Materials";
import { isAuthenticated } from "./lib/auth";

function FallbackRoute() {
  return <Navigate to={isAuthenticated() ? "/create" : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/create" replace />} />
          <Route path="/create" element={<CreateTask />} />
          <Route path="/tasks" element={<TaskList />} />
          <Route path="/review" element={<ReviewEditor />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/settings" element={<SettingsConfig />} />
        </Route>
      </Route>

      <Route path="*" element={<FallbackRoute />} />
    </Routes>
  );
}
