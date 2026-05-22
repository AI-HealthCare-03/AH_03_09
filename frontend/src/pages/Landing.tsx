import { Navigate } from "react-router-dom";
import { HeroSection } from "@/features/landing/HeroSection";
import { useAuthStore } from "@/store/authStore";

export default function Landing() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (accessToken) {
    return <Navigate to="/home" replace />;
  }
  return <HeroSection />;
}
