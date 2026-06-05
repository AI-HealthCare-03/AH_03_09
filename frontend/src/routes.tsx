import { createBrowserRouter } from "react-router-dom";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import AppLayout from "@/components/layout/AppLayout";
import ChatLayout from "@/components/layout/ChatLayout";
import Chat from "@/pages/chatbot/Chat";
import ChatPage from "@/pages/ChatPage";
import GuideDemo from "@/pages/GuideDemo";
import HealthGuide from "@/pages/HealthGuide";
import HealthProfile from "@/pages/HealthProfile";
import Home from "@/pages/Home";

import KakaoCallback from "@/pages/KakaoCallback";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Onboarding from "@/pages/Onboarding";
import MyDocuments from "@/pages/MyDocuments";
import NotFound from "@/pages/NotFound";
import Upload from "@/pages/ocr/Upload";
import UploadProcessing from "@/pages/ocr/UploadProcessing";
import UploadResult from "@/pages/ocr/UploadResult";
import UploadReview from "@/pages/ocr/UploadReview";
import Pharmacy from "@/pages/Pharmacy";
import Profile from "@/pages/Profile";
import Settings from "@/pages/Settings";

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  { path: "/login", element: <Login /> },
  { path: "/auth/kakao/callback", element: <KakaoCallback /> },

  {
    element: <ProtectedRoute />,
    children: [
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
          { path: "/health-profile", element: <HealthProfile /> },
          { path: "/pharmacy", element: <Pharmacy /> },
          { path: "/profile", element: <Profile /> },
          { path: "/settings", element: <Settings /> },
        ],
      },
      {
        element: <ChatLayout />,
        children: [
          { path: "/chat", element: <Chat /> },
          { path: "/chat/:sessionId", element: <Chat /> },
          { path: "/chat-v2", element: <ChatPage /> },
        ],
      },
    ],
  },

  { path: "/guide-demo", element: <GuideDemo /> },
  { path: "/health-guide-test", element: <HealthGuide /> },
  { path: "*", element: <NotFound /> },
]);
