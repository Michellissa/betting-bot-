import { api } from "@/lib/api";
import type { Prediction } from "@/lib/api";
import PredictionBadge from "@/components/prediction-badge";
import Link from "next/link";

export const dynamic = "force-dynamic";

function getDateLabel(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  if (diff > 0 && diff <= 7) return d.toLocaleDateString("en-US", { weekday: "long" });
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

const leagueColors: Record<string, string> = {
  "FIFA WORLD": "bg-emerald-100 text-emerald-700",
  "PL": "bg-purple-100 text-purple-700",
  "PD": "bg-red-100 text-red-700",
  "SA": "bg-blue-100 text-blue-700",
  "BL1": "bg-yellow-100 text-yellow-700",
  "FL1": "bg-sky-100 text-sky-700",
};

function LeagueBadge({ code }: { code: string }) {
  const colors = leagueColors[code] || "bg-zinc-100 text-zinc-600";
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${colors}`}>
      {code}
    </span>
  );
}

function ConfidenceDot({ level }: { level: string }) {
  const colors: Record<string, string> = {
    very_high: "bg-emerald-500",
    high: "bg-emerald-400",
    medium: "bg-amber-400",
    low: "bg-red-400",
    very_low: "bg-red-500",
  };
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${colors[level] || "bg-zinc-300"}`} />
  );
}

export default async function PredictionsPage() {
  let predictions: Prediction[] = [];

  try {
    predictions = await api.getUpcomingPredictions(100);
  } catch {
    // API not available
  }

  // Sort by match date ascending
  const sorted = [...predictions].sort((a, b) => {
    const da = new Date(a.match?.match_date || 0).getTime();
    const db = new Date(b.match?.match_date || 0).getTime();
    return da - db;
  });

  // Group by date label
  const groups: Record<string, Prediction[]> = {};
  const order: string[] = [];
  for (const p of sorted) {
    if (!p.match?.match_date) continue;
    const label = getDateLabel(p.match.match_date);
    if (!groups[label]) {
      groups[label] = [];
      order.push(label);
    }
    groups[label].push(p);
  }

  // Move "Today" and "Tomorrow" to front if they exist
  const priority = ["Today", "Tomorrow"];
  for (const p of priority) {
    if (order.includes(p)) {
      order.splice(order.indexOf(p), 1);
      order.unshift(p);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Predictions</h1>
        <p className="text-zinc-500 mt-1">
          Model predictions for upcoming matches
        </p>
      </div>

      {order.length > 0 ? (
        order.map((groupLabel) => (
          <section key={groupLabel}>
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-lg font-semibold text-zinc-900">{groupLabel}</h2>
              <div className="h-px flex-1 bg-zinc-200" />
              <span className="text-xs text-zinc-400">{groups[groupLabel].length} match{groups[groupLabel].length > 1 ? "es" : ""}</span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {groups[groupLabel].map((pred) => {
                const date = new Date(pred.match?.match_date || "");
                return (
                  <div
                    key={pred.id}
                    className="bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <LeagueBadge code={pred.match?.league?.code ?? "?"} />
                        {pred.match?.round && (
                          <span className="text-xs text-zinc-400">
                            {getRoundLabel(pred.match.round)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-400">
                          {date.toLocaleDateString("en-US", { month: "short", day: "numeric" })} {formatTime(pred.match?.match_date || "")}
                        </span>
                        <span className="text-xs text-zinc-500">{pred.model_name}</span>
                      </div>
                    </div>

                    <Link
                      href={`/matches/${pred.match_id}`}
                      className="block mb-3"
                    >
                      <p className="text-sm font-semibold text-zinc-900 hover:text-emerald-600 transition-colors">
                        {pred.match?.home_team?.name ?? `Team #${pred.match?.home_team_id}`}
                        {" vs "}
                        {pred.match?.away_team?.name ?? `Team #${pred.match?.away_team_id}`}
                      </p>
                    </Link>

                    <PredictionBadge
                      homeWin={pred.home_win_probability}
                      draw={pred.draw_probability}
                      awayWin={pred.away_win_probability}
                      confidence={pred.confidence_score}
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

                    <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-zinc-100">
                      <ConfidenceDot level={pred.confidence_level} />
                      <span className="text-xs text-zinc-500">{pred.confidence_level.replace("_", " ")} confidence</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))
      ) : (
        <div className="text-center py-16">
          <p className="text-zinc-400">
            No predictions found. Train models and run predictions first.
          </p>
        </div>
      )}
    </div>
  );
}

function getRoundLabel(round: number): string {
  if (round >= 1 && round <= 38) return `R${round}`;
  return `Round ${round}`;
}
