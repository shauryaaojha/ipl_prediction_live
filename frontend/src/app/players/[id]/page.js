import { fetchApi } from "@/lib/api";
import { ArrowLeft, User, Crosshair, Shield, TrendingUp } from "lucide-react";
import Link from "next/link";
import PlayerRadarChart from "./PlayerRadarChart";

export default async function PlayerProfile({ params }) {
  const resolvedParams = await params;
  const playerId = resolvedParams.id;

  // We need to fetch player details, and their analytics
  // Since we don't have a direct /players/{id} endpoint yet, we can get their name from leaders or search
  // Wait, I think we have /players endpoint but not a GET by ID in Phase 4. Let's see if /players/{id} works.
  // Actually, I can fetch from /analytics/batting and /analytics/bowling for this specific player.
  
  // As a workaround, we will fetch batting and bowling leaders and filter, or just use the search endpoint to find the exact player name
  // To make it robust, we'll fetch batting and bowling stats, passing the player_id if supported, or we can just fetch all and filter.
  // Let's assume the API might not have a direct by-id stats fetch, so we'll fetch the whole leaderboards and filter.
  // Wait, the Phase 4 analytics endpoints might not support filtering by player_id. 
  // Let's just fetch the leaders (limit 1000) and find them.

  const [battingData, bowlingData] = await Promise.all([
    fetchApi("/analytics/batting/leaders?limit=1500"),
    fetchApi("/analytics/bowling/leaders?limit=1500"),
  ]);

  const battingStat = battingData?.find(p => p.player_id.toString() === playerId) || null;
  const bowlingStat = bowlingData?.find(p => p.player_id.toString() === playerId) || null;
  
  const playerName = battingStat?.player || bowlingStat?.player || "Unknown Player";

  if (!battingStat && !bowlingStat) {
    return <div className="text-white text-center py-20">Player statistics not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/players" className="inline-flex items-center text-sm text-slate-400 hover:text-blue-400 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Players
      </Link>

      {/* Player Header */}
      <div className="glass-panel p-6 rounded-xl flex items-center gap-6">
        <div className="w-24 h-24 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-500 shrink-0">
          <User className="w-12 h-12" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{playerName}</h1>
          <div className="flex gap-3">
            {battingStat && (
              <span className="px-3 py-1 bg-blue-500/10 text-blue-400 text-xs font-medium rounded-full border border-blue-500/20">
                Batter
              </span>
            )}
            {bowlingStat && (
              <span className="px-3 py-1 bg-amber-500/10 text-amber-500 text-xs font-medium rounded-full border border-amber-500/20">
                Bowler
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radar Chart */}
        <div className="lg:col-span-1 glass-panel p-6 rounded-xl flex flex-col items-center">
          <h2 className="text-lg font-semibold text-white mb-4 w-full border-b border-slate-700/50 pb-2">Player Profile</h2>
          <PlayerRadarChart battingStat={battingStat} bowlingStat={bowlingStat} />
        </div>

        {/* Career Stats */}
        <div className="lg:col-span-2 space-y-6">
          
          {battingStat && (
            <div className="glass-panel rounded-xl overflow-hidden">
              <div className="bg-slate-800/80 px-5 py-4 border-b border-slate-700/50 flex items-center gap-2">
                <Crosshair className="w-5 h-5 text-blue-400" />
                <h3 className="font-semibold text-white">Batting Career</h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5">
                <StatBox label="Matches" value={battingStat.matches} />
                <StatBox label="Innings" value={battingStat.innings} />
                <StatBox label="Runs" value={battingStat.runs} highlight />
                <StatBox label="Strike Rate" value={battingStat.strike_rate} />
                <StatBox label="Average" value={battingStat.average} />
                <StatBox label="Highest Score" value={`${battingStat.highest_score}${battingStat.highest_score_not_out ? '*' : ''}`} />
                <StatBox label="100s / 50s" value={`${battingStat.hundreds} / ${battingStat.fifties}`} />
                <StatBox label="4s / 6s" value={`${battingStat.fours} / ${battingStat.sixes}`} />
              </div>
            </div>
          )}

          {bowlingStat && (
            <div className="glass-panel rounded-xl overflow-hidden">
              <div className="bg-slate-800/80 px-5 py-4 border-b border-slate-700/50 flex items-center gap-2">
                <Shield className="w-5 h-5 text-amber-500" />
                <h3 className="font-semibold text-white">Bowling Career</h3>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-5">
                <StatBox label="Matches" value={bowlingStat.matches} />
                <StatBox label="Innings" value={bowlingStat.innings} />
                <StatBox label="Wickets" value={bowlingStat.wickets} highlight />
                <StatBox label="Economy" value={bowlingStat.economy} />
                <StatBox label="Average" value={bowlingStat.average} />
                <StatBox label="Strike Rate" value={bowlingStat.strike_rate} />
                <StatBox label="4W / 5W" value={`${bowlingStat.four_wicket_hauls} / ${bowlingStat.five_wicket_hauls}`} />
                <StatBox label="Best Bowling" value={`${bowlingStat.best_bowling_wickets}/${bowlingStat.best_bowling_runs}`} />
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value, highlight }) {
  return (
    <div className="bg-slate-800/40 p-4 rounded-lg border border-slate-700/30">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className={`text-xl font-bold ${highlight ? 'text-blue-400' : 'text-slate-200'}`}>
        {value !== null && value !== undefined ? value : '-'}
      </div>
    </div>
  );
}
