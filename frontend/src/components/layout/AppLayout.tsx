import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { fetchJobStatus } from "@/api/ocr";
import AppHeader from "@/components/layout/AppHeader";
import AppSidebar from "@/components/layout/AppSidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useOcrStore } from "@/store/ocrStore";
import { useUiStore } from "@/store/uiStore";

function OcrBackgroundPoller() {
  const { activeJobId, activeRecordId, clearActiveJob } = useOcrStore();
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ["ocr-status-bg", activeJobId],
    queryFn: () => fetchJobStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "DONE" || status === "FAILED") return false;
      return 3000;
    },
  });

  useEffect(() => {
    if (!data) return;
    if (data.status === "DONE" && activeRecordId) {
      clearActiveJob();
      toast.success("OCR 처리가 완료됐어요!", {
        description: "결과를 확인해보세요.",
        action: {
          label: "결과 보기",
          onClick: () => navigate(`/upload/result/${activeRecordId}`),
        },
        duration: 8000,
      });
    } else if (data.status === "FAILED") {
      clearActiveJob();
      toast.error("OCR 처리에 실패했어요.", { description: "다시 업로드해 주세요." });
    }
  }, [data?.status, activeRecordId, clearActiveJob, navigate]);

  return null;
}

export default function AppLayout() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUiStore((s) => s.setSidebarCollapsed);

  return (
    <SidebarProvider open={!collapsed} onOpenChange={(open) => setCollapsed(!open)}>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
      <OcrBackgroundPoller />
    </SidebarProvider>
  );
}
