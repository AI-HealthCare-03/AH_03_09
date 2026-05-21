import { createBrowserRouter } from "react-router-dom";
import OnboardingGate from "@/components/common/OnboardingGate";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import AppLayout from "@/components/layout/AppLayout";
import ChatLayout from "@/components/layout/ChatLayout";
import Chat from "@/pages/Chat";
import HealthGuide from "@/pages/HealthGuide";
import Home from "@/pages/Home";
import KakaoCallback from "@/pages/KakaoCallback";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import MyDocuments from "@/pages/MyDocuments";
import NotFound from "@/pages/NotFound";
import Onboarding from "@/pages/Onboarding";
import Settings from "@/pages/Settings";
import Terms from "@/pages/Terms";
import Upload from "@/pages/Upload";
import UploadProcessing from "@/pages/UploadProcessing";
import UploadResult from "@/pages/UploadResult";
import UploadReview from "@/pages/UploadReview";

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/login", element: <Login /> },
  { path: "/auth/kakao/callback", element: <KakaoCallback /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <OnboardingGate />,
        children: [
          { path: "/terms", element: <Terms /> },
          { path: "/onboarding", element: <Onboarding /> },
          {
            element: <AppLayout />,
            children: [
              { path: "/home", element: <Home /> },
              { path: "/upload", element: <Upload /> },
              { path: "/upload/processing/:jobId", element: <UploadProcessing /> },
              { path: "/upload/review/:jobId", element: <UploadReview /> },
              { path: "/upload/result/:recordId", element: <UploadResult /> },
              { path: "/documents", element: <MyDocuments /> },
              { path: "/health-guide", element: <HealthGuide /> },
              { path: "/settings", element: <Settings /> },
            ],
          },
          {
            element: <ChatLayout />,
            children: [
              { path: "/chat", element: <Chat /> },
              { path: "/chat/:sessionId", element: <Chat /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
]);
