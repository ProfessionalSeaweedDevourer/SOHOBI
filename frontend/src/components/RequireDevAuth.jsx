import { Navigate, useLocation } from "react-router-dom";
import { isDevAuthenticated } from "../utils/devAuth";

export default function RequireDevAuth({ children }) {
  const location = useLocation();
  if (!isDevAuthenticated()) {
    return <Navigate to="/dev/login" state={{ from: location }} replace />;
  }
  return children;
}
