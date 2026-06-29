"use client";

import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function VenuePhaseChart({ data, metric }) {
  const chartData = useMemo(() => {
    // Sort logically: Powerplay -> Middle Overs -> Death Overs
    const order = { powerplay: 1, 'middle overs': 2, 'death overs': 3 };
    
    return [...data].sort((a, b) => {
      return (order[a.match_phase] || 99) - (order[b.match_phase] || 99);
    });
  }, [data]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-white font-bold mb-2 border-b border-slate-700 pb-1 capitalize">{label}</p>
          <div className="space-y-1 text-sm">
            <p className="text-emerald-400">Run Rate: <span className="font-bold">{point.runs_per_over.toFixed(2)}</span> rpo</p>
            <p className="text-slate-300">Total Runs: <span className="text-white">{point.total_runs}</span></p>
            <p className="text-slate-300">Total Wickets: <span className="text-white">{point.total_wickets}</span></p>
          </div>
        </div>
      );
    }
    return null;
  };

  // Give each phase a slightly different shade for visual interest
  const colors = {
    powerplay: "#3b82f6", // Blue
    'middle overs': "#f59e0b", // Amber
    'death overs': "#ef4444" // Red
  };

  return (
    <div className="w-full h-72 relative">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis 
            dataKey="match_phase" 
            stroke="#94a3b8" 
            fontSize={12} 
            tickMargin={10} 
            axisLine={false}
            tickLine={false}
            tickFormatter={(val) => val.charAt(0).toUpperCase() + val.slice(1)}
          />
          <YAxis 
            stroke="#94a3b8" 
            fontSize={12} 
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155', opacity: 0.4 }} />
          <Bar dataKey={metric} radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[entry.match_phase] || '#10b981'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
