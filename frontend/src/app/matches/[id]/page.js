import { fetchApi } from "@/lib/api";
import { ArrowLeft, MapPin, Calendar, Activity } from "lucide-react";
import Link from "next/link";
import Scorecard from "./Scorecard";
import MatchVisualizations from "./MatchVisualizations";

export default async function MatchDetail({ params }) {
  // Await params in Next.js 15
  const resolvedParams = await params;
  const matchId = resolvedParams.id;

  const [match, scorecards, deliveries] = await Promise.all([
    fetchApi(`/matches/${matchId}`),
    fetchApi(`/matches/${matchId}/scorecard`),
    fetchApi(`/matches/${matchId}/deliveries`),
  ]);

  if (!match) {
    return <div className="text-white text-center py-20">Match not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/matches" className="inline-flex items-center text-sm text-slate-400 hover:text-blue-400 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Matches
      </Link>

      {/* Match Header */}
      <div className="glass-panel p-6 rounded-xl border-l-4 border-l-blue-500">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-center md:text-left">
            <h1 className="text-2xl font-bold text-white mb-2">
              {match.team_a?.team_name} vs {match.team_b?.team_name}
            </h1>
            <div className="flex flex-wrap gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1"><Calendar className="w-4 h-4" /> {new Date(match.match_date).toLocaleDateString()}</span>
              <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {match.venue?.venue_name}</span>
            </div>
          </div>
          
          <div className="bg-slate-800/80 px-6 py-4 rounded-lg border border-slate-700/50 text-center">
            <div className="text-sm text-slate-400 mb-1">Result</div>
            <div className="font-bold text-amber-500">{match.winner?.team_name} won by {match.win_margin} {match.win_type}</div>
          </div>
        </div>
      </div>

      {/* Match Visualizations (Worm / Manhattan) */}
      {deliveries && deliveries.length > 0 && (
        <div className="pt-4">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" /> Match Flow
          </h2>
          <MatchVisualizations deliveries={deliveries} teamA={match.team_a?.team_code} teamB={match.team_b?.team_code} />
        </div>
      )}

      {/* Detailed Scorecards */}
      <div className="pt-4 space-y-6">
        <h2 className="text-xl font-semibold text-white mb-2">Scorecard</h2>
        {scorecards?.map((innings) => (
          <Scorecard key={innings.innings} data={innings} />
        ))}
      </div>
    </div>
  );
}
