import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import UserChat from "./pages/UserChat";
import DevChat from "./pages/DevChat";
import LogViewer from "./pages/LogViewer";
import DevLogin from "./pages/DevLogin";
import MapPage from "./pages/MapPage";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import Features from "./pages/Features";
import Changelog from "./pages/Changelog";
import MyReport from "./pages/MyReport";
import MyLogs from "./pages/MyLogs";
import AuthCallback from "./pages/AuthCallback";
import Roadmap from "./pages/Roadmap";
import RequireDevAuth from "./components/RequireDevAuth";
import { CursorGlow } from "./components/CursorGlow";
import { ToastProvider } from "./components/ToastProvider";
import { AuthProvider } from "./contexts/AuthContext";

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/user" element={<UserChat />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/features" element={<Features />} />
        <Route path="/dev/login" element={<DevLogin />} />
        <Route path="/dev" element={<RequireDevAuth><DevChat /></RequireDevAuth>} />
        <Route path="/dev/logs" element={<RequireDevAuth><LogViewer /></RequireDevAuth>} />
        <Route path="/changelog" element={<Changelog />} />
        <Route path="/my-report" element={<MyReport />} />
        <Route path="/my-logs" element={<MyLogs />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/roadmap" element={<Roadmap />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CursorGlow />
        <ToastProvider />
        <AnimatedRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
