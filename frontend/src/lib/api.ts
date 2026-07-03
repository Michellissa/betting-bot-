const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface League {
  id: number;
  name: string;
  code: string;
  country: string | null;
}

export interface Season {
  id: number;
  name: string;
  league_id: number;
  is_current: boolean;
}

export interface Team {
  id: number;
  name: string;
  short_name: string | null;
  code: string | null;
  logo_url: string | null;
  elo_rating: number | null;
}

export interface Match {
  id: number;
  league_id: number;
  season_id: number;
  home_team_id: number;
  away_team_id: number;
  match_date: string;
  round: number | null;
  venue: string | null;
  home_goals: number | null;
  away_goals: number | null;
  result: string | null;
  is_finished: boolean;
  league?: League;
  season?: Season;
  home_team?: Team;
  away_team?: Team;
}

export interface Prediction {
  id: number;
  match_id: number;
  model_name: string;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  over_2_5_probability: number | null;
  under_2_5_probability: number | null;
  btts_yes_probability: number | null;
  btts_no_probability: number | null;
  home_expected_goals: number | null;
  away_expected_goals: number | null;
  predicted_score: string | null;
  explanation: string | null;
  confidence_score: number;
  confidence_level: string;
  risk_score: number;
  risk_level: string;
  match?: Match;
}

export interface ModelInfo {
  id: number;
  model_name: string;
  model_version: string;
  model_type: string;
  is_active: boolean;
  training_date: string;
  metrics: ModelMetric[];
}

export interface ModelMetric {
  id: number;
  metric_name: string;
  metric_value: number;
  dataset_type: string;
  fold: number | null;
}

export interface DashboardStats {
  total_matches: number;
  finished_matches: number;
  upcoming_matches: number;
  total_predictions: number;
  active_models: number;
}

// --- World Cup 2026 types ---

export interface WCTeam {
  team_id: string;
  mp: string;
  w: string;
  d: string;
  l: string;
  pts: string;
  gf: string;
  ga: string;
  gd: string;
}

export interface WCGroup {
  group: string;
  teams: WCTeam[];
}

export interface WCGame {
  id: string;
  home_team_id: string;
  away_team_id: string;
  home_score: string;
  away_score: string;
  home_team_name_en: string;
  away_team_name_en: string;
  group: string;
  matchday: string;
  local_date: string;
  finished: string;
  time_elapsed: string;
  type: string;
  home_scorers: string | null;
  away_scorers: string | null;
  stadium_id: string;
}

export interface WCTeamInfo {
  id: string;
  name_en: string;
  flag: string;
  fifa_code: string;
  groups: string;
}

export const api = {
  health: () => fetchApi<{ status: string }>("/api/v1/health"),

  // Leagues
  getLeagues: () => fetchApi<League[]>("/api/v1/leagues"),

  // Matches
  getMatches: (params?: {
    league_id?: number;
    season_id?: number;
    finished?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.league_id) query.set("league_id", String(params.league_id));
    if (params?.season_id) query.set("season_id", String(params.season_id));
    if (params?.finished !== undefined)
      query.set("finished", String(params.finished));
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    const qs = query.toString();
    return fetchApi<{ matches: Match[]; total: number }>(`/api/v1/matches${qs ? `?${qs}` : ""}`)
      .then(r => r.matches);
  },

  getMatch: (id: number) => fetchApi<Match>(`/api/v1/matches/${id}`),

  // Predictions
  getPredictions: (params?: {
    match_id?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.match_id) query.set("match_id", String(params.match_id));
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return fetchApi<Prediction[]>(`/api/v1/predictions${qs ? `?${qs}` : ""}`);
  },

  getUpcomingPredictions: (limit = 20) =>
    fetchApi<Prediction[]>(`/api/v1/predictions/upcoming?limit=${limit}`),

  predictMatch: (matchId: number) =>
    fetchApi<Prediction>(
      "/api/v1/predictions/predict",
      {
        method: "POST",
        body: JSON.stringify({ match_id: matchId }),
      },
    ),

  // Models
  getModels: () => fetchApi<ModelInfo[]>("/api/v1/models"),
  getActiveModel: () => fetchApi<ModelInfo>("/api/v1/models/active"),

  // Dashboard
  getStats: () => fetchApi<DashboardStats>("/api/v1/stats"),

  // --- World Cup 2026 ---
  getWCStandings: () =>
    fetchApi<{ standings: WCGroup[] }>("/api/v1/worldcup/standings"),

  getWCGames: () =>
    fetchApi<{ games: WCGame[]; total: number }>("/api/v1/worldcup/games"),

  getWCTeams: () =>
    fetchApi<{ teams: WCTeamInfo[] }>("/api/v1/worldcup/teams"),

  getWCGroups: () =>
    fetchApi<{ groups: WCGroup[] }>("/api/v1/worldcup/groups"),
};
