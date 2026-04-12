import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./Layout";
import CreateTask from "./pages/CreateTask";
import TaskList from "./pages/TaskList";
import ReviewEditor from "./pages/ReviewEditor";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/create" replace />} />
        <Route path="/create" element={<CreateTask />} />
        <Route path="/tasks" element={<TaskList />} />
        <Route path="/review" element={<ReviewEditor />} />
      </Route>
    </Routes>
  );
}
