import type { Match } from "@/lib/api";

const resultColors: Record<string, string> = {
  H: "text-emerald-600",
  D: "text-amber-600",
  A: "text-red-600",
};

export default function MatchCard({
  match,
  showResult = true,
}: {
  match: Match;
  showResult?: boolean;
}) {
  const date = new Date(match.match_date);
  const formattedDate = date.toLocaleDateString("sv-SE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const formattedTime = date.toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
          {match.league?.code || `League #${match.league_id}`}
        </span>
        <span className="text-xs text-zinc-400">
          {formattedDate} {formattedTime}
        </span>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 text-right">
          <p className="text-sm font-semibold text-zinc-900">
            {match.home_team?.name || `Team #${match.home_team_id}`}
          </p>
          {match.home_team?.elo_rating && (
            <p className="text-xs text-zinc-400">
              Elo: {Math.round(match.home_team.elo_rating)}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          {match.is_finished && showResult ? (
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-zinc-900">
                {match.home_goals}
              </span>
              <span className="text-zinc-300 font-bold">-</span>
              <span className="text-2xl font-bold text-zinc-900">
                {match.away_goals}
              </span>
            </div>
          ) : (
            <span className="text-xs font-medium text-zinc-400 uppercase bg-zinc-100 px-3 py-1 rounded-full">
              VS
            </span>
          )}
        </div>

        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-zinc-900">
            {match.away_team?.name || `Team #${match.away_team_id}`}
          </p>
          {match.away_team?.elo_rating && (
            <p className="text-xs text-zinc-400">
              Elo: {Math.round(match.away_team.elo_rating)}
            </p>
          )}
        </div>
      </div>

      {match.result && showResult && (
        <div className="mt-3 text-center">
          <span
            className={`text-xs font-bold uppercase ${resultColors[match.result]}`}
          >
            {match.result === "H"
              ? "Home Win"
              : match.result === "A"
                ? "Away Win"
                : "Draw"}
          </span>
        </div>
      )}

      {match.round && (
        <div className="mt-2 text-center">
          <span className="text-xs text-zinc-400">Round {match.round}</span>
        </div>
      )}
    </div>
  );
}
