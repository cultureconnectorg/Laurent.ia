/**
 * MenuDrawer — drawer latéral ouvert via ☰.
 * Contenu : profil utilisateur · Nouvelle conversation · historique sessions · paramètres · logout.
 */
import { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, LogOut, LogIn, MessageSquare, Settings, Trash2, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const MenuDrawer = ({ open, onOpenChange, frekId, onPickSession, onNewSession }) => {
  const { user, isAuthenticated, login, logout, loading: authLoading } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = async () => {
    if (!frekId) return;
    setLoading(true);
    try {
      const url = isAuthenticated
        ? `${API}/laurentia/sessions/list`
        : `${API}/laurentia/sessions/list?frek_id=${encodeURIComponent(frekId)}`;
      const r = await fetch(url, { credentials: "include" });
      if (r.ok) {
        const data = await r.json();
        setSessions(data.sessions || []);
      }
    } catch (_) {}
    setLoading(false);
  };

  useEffect(() => {
    if (open) fetchSessions();
  }, [open, frekId, isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (sid) => {
    try {
      const url = isAuthenticated
        ? `${API}/laurentia/sessions/${sid}`
        : `${API}/laurentia/sessions/${sid}?frek_id=${encodeURIComponent(frekId)}`;
      const r = await fetch(url, { method: "DELETE", credentials: "include" });
      if (r.ok) {
        setSessions((s) => s.filter((x) => x.session_id !== sid));
        toast("Conversation supprimée");
      }
    } catch (_) {
      toast("Erreur suppression");
    }
  };

  const initials = (user?.name || user?.email || "H").slice(0, 2).toUpperCase();
  const displayName = user?.name || (user?.email ? user.email.split("@")[0] : "Mode démo");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="left"
        className="bg-[#0A0F1F] border-r border-white/[0.06] text-[#F1F4FA] w-[88vw] sm:w-[380px] p-0"
        data-testid="menu-drawer"
      >
        <SheetHeader className="px-5 pt-6 pb-4 border-b border-white/[0.06]">
          <SheetTitle className="font-serif italic text-2xl text-[#E7C566] tracking-tight">
            Laurent.ia
          </SheetTitle>
          <SheetDescription className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/40 mt-1">
            Intelligence souveraine
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col h-[calc(100%-92px)]">
          {/* Profil */}
          <div className="px-5 py-4 border-b border-white/[0.06]" data-testid="menu-profile">
            {authLoading ? (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/[0.05] animate-pulse" />
                <div className="flex-1 h-3 bg-white/[0.05] rounded animate-pulse" />
              </div>
            ) : isAuthenticated ? (
              <div className="flex items-center gap-3">
                {user.picture ? (
                  <img src={user.picture} alt={displayName} className="w-10 h-10 rounded-full ring-1 ring-[#E7C566]/30 object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] flex items-center justify-center ring-1 ring-[#E7C566]/30">
                    <span className="font-mono text-xs font-semibold text-white">{initials}</span>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-sans text-sm font-medium text-[#F1F4FA] truncate" data-testid="menu-user-name">{displayName}</div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40 truncate">
                    {user.frek_id}
                  </div>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={login}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full
                  bg-gradient-to-br from-[#2D6FE0] to-[#5BA0FF] text-white font-sans text-sm font-medium
                  shadow-[0_4px_18px_rgba(45,111,224,0.4)] hover:shadow-[0_4px_22px_rgba(45,111,224,0.55)] transition-shadow"
                data-testid="menu-login-btn"
              >
                <LogIn className="w-4 h-4" strokeWidth={2} />
                Connexion avec Google
              </button>
            )}
          </div>

          {/* Action: new conversation */}
          <div className="px-3 py-3">
            <button
              type="button"
              onClick={() => { onNewSession?.(); onOpenChange(false); }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left
                bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] transition-colors"
              data-testid="menu-new-conversation"
            >
              <Plus className="w-4 h-4 text-[#6BA8FF]" strokeWidth={2} />
              <span className="font-sans text-sm text-[#F1F4FA]">Nouvelle conversation</span>
            </button>
          </div>

          {/* Sessions list */}
          <div className="flex-1 min-h-0">
            <div className="px-5 pb-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/35">
              Historique
            </div>
            <ScrollArea className="h-full px-3">
              {loading ? (
                <div className="flex items-center gap-2 px-3 py-4 text-white/40 text-sm">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Chargement…
                </div>
              ) : sessions.length === 0 ? (
                <div className="px-3 py-6 text-center font-mono text-[11px] uppercase tracking-[0.22em] text-white/30" data-testid="menu-empty-state">
                  Aucune conversation
                </div>
              ) : (
                <ul className="space-y-1 pb-24" data-testid="menu-sessions-list">
                  {sessions.map((s) => (
                    <li key={s.session_id}>
                      <div className="group flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/[0.04] transition-colors">
                        <button
                          type="button"
                          onClick={() => { onPickSession?.(s.session_id); onOpenChange(false); }}
                          className="flex-1 min-w-0 flex items-center gap-3 text-left"
                          data-testid={`menu-session-${s.session_id}`}
                        >
                          <MessageSquare className="w-3.5 h-3.5 text-white/40 group-hover:text-[#6BA8FF] flex-shrink-0" strokeWidth={1.6} />
                          <div className="flex-1 min-w-0">
                            <div className="font-sans text-[13px] text-[#F1F4FA] truncate">{s.title}</div>
                            <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-white/30 mt-0.5">
                              {s.message_count} messages
                            </div>
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(s.session_id)}
                          aria-label="Supprimer"
                          className="opacity-0 group-hover:opacity-100 p-1 text-white/40 hover:text-red-400 transition-opacity"
                          data-testid={`menu-delete-${s.session_id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" strokeWidth={1.6} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </ScrollArea>
          </div>

          {/* Footer actions */}
          <div className="border-t border-white/[0.06] px-3 py-3 space-y-1">
            <button
              type="button"
              onClick={() => toast("Paramètres bientôt disponibles")}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left
                hover:bg-white/[0.04] transition-colors text-white/70 hover:text-white"
              data-testid="menu-settings"
            >
              <Settings className="w-4 h-4" strokeWidth={1.6} />
              <span className="font-sans text-sm">Paramètres</span>
            </button>
            {isAuthenticated && (
              <button
                type="button"
                onClick={logout}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left
                  hover:bg-red-500/10 transition-colors text-white/70 hover:text-red-300"
                data-testid="menu-logout-btn"
              >
                <LogOut className="w-4 h-4" strokeWidth={1.6} />
                <span className="font-sans text-sm">Se déconnecter</span>
              </button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default MenuDrawer;
