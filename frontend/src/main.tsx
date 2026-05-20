import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import App from "./App.tsx";
import "./styles/globals.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
