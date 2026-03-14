import React, { useEffect, useState } from 'react';
import { executeQuery } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const Coach = () => {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTeams = async () => {
      const data = await executeQuery("SELECT DISTINCT team_name FROM gold.dim_team ORDER BY team_name");
      setTeams(data.map(d => d.team_name));
      setSelectedTeam(data[0]?.team_name || '');
    };
    fetchTeams();
  }, []);

  useEffect(() => {
    if (!selectedTeam) return;
    
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const team = selectedTeam.replace(/'/g, "''"); // escape for SQL
        
        const [kpiBat, kpiBowl, topBatters, topBowlers, overRuns, dismissals, players] = await Promise.all([
          executeQuery(`SELECT SUM(batsman_runs) as total_runs, (SUM(batsman_runs)*100.0/COUNT(*)) as sr FROM silver.clean_deliveries WHERE batting_team = '${team}'`),
          executeQuery(`SELECT SUM(CAST(is_wicket AS INTEGER)) as total_wkts, 
                        (SELECT SUM(total_runs)/(COUNT(*)/6.0) FROM silver.clean_deliveries WHERE bowling_team = '${team}' AND over_num >= 16) as death_econ
                        FROM silver.clean_deliveries WHERE bowling_team = '${team}'`),
          executeQuery(`SELECT batsman as player, SUM(batsman_runs) as runs, (SUM(batsman_runs)*100.0/COUNT(*)) as sr FROM silver.clean_deliveries WHERE batting_team = '${team}' GROUP BY batsman ORDER BY runs DESC LIMIT 10`),
          executeQuery(`SELECT bowler as player, SUM(CAST(is_wicket AS INTEGER)) as wickets, SUM(total_runs)/(COUNT(*)/6.0) as economy FROM silver.clean_deliveries WHERE bowling_team = '${team}' GROUP BY bowler HAVING COUNT(*) >= 12 ORDER BY economy ASC LIMIT 10`),
          executeQuery(`SELECT over_num as over, AVG(total_runs) as avg_runs FROM silver.clean_deliveries WHERE batting_team = '${team}' GROUP BY over_num ORDER BY over_num`),
          executeQuery(`SELECT dismissal_kind, COUNT(*) as count FROM silver.clean_deliveries WHERE batting_team = '${team}' AND is_wicket = true GROUP BY dismissal_kind ORDER BY count DESC`),
          executeQuery(`SELECT player_name, role, runs, batting_avg, strike_rate, wickets, economy FROM silver.clean_players WHERE country = '${team}' ORDER BY runs DESC LIMIT 4`)
        ]);

        setDashboardData({
          kpis: {
            runs: kpiBat[0]?.total_runs || 0,
            sr: parseFloat(kpiBat[0]?.sr || 0).toFixed(1),
            wkts: kpiBowl[0]?.total_wkts || 0,
            deathEcon: parseFloat(kpiBowl[0]?.death_econ || 0).toFixed(2),
          },
          topBatters,
          topBowlers,
          overRuns: overRuns.map(r => ({ ...r, phase: r.over <= 6 ? 'Powerplay' : r.over <= 15 ? 'Middle' : 'Death' })),
          dismissals,
          players
        });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [selectedTeam]);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF19A3'];

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🧑‍💼 Coach Dashboard</h1>
        <p className="text-gray-500 mt-2">Persona: Team Coach | Focus: Player Form & Match Readiness</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">🌍 Select Team</label>
        <select 
          className="border border-gray-300 rounded-md px-4 py-2 w-64 focus:ring-blue-500 focus:border-blue-500"
          value={selectedTeam} 
          onChange={e => setSelectedTeam(e.target.value)}
        >
          {teams.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {loading || !dashboardData ? (
        <div className="animate-pulse bg-white border border-gray-100 rounded-xl p-8 h-96 w-full flex items-center justify-center text-gray-400">Loading Coach Data...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard title="🏏 Total Runs Scored" value={dashboardData.kpis.runs.toLocaleString()} />
            <KpiCard title="🎯 Wickets Taken" value={dashboardData.kpis.wkts} />
            <KpiCard title="⚡ Team Strike Rate" value={dashboardData.kpis.sr} />
            <KpiCard title="💀 Death Over Economy" value={dashboardData.kpis.deathEcon} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title={`🔥 Top Batters - ${selectedTeam}`}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dashboardData.topBatters}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="player" tick={{fontSize: 11}} interval={0} angle={-30} textAnchor="end" height={60} />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="runs" fill="#10b981" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title={`🎯 Bowler Economy - ${selectedTeam}`}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dashboardData.topBowlers}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="player" tick={{fontSize: 11}} interval={0} angle={-30} textAnchor="end" height={60} />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="economy" fill="#3b82f6" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="📈 Avg Runs per Over">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dashboardData.overRuns}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="over" />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="avg_runs" fill="#8b5cf6" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="🚨 Wicket Loss Analysis">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={dashboardData.dismissals} dataKey="count" nameKey="dismissal_kind" cx="50%" cy="50%" outerRadius={80} label>
                    {dashboardData.dismissals.map((entry, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">🃏 Player Profile Cards (Top 4)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {dashboardData.players.map((p, idx) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <h4 className="font-bold text-gray-900">{p.player_name}</h4>
                  <p className="text-sm text-blue-600 font-medium mb-3">{p.role}</p>
                  <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                    <div>Runs: <span className="font-semibold text-gray-900">{p.runs || 0}</span></div>
                    <div>Avg: <span className="font-semibold text-gray-900">{p.batting_avg || 0}</span></div>
                    <div>SR: <span className="font-semibold text-gray-900">{p.strike_rate || 0}</span></div>
                    <div>Wkts: <span className="font-semibold text-gray-900">{p.wickets || 0}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const KpiCard = ({ title, value }) => (
  <div className="border border-gray-100 bg-white shadow-sm rounded-xl p-5">
    <h3 className="text-sm font-medium text-gray-500 mb-1">{title}</h3>
    <p className="text-3xl font-bold text-gray-900">{value}</p>
  </div>
);

const ChartCard = ({ title, children }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h3 className="text-sm font-semibold text-gray-800 mb-4">{title}</h3>
    {children}
  </div>
);

export default Coach;
