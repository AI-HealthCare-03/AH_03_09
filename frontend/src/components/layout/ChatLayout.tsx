import { Outlet } from "react-router-dom";

/**
 * Full-screen route group for the chat experience. Intentionally NOT wrapped
 * in AppSidebar — the chat page owns its own session sidebar and sticky input
 * composer, and uses h-dvh directly.
 */
export default function ChatLayout() {
  return <Outlet />;
}
