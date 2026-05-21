import { UserIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ProfileModal from "@/components/common/ProfileModal";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useAuthStore } from "@/store/authStore";

export default function AppHeader() {
  const [profileOpen, setProfileOpen] = useState(false);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background px-4">
      <SidebarTrigger />
      <div className="ml-auto flex items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="내 정보"
          onClick={() => setProfileOpen(true)}
        >
          <UserIcon />
        </Button>
      </div>
      <ProfileModal
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onWithdrawn={() => {
          setProfileOpen(false);
          clear();
          navigate("/login", { replace: true });
        }}
      />
    </header>
  );
}
