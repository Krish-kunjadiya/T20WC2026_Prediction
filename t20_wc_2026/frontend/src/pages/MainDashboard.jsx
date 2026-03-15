import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const defaultKpis = {
  total_matches_played: 0,
  average_team_score: 0,
  net_run_rate: 0,
  net_run_rate_team: 'N/A',
  highest_team_score: 0,
  lowest_defended_score: 0,
};

const defaultCharts = {
  topPerformingTeamsData: [],
  topPerformingPlayersData: [],
  topBatsmenData: [],
  topBowlersData: [],
  bestCaptaincyData: [],
  keyRecordsData: [],
  keyInsightsData: [],
  teamOptions: [],
  teamBreakdown: [],
  headToHeadData: [],
  hypedMatchesData: [],
  aiInsightCards: [],
};

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') return 'N/A';
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
};

export default function MainDashboard() {
  const { selectedTeam: globalTeam, setSelectedTeam: setGlobalTeam } = useMatchup();
  const [kpis, setKpis] = useState(defaultKpis);
  const [charts, setCharts] = useState(defaultCharts);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadDashboard = async () => {
      try {
        const { data } = await api.get('/dashboard/summary');
        if (cancelled) return;

        const nextKpis = data?.kpis || defaultKpis;
        const nextCharts = data?.charts || defaultCharts;
        setKpis(nextKpis);
        setCharts(nextCharts);

        const availableTeams = nextCharts.teamOptions || [];
        const fallbackTeam = availableTeams[0] || (nextCharts.teamBreakdown || [])[0]?.team || '';
        if (fallbackTeam && (!globalTeam || !availableTeams.includes(globalTeam))) {
          setGlobalTeam(fallbackTeam);
        }
      } catch (err) {
        if (!cancelled) console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [globalTeam, setGlobalTeam]);

  const selectedTeam = useMemo(() => {
    const options = charts.teamOptions || [];
    if (globalTeam && options.includes(globalTeam)) {
      return globalTeam;
    }
    return options[0] || (charts.teamBreakdown || [])[0]?.team || '';
  }, [charts.teamBreakdown, charts.teamOptions, globalTeam]);

  const selectedTeamInsight = useMemo(() => {
    const rows = charts.teamBreakdown || [];
    return rows.find((row) => row.team === selectedTeam) || rows[0] || null;
  }, [charts.teamBreakdown, selectedTeam]);

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading analytics dashboard...</div>;
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen text-gray-900 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-extrabold text-gray-800">T20 World Cup Intelligence Dashboard</h1>
        <p className="text-gray-500">Top teams, top players, key records, rivalry insights, and team-level performance analysis</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Total Matches Played</p>
          <p className="text-3xl font-bold text-blue-600 mt-1">{kpis.total_matches_played || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Average Team Score</p>
          <p className="text-3xl font-bold text-emerald-600 mt-1">{kpis.average_team_score || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Net Run Rate</p>
          <p className="text-3xl font-bold text-indigo-600 mt-1">{kpis.net_run_rate || 0}</p>
          <p className="text-xs text-gray-500 mt-1">Leader: {kpis.net_run_rate_team || 'N/A'}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Highest Team Score</p>
          <p className="text-3xl font-bold text-fuchsia-600 mt-1">{kpis.highest_team_score || 0}</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-sm text-gray-500">Lowest Defended Score</p>
          <p className="text-3xl font-bold text-amber-600 mt-1">{kpis.lowest_defended_score || 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm xl:col-span-2">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Top 5-7 Best Performing Teams</h2>
          <p className="text-xs text-gray-500 mb-4">Ranked by win %, net run rate, and sustained scoring output</p>
          <div className="h-[340px]">
            {(charts.topPerformingTeamsData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topPerformingTeamsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="team" interval={0} angle={-20} textAnchor="end" height={85} />
                  <YAxis yAxisId="left" domain={[0, 100]} />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="winPct" fill="#2563eb" name="Win %" radius={[4, 4, 0, 0]} />
                  <Bar yAxisId="right" dataKey="nrr" fill="#14b8a6" name="NRR" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No team ranking data available.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-3 text-gray-800">AI Insight Cards</h2>
          <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1">
            {(charts.aiInsightCards || []).length > 0 ? (
              charts.aiInsightCards.map((card, idx) => (
                <div key={`${card.title}-${idx}`} className="rounded-lg border border-blue-100 bg-blue-50/60 p-3">
                  <p className="text-xs text-blue-700 font-medium">{card.title}</p>
                  <p className="text-base font-bold text-blue-900 mt-1">{formatValue(card.value)}</p>
                  <p className="text-xs text-blue-800 mt-1">{card.detail}</p>
                </div>
              ))
            ) : (
              <p className="text-gray-400">No AI insight cards available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Top Performing Players</h2>
          <p className="text-xs text-gray-500 mb-4">Overall impact combines runs, wickets, strike rate, and economy</p>
          <div className="h-[330px]">
            {(charts.topPerformingPlayersData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topPerformingPlayersData.slice(0, 8)} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" />
                  <YAxis dataKey="player" type="category" width={150} />
                  <Tooltip />
                  <Bar dataKey="impact" fill="#7c3aed" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No player impact data available.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Best Captaincy Proxy</h2>
          <p className="text-xs text-gray-500 mb-4">Team-level leadership proxy from win conversion, NRR, and pressure-match performance</p>
          <div className="h-[330px]">
            {(charts.bestCaptaincyData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.bestCaptaincyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="team" interval={0} angle={-20} textAnchor="end" height={85} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="captaincyIndex" fill="#0f766e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No captaincy proxy data available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Top Batsmen/Women</h2>
          <div className="h-[300px]">
            {(charts.topBatsmenData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topBatsmenData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="player" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="runs" fill="#f97316" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No batting records available.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Top Bowlers</h2>
          <div className="h-[300px]">
            {(charts.topBowlersData || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topBowlersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="player" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="wickets" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400">No bowling records available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-3 text-gray-800">Records Till Date</h2>
          <div className="space-y-3">
            {(charts.keyRecordsData || []).map((record, idx) => (
              <div key={`${record.title}-${idx}`} className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">{record.title}</p>
                <p className="text-lg font-bold text-gray-900 mt-1">{formatValue(record.value)}</p>
                <p className="text-xs text-gray-600 mt-1">{record.context}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-3 text-gray-800">Key Insights</h2>
          <div className="space-y-3">
            {(charts.keyInsightsData || []).length > 0 ? (
              charts.keyInsightsData.map((insight, idx) => (
                <div key={`${insight.title}-${idx}`} className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
                  <p className="text-sm font-semibold text-emerald-800">{insight.title}</p>
                  <p className="text-sm text-emerald-900 mt-1">{insight.detail}</p>
                </div>
              ))
            ) : (
              <p className="text-gray-400">No insights generated yet.</p>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-3 text-gray-800">Hyped Matches</h2>
          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
            {(charts.hypedMatchesData || []).length > 0 ? (
              charts.hypedMatchesData.map((match) => (
                <div key={match.matchId} className="rounded-lg border border-rose-200 bg-rose-50/60 p-3">
                  <p className="text-sm font-semibold text-rose-900">{match.fixture}</p>
                  <p className="text-xs text-rose-800 mt-1">{match.margin}</p>
                  <p className="text-xs text-rose-800">Hype Score: {match.hypeScore} | Total Runs: {match.totalRuns}</p>
                </div>
              ))
            ) : (
              <p className="text-gray-400">No hyped-match data available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Head-to-Head Highlights</h2>
            <p className="text-xs text-gray-500">Most recurring rivalries and win splits</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left p-3">Fixture</th>
                <th className="text-left p-3">Matches</th>
                <th className="text-left p-3">Wins ({'Team A'})</th>
                <th className="text-left p-3">Wins ({'Team B'})</th>
                <th className="text-left p-3">Last Winner</th>
              </tr>
            </thead>
            <tbody>
              {(charts.headToHeadData || []).slice(0, 10).map((row) => (
                <tr key={row.pair} className="border-b border-gray-100">
                  <td className="p-3 font-medium text-gray-900">{row.pair}</td>
                  <td className="p-3">{row.matches}</td>
                  <td className="p-3">{row.winsA}</td>
                  <td className="p-3">{row.winsB}</td>
                  <td className="p-3">{row.lastWinner || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Team-wise Performance Trend & Insights</h2>
            <p className="text-xs text-gray-500">Select any team for focused trend, records, and matchup intelligence</p>
          </div>
          <div className="w-full md:w-[280px]">
            <select
              className="w-full border border-gray-300 rounded-md p-2"
              value={selectedTeam}
              onChange={(e) => setGlobalTeam(e.target.value)}
            >
              {(charts.teamOptions || []).map((team) => (
                <option key={team} value={team}>{team}</option>
              ))}
            </select>
          </div>
        </div>

        {selectedTeamInsight ? (
          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Matches</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{selectedTeamInsight.summary?.matches || 0}</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Win %</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{selectedTeamInsight.summary?.winPct || 0}%</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">NRR</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{selectedTeamInsight.summary?.nrr || 0}</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Best Score</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{selectedTeamInsight.summary?.bestScore || 0}</p>
              </div>
              <div className="rounded-lg border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Highest Chase</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{selectedTeamInsight.summary?.highestChase || 0}</p>
              </div>
            </div>

            <div className="h-[360px]">
              {(selectedTeamInsight.trend || []).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={selectedTeamInsight.trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="matchLabel" interval={0} angle={-20} textAnchor="end" height={90} />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="teamScore" fill="#3b82f6" name="Team Score" radius={[4, 4, 0, 0]} />
                    <Line yAxisId="right" type="monotone" dataKey="cumulativeWinPct" stroke="#16a34a" strokeWidth={2.5} name="Cumulative Win %" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-400">No trend data available for selected team.</p>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-3">Team Key Insights</h3>
                <div className="space-y-2">
                  {(selectedTeamInsight.keyInsights || []).map((item, idx) => (
                    <div key={`${item.title}-${idx}`} className="rounded-md border border-gray-100 bg-gray-50 p-2">
                      <p className="text-xs text-gray-500">{item.title}</p>
                      <p className="text-sm font-medium text-gray-900 mt-1">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-3">Team Head-to-Head Snapshot</h3>
                <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
                  {(selectedTeamInsight.headToHead || []).map((row) => (
                    <div key={row.opponent} className="rounded-md border border-gray-100 bg-gray-50 p-2">
                      <p className="text-sm font-medium text-gray-900">vs {row.opponent}</p>
                      <p className="text-xs text-gray-600">{row.wins}/{row.matches} wins ({row.winPct}%)</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 p-4 overflow-x-auto">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">Top Performing Players for {selectedTeamInsight.team}</h3>
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left p-3">Player</th>
                    <th className="text-left p-3">Runs</th>
                    <th className="text-left p-3">Wickets</th>
                    <th className="text-left p-3">Strike Rate</th>
                    <th className="text-left p-3">Economy</th>
                    <th className="text-left p-3">Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedTeamInsight.topPlayers || []).map((player) => (
                    <tr key={player.player} className="border-b border-gray-100">
                      <td className="p-3 font-medium text-gray-900">{player.player}</td>
                      <td className="p-3">{player.runs}</td>
                      <td className="p-3">{player.wickets}</td>
                      <td className="p-3">{player.strikeRate}</td>
                      <td className="p-3">{player.economy}</td>
                      <td className="p-3">{player.impact}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <p className="text-gray-400">No team-level breakdown available.</p>
        )}
      </div>
    </div>
  );
}
