import { UserIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function AppHeader() {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur">
      <div className="ml-auto flex items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="내 정보"
          onClick={() => navigate("/profile")}
        >
          <UserIcon />
        </Button>
      </div>
    </header>
  );
}
