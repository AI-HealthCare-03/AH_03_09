import { Navigate } from "react-router-dom";
import { HeroSection } from "@/features/landing/HeroSection";
import { useAuthStore } from "@/store/authStore";

export default function Landing() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isOnboarded = useAuthStore((s) => s.isOnboarded);
  if (isAuthenticated && isOnboarded) {
    return <Navigate to="/home" replace />;
  }
  return <HeroSection />;
}
