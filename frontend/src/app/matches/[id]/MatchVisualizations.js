"use client";

import { useMemo, useState } from "react";
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from "recharts";

export default function MatchVisualizations({ deliveries, teamA, teamB }) {
  const [activeTab, setActiveTab] = useState("worm");

  const chartData = useMemo(() => {
    // Group deliveries by innings and over
    const overs = {};
    
    deliveries.forEach(d => {
      const { innings, over_number, total_runs } = d;
      const overStr = `Ov ${over_number}`;
      
      if (!overs[overStr]) {
        overs[overStr] = { overStr, over_number, inn1Runs: 0, inn2Runs: 0 };
      }
      
      if (innings === 1) overs[overStr].inn1Runs += total_runs;
      if (innings === 2) overs[overStr].inn2Runs += total_runs;
    });

    // Convert to array and sort by over
    let data = Object.values(overs).sort((a, b) => a.over_number - b.over_number);

    // Calculate cumulative runs (Worm)
    let cumulativeInn1 = 0;
    let cumulativeInn2 = 0;

    data = data.map(d => {
      cumulativeInn1 += d.inn1Runs;
      cumulativeInn2 += d.inn2Runs;
      
      return {
        ...d,
        inn1Cumulative: cumulativeInn1,
        inn2Cumulative: cumulativeInn2 > 0 || d.inn2Runs > 0 ? cumulativeInn2 : null,
      };
    });

    return data;
  }, [deliveries]);

  const team1Label = "Innings 1";
  const team2Label = "Innings 2";

  return (
    <div className="glass-panel p-6 rounded-xl">
      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-700/50 pb-2">
        <button 
          onClick={() => setActiveTab("worm")}
          className={`pb-2 px-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "worm" ? "border-blue-500 text-white" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Worm Graph (Cumulative)
        </button>
        <button 
          onClick={() => setActiveTab("manhattan")}
          className={`pb-2 px-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "manhattan" ? "border-blue-500 text-white" : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Manhattan (Runs/Over)
        </button>
      </div>

      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {activeTab === "worm" ? (
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="overStr" stroke="#94a3b8" fontSize={12} tickMargin={10} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#f8fafc' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Line type="monotone" dataKey="inn1Cumulative" name={team1Label} stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="inn2Cumulative" name={team2Label} stroke="#f59e0b" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
            </LineChart>
          ) : (
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="overStr" stroke="#94a3b8" fontSize={12} tickMargin={10} />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#f8fafc' }}
                cursor={{ fill: '#334155', opacity: 0.4 }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Bar dataKey="inn1Runs" name={team1Label} fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="inn2Runs" name={team2Label} fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
