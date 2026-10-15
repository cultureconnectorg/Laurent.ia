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
  // Detect the backend-owned Google OIDC result synchronously during render.
  if (location.hash?.includes("auth=success") || location.hash?.includes("auth=error")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<LaurentIA />} />
      <Route path="/laurentia" element={<LaurentIA />} />
      <Route path="/me/reports" element={<ReportsPage />} />
      <Route path="/admin/orchestrator" element={<AdminOrchestratorPage />} />
      <Route path="/admin/reports" element={<AdminReportsPage />} />
      <Route path="/echo/:publicId" element={<EchoPage />} />
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
