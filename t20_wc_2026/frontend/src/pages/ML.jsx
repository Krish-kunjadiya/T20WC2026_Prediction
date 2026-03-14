import React, { useState, useEffect } from 'react';
import api, { executeQuery } from '../api';

const ML = () => {
  const [teams, setTeams] = useState([]);
  
  // Predictor states
  const [teamA, setTeamA] = useState('');
  const [teamB, setTeamB] = useState('');
  const [tossWin, setTossWin] = useState('');
  const [tossDec, setTossDec] = useState('bat');
  const [prediction, setPrediction] = useState(null);
  
  // Score states
  const [scoreParams, setScoreParams] = useState({
    wickets_lost: 2, sixes: 5, fours: 10, pp_runs: 50
  });
  const [scorePred, setScorePred] = useState(null);

  useEffect(() => {
    api.get('/teams').then(res => {
      setTeams(res.data.teams);
      setTeamA(res.data.teams[0]);
      setTeamB(res.data.teams[1]);
      setTossWin(res.data.teams[0]);
    });
  }, []);

  const handlePredictMatch = async () => {
    try {
      const res = await api.post('/predict/match', {
        team_a: teamA, team_b: teamB, toss_winner: tossWin, toss_decision: tossDec, is_knockout: 0
      });
      setPrediction(res.data);
    } catch(err) {
      console.error(err);
      alert('Failed to get prediction from ML API');
    }
  };

  const handlePredictScore = async () => {
    try {
      const res = await api.post('/predict/score', {
        total_balls: 120,
        wickets_lost: parseInt(scoreParams.wickets_lost),
        sixes: parseInt(scoreParams.sixes),
        fours: parseInt(scoreParams.fours),
        pp_runs: parseInt(scoreParams.pp_runs),
        pp_run_rate: parseInt(scoreParams.pp_runs)/6.0,
        boundary_pct: (parseInt(scoreParams.sixes)*6 + parseInt(scoreParams.fours)*4) / 120.0
      });
      setScorePred(res.data);
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🤖 ML Predictions Dashboard</h1>
        <p className="text-gray-500 mt-2">XGBoost & LightGBM powered Match Outcome and Score predictors.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Match Outcome Predictor */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-6 flex items-center gap-2">
            🎯 Match Outcome Predictor
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Team A</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={teamA} onChange={e=>setTeamA(e.target.value)}>
                  {teams.map(t=><option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Team B</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={teamB} onChange={e=>setTeamB(e.target.value)}>
                  {teams.map(t=><option key={t}>{t}</option>)}
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Toss Winner</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={tossWin} onChange={e=>setTossWin(e.target.value)}>
                  <option value={teamA}>{teamA}</option>
                  <option value={teamB}>{teamB}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Decision</label>
                <select className="w-full border border-gray-300 rounded-md p-2" value={tossDec} onChange={e=>setTossDec(e.target.value)}>
                  <option value="bat">Bat First</option>
                  <option value="field">Field First</option>
                </select>
              </div>
            </div>

            <button onClick={handlePredictMatch} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium p-3 rounded-lg mt-2 transition">
              Run XGBoost Model
            </button>

            {prediction && (
              <div className="mt-4 p-5 bg-gray-50 border border-gray-200 rounded-lg text-center">
                <p className="text-gray-500 mb-2">Predicted Winner</p>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">{prediction.predicted_winner}</h3>
                <div className="flex justify-between items-center px-4 w-full text-sm font-medium">
                  <div className={prediction.predicted_winner === teamA ? 'text-green-600' : 'text-gray-500'}>{teamA}: {prediction.prob_team_a}%</div>
                  <div className={prediction.predicted_winner === teamB ? 'text-green-600' : 'text-gray-500'}>{teamB}: {prediction.prob_team_b}%</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Score Predictor */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-6 flex items-center gap-2">
            📊 First Innings Score Predictor
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Powerplay Runs</label>
                <input type="number" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.pp_runs} onChange={e=>setScoreParams({...scoreParams, pp_runs: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Wickets Lost</label>
                <input type="number" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.wickets_lost} onChange={e=>setScoreParams({...scoreParams, wickets_lost: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Total Sixes expected</label>
                <input type="number" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.sixes} onChange={e=>setScoreParams({...scoreParams, sixes: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Total Fours expected</label>
                <input type="number" className="w-full border border-gray-300 rounded-md p-2" value={scoreParams.fours} onChange={e=>setScoreParams({...scoreParams, fours: e.target.value})} />
              </div>
            </div>

            <button onClick={handlePredictScore} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium p-3 rounded-lg mt-2 transition">
              Run LightGBM Model
            </button>

            {scorePred && (
              <div className="mt-4 p-5 bg-gray-50 border border-gray-200 rounded-lg text-center">
                <p className="text-gray-500 mb-2">Predicted First Innings Score</p>
                <h3 className="text-4xl font-bold text-gray-900 mb-2">{scorePred.predicted_score}</h3>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${scorePred.classification === 'above_avg' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {scorePred.classification.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ML;
