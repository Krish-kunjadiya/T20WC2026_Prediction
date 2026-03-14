import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import api from '../api';

const TAB_MATCH = 'match';
const TAB_SCORE = 'score';
const TAB_CLUSTERS = 'clusters';
const TAB_RULES = 'rules';
const TAB_UPSET = 'upset';

const ML = () => {
  const [activeTab, setActiveTab] = useState(TAB_MATCH);
  const [teams, setTeams] = useState([]);

  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');
  const [tossWin, setTossWin] = useState('');
  const [tossDec, setTossDec] = useState('bat');
  const [prediction, setPrediction] = useState(null);

  const [scoreParams, setScoreParams] = useState({
    total_balls: 120,
    wickets_lost: 1,
    sixes: 5,
    fours: 10,
    pp_runs: 50,
  });
  const [scorePred, setScorePred] = useState(null);
  const [scoreError, setScoreError] = useState('');

  const [clusters, setClusters] = useState([]);
  const [topByType, setTopByType] = useState({});
  const [selectedClusterType, setSelectedClusterType] = useState('');

  const [rules, setRules] = useState([]);

  const [favTeam, setFavTeam] = useState('');
  const [underdogTeam, setUnderdogTeam] = useState('');
  const [upsetTossWinner, setUpsetTossWinner] = useState('');
  const [upsetResult, setUpsetResult] = useState(null);

  const [loadingClusters, setLoadingClusters] = useState(false);
  const [loadingRules, setLoadingRules] = useState(false);

  useEffect(() => {
    const loadTeams = async () => {
      try {
        const { data } = await api.get('/teams');
        const loadedTeams = data.teams || [];
        setTeams(loadedTeams);
        if (loadedTeams.length >= 2) {
          setTeamA(loadedTeams[0]);
          setTeamB(loadedTeams[1]);
          setTossWin(loadedTeams[0]);
          setFavTeam(loadedTeams[0]);
          setUnderdogTeam(loadedTeams[1]);
          setUpsetTossWinner(loadedTeams[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadTeams();
  }, []);

  useEffect(() => {
    if (activeTab !== TAB_CLUSTERS || clusters.length > 0) return;
    const loadClusters = async () => {
      setLoadingClusters(true);
      try {
        const { data } = await api.get('/ml/player-clusters');
        const clusterRows = data.clusters || [];
        setClusters(clusterRows);
        setTopByType(data.topByType || {});
        const keys = Object.keys(data.topByType || {});
        if (keys.length > 0) {
          setSelectedClusterType(keys[0]);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingClusters(false);
      }
    };
    loadClusters();
  }, [activeTab, clusters.length]);

  useEffect(() => {
    if (activeTab !== TAB_RULES || rules.length > 0) return;
    const loadRules = async () => {
      setLoadingRules(true);
      try {
        const { data } = await api.get('/ml/association-rules');
        setRules(data.rules || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingRules(false);
      }
    };
    loadRules();
  }, [activeTab, rules.length]);

  const tabs = [
    { key: TAB_MATCH, label: '🎯 Match Predictor' },
    { key: TAB_SCORE, label: '📊 Score Predictor' },
    { key: TAB_CLUSTERS, label: '👥 Player Clusters' },
    { key: TAB_RULES, label: '🔗 Association Rules' },
    { key: TAB_UPSET, label: '⚠️ Upset Detector' },
  ];

  const handlePredictMatch = async () => {
    try {
      const { data } = await api.post('/predict/match', {
        team_a: teamA,
        team_b: teamB,
        toss_winner: tossWin,
        toss_decision: tossDec,
        is_knockout: 0,
      });
      setPrediction(data);
    } catch (err) {
      console.error(err);
      setPrediction(null);
    }
  };

  const handlePredictScore = async () => {
    setScoreError('');
    try {
      const payload = {
        total_balls: Number(scoreParams.total_balls),
        wickets_lost: Number(scoreParams.wickets_lost),
        sixes: Number(scoreParams.sixes),
        fours: Number(scoreParams.fours),
        pp_runs: Number(scoreParams.pp_runs),
      };

      if (payload.total_balls < 30 || payload.total_balls > 120) {
        setScoreError('Balls played must be between 30 and 120.');
        setScorePred(null);
        return;
      }
      if (payload.wickets_lost < 0 || payload.wickets_lost > 10) {
        setScoreError('Wickets lost must be between 0 and 10.');
        setScorePred(null);
        return;
      }
      if (payload.sixes < 0 || payload.fours < 0 || payload.pp_runs < 0) {
        setScoreError('Sixes, fours, and powerplay runs cannot be negative.');
        setScorePred(null);
        return;
      }
      if (payload.sixes + payload.fours > payload.total_balls) {
        setScoreError('Sixes + fours cannot exceed total balls played.');
        setScorePred(null);
        return;
      }

      payload.pp_run_rate = payload.pp_runs / 6;
      payload.boundary_pct = (payload.sixes + payload.fours) / Math.max(payload.total_balls, 1);

      const { data } = await api.post('/predict/score', payload);
      setScorePred(data);
    } catch (err) {
      console.error(err);
      const detail = err?.response?.data?.detail;
      setScoreError(typeof detail === 'string' ? detail : 'Unable to predict score for the current input.');
      setScorePred(null);
    }
  };

  const handleUpsetPredict = async () => {
    try {
      const { data } = await api.post('/predict/upset', {
        favourite_team: favTeam,
        underdog_team: underdogTeam,
        toss_winner: upsetTossWinner,
        toss_bat_first: 1,
        is_knockout: 0,
      });
      setUpsetResult(data);
    } catch (err) {
      console.error(err);
      setUpsetResult(null);
    }
  };

  const probabilityData = useMemo(() => {
    if (!prediction) return [];
    return [
      { team: prediction.team_a, probability: prediction.prob_team_a },
      { team: prediction.team_b, probability: prediction.prob_team_b },
    ];
  }, [prediction]);

  const selectedTopPlayers = selectedClusterType ? (topByType[selectedClusterType] || []) : [];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🤖 ML Predictions Dashboard</h1>
        <p className="text-gray-500 mt-2">Match Outcome | Score | Clustering | Association | Upset detection</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-2 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 rounded-md text-sm font-medium ${
              activeTab === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === TAB_MATCH && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">🎯 Match Outcome Predictor (XGBoost)</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Team A</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={teamA} onChange={(e) => setTeamA(e.target.value)}>
                  {teams.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Team B</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={teamB} onChange={(e) => setTeamB(e.target.value)}>
                  {teams.filter((t) => t !== teamA).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Toss Winner</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={tossWin} onChange={(e) => setTossWin(e.target.value)}>
                  {[teamA, teamB].filter(Boolean).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">Toss Decision</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={tossDec} onChange={(e) => setTossDec(e.target.value)}>
                  <option value="bat">Bat</option>
                  <option value="field">Field</option>
                </select>
              </div>
            </div>
            <button onClick={handlePredictMatch} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
              Predict Match Outcome
            </button>
            {prediction && (
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                <p className="text-sm text-gray-500">Predicted Winner</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{prediction.predicted_winner}</p>
                {prediction.confidence !== undefined && (
                  <p className="text-xs text-gray-600 mt-2">Confidence: {prediction.confidence}%</p>
                )}
                {prediction.context_prob_team_a !== undefined && prediction.model_prob_team_a !== null && (
                  <p className="text-xs text-gray-600 mt-1">
                    Context: {prediction.context_prob_team_a}% | Model: {prediction.model_prob_team_a}%
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Win Probability</h2>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={probabilityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="team" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Bar dataKey="probability" radius={[6, 6, 0, 0]}>
                    {probabilityData.map((entry) => (
                      <Cell
                        key={entry.team}
                        fill={entry.team === prediction?.predicted_winner ? '#10b981' : '#f43f5e'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_SCORE && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">📊 First Innings Score Predictor (LightGBM)</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-700 mb-1">Powerplay Runs</label>
              <input type="number" min="0" max="120" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.pp_runs} onChange={(e) => setScoreParams({ ...scoreParams, pp_runs: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Wickets Lost</label>
              <input type="number" min="0" max="10" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.wickets_lost} onChange={(e) => setScoreParams({ ...scoreParams, wickets_lost: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Balls Played</label>
              <input type="number" min="30" max="120" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.total_balls} onChange={(e) => setScoreParams({ ...scoreParams, total_balls: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Sixes</label>
              <input type="number" min="0" max="36" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.sixes} onChange={(e) => setScoreParams({ ...scoreParams, sixes: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Fours</label>
              <input type="number" min="0" max="60" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.fours} onChange={(e) => setScoreParams({ ...scoreParams, fours: e.target.value })} />
            </div>
          </div>
          <button onClick={handlePredictScore} className="bg-emerald-600 text-white px-4 py-2 rounded-md hover:bg-emerald-700">
            Predict Final Score
          </button>
          {scoreError && <p className="text-sm text-red-600">{scoreError}</p>}
          {scorePred && (
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
              <p className="text-sm text-gray-500">Predicted Score</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{scorePred.predicted_score}</p>
              <p className="text-sm text-gray-600 mt-1">{String(scorePred.classification || '').replace('_', ' ')}</p>
              {scorePred.avg_reference_score !== undefined && (
                <p className="text-xs text-gray-500 mt-2">Tournament average reference: {scorePred.avg_reference_score}</p>
              )}
              {scorePred.historical_sample_size !== undefined && (
                <p className="text-xs text-gray-500">Historical similar samples: {scorePred.historical_sample_size}</p>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === TAB_CLUSTERS && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-800">👥 Player Role Clusters (K-Means)</h2>
            {loadingClusters ? (
              <p className="text-sm text-gray-500 mt-2">Loading clusters...</p>
            ) : (
              <div className="mt-4 h-[420px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" dataKey="strike_rate_live" name="Strike Rate" />
                    <YAxis type="number" dataKey="wickets" name="Wickets" />
                    <ZAxis type="number" dataKey="total_runs" range={[20, 250]} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter name="Players" data={clusters} fill="#3b82f6" fillOpacity={0.55} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <div className="flex items-center gap-3">
              <h3 className="text-md font-semibold text-gray-800">Top Players by Cluster</h3>
              <select className="border border-gray-300 rounded-md p-2 text-sm" value={selectedClusterType} onChange={(e) => setSelectedClusterType(e.target.value)}>
                {Object.keys(topByType).map((key) => (
                  <option key={key} value={key}>{key}</option>
                ))}
              </select>
            </div>
            <div className="overflow-auto mt-4">
              <table className="w-full text-sm min-w-[680px]">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left p-3">Player</th>
                    <th className="text-left p-3">Runs</th>
                    <th className="text-left p-3">Strike Rate</th>
                    <th className="text-left p-3">Wickets</th>
                    <th className="text-left p-3">Economy</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTopPlayers.map((p) => (
                    <tr key={`${p.player_name}-${p.cluster}`} className="border-b border-gray-100">
                      <td className="p-3 font-medium text-gray-900">{p.player_name}</td>
                      <td className="p-3">{p.total_runs}</td>
                      <td className="p-3">{Number(p.strike_rate_live).toFixed(2)}</td>
                      <td className="p-3">{p.wickets}</td>
                      <td className="p-3">{Number(p.economy_live).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_RULES && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-800">🔗 Winning Condition Rules (Apriori)</h2>
            {loadingRules ? (
              <p className="text-sm text-gray-500 mt-2">Loading association rules...</p>
            ) : (
              <div className="overflow-auto mt-4">
                <table className="w-full text-sm min-w-[880px]">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left p-3">Antecedents</th>
                      <th className="text-left p-3">Consequents</th>
                      <th className="text-left p-3">Support %</th>
                      <th className="text-left p-3">Confidence %</th>
                      <th className="text-left p-3">Lift</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.map((r, idx) => (
                      <tr key={idx} className="border-b border-gray-100">
                        <td className="p-3 text-gray-700">{String(r.antecedents)}</td>
                        <td className="p-3 text-gray-700">{String(r.consequents)}</td>
                        <td className="p-3">{r.support_pct}</td>
                        <td className="p-3">{r.confidence_pct}</td>
                        <td className="p-3">{r.lift}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h3 className="text-md font-semibold text-gray-800 mb-2">Top Rule Confidence</h3>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rules.slice(0, 8)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="antecedents" hide />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => `${value}%`} />
                  <Bar dataKey="confidence_pct" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_UPSET && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">⚠️ Upset Probability Detector</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-700 mb-1">Favourite Team</label>
              <select className="w-full border border-gray-300 rounded-md p-2" value={favTeam} onChange={(e) => setFavTeam(e.target.value)}>
                {teams.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Underdog Team</label>
              <select className="w-full border border-gray-300 rounded-md p-2" value={underdogTeam} onChange={(e) => setUnderdogTeam(e.target.value)}>
                {teams.filter((t) => t !== favTeam).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Toss Winner</label>
              <select className="w-full border border-gray-300 rounded-md p-2" value={upsetTossWinner} onChange={(e) => setUpsetTossWinner(e.target.value)}>
                {[favTeam, underdogTeam].filter(Boolean).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <button onClick={handleUpsetPredict} className="bg-amber-600 text-white px-4 py-2 rounded-md hover:bg-amber-700">
            Calculate Upset Probability
          </button>

          {upsetResult && (
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4 space-y-2">
              <p className="text-sm text-gray-500">Upset Risk</p>
              <p className="text-3xl font-bold text-gray-900">{upsetResult.upsetProbability}%</p>
              <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full ${upsetResult.upsetProbability > 35 ? 'bg-red-500' : 'bg-emerald-500'}`}
                  style={{ width: `${Math.min(100, upsetResult.upsetProbability)}%` }}
                />
              </div>
              <p className="text-sm font-medium text-gray-700">{upsetResult.riskLevel}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ML;
