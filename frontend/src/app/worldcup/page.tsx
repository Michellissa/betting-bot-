"use client";

import { useEffect, useState } from "react";
import { api, type WCGame, type WCGroup, type WCTeamInfo } from "@/lib/api";
import { Trophy, Calendar, CheckCircle, Globe, MapPin, Swords } from "lucide-react";

const GROUP_NAMES = "ABCDEFGHIJKL".split("");
const KNOCKOUT_STAGES = ["R32", "R16", "QF", "SF", "3RD", "FINAL"];

const STAGE_LABELS: Record<string, string> = {
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter-finals",
  SF: "Semi-finals",
  "3RD": "3rd Place",
  FINAL: "Final",
};

const STAGE_ORDER = ["R32", "R16", "QF", "SF", "3RD", "FINAL"];

export default function WorldCupPage() {
  const [standings, setStandings] = useState<WCGroup[]>([]);
  const [games, setGames] = useState<WCGame[]>([]);
  const [teams, setTeams] = useState<WCTeamInfo[]>([]);
  const [activeTab, setActiveTab] = useState<"groups" | "knockout">("groups");
  const [activeGroup, setActiveGroup] = useState<string>("A");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getWCStandings().then((r) => setStandings(r.standings)),
      api.getWCGames().then((r) => setGames(r.games)),
      api.getWCTeams().then((r) => setTeams(r.teams)),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-zinc-400">Loading World Cup 2026 data...</p>
      </div>
    );
  }

  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t]));

  const groupGames = games.filter((g) => GROUP_NAMES.includes(g.group));
  const knockoutGames = games.filter((g) => KNOCKOUT_STAGES.includes(g.group));
  const finishedKnockout = knockoutGames.filter((g) => g.finished === "TRUE");
  const upcomingKnockout = knockoutGames.filter((g) => g.finished !== "TRUE");

  const filteredGroupGames = groupGames.filter((g) => g.group === activeGroup);
  const groupStanding = standings.find((s) => s.group === activeGroup);

  function renderGame(g: WCGame) {
    const home = teamMap[g.home_team_id];
    const away = teamMap[g.away_team_id];
    const isFinished = g.finished === "TRUE";

    return (
      <div
        key={g.id}
        className={`flex items-center gap-3 p-3 rounded-lg text-sm ${
          isFinished ? "bg-zinc-50" : "bg-white border border-zinc-100"
        }`}
      >
        <div className="flex-1 flex items-center justify-end gap-2">
          {home?.flag && <img src={home.flag} alt="" className="w-5 h-3.5 object-cover rounded" />}
          <span className={`font-medium text-right ${isFinished ? "text-zinc-800" : "text-zinc-600"}`}>
            {home?.name_en ?? g.home_team_name_en}
          </span>
        </div>

        <div className="flex items-center gap-1.5 min-w-[60px] justify-center">
          {isFinished ? (
            <>
              <span className="font-bold text-zinc-900 tabular-nums">{g.home_score}</span>
              <span className="text-zinc-300">-</span>
              <span className="font-bold text-zinc-900 tabular-nums">{g.away_score}</span>
            </>
          ) : (
            <span className="text-xs text-zinc-400">VS</span>
          )}
        </div>

        <div className="flex-1 flex items-center gap-2">
          <span className={`font-medium ${isFinished ? "text-zinc-800" : "text-zinc-600"}`}>
            {away?.name_en ?? g.away_team_name_en}
          </span>
          {away?.flag && <img src={away.flag} alt="" className="w-5 h-3.5 object-cover rounded" />}
        </div>

        {isFinished && <CheckCircle size={14} className="text-zinc-300 flex-shrink-0" />}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Trophy className="text-yellow-500" size={28} />
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">FIFA World Cup 2026</h1>
          <p className="text-sm text-zinc-500">
            USA &middot; Canada &middot; Mexico &middot; 48 teams &middot; 104 matches
          </p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab("groups")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "groups"
              ? "bg-emerald-600 text-white"
              : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
          }`}
        >
          <Globe size={16} className="inline mr-1.5" />
          Group Stage
        </button>
        <button
          onClick={() => setActiveTab("knockout")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "knockout"
              ? "bg-emerald-600 text-white"
              : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
          }`}
        >
          <Swords size={16} className="inline mr-1.5" />
          Knockout Stage
          {upcomingKnockout.length > 0 && (
            <span className="ml-1.5 bg-red-500 text-white text-[10px] rounded-full px-1.5 py-0.5">
              {upcomingKnockout.length} live
            </span>
          )}
        </button>
      </div>

      {activeTab === "groups" ? (
        <>
          {/* Group tabs */}
          <div className="flex gap-1 overflow-x-auto pb-1">
            {GROUP_NAMES.map((g) => {
              const isActive = g === activeGroup;
              return (
                <button
                  key={g}
                  onClick={() => setActiveGroup(g)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${
                    isActive
                      ? "bg-emerald-600 text-white"
                      : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                  }`}
                >
                  Group {g}
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Standings */}
            <section className="bg-white rounded-xl border border-zinc-200 p-5">
              <h2 className="text-sm font-semibold text-zinc-900 mb-3 flex items-center gap-2">
                <Globe size={16} className="text-zinc-400" />
                Group {activeGroup} Standings
              </h2>

              {groupStanding ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-zinc-400 uppercase border-b border-zinc-100">
                      <th className="text-left py-2 pr-2">#</th>
                      <th className="text-left py-2 pr-2">Team</th>
                      <th className="text-center py-2 px-1">MP</th>
                      <th className="text-center py-2 px-1">W</th>
                      <th className="text-center py-2 px-1">D</th>
                      <th className="text-center py-2 px-1">L</th>
                      <th className="text-center py-2 px-1">GF</th>
                      <th className="text-center py-2 px-1">GA</th>
                      <th className="text-center py-2 px-1">GD</th>
                      <th className="text-center py-2 pl-1 font-bold">Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupStanding.teams.map((t, i) => {
                      const info = teamMap[t.team_id];
                      const gd = parseInt(t.gd);
                      return (
                        <tr key={t.team_id} className={`border-b border-zinc-50 ${i < 2 ? "bg-emerald-50/50" : ""}`}>
                          <td className="py-2 pr-2 text-zinc-400">{i + 1}</td>
                          <td className="py-2 pr-2">
                            <div className="flex items-center gap-2">
                              {info?.flag && <img src={info.flag} alt="" className="w-5 h-3.5 object-cover rounded" />}
                              <span className="font-medium text-zinc-800">{info?.name_en ?? `Team ${t.team_id}`}</span>
                            </div>
                          </td>
                          <td className="text-center py-2 px-1">{t.mp}</td>
                          <td className="text-center py-2 px-1 text-emerald-600 font-medium">{t.w}</td>
                          <td className="text-center py-2 px-1 text-amber-600 font-medium">{t.d}</td>
                          <td className="text-center py-2 px-1 text-red-500 font-medium">{t.l}</td>
                          <td className="text-center py-2 px-1">{t.gf}</td>
                          <td className="text-center py-2 px-1">{t.ga}</td>
                          <td className={`text-center py-2 px-1 font-medium ${gd > 0 ? "text-emerald-600" : gd < 0 ? "text-red-500" : ""}`}>
                            {gd > 0 ? `+${gd}` : gd}
                          </td>
                          <td className="text-center py-2 pl-1 font-bold text-zinc-900">{t.pts}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-zinc-400 py-4 text-center">No standings data</p>
              )}
            </section>

            {/* Group matches */}
            <section className="bg-white rounded-xl border border-zinc-200 p-5">
              <h2 className="text-sm font-semibold text-zinc-900 mb-3 flex items-center gap-2">
                <Calendar size={16} className="text-zinc-400" />
                Group {activeGroup} Matches
              </h2>
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {filteredGroupGames.length > 0 ? (
                  filteredGroupGames.map(renderGame)
                ) : (
                  <p className="text-sm text-zinc-400 text-center py-8">No matches in Group {activeGroup}</p>
                )}
              </div>
            </section>
          </div>
        </>
      ) : (
        /* Knockout Stage */
        <div className="space-y-6">
          {STAGE_ORDER.map((stage) => {
            const stageGames = knockoutGames.filter((g) => g.group === stage);
            if (stageGames.length === 0) return null;
            const finished = stageGames.filter((g) => g.finished === "TRUE");
            const upcoming = stageGames.filter((g) => g.finished !== "TRUE");

            return (
              <section key={stage} className="bg-white rounded-xl border border-zinc-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                    <Swords size={16} className="text-zinc-400" />
                    {STAGE_LABELS[stage] ?? stage}
                  </h2>
                  {upcoming.length > 0 && (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                      {upcoming.length} upcoming
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  {stageGames.map(renderGame)}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {/* All groups quick view */}
      <section className="bg-white rounded-xl border border-zinc-200 p-5">
        <h2 className="text-sm font-semibold text-zinc-900 mb-3">All Groups — Quick View</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {standings.map((g) => (
            <div key={g.group} className="bg-zinc-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-zinc-500 mb-2">Group {g.group}</p>
              <div className="space-y-1">
                {g.teams.sort((a, b) => parseInt(b.pts) - parseInt(a.pts)).map((t, i) => {
                  const info = teamMap[t.team_id];
                  return (
                    <div key={t.team_id} className={`flex items-center gap-1.5 text-xs ${i < 2 ? "text-zinc-800 font-medium" : "text-zinc-400"}`}>
                      {info?.flag && <img src={info.flag} alt="" className="w-4 h-3 object-cover rounded" />}
                      <span className="truncate">{info?.fifa_code ?? t.team_id}</span>
                      <span className="ml-auto font-semibold">{t.pts}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
