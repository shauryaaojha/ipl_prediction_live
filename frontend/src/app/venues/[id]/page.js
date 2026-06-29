import { fetchApi } from "@/lib/api";
import { ArrowLeft, MapPin, Target, Activity } from "lucide-react";
import Link from "next/link";
import VenuePhaseChart from "./VenuePhaseChart";

export default async function VenueProfile({ params }) {
  const resolvedParams = await params;
  const venueId = resolvedParams.id;

  // Fetch venue details and analytics
  const [venues, phases] = await Promise.all([
    fetchApi("/venues"),
    fetchApi(`/analytics/venues/${venueId}/phases`),
  ]);

  const venue = venues?.find(v => v.venue_id.toString() === venueId);

  if (!venue) {
    return <div className="text-white text-center py-20">Venue not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/venues" className="inline-flex items-center text-sm text-slate-400 hover:text-blue-400 transition-colors">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Stadiums
      </Link>

      {/* Venue Header */}
      <div className="glass-panel p-6 rounded-xl flex items-center gap-6 border-l-4 border-l-emerald-500">
        <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-emerald-500 shrink-0">
          <MapPin className="w-10 h-10" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{venue.venue_name}</h1>
          <div className="inline-block px-3 py-1 bg-slate-800 text-slate-300 text-sm rounded-lg border border-slate-700">
            Ground Analytics
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Match Phases Chart */}
        <div className="glass-panel p-6 rounded-xl">
          <div className="flex items-center gap-2 mb-6 border-b border-slate-700/50 pb-4">
            <Activity className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold text-white">Scoring by Phase</h2>
          </div>
          {phases && phases.length > 0 ? (
            <VenuePhaseChart data={phases} metric="runs_per_over" />
          ) : (
            <div className="text-slate-500 text-sm py-10 text-center">No phase data available.</div>
          )}
        </div>

        {/* Phase Breakdown Table */}
        <div className="glass-panel p-6 rounded-xl flex flex-col">
          <div className="flex items-center gap-2 mb-4 border-b border-slate-700/50 pb-4">
            <Target className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-white">Phase Statistics</h2>
          </div>
          
          {phases && phases.length > 0 ? (
            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="text-slate-400 bg-slate-800/40">
                  <tr>
                    <th className="px-4 py-3 font-medium rounded-tl-lg">Match Phase</th>
                    <th className="px-4 py-3 font-medium text-right">Total Runs</th>
                    <th className="px-4 py-3 font-medium text-right">Wickets</th>
                    <th className="px-4 py-3 font-medium text-right text-emerald-400">Run Rate</th>
                    <th className="px-4 py-3 font-medium text-right rounded-tr-lg">Avg / Wicket</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50 text-slate-200">
                  {phases.map((phase, i) => {
                    const average = phase.total_wickets > 0 ? (phase.total_runs / phase.total_wickets).toFixed(2) : '-';
                    return (
                      <tr key={i} className="hover:bg-slate-700/20">
                        <td className="px-4 py-3 font-medium text-white capitalize">{phase.match_phase}</td>
                        <td className="px-4 py-3 text-right">{phase.total_runs}</td>
                        <td className="px-4 py-3 text-right">{phase.total_wickets}</td>
                        <td className="px-4 py-3 text-right font-bold text-emerald-400">
                          {phase.runs_per_over.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right font-medium">
                          {average}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
             <div className="text-slate-500 text-sm py-10 text-center flex-1 flex items-center justify-center">No phase data available.</div>
          )}
        </div>

      </div>
    </div>
  );
}
