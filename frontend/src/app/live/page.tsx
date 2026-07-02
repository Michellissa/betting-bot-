import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

interface LiveMatch {
  external_id: string;
  source: string;
  match_date: string | null;
  status: string | null;
  status_text: string | null;
  home_team_name: string;
  away_team_name: string;
  home_team_logo: string | null;
  away_team_logo: string | null;
  home_goals: number | null;
  away_goals: number | null;
  result: string | null;
}

function statusBadge(status: string | null, statusText: string | null): { label: string; color: string } {
  if (!status) return { label: "Unknown", color: "bg-zinc-100 text-zinc-600" };
  const s = status.toLowerCase();
  if (s === "live" || s === "inprogress") return { label: "LIVE", color: "bg-red-500 text-white animate-pulse" };
  if (s === "finished" || s === "ended") return { label: "FT", color: "bg-zinc-800 text-white" };
  if (s === "halftime") return { label: "HT", color: "bg-amber-500 text-white" };
  if (s === "pending" || s === "scheduled") return { label: statusText || "Scheduled", color: "bg-blue-100 text-blue-700" };
  if (s === "postponed") return { label: "Postponed", color: "bg-gray-100 text-gray-500" };
  return { label: statusText || s, color: "bg-zinc-100 text-zinc-600" };
}

export default async function LivePage() {
  let matches: LiveMatch[] = [];
  let error: string | null = null;

  try {
    const res = await fetch(`${api}/matches/live?limit=50`, { cache: "no-store" });
    const data = await res.json();
    matches = data.matches || [];
    if (data.error) error = data.error;
  } catch {
    error = "Failed to fetch live matches";
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
        <h1 className="text-2xl font-bold text-zinc-800">Live Matches</h1>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      {matches.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-zinc-400">No live matches right now. Check back during match hours.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((m) => {
            const badge = statusBadge(m.status, m.status_text);
            return (
              <div key={m.external_id} className="bg-white border border-zinc-200 rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center gap-2 w-2/5 min-w-0">
                    {m.home_team_logo && (
                      <img src={m.home_team_logo} alt="" className="w-6 h-6 object-contain shrink-0" />
                    )}
                    <span className="text-sm font-semibold text-zinc-800 truncate">{m.home_team_name}</span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xl font-bold text-zinc-900 w-6 text-center">{m.home_goals ?? "-"}</span>
                    <span className="text-xs text-zinc-400">:</span>
                    <span className="text-xl font-bold text-zinc-900 w-6 text-center">{m.away_goals ?? "-"}</span>
                  </div>

                  <div className="flex items-center gap-2 w-2/5 min-w-0 justify-end">
                    <span className="text-sm font-semibold text-zinc-800 truncate">{m.away_team_name}</span>
                    {m.away_team_logo && (
                      <img src={m.away_team_logo} alt="" className="w-6 h-6 object-contain shrink-0" />
                    )}
                  </div>
                </div>

                <div className="ml-4 shrink-0">
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${badge.color}`}>
                    {badge.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
