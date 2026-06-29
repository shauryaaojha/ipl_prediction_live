import { getDashboardStats, fetchApi } from "@/lib/api";
import Link from "next/link";
import { ArrowRight, Trophy, TrendingUp } from "lucide-react";

export default async function Dashboard() {
  const [stats, battingLeaders, bowlingLeaders] = await Promise.all([
    getDashboardStats(),
    fetchApi("/analytics/batting/leaders?limit=5"),
    fetchApi("/analytics/bowling/leaders?limit=5"),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Platform Overview</h1>
        <p className="text-slate-400">Real-time analytics across 17 IPL seasons.</p>
      </div>

      {/* Headline Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Total Matches" value={stats.totalMatches} />
        <StatCard title="Players Profiled" value={stats.totalPlayers} />
        <StatCard title="Venues Tracked" value={stats.totalVenues} />
      </div>

      {/* Leaderboards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-6">
        {/* Batting */}
        <div className="glass-panel rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-700/50 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Trophy className="w-5 h-5 text-amber-500" />
              All-Time Top Run Scorers
            </h2>
          </div>
          <div className="p-0">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-800/30 text-slate-400 text-sm">
                  <th className="py-3 px-5 font-medium">Rank</th>
                  <th className="py-3 px-5 font-medium">Player</th>
                  <th className="py-3 px-5 font-medium text-right">Runs</th>
                  <th className="py-3 px-5 font-medium text-right">SR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {battingLeaders?.map((player, i) => (
                  <tr key={player.player_id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="py-3 px-5 text-slate-400">#{i + 1}</td>
                    <td className="py-3 px-5 font-medium text-white">
                      <Link href={`/players/${player.player_id}`} className="hover:text-blue-400 transition-colors">
                        {player.player}
                      </Link>
                    </td>
                    <td className="py-3 px-5 text-right font-semibold text-blue-400">{player.runs.toLocaleString()}</td>
                    <td className="py-3 px-5 text-right text-slate-300">{player.strike_rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Bowling */}
        <div className="glass-panel rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-700/50 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              All-Time Top Wicket Takers
            </h2>
          </div>
          <div className="p-0">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-800/30 text-slate-400 text-sm">
                  <th className="py-3 px-5 font-medium">Rank</th>
                  <th className="py-3 px-5 font-medium">Player</th>
                  <th className="py-3 px-5 font-medium text-right">Wickets</th>
                  <th className="py-3 px-5 font-medium text-right">Econ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {bowlingLeaders?.map((player, i) => (
                  <tr key={player.player_id} className="hover:bg-slate-700/20 transition-colors">
                    <td className="py-3 px-5 text-slate-400">#{i + 1}</td>
                    <td className="py-3 px-5 font-medium text-white">
                      <Link href={`/players/${player.player_id}`} className="hover:text-blue-400 transition-colors">
                        {player.player}
                      </Link>
                    </td>
                    <td className="py-3 px-5 text-right font-semibold text-amber-500">{player.wickets}</td>
                    <td className="py-3 px-5 text-right text-slate-300">{player.economy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="glass-card p-6 rounded-xl flex flex-col justify-center">
      <h3 className="text-slate-400 text-sm font-medium mb-2 uppercase tracking-wider">{title}</h3>
      <div className="text-3xl font-bold text-white">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  );
}
