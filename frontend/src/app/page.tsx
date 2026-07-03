import { api } from "@/lib/api";
import type { Prediction } from "@/lib/api";
import StatCard from "@/components/stat-card";
import MatchCard from "@/components/match-card";
import PredictionBadge from "@/components/prediction-badge";
import Link from "next/link";
import {
  Trophy,
  LineChart,
  Brain,
  Calendar,
  TrendingUp,
  Activity,
} from "lucide-react";

export const dynamic = "force-dynamic";

function getDateLabel(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff > 0 && diff <= 7) return d.toLocaleDateString("en-US", { weekday: "long" });
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export default async function DashboardPage() {
  let stats = { total_matches: 0, finished_matches: 0, upcoming_matches: 0, total_predictions: 0, active_models: 0 };
  let recentMatches: Awaited<ReturnType<typeof api.getMatches>> = [];
  let upcomingPredictions: Prediction[] = [];

  try {
    stats = await api.getStats();
  } catch {
    // API not available
  }

  try {
    recentMatches = await api.getMatches({ finished: true, limit: 5 });
  } catch {
    // API not available
  }

  try {
    upcomingPredictions = await api.getUpcomingPredictions(10);
  } catch {
    // API not available
  }

  const sorted = [...upcomingPredictions].sort((a, b) => {
    const da = new Date(a.match?.match_date || 0).getTime();
    const db = new Date(b.match?.match_date || 0).getTime();
    return da - db;
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Dashboard</h1>
        <p className="text-zinc-500 mt-1">
          Overview of matches, predictions, and model performance
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Matches"
          value={stats.total_matches}
          icon={Trophy}
          color="emerald"
        />
        <StatCard
          title="Finished"
          value={stats.finished_matches}
          subtitle={`${stats.upcoming_matches} upcoming`}
          icon={Calendar}
          color="blue"
        />
        <StatCard
          title="Predictions"
          value={stats.total_predictions}
          icon={LineChart}
          color="amber"
        />
        <StatCard
          title="Active Models"
          value={stats.active_models}
          icon={Brain}
          color="violet"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-zinc-900 flex items-center gap-2">
              <Activity size={18} className="text-zinc-400" />
              Recent Results
            </h2>
            <Link href="/matches" className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {recentMatches.length > 0 ? (
              recentMatches.map((match) => (
                <MatchCard key={match.id} match={match} />
              ))
            ) : (
              <p className="text-sm text-zinc-400 text-center py-8">
                No recent matches. Connect the API and seed data.
              </p>
            )}
          </div>
        </section>

        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-zinc-900 flex items-center gap-2">
              <TrendingUp size={18} className="text-zinc-400" />
              Upcoming Predictions
            </h2>
            <Link href="/predictions" className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {sorted.length > 0 ? (
              sorted.map((pred) => {
                const dateLabel = getDateLabel(pred.match?.match_date || "");
                return (
                  <div
                    key={pred.id}
                    className="bg-white rounded-xl border border-zinc-200 p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                        {pred.match?.league?.code ?? "League"}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-400">{formatDate(pred.match?.match_date || "")}</span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          pred.confidence_level === "high" || pred.confidence_level === "very_high"
                            ? "bg-emerald-100 text-emerald-700"
                            : pred.confidence_level === "medium"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-red-100 text-red-700"
                        }`}>
                          {dateLabel}
                        </span>
                      </div>
                    </div>
                    <Link href={`/matches/${pred.match_id}`}>
                      <p className="text-sm font-semibold text-zinc-900 hover:text-emerald-600 transition-colors mb-2">
                        {pred.match?.home_team?.name ?? `#${pred.match?.home_team_id}`} vs{" "}
                        {pred.match?.away_team?.name ?? `#${pred.match?.away_team_id}`}
                      </p>
                    </Link>
                    <PredictionBadge
                      homeWin={pred.home_win_probability}
                      draw={pred.draw_probability}
                      awayWin={pred.away_win_probability}
                      confidence={pred.confidence_score}
                      dataConfidence={pred.data_confidence_score}
                      over25={pred.over_2_5_probability}
                      bttsYes={pred.btts_yes_probability}
                      predictedScore={pred.predicted_score}
                    />
                    {pred.explanation && (
                      <div className="mt-2 pt-2 border-t border-zinc-100">
                        <p className="text-xs text-zinc-500 leading-relaxed whitespace-pre-line">
                          {pred.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-zinc-400 text-center py-8">
                No predictions yet. Train models and generate predictions.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
