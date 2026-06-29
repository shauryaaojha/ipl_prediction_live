"use client";

import { useMemo } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function TeamPerformanceChart({ data }) {
  const chartData = useMemo(() => {
    // API returns: season, matches_played, won, lost, win_percentage, titles
    return data.map(d => ({
      ...d,
      season: d.season.toString(),
      // Ensure win_percentage is a number
      win_percentage: typeof d.win_percentage === 'string' ? parseFloat(d.win_percentage) : d.win_percentage
    })).sort((a, b) => parseInt(a.season) - parseInt(b.season)); // Sort chronologically
  }, [data]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-white font-bold mb-2 border-b border-slate-700 pb-1">Season {label}</p>
          <div className="space-y-1 text-sm">
            <p className="text-slate-300">Matches: <span className="text-white">{point.matches_played}</span></p>
            <p className="text-blue-400">Won: <span className="font-bold">{point.won}</span></p>
            <p className="text-red-400">Lost: <span className="font-bold">{point.lost}</span></p>
            <p className="text-amber-500 font-medium pt-1">Win Rate: {point.win_percentage.toFixed(1)}%</p>
            {point.titles > 0 && (
              <p className="text-yellow-400 font-bold mt-2">🏆 Champion</p>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-72 relative">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorWinPct" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis 
            dataKey="season" 
            stroke="#94a3b8" 
            fontSize={12} 
            tickMargin={10} 
            axisLine={false}
            tickLine={false}
          />
          <YAxis 
            stroke="#94a3b8" 
            fontSize={12} 
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#475569', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Area 
            type="monotone" 
            dataKey="win_percentage" 
            stroke="#3b82f6" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorWinPct)" 
            activeDot={{ r: 6, fill: '#3b82f6', stroke: '#1e293b', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
