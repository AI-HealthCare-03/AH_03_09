import { Navigate } from "react-router-dom";
import { HeroSection } from "@/features/landing/HeroSection";
import { useAuthStore } from "@/store/authStore";

export default function Landing() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }
  return <HeroSection />;
}
