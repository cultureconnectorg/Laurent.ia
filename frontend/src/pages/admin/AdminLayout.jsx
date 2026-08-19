/**
 * AdminLayout — wrapper commun aux pages admin (auth + role gate + nav).
 */
import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft, BarChart3, Cpu } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export default function AdminLayout({ title, subtitle, children }) {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) { navigate("/"); return; }
    const role = (user?.role || "").toLowerCase();
    if (role !== "founder" && role !== "admin") navigate("/");
  }, [loading, isAuthenticated, user, navigate]);

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-white" data-testid="admin-page">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#0A0A0B]/95 backdrop-blur border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="p-2 -ml-2 rounded-lg hover:bg-white/[0.06] transition-colors text-white/70 hover:text-white"
            data-testid="admin-back-btn"
            aria-label="Retour"
          >
            <ArrowLeft className="w-5 h-5" strokeWidth={1.6} />
          </button>
          <div className="flex-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-[#E7C566]/80">
              Admin · {(user?.role || "").toUpperCase()}
            </div>
            <div className="font-sans text-base font-medium">{title}</div>
            {subtitle && <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/40">{subtitle}</div>}
          </div>
          <nav className="flex rounded-full bg-white/[0.04] p-0.5 border border-white/[0.06]">
            <AdminTab to="/admin/orchestrator" current={pathname} icon={<Cpu className="w-3 h-3" strokeWidth={1.8}/>} label="Orchestrator" testId="tab-orchestrator" />
            <AdminTab to="/admin/reports"      current={pathname} icon={<BarChart3 className="w-3 h-3" strokeWidth={1.8}/>} label="Reports"      testId="tab-reports" />
          </nav>
        </div>
      </div>
      <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">{children}</div>
    </div>
  );
}

function AdminTab({ to, current, icon, label, testId }) {
  const navigate = useNavigate();
  const active = current === to;
  return (
    <button
      onClick={() => navigate(to)}
      data-testid={testId}
      className={`px-3 py-1.5 rounded-full text-[11px] font-mono uppercase tracking-[0.2em] flex items-center gap-1.5 transition-colors ${
        active ? "bg-white text-black" : "text-white/60 hover:text-white"
      }`}
    >
      {icon}{label}
    </button>
  );
}
