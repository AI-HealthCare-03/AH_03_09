import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

/**
 * Renders inside ProtectedRoute. Enforces the order:
 *  1. accept terms  → /terms
 *  2. complete onboarding profile → /onboarding
 *  3. enter the app (children render)
 *
 * Already-completed users hitting /terms or /onboarding directly are
 * redirected to /home.
 *
 * TODO(BE): once POST /api/v1/users/onboarding lands, sync these flags from
 * the server response instead of localStorage and migrate existing users.
 */
export default function OnboardingGate() {
  const termsAcceptedAt = useAuthStore((s) => s.termsAcceptedAt);
  const onboardingCompletedAt = useAuthStore((s) => s.onboardingCompletedAt);
  const { pathname } = useLocation();

  const onTerms = pathname === "/terms";
  const onOnboarding = pathname === "/onboarding";

  if (!termsAcceptedAt) {
    return onTerms ? <Outlet /> : <Navigate to="/terms" replace />;
  }

  if (!onboardingCompletedAt) {
    return onOnboarding ? <Outlet /> : <Navigate to="/onboarding" replace />;
  }

  if (onTerms || onOnboarding) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
}
