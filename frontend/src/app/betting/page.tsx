import { DollarSign, TrendingUp, AlertTriangle, Info } from "lucide-react";

export default function BettingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Betting</h1>
        <p className="text-zinc-500 mt-1">
          Value betting opportunities based on model predictions vs market odds
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start gap-3">
        <Info size={20} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-amber-800">
            Market odds integration required
          </p>
          <p className="text-xs text-amber-700 mt-1">
            To detect value betting opportunities, configure an odds API provider
            (e.g., Odds API) and set the API key in your .env file. The system
            then compares model probabilities against market odds to find
            positive expected value bets.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-zinc-200 p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-500">
              <DollarSign size={20} />
            </div>
            <h3 className="font-semibold text-zinc-900 text-sm">
              Bankroll
            </h3>
          </div>
          <p className="text-2xl font-bold text-zinc-900">$10,000</p>
          <p className="text-xs text-zinc-400 mt-1">Starting bankroll</p>
        </div>

        <div className="bg-white rounded-xl border border-zinc-200 p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-500">
              <TrendingUp size={20} />
            </div>
            <h3 className="font-semibold text-zinc-900 text-sm">
              Kelly Fraction
            </h3>
          </div>
          <p className="text-2xl font-bold text-zinc-900">25%</p>
          <p className="text-xs text-zinc-400 mt-1">
            Conservative Kelly multiplier
          </p>
        </div>

        <div className="bg-white rounded-xl border border-zinc-200 p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-500">
              <AlertTriangle size={20} />
            </div>
            <h3 className="font-semibold text-zinc-900 text-sm">
              Min EV
            </h3>
          </div>
          <p className="text-2xl font-bold text-zinc-900">5%</p>
          <p className="text-xs text-zinc-400 mt-1">
            Minimum expected value threshold
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-zinc-200 p-8 text-center">
        <DollarSign size={48} className="mx-auto text-zinc-300 mb-4" />
        <h3 className="text-lg font-semibold text-zinc-900 mb-2">
          No Betting Opportunities Yet
        </h3>
        <p className="text-sm text-zinc-400 max-w-md mx-auto">
          Once you have trained models, generated predictions, and configured an
          odds API, value betting opportunities will appear here with suggested
          stake amounts based on the Kelly Criterion.
        </p>

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto text-left">
          <div className="bg-zinc-50 rounded-lg p-4">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-1">
              Step 1
            </p>
            <p className="text-sm text-zinc-700">Train prediction models</p>
          </div>
          <div className="bg-zinc-50 rounded-lg p-4">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-1">
              Step 2
            </p>
            <p className="text-sm text-zinc-700">
              Generate predictions for upcoming matches
            </p>
          </div>
          <div className="bg-zinc-50 rounded-lg p-4">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-1">
              Step 3
            </p>
            <p className="text-sm text-zinc-700">
              Fetch market odds and compare
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
