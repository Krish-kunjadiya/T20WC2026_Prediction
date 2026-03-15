import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const defaultStrategistInsights = {
  qualificationProbability: {
    probabilityPct: 0,
    currentRank: 0,
    currentPoints: 0,
    currentNrr: 0,
    playoffCutoffPoints: 0,
  },
  matchStrategyOverview: {
    overallWinPct: 0,
    recentWinPct: 0,
    headToHeadWinPct: 0,
    nrr: 0,
    averageTeamScore: 0,
    powerplayRunRate: 0,
    middleRunRate: 0,
    deathRunRate: 0,
    strategyIndex: 0,
    strategySignal: 'No strategy signal available.',
  },
  optimalTossStrategy: {
    batFirstWinPct: 0,
    chasingWinPct: 0,
    batFirstMatches: 0,
    chasingMatches: 0,
    venueAvgFirstInningsScore: 0,
    recommendedTossDecision: 'N/A',
  },
  opponentWeaknessAnalysis: {
    weaknessVsType: 'N/A',
    weakPhase: 'N/A',
    phaseRunRates: { powerplay: 0, middle: 0, death: 0 },
    chasingWinPct: 0,
    poorChasingRecord: false,
    lowerOrderAverageRuns: 0,
    weakLowerOrder: false,
    recommendedExploitation: [],
  },
  keyPlayerImpactAnalysis: {
    topImpactPlayers: [],
    matchWinningPerformances: [],
    clutchPerformanceIndicator: [],
    playerVsOpponentRecord: [],
  },
  scenarioSimulation: [],
  aiStrategyInsights: [],
};

const Strategist = () => {
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();

  const [loading, setLoading] = useState(true);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [error, setError] = useState('');
  const [overview, setOverview] = useState({
    pointsTable: [],
    qualificationData: [],
    runsMarginDistribution: [],
    wicketsMarginDistribution: [],
  });
  const [insights, setInsights] = useState(defaultStrategistInsights);
  const [venues, setVenues] = useState([]);
  const [selectedVenue, setSelectedVenue] = useState('Neutral Venue');

  const fetchOverview = async () => {
    setLoading(true);
    setError('');
    try {
      const [overviewRes, venueRes] = await Promise.all([
        api.get('/strategist/overview'),
        api.get('/venues'),
      ]);

      const nextOverview = overviewRes.data || {
        pointsTable: [],
        qualificationData: [],
        runsMarginDistribution: [],
        wicketsMarginDistribution: [],
      };
      setOverview(nextOverview);

      const nextVenues = venueRes.data?.venues || [];
      setVenues(nextVenues);
      if (nextVenues.length > 0) {
        setSelectedVenue((prev) => (nextVenues.includes(prev) ? prev : nextVenues[0]));
      }
    } catch (err) {
      console.error(err);
      setError('Unable to load strategist overview.');
    } finally {
      setLoading(false);
    }
  };

  const fetchTeamInsights = async () => {
    if (!selectedTeam || !selectedOpponent || selectedTeam === selectedOpponent) {
      return;
    }

    setLoadingInsights(true);
    setError('');
    try {
      const { data } = await api.get('/strategist/team-insights', {
        params: {
          team: selectedTeam,
          opponent: selectedOpponent,
          venue: selectedVenue,
        },
      });
      setInsights({ ...defaultStrategistInsights, ...(data || {}) });
    } catch (err) {
      console.error(err);
      setError('Unable to load strategist team insights for the selected matchup.');
      setInsights(defaultStrategistInsights);
    } finally {
      setLoadingInsights(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  useEffect(() => {
    if (!loading && selectedTeam && selectedOpponent && selectedTeam !== selectedOpponent) {
      fetchTeamInsights();
    }
  }, [loading, selectedTeam, selectedOpponent, selectedVenue]);

  const pointsTable = overview.pointsTable || [];
  const qualData = overview.qualificationData || [];
  const runMargins = overview.runsMarginDistribution || [];
  const wicketMargins = overview.wicketsMarginDistribution || [];

  const selectedTeamRank = useMemo(() => {
    const row = pointsTable.find((r) => r.Team === selectedTeam);
    return row ? row.Rank : null;
  }, [pointsTable, selectedTeam]);

  const selectedTeamQual = useMemo(() => {
    const row = qualData.find((entry) => entry.team === selectedTeam);
    return row ? row.qualPct : insights.qualificationProbability?.probabilityPct || 0;
  }, [qualData, selectedTeam, insights.qualificationProbability]);

  if (loading) {
    return <div className="text-gray-500">Loading strategist dashboard from live data...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tournament Strategist Dashboard</h1>
        <p className="text-gray-500 mt-2">Qualification edge, toss strategy, matchup weaknesses, impact players, and scenario planning</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Team</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            disabled={matchupLoading || teams.length === 0}
          >
            {teams.map((team) => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Opponent</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={selectedOpponent}
            onChange={(e) => setSelectedOpponent(e.target.value)}
            disabled={matchupLoading || teams.length <= 1}
          >
            {teams.filter((team) => team !== selectedTeam).map((team) => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Venue Context</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2"
            value={selectedVenue}
            onChange={(e) => setSelectedVenue(e.target.value)}
          >
            {venues.map((venue) => (
              <option key={venue} value={venue}>{venue}</option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={fetchTeamInsights}
            disabled={loadingInsights || !selectedTeam || !selectedOpponent || selectedTeam === selectedOpponent}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-60"
          >
            {loadingInsights ? 'Refreshing...' : 'Refresh Strategy'}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <p className="text-xs text-gray-500">Qualification Probability</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{selectedTeamQual}%</p>
          <p className="text-sm text-gray-600 mt-1">
            Rank #{insights.qualificationProbability?.currentRank || selectedTeamRank || 'N/A'} | Pts {insights.qualificationProbability?.currentPoints || 0} | NRR {Number(insights.qualificationProbability?.currentNrr || 0).toFixed(3)}
          </p>
          <p className="text-xs text-gray-500 mt-2">Top-4 cutoff points: {insights.qualificationProbability?.playoffCutoffPoints || 0}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-5 lg:col-span-2">
          <p className="text-xs text-gray-500">Match Strategy Overview</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
            <MetricCell label="Overall Win %" value={`${insights.matchStrategyOverview?.overallWinPct || 0}%`} />
            <MetricCell label="Recent Win %" value={`${insights.matchStrategyOverview?.recentWinPct || 0}%`} />
            <MetricCell label="H2H Win %" value={`${insights.matchStrategyOverview?.headToHeadWinPct || 0}%`} />
            <MetricCell label="NRR" value={Number(insights.matchStrategyOverview?.nrr || 0).toFixed(3)} />
            <MetricCell label="Avg Team Score" value={Number(insights.matchStrategyOverview?.averageTeamScore || 0).toFixed(1)} />
            <MetricCell label="Powerplay RR" value={Number(insights.matchStrategyOverview?.powerplayRunRate || 0).toFixed(2)} />
            <MetricCell label="Middle RR" value={Number(insights.matchStrategyOverview?.middleRunRate || 0).toFixed(2)} />
            <MetricCell label="Death RR" value={Number(insights.matchStrategyOverview?.deathRunRate || 0).toFixed(2)} />
          </div>
          <p className="text-sm text-gray-700 mt-3">
            Strategy Index: <span className="font-semibold text-gray-900">{insights.matchStrategyOverview?.strategyIndex || 0}</span>
          </p>
          <p className="text-sm text-gray-600">{insights.matchStrategyOverview?.strategySignal || 'No strategy signal available.'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Optimal Toss Strategy</h2>
          <div className="grid grid-cols-2 gap-3">
            <MetricCell label="Win % Batting First" value={`${insights.optimalTossStrategy?.batFirstWinPct || 0}%`} />
            <MetricCell label="Win % Chasing" value={`${insights.optimalTossStrategy?.chasingWinPct || 0}%`} />
            <MetricCell label="Bat First Matches" value={`${insights.optimalTossStrategy?.batFirstMatches || 0}`} />
            <MetricCell label="Chasing Matches" value={`${insights.optimalTossStrategy?.chasingMatches || 0}`} />
          </div>
          <p className="text-sm text-gray-700 mt-3">Venue Avg 1st Innings: <span className="font-semibold text-gray-900">{insights.optimalTossStrategy?.venueAvgFirstInningsScore || 0}</span></p>
          <p className="text-sm text-gray-700 mt-1">
            Recommended toss decision: <span className="font-semibold text-blue-700">{insights.optimalTossStrategy?.recommendedTossDecision || 'N/A'}</span>
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Opponent Weakness Analysis</h2>
          <div className="grid grid-cols-2 gap-3">
            <MetricCell label="Weakness Type" value={insights.opponentWeaknessAnalysis?.weaknessVsType || 'N/A'} />
            <MetricCell label="Weak Phase" value={insights.opponentWeaknessAnalysis?.weakPhase || 'N/A'} />
            <MetricCell label="Chasing Win %" value={`${insights.opponentWeaknessAnalysis?.chasingWinPct || 0}%`} />
            <MetricCell label="Lower Order Avg" value={`${insights.opponentWeaknessAnalysis?.lowerOrderAverageRuns || 0}`} />
          </div>
          <div className="mt-3 text-sm text-gray-700 space-y-1">
            <p>Powerplay RR: {insights.opponentWeaknessAnalysis?.phaseRunRates?.powerplay || 0}</p>
            <p>Middle RR: {insights.opponentWeaknessAnalysis?.phaseRunRates?.middle || 0}</p>
            <p>Death RR: {insights.opponentWeaknessAnalysis?.phaseRunRates?.death || 0}</p>
          </div>
          <ul className="mt-3 space-y-1 text-sm text-gray-700 list-disc pl-5">
            {(insights.opponentWeaknessAnalysis?.recommendedExploitation || []).map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-5">
        <h2 className="text-lg font-semibold text-gray-800">Key Player Impact Analysis</h2>

        <div className="overflow-auto">
          <table className="w-full min-w-[840px] text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left p-3">Player</th>
                <th className="text-left p-3">Impact Score</th>
                <th className="text-left p-3">Runs</th>
                <th className="text-left p-3">Wickets</th>
                <th className="text-left p-3">Strike Rate</th>
                <th className="text-left p-3">Economy</th>
              </tr>
            </thead>
            <tbody>
              {(insights.keyPlayerImpactAnalysis?.topImpactPlayers || []).map((row) => (
                <tr key={row.player} className="border-b border-gray-100">
                  <td className="p-3 font-medium text-gray-900">{row.player}</td>
                  <td className="p-3">{row.impactScore}</td>
                  <td className="p-3">{row.runs}</td>
                  <td className="p-3">{row.wickets}</td>
                  <td className="p-3">{row.strikeRate}</td>
                  <td className="p-3">{row.economy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-2">Match-winning Performances</h3>
            <ul className="space-y-1 text-sm text-gray-700">
              {(insights.keyPlayerImpactAnalysis?.matchWinningPerformances || []).map((entry) => (
                <li key={entry.player}>{entry.player}: {entry.performances}</li>
              ))}
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-2">Clutch Performance Indicator</h3>
            <ul className="space-y-1 text-sm text-gray-700">
              {(insights.keyPlayerImpactAnalysis?.clutchPerformanceIndicator || []).map((entry) => (
                <li key={entry.player}>{entry.player}: {entry.indicator} ({entry.clutchWins} clutch wins)</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="overflow-auto">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">Player vs Opponent Record</h3>
          <table className="w-full min-w-[820px] text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left p-3">Player</th>
                <th className="text-left p-3">Runs vs Opp</th>
                <th className="text-left p-3">Wickets vs Opp</th>
                <th className="text-left p-3">SR vs Opp</th>
                <th className="text-left p-3">Economy vs Opp</th>
                <th className="text-left p-3">Matchup Score</th>
              </tr>
            </thead>
            <tbody>
              {(insights.keyPlayerImpactAnalysis?.playerVsOpponentRecord || []).map((row) => (
                <tr key={row.player} className="border-b border-gray-100">
                  <td className="p-3 font-medium text-gray-900">{row.player}</td>
                  <td className="p-3">{row.runsVsOpponent}</td>
                  <td className="p-3">{row.wicketsVsOpponent}</td>
                  <td className="p-3">{row.strikeRateVsOpponent}</td>
                  <td className="p-3">{row.economyVsOpponent}</td>
                  <td className="p-3">{row.matchupScore}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Scenario Simulation</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(insights.scenarioSimulation || []).map((scenario) => (
            <div key={scenario.scenarioId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <p className="text-sm font-semibold text-gray-900">{scenario.label}</p>
              <p className="text-sm text-gray-700 mt-1">Projected Rank: #{scenario.projectedRank}</p>
              <p className="text-sm text-gray-700">Projected NRR: {Number(scenario.projectedNrr || 0).toFixed(3)}</p>
              <p className="text-sm text-gray-700">Qualification: {scenario.qualificationProbability}%</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">AI Strategy Insights</h2>
        <ul className="space-y-2 list-disc pl-5 text-sm text-gray-700">
          {(insights.aiStrategyInsights || []).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">📋 Current Points Table</h2>
        <div className="overflow-auto max-h-[460px] rounded-lg border border-gray-100">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-gray-50 text-gray-700 border-b border-gray-200 sticky top-0 z-10">
              <tr>
                <th className="text-left p-3">Rank</th>
                <th className="text-left p-3">Team</th>
                <th className="text-left p-3">P</th>
                <th className="text-left p-3">W</th>
                <th className="text-left p-3">L</th>
                <th className="text-left p-3">Pts</th>
                <th className="text-left p-3">NRR</th>
              </tr>
            </thead>
            <tbody>
              {pointsTable.map((row) => (
                <tr
                  key={row.Team}
                  className={`border-b border-gray-100 ${row.Rank <= 4 ? 'bg-emerald-50' : 'bg-white'}`}
                >
                  <td className="p-3 font-semibold text-gray-700">{row.Rank}</td>
                  <td className="p-3 font-medium text-gray-900">{row.Team}</td>
                  <td className="p-3">{row.P}</td>
                  <td className="p-3">{row.W}</td>
                  <td className="p-3">{row.L}</td>
                  <td className="p-3 font-semibold">{row.Pts}</td>
                  <td className="p-3">{Number(row.NRR).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-500 mt-3">Top 4 teams are highlighted as projected knockout qualifiers.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">🎯 Qualification Probability</h2>
          <p className="text-sm text-gray-500 mb-4">Projected top-4 qualification probability (%) by current rank, points, and NRR cushion.</p>
          <div className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="team" angle={-25} textAnchor="end" height={70} interval={0} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="qualPct" radius={[6, 6, 0, 0]}>
                  {qualData.map((entry) => (
                    <Cell key={entry.team} fill={entry.qualPct >= 60 ? '#10b981' : entry.qualPct >= 40 ? '#f59e0b' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">📈 Selected Team Snapshot</h2>
          <p className="text-sm text-gray-500 mb-4">Centralized team selection currently set to {selectedTeam || 'N/A'} vs {selectedOpponent || 'N/A'}.</p>
          <div className="grid grid-cols-2 gap-3">
            <MetricCell label="Current Rank" value={selectedTeamRank ? `#${selectedTeamRank}` : 'N/A'} />
            <MetricCell label="Qualification %" value={`${selectedTeamQual}%`} />
            <MetricCell label="Opponent" value={selectedOpponent || 'N/A'} />
            <MetricCell label="Venue" value={selectedVenue || 'N/A'} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📊 Distribution of Win by Runs</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={runMargins}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="margin" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📊 Distribution of Win by Wickets</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wicketMargins}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="margin" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

const MetricCell = ({ label, value }) => (
  <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
    <p className="text-xs text-gray-500">{label}</p>
    <p className="text-sm font-semibold text-gray-900 mt-1">{value}</p>
  </div>
);

export default Strategist;
