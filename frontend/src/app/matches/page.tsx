import { api } from "@/lib/api";
import MatchCard from "@/components/match-card";
import Link from "next/link";
import { Filter } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<{ finished?: string; league_id?: string }>;
}) {
  const params = await searchParams;
  const finished = params.finished !== "false";
  const leagueId = params.league_id ? Number(params.league_id) : undefined;

  let matches: Awaited<ReturnType<typeof api.getMatches>> = [];
  let leagues: Awaited<ReturnType<typeof api.getLeagues>> = [];

  try {
    matches = await api.getMatches({ finished, league_id: leagueId, limit: 50 });
  } catch {
    // API not available
  }

  try {
    leagues = await api.getLeagues();
  } catch {
    // API not available
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Matches</h1>
          <p className="text-zinc-500 mt-1">
            {finished ? "Completed" : "Upcoming"} matches
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href={`/matches?finished=${!finished}${leagueId ? `&league_id=${leagueId}` : ""}`}
            className="text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
          >
            Show {finished ? "upcoming" : "finished"}
          </Link>
        </div>
      </div>

      {leagues.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter size={14} className="text-zinc-400" />
          <Link
            href="/matches"
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
              !leagueId
                ? "bg-emerald-600 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
            }`}
          >
            All
          </Link>
          {leagues.map((league) => (
            <Link
              key={league.id}
              href={`/matches?league_id=${league.id}&finished=${finished}`}
              className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                leagueId === league.id
                  ? "bg-emerald-600 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {league.code}
            </Link>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {matches.length > 0 ? (
          matches.map((match) => (
            <Link key={match.id} href={`/matches/${match.id}`}>
              <MatchCard match={match} showResult={finished} />
            </Link>
          ))
        ) : (
          <div className="col-span-full text-center py-16">
            <p className="text-zinc-400">
              {finished
                ? "No finished matches found. Fetch data from API or seed the database."
                : "No upcoming matches found."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
