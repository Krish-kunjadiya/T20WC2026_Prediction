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

const emptyInsights = {
  expectedFirstInningsScore: { mean: 0, q25: 0, q75: 0, samples: 0 },
  venuePerformanceIndex: { winPct: 0, matches: 0 },
  headToHeadDominance: { wins: 0, matches: 0, winPct: 50 },
  tossImpactAnalysis: { batFirstWinPct: 0, chasingWinPct: 0, batFirstMatches: 0, chasingMatches: 0 },
  teamStrengthComparison: {
    battingIndex: 0,
    opponentBowlingIndex: 0,
    differential: 0,
    opponentBattingIndex: 0,
    teamBowlingIndex: 0,
    reverseDifferential: 0,
  },
  upsetProbabilityIndicator: { favourite: 'N/A', underdog: 'N/A', upsetPct: 0, riskLevel: 'Low' },
  phaseWiseRunScoringEfficiency: [],
  bowlingPressureMetric: { dotBallPct: 0, wicketFrequencyPct: 0, pressureScore: 0 },
  qualificationProbability: { probabilityPct: 0 },
};

const Analyst = () => {
  const [meta, setMeta] = useState({ teams: [], venues: [] });
  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');
  const [venue, setVenue] = useState('Neutral Venue');
  const [tossWinner, setTossWinner] = useState('');
  const [tossDecision, setTossDecision] = useState('bat');

  const [winProb, setWinProb] = useState(null);
  const [insights, setInsights] = useState(emptyInsights);
  const [loading, setLoading] = useState(false);
  const [lastRunKey, setLastRunKey] = useState('');

  useEffect(() => {
    const loadMeta = async () => {
      try {
        const { data } = await api.get('/analyst/meta');
        const teams = data.teams || [];
        const venues = data.venues || [];
        setMeta({ teams, venues });

        if (teams.length >= 2) {
          setTeamA(teams[0]);
          setTeamB(teams[1]);
          setTossWinner(teams[0]);
        }
        if (venues.length > 0) {
          setVenue(venues[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };

    loadMeta();
  }, []);

  const canRun = teamA && teamB && teamA !== teamB;
  const selectionKey = `${teamA}|${teamB}|${venue}|${tossWinner}|${tossDecision}`;
  const needsRefresh = Boolean(lastRunKey) && lastRunKey !== selectionKey;

  const runAnalysis = async () => {
    if (!canRun) return;

    setLoading(true);
    try {
      const [winRes, insightsRes] = await Promise.all([
        api.post('/analyst/win-probability', {
          team_a: teamA,
          team_b: teamB,
          toss_winner: tossWinner || teamA,
          toss_decision: tossDecision,
          venue,
          is_knockout: 0,
        }),
        api.get('/analyst/insights', {
          params: {
            team: teamA,
            opponent: teamB,
            venue,
            toss_winner: tossWinner || teamA,
            toss_decision: tossDecision,
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

  const strengthData = useMemo(
    () => [
      {
        metric: 'Team Batting vs Opp Bowling',
        value: insights.teamStrengthComparison?.differential || 0,
      },
      {
        metric: 'Opp Batting vs Team Bowling',
        value: insights.teamStrengthComparison?.reverseDifferential || 0,
      },
    ],
    [insights.teamStrengthComparison]
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">📈 Team Analyst Dashboard</h1>
        <p className="text-gray-500 mt-2">Win probability, venue intelligence, H2H dominance, and tactical efficiency</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <div>
          <label className="block text-sm text-gray-700 mb-1">Team A</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={teamA} onChange={(e) => setTeamA(e.target.value)}>
            {(meta.teams || []).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Team B</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={teamB} onChange={(e) => setTeamB(e.target.value)}>
            {(meta.teams || []).filter((t) => t !== teamA).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Venue</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={venue} onChange={(e) => setVenue(e.target.value)}>
            {(meta.venues || []).map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Toss Winner</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={tossWinner} onChange={(e) => setTossWinner(e.target.value)}>
            {[teamA, teamB].filter(Boolean).map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Toss Decision</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={tossDecision} onChange={(e) => setTossDecision(e.target.value)}>
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
        {needsRefresh && (
          <p className="text-sm text-amber-600">Filters changed. Click Get Insights to refresh results.</p>
        )}
      </div>

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
            <p className="text-sm text-gray-600">Matches: {insights.venuePerformanceIndex?.matches || 0}</p>
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

          <div className="bg-white rounded-xl border border-gray-100 p-4 sm:col-span-2">
            <p className="text-xs text-gray-500">Qualification Probability</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{insights.qualificationProbability?.probabilityPct || 0}%</p>
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
                  <Bar dataKey="teamRunRate" fill="#16a34a" name={`${teamA} Run Rate`} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="opponentRunRate" fill="#dc2626" name={`${teamB} Run Rate`} radius={[4, 4, 0, 0]} />
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Team Strength Comparison</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={strengthData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="metric" interval={0} angle={-20} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Batting Index: {insights.teamStrengthComparison?.battingIndex || 0} | Opp Bowling Index: {insights.teamStrengthComparison?.opponentBowlingIndex || 0}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Bowling Pressure Metric</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
              <p className="text-xs text-gray-500">Dot Ball %</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{insights.bowlingPressureMetric?.dotBallPct || 0}</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
              <p className="text-xs text-gray-500">Wicket Frequency %</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{insights.bowlingPressureMetric?.wicketFrequencyPct || 0}</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
              <p className="text-xs text-gray-500">Pressure Score</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{insights.bowlingPressureMetric?.pressureScore || 0}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analyst;
