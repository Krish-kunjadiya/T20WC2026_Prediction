import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';

const PIE_COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#8b5cf6'];

export default function MainDashboard() {
  const [kpis, setKpis] = useState({
    total_matches: 0,
    total_teams: 0,
    avg_first_innings_score: 0,
    chasing_win_pct: 0,
  });

  const [charts, setCharts] = useState({
    evolutionData: [],
    topBatsmenData: [],
    topBowlersData: [],
    venueMatchesData: [],
    venueWinStyleData: [],
    tossImpactData: [],
    matchCompetitivenessData: [],
    powerplayLeadersData: [],
    deathBowlingLeadersData: [],
    playerArchetypesData: [],
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8001/dashboard/summary')
      .then((res) => res.json())
      .then((data) => {
        setKpis(data?.kpis || {});
        setCharts(data?.charts || {});
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const evolutionData = useMemo(() => [...(charts.evolutionData || [])], [charts.evolutionData]);

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading real analytics from data lake...</div>;
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen text-gray-900 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-extrabold text-gray-800">T20 World Cup Intelligence Dashboard</h1>
        <p className="text-gray-500">Real-data insights from Silver and Gold layers</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Total Matches</p>
          <p className="text-3xl font-bold text-blue-600 mt-1">{kpis.total_matches || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Teams Covered</p>
          <p className="text-3xl font-bold text-indigo-600 mt-1">{kpis.total_teams || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Avg 1st Innings Score</p>
          <p className="text-3xl font-bold text-emerald-600 mt-1">{kpis.avg_first_innings_score || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Chasing Win %</p>
          <p className="text-3xl font-bold text-amber-600 mt-1">{kpis.chasing_win_pct || 0}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">The Evolution of T20 (Year-wise)</h2>
          <p className="text-xs text-gray-500 mb-4">Yearly shift in scoring, strike intent, and wicket pressure</p>
          <div className="h-[330px]">
            {evolutionData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={evolutionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="year" stroke="#64748b" />
                  <YAxis yAxisId="left" stroke="#2563eb" />
                  <YAxis yAxisId="right" orientation="right" stroke="#16a34a" />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="avgScore" fill="#2563eb" name="Avg 1st Inns Score" radius={[4, 4, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="strikeRate" stroke="#16a34a" strokeWidth={2.5} name="Strike Rate" />
                  <Line yAxisId="right" type="monotone" dataKey="wktProb" stroke="#dc2626" strokeWidth={2.5} name="Wicket %" />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No evolution data available</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Player Insights: Top Batsmen</h2>
          <p className="text-xs text-gray-500 mb-4">Tournament run leaders</p>
          <div className="h-[330px]">
            {(charts.topBatsmenData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topBatsmenData} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="player" width={140} />
                  <Tooltip />
                  <Bar dataKey="runs" fill="#0ea5e9" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No batting leaderboard available</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Player Insights: Top Bowlers</h2>
          <p className="text-xs text-gray-500 mb-4">Highest wicket-takers</p>
          <div className="h-[320px]">
            {(charts.topBowlersData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topBowlersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="player" interval={0} angle={-30} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="wickets" fill="#7c3aed" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No bowling leaderboard available</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Venue Insights: Most Played Grounds</h2>
          <p className="text-xs text-gray-500 mb-4">Top venues by match count</p>
          <div className="h-[320px]">
            {(charts.venueMatchesData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.venueMatchesData} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="venue" width={170} />
                  <Tooltip />
                  <Bar dataKey="matches" fill="#f59e0b" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No venue counts available</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Bat First vs Chasing Wins by Venue</h2>
          <p className="text-xs text-gray-500 mb-4">Where batting first or bowling first has worked more</p>
          <div className="h-[320px]">
            {(charts.venueWinStyleData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.venueWinStyleData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="venue" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="batFirstWins" stackId="a" fill="#2563eb" name="Bat First Wins" />
                  <Bar dataKey="chasingWins" stackId="a" fill="#16a34a" name="Chasing Wins" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No venue win-style data available</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Toss Decision Impact</h2>
          <p className="text-xs text-gray-500 mb-4">Win rate when toss winner chooses bat vs field</p>
          <div className="h-[320px]">
            {(charts.tossImpactData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.tossImpactData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="decision" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="winPct" fill="#14b8a6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No toss impact data available</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Powerplay Leaders</h2>
          <p className="text-xs text-gray-500 mb-4">Highest run rates in overs 1-6</p>
          <div className="h-[300px]">
            {(charts.powerplayLeadersData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.powerplayLeadersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="team" interval={0} angle={-25} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="runRate" fill="#22c55e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No powerplay leadership data available</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Death Overs Bowling Leaders</h2>
          <p className="text-xs text-gray-500 mb-4">Best economy in overs 17-20</p>
          <div className="h-[300px]">
            {(charts.deathBowlingLeadersData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.deathBowlingLeadersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="team" interval={0} angle={-25} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="economy" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No death bowling data available</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-8">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Match Competitiveness Mix</h2>
          <p className="text-xs text-gray-500 mb-4">Close vs competitive vs dominant outcomes</p>
          <div className="h-[320px]">
            {(charts.matchCompetitivenessData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={charts.matchCompetitivenessData} dataKey="matches" nameKey="bucket" outerRadius={105} label>
                    {charts.matchCompetitivenessData.map((entry, idx) => (
                      <Cell key={`${entry.bucket}-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No competitiveness data available</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Player Archetypes</h2>
          <p className="text-xs text-gray-500 mb-4">Average vs strike-rate landscape (bubble size by runs)</p>
          <div className="h-[320px]">
            {(charts.playerArchetypesData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" dataKey="average" name="Average" />
                  <YAxis type="number" dataKey="strikeRate" name="Strike Rate" />
                  <ZAxis type="number" dataKey="runs" range={[40, 320]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={charts.playerArchetypesData} fill="#3b82f6" fillOpacity={0.55} />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No player archetype data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
