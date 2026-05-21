import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

export default function Landing() {
  const accessToken = useAuthStore((s) => s.accessToken);
  return <Navigate to={accessToken ? "/home" : "/login"} replace />;
}
