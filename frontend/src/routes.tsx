import { createBrowserRouter, Navigate } from "react-router-dom";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import Chat from "@/pages/Chat";
import KakaoCallback from "@/pages/KakaoCallback";
import Login from "@/pages/Login";
import NotFound from "@/pages/NotFound";

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/auth/kakao/callback", element: <KakaoCallback /> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/", element: <Navigate to="/chat" replace /> },
      { path: "/chat", element: <Chat /> },
      { path: "/chat/:sessionId", element: <Chat /> },
    ],
  },
  { path: "*", element: <NotFound /> },
]);
