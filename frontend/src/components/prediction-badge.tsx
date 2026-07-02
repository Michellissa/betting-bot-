interface PredictionBadgeProps {
  homeWin: number;
  draw: number;
  awayWin: number;
  confidence?: number;
  over25?: number | null;
  bttsYes?: number | null;
  predictedScore?: string | null;
}

export default function PredictionBadge({
  homeWin,
  draw,
  awayWin,
  confidence,
  over25,
  bttsYes,
  predictedScore,
}: PredictionBadgeProps) {
  const maxProb = Math.max(homeWin, draw, awayWin);
  const predicted =
    maxProb === homeWin ? "H" : maxProb === draw ? "D" : "A";

  const resultLabels: Record<string, string> = {
    H: "Home",
    D: "Draw",
    A: "Away",
  };

  const resultColors: Record<string, string> = {
    H: "bg-emerald-500",
    D: "bg-amber-500",
    A: "bg-red-500",
  };

  return (
    <div className="space-y-3">
      {/* Result prediction */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div
            className={`w-2 h-2 rounded-full ${resultColors[predicted]}`}
          />
          <span className="text-sm font-semibold">
            {resultLabels[predicted]}
          </span>
          {confidence !== undefined && (
            <span className="text-xs text-zinc-400">
              ({(confidence * 100).toFixed(0)}% confidence)
            </span>
          )}
        </div>

        <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-zinc-100">
          <div
            className="bg-emerald-500 transition-all"
            style={{ width: `${homeWin * 100}%` }}
          />
          <div
            className="bg-amber-500 transition-all"
            style={{ width: `${draw * 100}%` }}
          />
          <div
            className="bg-red-500 transition-all"
            style={{ width: `${awayWin * 100}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-zinc-400 mt-0.5">
          <span>H {(homeWin * 100).toFixed(0)}%</span>
          <span>D {(draw * 100).toFixed(0)}%</span>
          <span>A {(awayWin * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Predicted score */}
      {predictedScore && (
        <div className="text-center">
          <span className="text-xs text-zinc-400">Predicted </span>
          <span className="text-sm font-bold text-zinc-800">{predictedScore}</span>
        </div>
      )}

      {/* Over/Under 2.5 & BTTS */}
      <div className="flex gap-4 text-xs">
        {over25 !== null && over25 !== undefined && (
          <div>
            <span className="text-zinc-400">O2.5 </span>
            <span className="font-medium">
              {(over25 * 100).toFixed(0)}%
            </span>
          </div>
        )}
        {bttsYes !== null && bttsYes !== undefined && (
          <div>
            <span className="text-zinc-400">BTTS </span>
            <span className="font-medium">
              {(bttsYes * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
