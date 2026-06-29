import { fetchApi } from "@/lib/api";
import { ArrowLeft, Shield, Swords, Calendar } from "lucide-react";
import Link from "next/link";
import TeamPerformanceChart from "./TeamPerformanceChart";

export default async function TeamProfile({ params }) {
  const resolvedParams = await params;
  const teamId = resolvedParams.id;

  // We need to fetch the team name. Easiest way is to fetch all teams and filter.
  const teams = await fetchApi("/teams") || [];
  const team = teams.find(t => t.team_id.toString() === teamId);

  if (!team) {
    return <div className="text-white text-center py-20">Team not found.</div>;
  }

  // Fetch team analytics
  const [seasons, h2h] = await Promise.all([
    fetchApi(`/analytics/teams/${teamId}/seasons`),
    fetchApi(`/analytics/teams/${teamId}/h2h`),
  ]);

  return (
    <div className="space-y-6">
      <Link href="/teams" className="inline-flex items-center text-sm text-slate-400 hover:text-blue-400 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Franchises
      </Link>

      {/* Team Header */}
      <div className="glass-panel p-6 rounded-xl flex items-center gap-6 border-l-4 border-l-amber-500">
        <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-amber-500 shrink-0">
          <Shield className="w-10 h-10" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{team.team_name}</h1>
          <div className="inline-block px-3 py-1 bg-slate-800 text-slate-300 font-mono text-sm rounded-lg border border-slate-700">
            {team.team_code}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Season Trends Chart */}
        <div className="glass-panel p-6 rounded-xl">
          <div className="flex items-center gap-2 mb-6 border-b border-slate-700/50 pb-4">
            <Calendar className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Season by Season Win %</h2>
          </div>
          {seasons && seasons.length > 0 ? (
            <TeamPerformanceChart data={seasons} />
          ) : (
            <div className="text-slate-500 text-sm py-10 text-center">No season data available.</div>
          )}
        </div>

        {/* Head-to-Head Table */}
        <div className="glass-panel p-6 rounded-xl flex flex-col">
          <div className="flex items-center gap-2 mb-4 border-b border-slate-700/50 pb-4">
            <Swords className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-white">Head-to-Head Record</h2>
          </div>
          
          {h2h && h2h.length > 0 ? (
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="text-slate-400 bg-slate-800/40">
                  <tr>
                    <th className="px-4 py-3 font-medium rounded-tl-lg">Opponent</th>
                    <th className="px-4 py-3 font-medium text-right">Matches</th>
                    <th className="px-4 py-3 font-medium text-right text-blue-400">Won</th>
                    <th className="px-4 py-3 font-medium text-right text-red-400">Lost</th>
                    <th className="px-4 py-3 font-medium text-right rounded-tr-lg">Win %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50 text-slate-200">
                  {h2h.map((opp, i) => (
                    <tr key={i} className="hover:bg-slate-700/20">
                      <td className="px-4 py-3 font-medium text-white">{opp.opponent}</td>
                      <td className="px-4 py-3 text-right">{opp.matches_played}</td>
                      <td className="px-4 py-3 text-right font-bold text-blue-400">{opp.won}</td>
                      <td className="px-4 py-3 text-right text-red-400">{opp.lost}</td>
                      <td className="px-4 py-3 text-right font-medium">
                        {((opp.won / opp.matches_played) * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
             <div className="text-slate-500 text-sm py-10 text-center flex-1 flex items-center justify-center">No H2H data available.</div>
          )}
        </div>

      </div>
    </div>
  );
}
