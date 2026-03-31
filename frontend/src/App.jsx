import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import UserChat from "./pages/UserChat";
import DevChat from "./pages/DevChat";
import LogViewer from "./pages/LogViewer";
import DevLogin from "./pages/DevLogin";
import MapPage from "./pages/MapPage";
import RequireDevAuth from "./components/RequireDevAuth";
import { CursorGlow } from "./components/CursorGlow";
import { ToastProvider } from "./components/ToastProvider";
import { KeyboardShortcuts } from "./components/KeyboardShortcuts";

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/user" element={<UserChat />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/dev/login" element={<DevLogin />} />
        <Route path="/dev" element={<RequireDevAuth><DevChat /></RequireDevAuth>} />
        <Route path="/dev/logs" element={<RequireDevAuth><LogViewer /></RequireDevAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <CursorGlow />
      <ToastProvider />
      <KeyboardShortcuts />
      <AnimatedRoutes />
    </BrowserRouter>
  );
}
