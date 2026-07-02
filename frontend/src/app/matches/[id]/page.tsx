import { api } from "@/lib/api";
import MatchCard from "@/components/match-card";
import PredictionBadge from "@/components/prediction-badge";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function MatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const matchId = Number(id);

  let match: Awaited<ReturnType<typeof api.getMatch>> | null = null;
  let predictions: Awaited<ReturnType<typeof api.getPredictions>> = [];

  try {
    match = await api.getMatch(matchId);
  } catch {
    // API not available
  }

  try {
    predictions = await api.getPredictions({ match_id: matchId });
  } catch {
    // API not available
  }

  if (!match) {
    return (
      <div className="text-center py-16">
        <p className="text-zinc-400">Match not found</p>
        <Link
          href="/matches"
          className="text-emerald-600 hover:text-emerald-700 mt-4 inline-block"
        >
          Back to matches
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <Link
        href="/matches"
        className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-700 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to matches
      </Link>

      <MatchCard match={match} />

      <section>
        <h2 className="text-lg font-semibold text-zinc-900 mb-4">
          Predictions
        </h2>
        {predictions.length > 0 ? (
          <div className="space-y-3">
            {predictions.map((pred) => (
              <div
                key={pred.id}
                className="bg-white rounded-xl border border-zinc-200 p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-sm font-semibold text-zinc-900">
                      {pred.model_name}
                    </span>
                    <span className="ml-2 text-xs text-zinc-400">
                      v{pred.match?.season?.name ?? ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        pred.confidence_level === "high" ||
                        pred.confidence_level === "very_high"
                          ? "bg-emerald-100 text-emerald-700"
                          : pred.confidence_level === "medium"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-red-100 text-red-700"
                      }`}
                    >
                      {pred.confidence_level.replace("_", " ")}
                    </span>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        pred.risk_level === "low" || pred.risk_level === "very_low"
                          ? "bg-emerald-100 text-emerald-700"
                          : pred.risk_level === "medium"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-red-100 text-red-700"
                      }`}
                    >
                      Risk: {pred.risk_level.replace("_", " ")}
                    </span>
                  </div>
                </div>
                <PredictionBadge
                  homeWin={pred.home_win_probability}
                  draw={pred.draw_probability}
                  awayWin={pred.away_win_probability}
                  confidence={pred.confidence_score}
                  over25={pred.over_2_5_probability}
                  bttsYes={pred.btts_yes_probability}
                  predictedScore={pred.predicted_score}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-zinc-200 p-8 text-center">
            <p className="text-sm text-zinc-400">
              No predictions for this match. Run the prediction pipeline first.
            </p>
          </div>
        )}
      </section>

      {match.venue && (
        <section className="bg-white rounded-xl border border-zinc-200 p-5">
          <h2 className="text-sm font-semibold text-zinc-900 mb-2">
            Match Info
          </h2>
          <p className="text-sm text-zinc-600">{match.venue}</p>
        </section>
      )}
    </div>
  );
}
