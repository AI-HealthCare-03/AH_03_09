import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OcrStore {
  activeJobId: string | null;
  activeRecordId: number | null;
  setActiveJob: (jobId: string, recordId: number) => void;
  clearActiveJob: () => void;
}

export const useOcrStore = create<OcrStore>()(
  persist(
    (set) => ({
      activeJobId: null,
      activeRecordId: null,
      setActiveJob: (jobId, recordId) => set({ activeJobId: jobId, activeRecordId: recordId }),
      clearActiveJob: () => set({ activeJobId: null, activeRecordId: null }),
    }),
    { name: "ocr-store" },
  ),
);
