import Link from "next/link";
import { Search, Activity, Users, Shield, MapPin, Menu } from "lucide-react";

export function Sidebar() {
  const links = [
    { href: "/", label: "Dashboard", icon: <Activity className="w-5 h-5" /> },
    { href: "/matches", label: "Matches", icon: <Shield className="w-5 h-5" /> }, // Shield as placeholder for cricket
    { href: "/players", label: "Players", icon: <Users className="w-5 h-5" /> },
    { href: "/teams", label: "Teams", icon: <Shield className="w-5 h-5" /> },
    { href: "/venues", label: "Venues", icon: <MapPin className="w-5 h-5" /> },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 glass-panel border-r border-slate-700/50 z-40 hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-slate-700/50">
        <div className="font-bold text-xl tracking-tight bg-gradient-to-r from-blue-400 to-amber-400 bg-clip-text text-transparent">
          IPL Analytics
        </div>
      </div>
      
      <nav className="flex-1 py-6 px-4 space-y-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 hover:text-white hover:bg-blue-600/20 transition-all group"
          >
            <span className="text-slate-400 group-hover:text-blue-400 transition-colors">
              {link.icon}
            </span>
            <span className="font-medium">{link.label}</span>
          </Link>
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-700/50">
        <div className="text-xs text-slate-500 font-medium">v1.0.0 &bull; Phase 3</div>
      </div>
    </aside>
  );
}

export function Navbar() {
  return (
    <header className="h-16 glass-panel border-b border-slate-700/50 flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button className="md:hidden text-slate-400 hover:text-white">
          <Menu className="w-6 h-6" />
        </button>
        {/* Placeholder for breadcrumbs or title */}
      </div>

      <div className="flex items-center">
        {/* Search Bar */}
        <div className="relative w-64 md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search players, teams, venues..." 
            className="w-full bg-slate-800/50 border border-slate-700 rounded-full py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
          />
        </div>
      </div>
    </header>
  );
}
