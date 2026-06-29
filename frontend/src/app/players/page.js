import { fetchApi } from "@/lib/api";
import Link from "next/link";
import { User, Activity, Search } from "lucide-react";

export const metadata = {
  title: "Players | IPL Analytics",
};

export default async function PlayersPage({ searchParams }) {
  const params = await searchParams;
  const page = parseInt(params.page || "1", 10);
  const q = params.q || "";

  // If there's a search query, use the search endpoint, else use paginated players
  let data;
  if (q) {
    data = await fetchApi(`/search?q=${encodeURIComponent(q)}`);
    // Search returns { players: [], teams: [], venues: [] }
    data = { data: data?.players || [], pagination: { page: 1, total_pages: 1 } };
  } else {
    data = await fetchApi(`/players?page=${page}&per_page=24`);
  }
  
  const players = data?.data || [];
  const pagination = data?.pagination || { total_pages: 1, page: 1 };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Players Directory</h1>
          <p className="text-slate-400">Comprehensive profiles and analytics for every IPL player.</p>
        </div>

        {/* Player Search Form */}
        <form className="relative w-full md:w-72" method="GET" action="/players">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            name="q"
            defaultValue={q}
            placeholder="Search players..." 
            className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg pl-10 pr-4 py-2 outline-none focus:border-blue-500 transition-colors"
          />
        </form>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {players.map((player) => (
          <Link key={player.player_id} href={`/players/${player.player_id}`}>
            <div className="glass-card p-5 rounded-xl hover:border-blue-500/50 cursor-pointer flex items-center gap-4 group">
              <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-colors shrink-0">
                <User className="w-6 h-6" />
              </div>
              <div className="overflow-hidden">
                <div className="font-bold text-slate-200 truncate group-hover:text-blue-400 transition-colors">
                  {player.player_name || player.name}
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                  <Activity className="w-3 h-3" /> View Analytics
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {players.length === 0 && (
        <div className="text-center py-20 text-slate-400">
          No players found. Try a different search.
        </div>
      )}

      {/* Pagination Controls - only show if not searching */}
      {!q && (
        <div className="flex justify-center gap-2 pt-6">
          {pagination.page > 1 && (
            <Link 
              href={`/players?page=${pagination.page - 1}`}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            >
              Previous
            </Link>
          )}
          <span className="px-4 py-2 text-slate-400">Page {pagination.page} of {pagination.total_pages}</span>
          {pagination.page < pagination.total_pages && (
            <Link 
              href={`/players?page=${pagination.page + 1}`}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
            >
              Next
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
