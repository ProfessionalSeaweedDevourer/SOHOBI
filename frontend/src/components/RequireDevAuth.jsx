import { useState, useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { isDevAuthenticated } from "../utils/devAuth";

export default function RequireDevAuth({ children }) {
  const location = useLocation();
  const [authState, setAuthState] = useState("checking");

  useEffect(() => {
    isDevAuthenticated().then((ok) => setAuthState(ok ? "ok" : "fail"));
  }, []);

  if (authState === "checking") return null;
  if (authState === "fail") {
    return <Navigate to="/dev/login" state={{ from: location }} replace />;
  }
  return children;
}
