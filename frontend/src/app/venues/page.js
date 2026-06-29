import { fetchApi } from "@/lib/api";
import Link from "next/link";
import { MapPin, ChevronRight, Activity } from "lucide-react";

export const metadata = {
  title: "Venues | IPL Analytics",
};

export default async function VenuesPage() {
  const venues = await fetchApi("/venues") || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Stadiums & Venues</h1>
        <p className="text-slate-400">Analytics across all historical IPL host grounds.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {venues.map((venue) => (
          <Link key={venue.venue_id} href={`/venues/${venue.venue_id}`}>
            <div className="glass-card p-6 rounded-xl hover:border-blue-500/50 cursor-pointer group flex flex-col h-full transition-all hover:-translate-y-1">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center shrink-0 group-hover:bg-blue-600/20 group-hover:border-blue-500/50 transition-colors">
                  <MapPin className="w-5 h-5 text-slate-400 group-hover:text-blue-400" />
                </div>
                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-blue-400 transition-colors" />
              </div>
              
              <div className="mt-auto">
                <h3 className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors line-clamp-2">
                  {venue.venue_name}
                </h3>
                <div className="text-sm text-slate-500 mt-2 flex items-center gap-1">
                  <Activity className="w-3 h-3" /> View Ground Stats
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
