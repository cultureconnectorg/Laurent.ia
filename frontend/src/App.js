import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import LaurentIA from "@/pages/LaurentIA";
import AuthCallback from "@/pages/AuthCallback";
import EchoPage from "@/pages/EchoPage";
import ReportsPage from "@/pages/ReportsPage";
import AdminOrchestratorPage from "@/pages/admin/AdminOrchestratorPage";
import AdminReportsPage from "@/pages/admin/AdminReportsPage";

function AppRouter() {
  const location = useLocation();
  // CRITICAL race-condition fix: detect session_id in URL hash *synchronously during render*.
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<LaurentIA />} />
      <Route path="/laurentia" element={<LaurentIA />} />
      <Route path="/me/reports" element={<ReportsPage />} />
      <Route path="/admin/orchestrator" element={<AdminOrchestratorPage />} />
      <Route path="/admin/reports" element={<AdminReportsPage />} />
      <Route path="/echo/:sessionId" element={<EchoPage />} />
    </Routes>
  );
}

function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
      });
    }
  }, []);

  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
      <Toaster theme="dark" position="top-center" />
    </div>
  );
}

export default App;
