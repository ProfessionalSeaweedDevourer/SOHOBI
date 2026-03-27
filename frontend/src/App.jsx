import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import UserChat from "./pages/UserChat";
import DevChat from "./pages/DevChat";
import LogViewer from "./pages/LogViewer";
import DevLogin from "./pages/DevLogin";
import RequireDevAuth from "./components/RequireDevAuth";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/user" element={<UserChat />} />
        <Route path="/dev/login" element={<DevLogin />} />
        <Route path="/dev" element={<RequireDevAuth><DevChat /></RequireDevAuth>} />
        <Route path="/dev/logs" element={<RequireDevAuth><LogViewer /></RequireDevAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
