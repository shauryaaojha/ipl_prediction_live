import { fetchApi } from "@/lib/api";
import Link from "next/link";
import { Calendar, MapPin, Trophy } from "lucide-react";

export const metadata = {
  title: "Matches | IPL Analytics",
};

export default async function MatchesPage({ searchParams }) {
  // Await searchParams in Next.js 15 before using
  const params = await searchParams;
  const page = parseInt(params.page || "1", 10);
  const season = params.season || "";

  let url = `/matches?page=${page}&per_page=20`;
  if (season) url += `&season=${season}`;

  const data = await fetchApi(url);
  const matches = data?.data || [];
  const pagination = data?.pagination || { total_pages: 1, page: 1 };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Matches</h1>
          <p className="text-slate-400">Browse and analyze all historical IPL matches.</p>
        </div>

        {/* Season Filter (Simple form) */}
        <form className="flex gap-2" method="GET" action="/matches">
          <select 
            name="season" 
            defaultValue={season}
            className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 outline-none focus:border-blue-500"
          >
            <option value="">All Seasons</option>
            {[...Array(17)].map((_, i) => (
              <option key={i} value={2024 - i}>{2024 - i}</option>
            ))}
          </select>
          <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors">
            Filter
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {matches.map((match) => (
          <Link key={match.match_id} href={`/matches/${match.match_id}`}>
            <div className="glass-card p-5 rounded-xl hover:border-blue-500/50 cursor-pointer">
              <div className="flex justify-between text-sm text-slate-400 mb-4">
                <span className="flex items-center gap-1"><Calendar className="w-4 h-4" /> {new Date(match.match_date).toLocaleDateString()}</span>
                <span className="flex items-center gap-1 text-right"><MapPin className="w-4 h-4" /> {match.venue?.venue_name}</span>
              </div>
              
              <div className="flex justify-between items-center mb-4">
                <div className={`text-xl font-bold ${match.winner?.team_id === match.team_a?.team_id ? 'text-blue-400' : 'text-slate-200'}`}>
                  {match.team_a?.team_name}
                </div>
                <div className="text-sm font-medium text-slate-500 px-3 py-1 bg-slate-800 rounded-full">VS</div>
                <div className={`text-xl font-bold ${match.winner?.team_id === match.team_b?.team_id ? 'text-blue-400' : 'text-slate-200'}`}>
                  {match.team_b?.team_name}
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm text-amber-500 font-medium bg-amber-500/10 px-3 py-2 rounded-lg">
                <Trophy className="w-4 h-4" />
                {match.winner?.team_name} won by {match.win_margin} {match.win_type}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Pagination Controls */}
      <div className="flex justify-center gap-2 pt-6">
        {pagination.page > 1 && (
          <Link 
            href={`/matches?page=${pagination.page - 1}${season ? `&season=${season}` : ''}`}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
          >
            Previous
          </Link>
        )}
        <span className="px-4 py-2 text-slate-400">Page {pagination.page} of {pagination.total_pages}</span>
        {pagination.page < pagination.total_pages && (
          <Link 
            href={`/matches?page=${pagination.page + 1}${season ? `&season=${season}` : ''}`}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
          >
            Next
          </Link>
        )}
      </div>
    </div>
  );
}
