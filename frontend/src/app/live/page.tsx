"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type LiveMatch } from "@/lib/api";

const POLL_INTERVAL = 30_000; // 30 seconds

function statusBadge(status: string, statusText: string | null, liveMinute?: number | null): { label: string; color: string } {
  const s = status.toLowerCase();
  if (s === "live") {
    const minute = liveMinute != null ? ` ${liveMinute}'` : "";
    return { label: `LIVE${minute}`, color: "bg-red-500 text-white animate-pulse" };
  }
  if (s === "finished") return { label: "FT", color: "bg-zinc-800 text-white" };
  if (s === "halftime") return { label: "HT", color: "bg-amber-500 text-white" };
  if (s === "scheduled") return { label: statusText || "Scheduled", color: "bg-blue-100 text-blue-700" };
  if (s === "postponed") return { label: "Postponed", color: "bg-gray-100 text-gray-500" };
  return { label: statusText || s, color: "bg-zinc-100 text-zinc-600" };
}

function shouldPoll(status: string): boolean {
  const s = status.toLowerCase();
  return s === "live" || s === "halftime" || s === "inprogress";
}

export default function LivePage() {
  const [matches, setMatches] = useState<LiveMatch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  const fetchLive = useCallback(async () => {
    try {
      const data = await api.getLiveMatches(50);
      setMatches(data.matches || []);
      setError(data.error || null);
      setLastUpdated(new Date());

      // Stop polling if no matches are live/ht
      const hasActive = (data.matches || []).some(m => shouldPoll(m.status));
      setIsPolling(hasActive);
    } catch {
      setError("Failed to fetch live matches");
    }
  }, []);

  useEffect(() => {
    fetchLive();
    const interval = setInterval(() => {
      if (isPolling) {
        fetchLive();
      }
    }, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchLive, isPolling]);

  const liveCount = matches.filter(m => shouldPoll(m.status)).length;
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${isPolling ? "bg-red-500 animate-pulse" : "bg-zinc-400"}`} />
          <h1 className="text-2xl font-bold text-zinc-800">Live Matches</h1>
          {liveCount > 0 && (
            <span className="text-sm text-zinc-400">({liveCount} live)</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          {lastUpdated && (
            <span>
              Updated {Math.round((now - lastUpdated.getTime()) / 1000)}s ago
            </span>
          )}
          <button
            onClick={fetchLive}
            className="px-2.5 py-1 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-600 transition-colors"
          >
            Refresh
          </button>
        </div>
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
            const badge = statusBadge(m.status, m.status_text, m.live_minute);
            const isActive = shouldPoll(m.status);
            return (
              <div
                key={m.external_id}
                className={`bg-white border rounded-xl p-4 flex items-center justify-between transition-opacity ${
                  isActive ? "border-red-200" : "border-zinc-200"
                }`}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex items-center gap-2 w-2/5 min-w-0">
                    {m.home_team_logo && (
                      <img src={m.home_team_logo} alt="" className="w-6 h-6 object-contain shrink-0" />
                    )}
                    <span className="text-sm font-semibold text-zinc-800 truncate">{m.home_team_name}</span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-xl font-bold w-6 text-center ${m.home_goals != null && (m.status === "live" || m.status === "finished" || m.status === "halftime") ? "text-zinc-900" : "text-zinc-400"}`}>
                      {m.home_goals ?? "-"}
                    </span>
                    <span className="text-xs text-zinc-400">:</span>
                    <span className={`text-xl font-bold w-6 text-center ${m.away_goals != null && (m.status === "live" || m.status === "finished" || m.status === "halftime") ? "text-zinc-900" : "text-zinc-400"}`}>
                      {m.away_goals ?? "-"}
                    </span>
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
