import { fetchApi } from "@/lib/api";
import Link from "next/link";
import { Shield, ChevronRight } from "lucide-react";

export const metadata = {
  title: "Teams | IPL Analytics",
};

export default async function TeamsPage() {
  const teams = await fetchApi("/teams") || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Franchises</h1>
        <p className="text-slate-400">Current and historical IPL teams.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {teams.map((team) => (
          <Link key={team.team_id} href={`/teams/${team.team_id}`}>
            <div className="glass-card p-6 rounded-xl hover:border-blue-500/50 cursor-pointer group flex items-center justify-between transition-all hover:scale-[1.02]">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center shrink-0 group-hover:border-blue-500/50 transition-colors">
                  <Shield className="w-6 h-6 text-slate-400 group-hover:text-blue-400" />
                </div>
                <div>
                  <div className="font-bold text-lg text-white group-hover:text-blue-400 transition-colors">
                    {team.team_name}
                  </div>
                  <div className="text-sm font-medium text-slate-500 mt-1">
                    {team.team_code}
                  </div>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-blue-400 transition-colors" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
