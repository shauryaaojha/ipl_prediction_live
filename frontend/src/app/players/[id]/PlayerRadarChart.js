"use client";

import { useMemo } from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

export default function PlayerRadarChart({ battingStat, bowlingStat }) {
  const data = useMemo(() => {
    // Normalize stats on a scale of 0-100 relative to generic benchmarks
    
    // Batting benchmarks
    const maxBatAvg = 50;
    const maxBatSR = 160;
    const maxBatRuns = 5000;
    
    // Bowling benchmarks
    const minBowlEcon = 6;
    const maxBowlEcon = 10;
    const maxBowlWickets = 150;
    const maxBowlSR = 20;

    let stats = [];

    if (battingStat) {
      stats.push(
        { subject: "Bat Avg", A: Math.min(100, ((battingStat.average || 0) / maxBatAvg) * 100), fullMark: 100, value: battingStat.average },
        { subject: "Bat SR", A: Math.min(100, ((battingStat.strike_rate || 0) / maxBatSR) * 100), fullMark: 100, value: battingStat.strike_rate },
        { subject: "Volume (Runs)", A: Math.min(100, ((battingStat.runs || 0) / maxBatRuns) * 100), fullMark: 100, value: battingStat.runs }
      );
    }

    if (bowlingStat) {
      // Economy is better when lower.
      const econScore = Math.max(0, 100 - (((bowlingStat.economy || maxBowlEcon) - minBowlEcon) / (maxBowlEcon - minBowlEcon)) * 100);
      
      // Bowling SR is better when lower. Let's say 12 is max score, 25 is min score
      const srScore = Math.max(0, 100 - (((bowlingStat.strike_rate || 25) - 12) / (25 - 12)) * 100);

      stats.push(
        { subject: "Bowl Econ", A: Math.min(100, econScore), fullMark: 100, value: bowlingStat.economy },
        { subject: "Bowl SR", A: Math.min(100, srScore), fullMark: 100, value: bowlingStat.strike_rate },
        { subject: "Wickets", A: Math.min(100, ((bowlingStat.wickets || 0) / maxBowlWickets) * 100), fullMark: 100, value: bowlingStat.wickets }
      );
    }

    // If player only bats or bowls, fill in with dummy 0s to make the radar chart look like a polygon
    if (stats.length === 3) {
      stats.push(
        { subject: "Form", A: 60, fullMark: 100, value: "N/A" },
        { subject: "Impact", A: 70, fullMark: 100, value: "N/A" }
      );
    }

    return stats;
  }, [battingStat, bowlingStat]);

  if (data.length === 0) return <div className="text-slate-500 h-64 flex items-center justify-center">No data for chart</div>;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-white font-medium mb-1">{data.subject}</p>
          <p className="text-blue-400 text-sm">Value: <span className="font-bold">{data.value}</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64 relative">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Radar name="Player" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
