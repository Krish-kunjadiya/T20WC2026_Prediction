import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const defaultCoachData = {
  topFormPlayers: [],
  bestPowerplayBatter: { player: 'N/A', strikeRate: 0, runs: 0, balls: 0 },
  mostReliableMiddleOrderBatter: { player: 'N/A', average: 0, runs: 0, dismissals: 0 },
  bestDeathOverBowler: { player: 'N/A', economy: 0, wickets: 0, balls: 0 },
  playerMatchupAdvantage: { batter: 'N/A', bowler: 'N/A', successRate: 0, runs: 0, balls: 0 },
  matchupRows: [],
  mostConsistentPerformer: { player: 'N/A', variance: 0, formIndex: 0, matches: 0 },
  battingDepthStrength: { averageRuns: 0, positions: [] },
  bowlingPhaseEffectiveness: { bestPhase: { phase: 'N/A', wickets: 0 }, phaseWickets: [] },
  playerWeaknessIndicator: { player: 'N/A', phase: 'N/A', strikeRate: 0, dismissalRate: 0, note: '' },
  optimalPlayingXI: [],
  recentMatchesAnalyzed: 0,
};

const toNumber = (value, digits = 2) => Number(value || 0).toFixed(digits);

const Coach = () => {
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();
  const [coachData, setCoachData] = useState(defaultCoachData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!selectedTeam) {
      setCoachData(defaultCoachData);
      setLoading(false);
      return;
    }

    const loadCoachInsights = async () => {
      setLoading(true);
      setError('');
      try {
        const params = {
          team: selectedTeam,
          recent_matches: 5,
        };
        if (selectedOpponent && selectedOpponent !== selectedTeam) {
          params.opponent = selectedOpponent;
        }

        const { data } = await api.get('/coach/insights', { params });
        setCoachData({ ...defaultCoachData, ...(data || {}) });
      } catch (err) {
        console.error(err);
        setError('Unable to compute coach insights for this selection.');
        setCoachData(defaultCoachData);
      } finally {
        setLoading(false);
      }
    };

    loadCoachInsights();
  }, [selectedTeam, selectedOpponent]);

  const matchupChartData = useMemo(
    () => (coachData.matchupRows || []).slice(0, 8).map((row) => ({
      pair: `${row.batter} vs ${row.bowler}`,
      advantage: Number(row.advantage_score || 0),
    })),
    [coachData.matchupRows]
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Coach Dashboard</h1>
        <p className="text-gray-500 mt-2">Player form, phase execution, matchup edge, and optimal XI recommendations</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Team</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            value={selectedTeam}
            onChange={(event) => setSelectedTeam(event.target.value)}
            disabled={matchupLoading || teams.length === 0}
          >
            {teams.map((team) => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Opponent for Matchup</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2"
            value={selectedOpponent}
            onChange={(event) => setSelectedOpponent(event.target.value)}
            disabled={matchupLoading || teams.length <= 1}
          >
            <option value="">All Opponents</option>
            {teams.filter((team) => team !== selectedTeam).map((team) => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>
        </div>

        <div className="rounded-lg border border-blue-100 bg-blue-50 p-3">
          <p className="text-xs text-blue-700">Recent Sample</p>
          <p className="text-2xl font-bold text-blue-900 mt-1">{coachData.recentMatchesAnalyzed || 0}</p>
          <p className="text-sm text-blue-700">matches used for form and consistency</p>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <div className="animate-pulse bg-white border border-gray-100 rounded-xl p-8 h-80 flex items-center justify-center text-gray-400">
          Loading coach intelligence...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
            <KpiCard title="Best Powerplay Batter" main={coachData.bestPowerplayBatter?.player || 'N/A'} sub={`SR ${toNumber(coachData.bestPowerplayBatter?.strikeRate)} | Runs ${coachData.bestPowerplayBatter?.runs || 0}`} />
            <KpiCard title="Reliable Middle Order" main={coachData.mostReliableMiddleOrderBatter?.player || 'N/A'} sub={`Avg ${toNumber(coachData.mostReliableMiddleOrderBatter?.average)} | Runs ${coachData.mostReliableMiddleOrderBatter?.runs || 0}`} />
            <KpiCard title="Best Death Bowler" main={coachData.bestDeathOverBowler?.player || 'N/A'} sub={`Econ ${toNumber(coachData.bestDeathOverBowler?.economy)} | Wkts ${coachData.bestDeathOverBowler?.wickets || 0}`} />
            <KpiCard title="Most Consistent Performer" main={coachData.mostConsistentPerformer?.player || 'N/A'} sub={`Variance ${toNumber(coachData.mostConsistentPerformer?.variance)} | FI ${toNumber(coachData.mostConsistentPerformer?.formIndex)}`} />
            <KpiCard title="Batting Depth Strength (6-8)" main={toNumber(coachData.battingDepthStrength?.averageRuns)} sub="Average runs per batter innings" />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <ChartCard title="Top 5 Players by Recent Form Index">
              {(coachData.topFormPlayers || []).length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={coachData.topFormPlayers}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="player" interval={0} angle={-18} textAnchor="end" height={78} />
                    <YAxis />
                    <Tooltip formatter={(value) => Number(value).toFixed(2)} />
                    <Bar dataKey="formIndex" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState />
              )}
            </ChartCard>

            <ChartCard title="Bowling Phase Effectiveness (Wickets)">
              {(coachData.bowlingPhaseEffectiveness?.phaseWickets || []).length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={coachData.bowlingPhaseEffectiveness?.phaseWickets || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="phase" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="wickets" fill="#16a34a" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState />
              )}
            </ChartCard>

            <ChartCard title="Batting Depth by Position (6-8)">
              {(coachData.battingDepthStrength?.positions || []).length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={coachData.battingDepthStrength?.positions || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="position" />
                    <YAxis />
                    <Tooltip formatter={(value) => Number(value).toFixed(2)} />
                    <Bar dataKey="avgRuns" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState />
              )}
            </ChartCard>

            <ChartCard title="Player Matchup Advantage">
              {matchupChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={matchupChartData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="pair" width={210} />
                    <Tooltip formatter={(value) => Number(value).toFixed(2)} />
                    <Bar dataKey="advantage" fill="#8b5cf6" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState text="Select an opponent to view matchup edge." />
              )}
            </ChartCard>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-2">Player Weakness Indicator</h3>
              <p className="text-sm text-gray-600">{coachData.playerWeaknessIndicator?.note || 'No weakness pattern available.'}</p>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <StatRow label="Player" value={coachData.playerWeaknessIndicator?.player || 'N/A'} />
                <StatRow label="Phase" value={coachData.playerWeaknessIndicator?.phase || 'N/A'} />
                <StatRow label="Strike Rate" value={toNumber(coachData.playerWeaknessIndicator?.strikeRate)} />
                <StatRow label="Dismissal Rate" value={`${toNumber(coachData.playerWeaknessIndicator?.dismissalRate)}%`} />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-2">Player Matchup Advantage (Top Pair)</h3>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <StatRow label="Batter" value={coachData.playerMatchupAdvantage?.batter || 'N/A'} />
                <StatRow label="Bowler" value={coachData.playerMatchupAdvantage?.bowler || 'N/A'} />
                <StatRow label="Success Rate" value={`${toNumber(coachData.playerMatchupAdvantage?.successRate)}%`} />
                <StatRow label="Runs (Balls)" value={`${coachData.playerMatchupAdvantage?.runs || 0} (${coachData.playerMatchupAdvantage?.balls || 0})`} />
              </div>
              <p className="text-sm text-gray-600 mt-4">
                Best bowling phase for wickets: <span className="font-semibold text-gray-900">{coachData.bowlingPhaseEffectiveness?.bestPhase?.phase || 'N/A'}</span>
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-base font-semibold text-gray-800 mb-3">Optimal Playing XI Suggestion</h3>
            <p className="text-sm text-gray-500 mb-4">Recommended using base performance + recent form + opponent matchup adjustment.</p>
            <div className="overflow-auto max-h-[430px]">
              <table className="w-full min-w-[820px] text-sm">
                <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
                  <tr>
                    <th className="text-left p-3">Rank</th>
                    <th className="text-left p-3">Player</th>
                    <th className="text-left p-3">Role</th>
                    <th className="text-left p-3">Perf</th>
                    <th className="text-left p-3">Form</th>
                    <th className="text-left p-3">Matchup Bonus</th>
                    <th className="text-left p-3">Composite</th>
                  </tr>
                </thead>
                <tbody>
                  {(coachData.optimalPlayingXI || []).map((row) => (
                    <tr key={`${row.xi_rank}-${row.player_name}`} className="border-b border-gray-100">
                      <td className="p-3 font-medium">{row.xi_rank}</td>
                      <td className="p-3">{row.player_name}</td>
                      <td className="p-3">{row.role || 'Unknown'}</td>
                      <td className="p-3">{toNumber(row.perf_score)}</td>
                      <td className="p-3">{toNumber(row.form_index)}</td>
                      <td className="p-3">{toNumber(row.matchup_bonus)}</td>
                      <td className="p-3 font-semibold">{toNumber(row.composite_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const KpiCard = ({ title, main, sub }) => (
  <div className="border border-gray-100 bg-white shadow-sm rounded-xl p-4">
    <p className="text-xs text-gray-500 uppercase tracking-wide">{title}</p>
    <p className="text-lg font-bold text-gray-900 mt-1">{main}</p>
    <p className="text-sm text-gray-600 mt-1">{sub}</p>
  </div>
);

const ChartCard = ({ title, children }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h3 className="text-sm font-semibold text-gray-800 mb-3">{title}</h3>
    {children}
  </div>
);

const StatRow = ({ label, value }) => (
  <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
    <p className="text-xs text-gray-500">{label}</p>
    <p className="text-sm font-semibold text-gray-900 mt-1">{value}</p>
  </div>
);

const EmptyState = ({ text = 'No data available for this selection.' }) => (
  <div className="h-[320px] flex items-center justify-center text-sm text-gray-400">{text}</div>
);

export default Coach;
