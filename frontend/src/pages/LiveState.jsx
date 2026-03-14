import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Card } from '../components/Card';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Legend
} from 'recharts';

const initialWinProb = [
  { over: 0, teamA: 50, teamB: 50 },
  { over: 1, teamA: 52, teamB: 48 },
  { over: 2, teamA: 49, teamB: 51 },
  { over: 3, teamA: 55, teamB: 45 },
];

export default function LiveState() {
  const [matchState, setMatchState] = useState({
    teamA: 'India',
    teamB: 'Australia',
    score: '45/1',
    overs: '5.2',
    rr: '8.43',
    target: '185',
    reqRr: '9.54',
    striker: { name: 'V. Kohli', runs: 24, balls: 14 },
    nonStriker: { name: 'R. Sharma', runs: 18, balls: 11 },
    bowler: { name: 'P. Cummins', overs: '1.2', runs: 12, wickets: 0 }
  });

  const [winProbData, setWinProbData] = useState(initialWinProb);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let interval;
    if (isLive) {
      interval = setInterval(() => {
        setWinProbData(prev => {
          const last = prev[prev.length - 1];
          // Mock some jitter in win prob
          const diff = (Math.random() - 0.5) * 5;
          let newA = last.teamA + diff;
          if (newA > 99) newA = 99;
          if (newA < 1) newA = 1;

          return [...prev, {
            over: last.over + 0.5,
            teamA: parseFloat(newA.toFixed(1)),
            teamB: parseFloat((100 - newA).toFixed(1))
          }];
        });
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [isLive]);

  return (
    <Layout>
      <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Live Match State</h2>
          <p className="text-gray-500">Real-time predictive analytics and ball-by-ball insights.</p>
        </div>
        <button 
          onClick={() => setIsLive(!isLive)}
          className={`px-4 py-2 rounded font-medium text-white ${isLive ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}
        >
          {isLive ? 'Stop Simulation' : 'Go Live'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Scorecard */}
        <Card className="p-6 md:col-span-1 border-t-4 border-t-primary-500">
          <div className="flex justify-between items-center border-b pb-4 mb-4">
            <h3 className="text-xl font-bold">{matchState.teamA}</h3>
            <span className="text-3xl font-black text-primary-600">{matchState.score}</span>
          </div>
          <div className="flex gap-4 text-sm mb-6">
             <div><span className="text-gray-500">Overs:</span> <span className="font-bold">{matchState.overs}</span></div>
             <div><span className="text-gray-500">RR:</span> <span className="font-bold">{matchState.rr}</span></div>
          </div>
          <div className="space-y-3">
             <div className="flex justify-between">
                <span className="font-medium">{matchState.striker.name}*</span>
                <span>{matchState.striker.runs} ({matchState.striker.balls})</span>
             </div>
             <div className="flex justify-between text-gray-600">
                <span>{matchState.nonStriker.name}</span>
                <span>{matchState.nonStriker.runs} ({matchState.nonStriker.balls})</span>
             </div>
             <hr className="my-2" />
             <div className="flex justify-between text-sm">
                <span className="font-medium text-gray-600">Bowler: {matchState.bowler.name}</span>
                <span>{matchState.bowler.wickets}-{matchState.bowler.runs} ({matchState.bowler.overs})</span>
             </div>
          </div>
        </Card>

        {/* Live Predictor */}
        <Card className="p-6 md:col-span-2">
          <h3 className="text-lg font-semibold mb-4">Live Win Probability (%)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={winProbData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorA" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="over" type="number" domain={['dataMin', 'dataMax']} tickCount={6} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="teamA" stroke="#3b82f6" fillOpacity={1} fill="url(#colorA)" name={matchState.teamA} />
                <Area type="monotone" dataKey="teamB" stroke="#f59e0b" fillOpacity={0} name={matchState.teamB} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Current Over Timeline</h3>
          <div className="flex gap-2 items-center">
             <div className="w-10 h-10 rounded-full bg-gray-100 border flex items-center justify-center font-bold">1</div>
             <div className="w-10 h-10 rounded-full bg-gray-100 border flex items-center justify-center font-bold">0</div>
             <div className="w-10 h-10 rounded-full bg-primary-100 border-primary-300 text-primary-700 flex items-center justify-center font-bold">4</div>
             <div className="w-10 h-10 rounded-full bg-gray-100 border flex items-center justify-center font-bold">1</div>
             <div className="w-10 h-10 rounded-full bg-gray-50 border border-dashed text-gray-400 flex items-center justify-center">-</div>
             <div className="w-10 h-10 rounded-full bg-gray-50 border border-dashed text-gray-400 flex items-center justify-center">-</div>
          </div>
        </Card>
        
        <Card className="p-4 bg-primary-50 border-primary-200">
           <h3 className="text-primary-800 font-bold mb-2">AI Insights</h3>
           <ul className="list-disc list-inside space-y-2 text-primary-900 text-sm ml-4">
              <li>{matchState.striker.name} has a strike rate of 175.0 against {matchState.bowler.name} historically.</li>
              <li>Expected score at the end of powerplay: 52-58 runs.</li>
              <li>Win probability for {matchState.teamA} increased by 4% after the last boundary.</li>
           </ul>
        </Card>
      </div>
      </div>
    </Layout>
  );
}
