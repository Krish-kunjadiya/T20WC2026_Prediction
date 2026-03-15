import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const emptyInsights = {
  expectedFirstInningsScore: { mean: 0, q25: 0, q75: 0, samples: 0 },
  venuePerformanceIndex: { winPct: 0, matches: 0 },
  headToHeadDominance: { wins: 0, matches: 0, winPct: 50 },
  tossImpactAnalysis: { batFirstWinPct: 0, chasingWinPct: 0, batFirstMatches: 0, chasingMatches: 0 },
  upsetProbabilityIndicator: { favourite: 'N/A', underdog: 'N/A', upsetPct: 0, riskLevel: 'Low' },
  phaseWiseRunScoringEfficiency: [],
  filtersApplied: { sampledMatches: 0, effectiveSampledMatches: 0, fallbackUsed: false },
};

const canonicalPair = (teamA, teamB) => [teamA, teamB].map((team) => String(team || '').trim()).sort((a, b) => a.localeCompare(b));

const Analyst = () => {
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();
  const [meta, setMeta] = useState({ venues: [] });
  const [venue, setVenue] = useState('Neutral Venue');
  const [useVenueFilter, setUseVenueFilter] = useState(false);
  const [useTossFilter, setUseTossFilter] = useState(false);
  const [tossResultFilter, setTossResultFilter] = useState('all');
  const [tossDecisionFilter, setTossDecisionFilter] = useState('any');

  const [winProb, setWinProb] = useState(null);
  const [insights, setInsights] = useState(emptyInsights);
  const [loading, setLoading] = useState(false);
  const [lastRunKey, setLastRunKey] = useState('');

  useEffect(() => {
    const loadMeta = async () => {
      try {
        const { data } = await api.get('/analyst/meta');
        const venues = data.venues || [];
        setMeta({ venues });

        if (venues.length > 0) {
          setVenue(venues[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };

    loadMeta();
  }, []);

  const canRun = selectedTeam && selectedOpponent && selectedTeam !== selectedOpponent;
  const [pairA, pairB] = canonicalPair(selectedTeam, selectedOpponent);
  const selectionKey = `${pairA}|${pairB}|${venue}|${useVenueFilter}|${useTossFilter}|${tossResultFilter}|${tossDecisionFilter}`;
  const needsRefresh = Boolean(lastRunKey) && lastRunKey !== selectionKey;

  const runAnalysis = async () => {
    if (!canRun) return;

    setLoading(true);
    try {
      const [winRes, insightsRes] = await Promise.all([
        api.post('/analyst/win-probability', {
          team_a: pairA,
          team_b: pairB,
          toss_winner: pairA,
          toss_decision: 'bat',
          venue,
          is_knockout: 0,
          use_venue_filter: useVenueFilter,
          use_toss_filter: useTossFilter,
          toss_result_filter: tossResultFilter,
          toss_decision_filter: tossDecisionFilter,
        }),
        api.get('/analyst/insights', {
          params: {
            team: pairA,
            opponent: pairB,
            venue,
            toss_winner: pairA,
            toss_decision: 'bat',
            use_venue_filter: useVenueFilter,
            use_toss_filter: useTossFilter,
            toss_result_filter: tossResultFilter,
            toss_decision_filter: tossDecisionFilter,
          },
        }),
      ]);

      setWinProb(winRes.data || null);
      setInsights(insightsRes.data || emptyInsights);
      setLastRunKey(selectionKey);
    } catch (err) {
      console.error(err);
      setWinProb(null);
      setInsights(emptyInsights);
    } finally {
      setLoading(false);
    }
  };

  const probabilityChart = useMemo(() => {
    if (!winProb) return [];
    return [
      { team: winProb.teamA, probability: winProb.probTeamA },
      { team: winProb.teamB, probability: winProb.probTeamB },
    ];
  }, [winProb]);

  const tossImpactData = useMemo(
    () => [
      { label: 'Bat First', winPct: insights.tossImpactAnalysis?.batFirstWinPct || 0 },
      { label: 'Chasing', winPct: insights.tossImpactAnalysis?.chasingWinPct || 0 },
    ],
    [insights.tossImpactAnalysis]
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Team Analyst Dashboard</h1>
        <p className="text-gray-500 mt-2">Win probability, venue-aware/toss-aware analysis, and pair-level tactical insights</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-700 mb-1">Team A</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            disabled={matchupLoading || teams.length === 0}
          >
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Team B</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={selectedOpponent}
            onChange={(e) => setSelectedOpponent(e.target.value)}
            disabled={matchupLoading || teams.length <= 1}
          >
            {teams.filter((t) => t !== selectedTeam).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={useVenueFilter} onChange={(e) => setUseVenueFilter(e.target.checked)} />
          Use selected venue for analysis
        </label>

        <div>
          <label className="block text-xs text-gray-600 mb-1">Venue</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            disabled={!useVenueFilter}
          >
            {(meta.venues || []).map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={useTossFilter} onChange={(e) => setUseTossFilter(e.target.checked)} />
          Use toss-based historical filter
        </label>

        <div>
          <label className="block text-xs text-gray-600 mb-1">Toss Result Filter</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={tossResultFilter}
            onChange={(e) => setTossResultFilter(e.target.value)}
            disabled={!useTossFilter}
          >
            <option value="all">All</option>
            <option value="won">Team Won Toss</option>
            <option value="lost">Team Lost Toss</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-600 mb-1">Toss Decision Filter</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
            value={tossDecisionFilter}
            onChange={(e) => setTossDecisionFilter(e.target.value)}
            disabled={!useTossFilter}
          >
            <option value="any">Any</option>
            <option value="bat">Bat First</option>
            <option value="field">Field First</option>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={runAnalysis}
          disabled={!canRun || loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md disabled:opacity-60"
        >
          {loading ? 'Calculating...' : 'Get Insights'}
        </button>
        {winProb?.confidence !== undefined && (
          <p className="text-sm text-gray-600">Confidence: {winProb.confidence}%</p>
        )}
        <p className="text-sm text-gray-600">
          Sampled matches: {insights.filtersApplied?.sampledMatches || 0}
          {insights.filtersApplied?.fallbackUsed ? ` (fallback used: ${insights.filtersApplied?.effectiveSampledMatches || 0})` : ''}
        </p>
        {insights.filtersApplied?.fallbackUsed && (
          <p className="text-sm text-amber-700">No rows for selected filters. Showing pair-level history fallback.</p>
        )}
        {needsRefresh && (
          <p className="text-sm text-amber-600">Filters changed. Click Get Insights to refresh results.</p>
        )}
      </div>

      <p className="text-xs text-gray-500">Team pair is normalized to a canonical order so A vs B and B vs A return the same analysis.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Match Win Probability Prediction</h2>
          <div className="h-[320px]">
            {probabilityChart.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={probabilityChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="team" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="probability" fill="#2563eb" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">Run simulation to view win probabilities.</p>
            )}
          </div>
          {winProb && (
            <p className="text-sm text-gray-600 mt-2">
              Predicted winner: <span className="font-semibold text-gray-900">{winProb.predictedWinner}</span>
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Expected 1st Innings Score</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{insights.expectedFirstInningsScore?.mean || 0}</p>
            <p className="text-sm text-gray-600">P25-P75: {insights.expectedFirstInningsScore?.q25 || 0} - {insights.expectedFirstInningsScore?.q75 || 0}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Venue Performance Index</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{insights.venuePerformanceIndex?.winPct || 0}%</p>
            <p className="text-sm text-gray-600">Matches: {insights.venuePerformanceIndex?.matches || 0} ({useVenueFilter ? 'Venue-filtered' : 'All venues'})</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Head-to-Head Dominance</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{insights.headToHeadDominance?.winPct || 0}%</p>
            <p className="text-sm text-gray-600">{insights.headToHeadDominance?.wins || 0}/{insights.headToHeadDominance?.matches || 0} wins</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Upset Probability</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{insights.upsetProbabilityIndicator?.upsetPct || 0}%</p>
            <p className="text-sm text-gray-600">{insights.upsetProbabilityIndicator?.riskLevel || 'Low'}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Phase-wise Run Scoring Efficiency</h2>
          <div className="h-[320px]">
            {(insights.phaseWiseRunScoringEfficiency || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={insights.phaseWiseRunScoringEfficiency}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="phase" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="teamRunRate" fill="#16a34a" name={`${selectedTeam} Run Rate`} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="opponentRunRate" fill="#dc2626" name={`${selectedOpponent} Run Rate`} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">No phase data available.</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Toss Impact Analysis</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tossImpactData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="winPct" fill="#f59e0b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Bat first matches: {insights.tossImpactAnalysis?.batFirstMatches || 0} | Chasing matches: {insights.tossImpactAnalysis?.chasingMatches || 0}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Analyst;
