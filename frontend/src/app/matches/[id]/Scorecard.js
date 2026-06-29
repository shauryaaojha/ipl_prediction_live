export default function Scorecard({ data }) {
  return (
    <div className="glass-panel rounded-xl overflow-hidden mb-6">
      <div className="bg-slate-800/80 px-5 py-4 border-b border-slate-700/50 flex justify-between items-center">
        <h3 className="font-semibold text-white">Innings {data.innings}</h3>
        <div className="font-bold text-blue-400">
          {data.total_runs} / {data.total_wickets} <span className="text-sm font-normal text-slate-400 ml-1">({data.total_overs} ov)</span>
        </div>
      </div>

      {/* Batting Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-800/40 text-slate-400">
            <tr>
              <th className="px-5 py-3 font-medium w-1/3">Batter</th>
              <th className="px-5 py-3 font-medium text-right">R</th>
              <th className="px-5 py-3 font-medium text-right">B</th>
              <th className="px-5 py-3 font-medium text-right">4s</th>
              <th className="px-5 py-3 font-medium text-right">6s</th>
              <th className="px-5 py-3 font-medium text-right">SR</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50 text-slate-200">
            {data.batting.map((batter, i) => (
              <tr key={i} className="hover:bg-slate-700/20">
                <td className="px-5 py-3 font-medium">
                  {batter.player_name}
                  {batter.dismissed_by && (
                    <span className="block text-xs text-slate-500 font-normal mt-0.5">
                      b {batter.dismissed_by} ({batter.dismissal_type})
                    </span>
                  )}
                  {!batter.dismissed_by && (
                    <span className="block text-xs text-amber-500/80 font-normal mt-0.5">
                      not out
                    </span>
                  )}
                </td>
                <td className="px-5 py-3 font-bold text-right">{batter.runs}</td>
                <td className="px-5 py-3 text-right text-slate-400">{batter.balls}</td>
                <td className="px-5 py-3 text-right text-slate-400">{batter.fours}</td>
                <td className="px-5 py-3 text-right text-slate-400">{batter.sixes}</td>
                <td className="px-5 py-3 text-right text-slate-400">{batter.strike_rate}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bowling Table */}
      <div className="overflow-x-auto border-t border-slate-700/50 mt-2">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-800/40 text-slate-400">
            <tr>
              <th className="px-5 py-3 font-medium w-1/3">Bowler</th>
              <th className="px-5 py-3 font-medium text-right">O</th>
              <th className="px-5 py-3 font-medium text-right">R</th>
              <th className="px-5 py-3 font-medium text-right">W</th>
              <th className="px-5 py-3 font-medium text-right">ECON</th>
              <th className="px-5 py-3 font-medium text-right">Dots</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50 text-slate-200">
            {data.bowling.map((bowler, i) => (
              <tr key={i} className="hover:bg-slate-700/20">
                <td className="px-5 py-3 font-medium">{bowler.player_name}</td>
                <td className="px-5 py-3 text-right text-slate-400">{bowler.overs}</td>
                <td className="px-5 py-3 text-right text-slate-400">{bowler.runs}</td>
                <td className="px-5 py-3 font-bold text-right text-amber-500">{bowler.wickets}</td>
                <td className="px-5 py-3 text-right text-slate-400">{bowler.economy}</td>
                <td className="px-5 py-3 text-right text-slate-400">{bowler.dots}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
