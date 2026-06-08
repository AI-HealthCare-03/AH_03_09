import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isOnboarded = useAuthStore((s) => s.isOnboarded);
  const { pathname } = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  if (isOnboarded && pathname === "/onboarding") {
    return <Navigate to="/home" replace />;
  }
  if (!isOnboarded && pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return <Outlet />;
}
