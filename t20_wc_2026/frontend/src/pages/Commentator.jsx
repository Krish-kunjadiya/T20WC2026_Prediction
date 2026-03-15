import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const defaultOverview = {
  topRunScorers: [],
  topWicketTakers: [],
  mostSixes: [],
  teamTotalRuns: [],
  recordHighlights: {
    highestIndividualScore: 0,
    highestTeamTotal: 0,
    totalSixes: 0,
    totalFours: 0,
  },
};

const defaultInsights = {
  topRunScorer: { player: 'N/A', runs: 0 },
  milestoneAlert: 'No milestone data.',
  bestPerformerAtVenue: { player: 'N/A', runs: 0, wickets: 0, score: 0 },
  fastestScorer: { player: 'N/A', strikeRate: 0 },
  recordWatch: 'No record watch data.',
  teamMomentum: { runsLast3Overs: 0, expectedLast3Overs: 0, momentumDelta: 0, indicator: 'Neutral' },
  runRateComparison: { currentRunRate: 0, venueAvgRunRate: 0, delta: 0 },
  bestBowlerVsOpponent: { bowler: 'N/A', wickets: 0, balls: 0 },
  funFact: 'No venue trend found.',
  winProbabilityTimeline: [],
  currentWinProbability: { probTeamA: 50, probTeamB: 50 },
};

const Commentator = () => {
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();
  const [meta, setMeta] = useState({ teams: [], venues: [], matches: [] });
  const [overview, setOverview] = useState(defaultOverview);
  const [liveFeed, setLiveFeed] = useState({ available: false, events: [] });
  const [insights, setInsights] = useState(defaultInsights);

  const [venue, setVenue] = useState('Neutral Venue');
  const [matchId, setMatchId] = useState('');

  const [loadingInsights, setLoadingInsights] = useState(false);
  const [insightsRequested, setInsightsRequested] = useState(false);

  useEffect(() => {
    const loadBase = async () => {
      try {
        const [metaRes, overviewRes, liveRes] = await Promise.all([
          api.get('/commentator/meta'),
          api.get('/commentator/overview'),
          api.get('/commentator/live-feed'),
        ]);

        const loadedMeta = metaRes.data || { teams: [], venues: [], matches: [] };
        setMeta(loadedMeta);
        setOverview(overviewRes.data || defaultOverview);
        setLiveFeed(liveRes.data || { available: false, events: [] });

        const venues = loadedMeta.venues || [];
        const matches = loadedMeta.matches || [];

        if (venues.length > 0) {
          setVenue(venues[0]);
        }
        if (matches.length > 0) {
          setMatchId(matches[0].matchId);
        }
      } catch (err) {
        console.error(err);
      }
    };

    loadBase();
  }, []);

  useEffect(() => {
    const matches = meta.matches || [];
    if (!selectedTeam || !selectedOpponent || !matches.length) {
      return;
    }

    const currentMatch = matches.find((m) => m.matchId === matchId);
    const currentFitsPair =
      currentMatch
      && [currentMatch.team1, currentMatch.team2].includes(selectedTeam)
      && [currentMatch.team1, currentMatch.team2].includes(selectedOpponent);

    if (currentFitsPair) {
      return;
    }

    const preferredMatch = matches.find(
      (m) => [m.team1, m.team2].includes(selectedTeam) && [m.team1, m.team2].includes(selectedOpponent),
    );

    if (preferredMatch && preferredMatch.matchId !== matchId) {
      setMatchId(preferredMatch.matchId);
    }
  }, [meta.matches, selectedTeam, selectedOpponent, matchId]);

  const canGetInsights = selectedTeam && selectedOpponent && selectedTeam !== selectedOpponent;

  const loadInsights = async () => {
    if (!canGetInsights) return;

    setLoadingInsights(true);
    setInsightsRequested(true);
    try {
      const { data } = await api.get('/commentator/insights', {
        params: {
          team: selectedTeam,
          opponent: selectedOpponent,
          venue,
          match_id: matchId || undefined,
        },
      });
      setInsights(data || defaultInsights);
    } catch (err) {
      console.error(err);
      setInsights(defaultInsights);
    } finally {
      setLoadingInsights(false);
    }
  };

  const topLiveEvents = useMemo(() => (liveFeed.events || []).slice(0, 10), [liveFeed.events]);

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🎙️ Commentator & Media Dashboard</h1>
        <p className="text-gray-500 mt-2">Live narrative, milestone alerts, venue records, and momentum intelligence</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">🔴 Live Feed</h2>
        {liveFeed.available && topLiveEvents.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {topLiveEvents.map((event) => (
              <div key={event.event_id} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                <p className="text-xs text-gray-500">Over {event.over_num}.{event.ball_num}</p>
                <p className="text-sm font-semibold text-gray-900 mt-1">{event.batting_team}</p>
                <p className="text-sm text-gray-700">Runs: {event.runs_scored}</p>
                <p className="text-xs text-gray-500">{event.is_wicket ? 'Wicket!' : 'In play'}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Live simulator feed not available. Start simulator to stream ball-by-ball updates.</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm text-gray-700 mb-1">Team</label>
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
          <label className="block text-sm text-gray-700 mb-1">Opponent</label>
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

        <div>
          <label className="block text-sm text-gray-700 mb-1">Venue</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={venue} onChange={(e) => setVenue(e.target.value)}>
            {(meta.venues || []).map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Match Context</label>
          <select className="w-full border border-gray-300 rounded-md p-2" value={matchId} onChange={(e) => setMatchId(e.target.value)}>
            {(meta.matches || []).slice(0, 200).map((m) => (
              <option key={m.matchId} value={m.matchId}>{m.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={loadInsights}
          disabled={!canGetInsights || loadingInsights}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md disabled:opacity-60"
        >
          {loadingInsights ? 'Calculating...' : 'Get Insights'}
        </button>
        {!insightsRequested && (
          <p className="text-sm text-gray-600">Choose filters, then click Get Insights to load analysis.</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">Current Win Probability (During Match)</h2>
            {loadingInsights && <span className="text-sm text-gray-500">Updating...</span>}
          </div>
          <div className="h-[320px]">
            {(insights.winProbabilityTimeline || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={insights.winProbabilityTimeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="over" hide />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="probTeamA" stroke="#2563eb" strokeWidth={2.5} name="Team A %" dot={false} />
                  <Line type="monotone" dataKey="probTeamB" stroke="#16a34a" strokeWidth={2.5} name="Team B %" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">{insightsRequested ? 'No probability timeline for the current match context.' : 'Click Get Insights to build the probability timeline.'}</p>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Current: {selectedTeam || 'Team A'} {insights.currentWinProbability?.probTeamA ?? 50}% | {selectedOpponent || 'Team B'} {insights.currentWinProbability?.probTeamB ?? 50}%
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Top Team Run Scorer</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{insights.topRunScorer?.player || 'N/A'}</p>
            <p className="text-sm text-gray-600">Runs: {insights.topRunScorer?.runs ?? 0}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-xs text-gray-500">Fastest Scorer (Team SR)</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{insights.fastestScorer?.player || 'N/A'}</p>
            <p className="text-sm text-gray-600">SR: {insights.fastestScorer?.strikeRate ?? 0}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4 sm:col-span-2">
            <p className="text-xs text-gray-500">Player Milestone Alert</p>
            <p className="text-sm text-gray-800 mt-1">{insights.milestoneAlert || 'No milestone alert available.'}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-4 sm:col-span-2">
            <p className="text-xs text-gray-500">Best Performer at Venue (Historical)</p>
            <p className="text-sm text-gray-800 mt-1">
              {insights.bestPerformerAtVenue?.player || 'N/A'} | Runs: {insights.bestPerformerAtVenue?.runs ?? 0} | Wickets: {insights.bestPerformerAtVenue?.wickets ?? 0}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Record Watch</p>
          <p className="text-sm text-gray-800 mt-1">{insights.recordWatch || 'No record watch data.'}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Team Momentum Indicator</p>
          <p className="text-sm text-gray-800 mt-1">
            Last 3 overs: {insights.teamMomentum?.runsLast3Overs ?? 0} vs expected {insights.teamMomentum?.expectedLast3Overs ?? 0}
          </p>
          <p className="text-sm font-medium text-gray-900">{insights.teamMomentum?.indicator || 'Neutral'} ({insights.teamMomentum?.momentumDelta ?? 0})</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Historic Comparison</p>
          <p className="text-sm text-gray-800 mt-1">
            Current RR: {insights.runRateComparison?.currentRunRate ?? 0} | Venue RR: {insights.runRateComparison?.venueAvgRunRate ?? 0}
          </p>
          <p className="text-sm font-medium text-gray-900">Delta: {insights.runRateComparison?.delta ?? 0}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Most Successful Bowler vs Opponent</p>
          <p className="text-sm font-semibold text-gray-900 mt-1">{insights.bestBowlerVsOpponent?.bowler || 'N/A'}</p>
          <p className="text-sm text-gray-600">Wickets: {insights.bestBowlerVsOpponent?.wickets ?? 0}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4 lg:col-span-2">
          <p className="text-xs text-gray-500">Fun Fact Generator</p>
          <p className="text-sm text-gray-800 mt-1">{insights.funFact || 'No fun fact available.'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Top Run Scorers (Tournament)</h2>
          <div className="h-[300px]">
            {(overview.topRunScorers || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.topRunScorers}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="player" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="runs" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">No data available.</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Top Wicket Takers (Tournament)</h2>
          <div className="h-[300px]">
            {(overview.topWicketTakers || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.topWicketTakers}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="bowler" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="wickets" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">No data available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Most Sixes by Player</h2>
          <div className="h-[280px]">
            {(overview.mostSixes || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.mostSixes}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="player" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="sixes" fill="#f97316" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">No six-hitting data available.</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Team Total Runs</h2>
          <div className="h-[280px]">
            {(overview.teamTotalRuns || []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.teamTotalRuns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="team" interval={0} angle={-25} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="runs" fill="#06b6d4" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">No team scoring data available.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Highest Individual Score</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{overview.recordHighlights?.highestIndividualScore ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Highest Team Total</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{overview.recordHighlights?.highestTeamTotal ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Total Sixes</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{overview.recordHighlights?.totalSixes ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Total Fours</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{overview.recordHighlights?.totalFours ?? 0}</p>
        </div>
      </div>
    </div>
  );
};

export default Commentator;
