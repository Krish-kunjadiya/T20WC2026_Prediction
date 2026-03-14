import React, { useEffect, useState } from 'react';
import { executeQuery } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';

const Analyst = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Simulator state
  const [teams, setTeams] = useState([]);
  const [sim, setSim] = useState({ teamA: '', teamB: '', tossWin: '' });
  const [simResult, setSimResult] = useState(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const teamList = await executeQuery('SELECT DISTINCT team_name FROM gold.dim_team ORDER BY team_name');
        const teamNames = teamList.map(t => t.team_name);
        setTeams(teamNames);
        setSim({ teamA: teamNames[0] || '', teamB: teamNames[1] || '', tossWin: teamNames[0] || ''});

        const [batDepth, bowlVar, tossAdv, phaseRuns] = await Promise.all([
          executeQuery(`
            SELECT batting_team as team, SUM(batsman_runs)*1.0 / COUNT(DISTINCT batsman) as depth_score
            FROM silver.clean_deliveries GROUP BY batting_team ORDER BY depth_score DESC LIMIT 12
          `),
          executeQuery(`
            SELECT bowling_team as team, SUM(CAST(is_wicket AS INTEGER))*1.0 / NULLIF(COUNT(DISTINCT bowler),0) as variety_index
            FROM silver.clean_deliveries GROUP BY bowling_team ORDER BY variety_index DESC LIMIT 12
          `),
          executeQuery(`
            SELECT toss_winner as team, AVG(CASE WHEN toss_winner = winner THEN 1.0 ELSE 0.0 END)*100 as win_rate
            FROM silver.clean_matches GROUP BY toss_winner HAVING COUNT(*) >= 3 ORDER BY win_rate DESC LIMIT 12
          `),
          executeQuery(`
            SELECT batting_team as team, 
                   CASE WHEN over_num <= 6 THEN 'Powerplay' WHEN over_num <= 15 THEN 'Middle' ELSE 'Death' END as phase,
                   AVG(total_runs) as avg_runs
            FROM silver.clean_deliveries 
            GROUP BY batting_team, CASE WHEN over_num <= 6 THEN 'Powerplay' WHEN over_num <= 15 THEN 'Middle' ELSE 'Death' END
          `)
        ]);

        // pivot phaseRuns
        const phasePivoted = [];
        const tMap = {};
        phaseRuns.forEach(r => {
           if(!tMap[r.team]) tMap[r.team] = { team: r.team, Powerplay: 0, Middle: 0, Death: 0 };
           tMap[r.team][r.phase] = parseFloat(r.avg_runs);
        });
        // Select top 8 teams by total sum for display
        const topTeams = Object.values(tMap).sort((a,b) => (b.Powerplay+b.Middle+b.Death) - (a.Powerplay+a.Middle+a.Death)).slice(0, 8);

        setData({ batDepth, bowlVar, tossAdv, phaseRuns: topTeams });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const calculateSim = async () => {
    if (!sim.teamA || !sim.teamB) return;
    const { teamA, teamB, tossWin } = sim;
    const ta = teamA.replace(/'/g, "''");
    const tb = teamB.replace(/'/g, "''");
    
    try {
      const res = await executeQuery(`SELECT winner FROM silver.clean_matches WHERE (team1='${ta}' AND team2='${tb}') OR (team1='${tb}' AND team2='${ta}')`);
      const total = res.length;
      const aWins = res.filter(r => r.winner === teamA).length;
      const tossBoost = tossWin === teamA ? 5 : -5;

      let probA, probB;
      if (total > 0) {
        probA = Math.max(0, Math.min(100, (aWins / total * 100) + tossBoost));
        probB = 100 - probA;
      } else {
        probA = 50 + tossBoost;
        probB = 50 - tossBoost;
      }

      setSimResult({ probA: probA.toFixed(1), probB: probB.toFixed(1), message: `Based on ${total} H2H matches + toss advantage`});
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📈 Team Analyst Dashboard</h1>
        <p className="text-gray-500 mt-2">Persona: Team Analyst | Focus: Strategy & Win Probability</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">🎯 Match Win Probability Simulator</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium mb-1">Team A</label>
            <select className="border border-gray-300 rounded px-3 py-2" value={sim.teamA} onChange={e=>setSim({...sim, teamA: e.target.value})}>
              {teams.map(t=><option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Team B</label>
            <select className="border border-gray-300 rounded px-3 py-2" value={sim.teamB} onChange={e=>setSim({...sim, teamB: e.target.value})}>
              {teams.map(t=><option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Toss Winner</label>
            <select className="border border-gray-300 rounded px-3 py-2" value={sim.tossWin} onChange={e=>setSim({...sim, tossWin: e.target.value})}>
              <option value={sim.teamA}>{sim.teamA}</option>
              <option value={sim.teamB}>{sim.teamB}</option>
            </select>
          </div>
          <button onClick={calculateSim} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition">
            🔮 Calculate
          </button>
        </div>

        {simResult && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-100">
            <p className="text-sm text-gray-500 mb-3">{simResult.message}</p>
            <div className="flex items-center gap-8">
              <div className="flex-1">
                <div className="flex justify-between font-bold text-gray-800 mb-1">
                  <span>{sim.teamA}</span><span>{simResult.probA}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3"><div className="bg-emerald-500 h-3 rounded-full" style={{width: `${simResult.probA}%`}}></div></div>
              </div>
              <div className="text-xl font-bold text-gray-400">VS</div>
              <div className="flex-1">
                <div className="flex justify-between font-bold text-gray-800 mb-1">
                  <span>{sim.teamB}</span><span>{simResult.probB}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3"><div className="bg-red-500 h-3 rounded-full" style={{width: `${simResult.probB}%`}}></div></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {!loading && data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-80">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">🏏 Batting Depth Score (Runs / Batter)</h3>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={data.batDepth}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="team" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" height={60} />
                <YAxis />
                <RechartsTooltip />
                <Bar dataKey="depth_score" fill="#10b981" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-80">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">🎯 Bowling Variety Index (Wickets / Bowler)</h3>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={data.bowlVar}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="team" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" height={60} />
                <YAxis />
                <RechartsTooltip />
                <Bar dataKey="variety_index" fill="#3b82f6" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-80">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">🪙 Toss Win → Match Win Rate (%)</h3>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={data.tossAdv}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="team" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" height={60} />
                <YAxis domain={[0, 100]} />
                <RechartsTooltip />
                <Bar dataKey="win_rate" fill="#f59e0b" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-80">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">⚡ Phase-wise Run Rate (Top 8 Teams)</h3>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={data.phaseRuns}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="team" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" height={60} />
                <YAxis />
                <RechartsTooltip />
                <Legend />
                <Bar dataKey="Powerplay" fill="#00CC96" radius={[2,2,0,0]} />
                <Bar dataKey="Middle" fill="#636EFA" radius={[2,2,0,0]} />
                <Bar dataKey="Death" fill="#EF553B" radius={[2,2,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analyst;
