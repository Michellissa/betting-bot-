"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type LiveMatch } from "@/lib/api";

interface LiveScoreOverlayProps {
  homeTeam: string;
  awayTeam: string;
  matchDate: string;
}

const POLL_INTERVAL = 30_000;

function buildSlug(home: string, away: string, dateStr: string): string {
  const d = new Date(dateStr);
  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  const date = d.getDate();
  const month = months[d.getMonth()];
  const year = d.getFullYear();
  return `${home.toLowerCase().replace(/\s+/g, "-")}-vs-${away.toLowerCase().replace(/\s+/g, "-")}-${month}-${date}-${year}`;
}

export default function LiveScoreOverlay({ homeTeam, awayTeam, matchDate }: LiveScoreOverlayProps) {
  const [liveData, setLiveData] = useState<LiveMatch | null>(null);
  const [error, setError] = useState<string | null>(null);

  const slug = buildSlug(homeTeam, awayTeam, matchDate);

  const fetchLive = useCallback(async () => {
    try {
      const data = await api.getLiveMatchDetail(slug);
      if (data.match) {
        setLiveData(data.match);
        setError(null);
      }
    } catch {
      // SportScore may not have this match — that's OK
    }
  }, [slug]);

  useEffect(() => {
    fetchLive();
    const interval = setInterval(fetchLive, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchLive]);

  if (!liveData || liveData.status === "scheduled" || liveData.status === "unknown") {
    return null;
  }

  const isFinished = liveData.status === "finished";
  const isLive = liveData.status === "live";
  const isHT = liveData.status === "halftime";

  return (
    <div className={`rounded-xl border p-5 ${
      isLive ? "border-red-200 bg-red-50" :
      isHT ? "border-amber-200 bg-amber-50" :
      "border-zinc-200 bg-zinc-50"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-600 uppercase tracking-wide">
          {isLive ? "Live Score" : isHT ? "Half Time" : "Full Time"}
        </h3>
        {isLive && liveData.live_minute != null && (
          <span className="text-xs font-bold text-red-600 bg-red-100 px-2 py-0.5 rounded-full">
            {liveData.live_minute}&apos;
          </span>
        )}
      </div>

      <div className="flex items-center justify-center gap-6 py-3">
        <div className="text-right flex-1">
          <p className="text-sm font-semibold text-zinc-900">{homeTeam}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold text-zinc-900">{liveData.home_goals ?? 0}</span>
          <span className="text-zinc-300 text-xl font-bold">-</span>
          <span className="text-3xl font-bold text-zinc-900">{liveData.away_goals ?? 0}</span>
        </div>
        <div className="text-left flex-1">
          <p className="text-sm font-semibold text-zinc-900">{awayTeam}</p>
        </div>
      </div>

      {liveData.goals && liveData.goals.length > 0 && (
        <div className="mt-3 pt-3 border-t border-zinc-200">
          <p className="text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wide">Goals</p>
          <div className="space-y-1">
            {liveData.goals.map((g, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-xs">⚽</span>
                <span className="font-medium text-zinc-700">
                  {g.side === "home" ? homeTeam : awayTeam}
                </span>
                <span className="text-zinc-500">
                  {g.player} {g.minute}&apos;
                </span>
                <span className="text-xs text-zinc-400">
                  ({g.home_score}-{g.away_score})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}
    </div>
  );
}
