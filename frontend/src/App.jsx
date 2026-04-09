import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import UserChat from "./pages/UserChat";
import RequireDevAuth from "./components/RequireDevAuth";
import { CursorGlow } from "./components/CursorGlow";
import { ToastProvider } from "./components/ToastProvider";
import AutoSEO from "./components/AutoSEO";
import { AuthProvider } from "./contexts/AuthContext";
import { LoadingSpinner } from "./components/LoadingSpinner";

const MapPage       = lazy(() => import("./pages/MapPage"));
const LogViewer     = lazy(() => import("./pages/LogViewer"));
const PrivacyPolicy = lazy(() => import("./pages/PrivacyPolicy"));
const Roadmap       = lazy(() => import("./pages/Roadmap"));
const Changelog     = lazy(() => import("./pages/Changelog"));
const MyReport      = lazy(() => import("./pages/MyReport"));
const MyLogs        = lazy(() => import("./pages/MyLogs"));
const Features      = lazy(() => import("./pages/Features"));
const DevHub        = lazy(() => import("./pages/DevHub"));
const DevLogin      = lazy(() => import("./pages/DevLogin"));
const StatsPage     = lazy(() => import("./pages/StatsPage"));
const AuthCallback  = lazy(() => import("./pages/AuthCallback"));

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <AutoSEO />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Landing />} />
          <Route path="/home" element={<Home />} />
          <Route path="/user" element={<UserChat />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/features" element={<Features />} />
          <Route path="/dev/login" element={<DevLogin />} />
          <Route path="/dev" element={<RequireDevAuth><DevHub /></RequireDevAuth>} />
          <Route path="/dev/logs" element={<RequireDevAuth><LogViewer /></RequireDevAuth>} />
          <Route path="/dev/stats" element={<RequireDevAuth><StatsPage /></RequireDevAuth>} />
          <Route path="/changelog" element={<Changelog />} />
          <Route path="/my-report" element={<MyReport />} />
          <Route path="/my-logs" element={<MyLogs />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </Suspense>
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
