import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  ComposedChart, AreaChart, Area, ScatterChart, Scatter, ZAxis, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, PieChart, Pie, Cell, Label
} from 'recharts';

export default function MainDashboard() {
  const [kpis, setKpis] = useState({ total_matches: 0, total_teams: 0, avg_first_innings_score: 0 });
  const [chartsData, setChartsData] = useState({
    evolutionData: [],
    survivalData: [],
    winDistributionData: []
  });

  const [loading, setLoading] = useState(true);

  // Fallback visual data for complex multi-metric archetype representations currently building in pipeline
  const teamArchetypeData = [
    { metric: 'Powerplay Aggression', teamA: 85, benchmark: 65, fullMark: 100 },
    { metric: 'Death Bowling', teamA: 90, benchmark: 70, fullMark: 100 },
    { metric: 'Spin Handling', teamA: 65, benchmark: 75, fullMark: 100 },
    { metric: 'Pace Rotation', teamA: 80, benchmark: 60, fullMark: 100 },
    { metric: 'Fielding Efficiency', teamA: 88, benchmark: 68, fullMark: 100 },
    { metric: 'Middle Over Retention', teamA: 75, benchmark: 70, fullMark: 100 },
  ];

  const playerScatterData = [
    { name: 'Player 1', average: 35, strikeRate: 145, runs: 2500, type: 'Opener' },
    { name: 'Player 2', average: 42, strikeRate: 135, runs: 3000, type: 'Anchor' },
    { name: 'Player 3', average: 25, strikeRate: 165, runs: 1500, type: 'Finisher' },
    { name: 'Player 4', average: 31, strikeRate: 155, runs: 2100, type: 'Aggressor' },
    { name: 'Player 5', average: 22, strikeRate: 175, runs: 1200, type: 'Finisher' },
    { name: 'Player 6', average: 48, strikeRate: 125, runs: 3500, type: 'Anchor' },
    { name: 'Player 7', average: 29, strikeRate: 140, runs: 1800, type: 'Opener' },
  ];

  const COLORS = ['#3b82f6', '#10b981', '#94a3b8'];

  useEffect(() => {
    Promise.all([
      fetch('http://localhost:8000/dashboard/kpis').then(res => res.json()),
      fetch('http://localhost:8000/dashboard/charts').then(res => res.json())
    ])
    .then(([kpiData, charts]) => {
      setKpis(kpiData);
      setChartsData(charts);
      setLoading(false);
    })
    .catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if(loading) return <div className="p-8 text-center text-gray-500">Loading Real Analytics from Data Lake...</div>;

  return (
    <div className="p-6 bg-gray-50 min-h-screen text-gray-900 flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-gray-200 pb-5 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-800">
            Global T20 Intelligence (Live DB)
          </h1>
          <p className="text-gray-500 mt-1">Cross-era Insights, Predictive Matrices, & Executive Summaries</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
            <p className="text-sm font-medium text-gray-500">Historical Matches</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{kpis.total_matches || "0"}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
            <p className="text-sm font-medium text-gray-500">Avg Par Score</p>
            <p className="text-2xl font-bold text-teal-600 mt-1">{kpis.avg_first_innings_score || "0"}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
             <p className="text-sm font-medium text-gray-500">Global Teams</p>
             <p className="text-2xl font-bold text-purple-600 mt-1">{kpis.total_teams || "0"}</p>
          </div>
        </div>
      </div>

      {/* Grid Layout Row 1: Time Series & Survival */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Evolution Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-4 text-gray-800">The Evolution of T20 (Risk vs Return)</h2>
          <div className="h-[320px]">
             {chartsData.evolutionData && chartsData.evolutionData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartsData.evolutionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="year" stroke="#64748b" />
                <YAxis yAxisId="left" stroke="#3b82f6" domain={['auto', 'auto']} />
                <YAxis yAxisId="right" orientation="right" stroke="#10b981" domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                <Legend iconType="circle" />
                <Bar yAxisId="left" dataKey="avgScore" fill="#3b82f6" name="Avg Par Score" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="strikeRate" stroke="#10b981" strokeWidth={3} name="Global Strike Rate" />
              </ComposedChart>
            </ResponsiveContainer>
            ) : <p className="text-gray-400">Syncing Evolution metrics...</p>}
          </div>
        </div>

        {/* Phase Survival */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-4 text-gray-800">Phase Survival & Over-by-Over Mapping</h2>
          <div className="h-[320px]">
            {chartsData.survivalData && chartsData.survivalData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartsData.survivalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="over" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                <Legend iconType="circle" />
                <Area type="monotone" dataKey="expRuns" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.2} name="Expected Runs per Over" />
                <Area type="monotone" dataKey="wktProb" stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} name="Wicket Probability %" />
              </AreaChart>
            </ResponsiveContainer>
            ) : <p className="text-gray-400">Syncing Survival metrics...</p>}
          </div>
        </div>
      </div>

      {/* Grid Layout Row 2: Summaries & KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Win Record Pie Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Global Match Resolution</h2>
          <p className="text-xs text-gray-500 flex-1 mb-4">Historical Toss to Match Outcome Rates</p>
          <div className="h-[250px]">
            {chartsData.winDistributionData && chartsData.winDistributionData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chartsData.winDistributionData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {chartsData.winDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
            ) : <p className="text-gray-400">Syncing Resolution records...</p>}
          </div>
        </div>

        {/* Radar Chart: Team Archetype */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Elite Team Archetypes (Analyst Proxy)</h2>
          <p className="text-xs text-gray-500 mb-4">Under-development benchmark mapping</p>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={teamArchetypeData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#64748b', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#94a3b8' }} />
                <Radar name="Champion Team" dataKey="teamA" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.5} />
                <Radar name="Global Benchmark" dataKey="benchmark" stroke="#94a3b8" fill="#cbd5e1" fillOpacity={0.3} />
                <Legend iconType="circle" />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Global Record Factoids */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-lg font-bold mb-4 text-gray-800">Executive Query Summary</h2>
            <div className="flex flex-col gap-4">
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 flex justify-between items-center">
                    <div>
                        <p className="text-xs text-gray-500 uppercase font-semibold">Highest Team Total</p>
                        <p className="text-sm font-bold text-gray-800 mt-1">Afghanistan (278/3)</p>
                    </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 flex justify-between items-center">
                    <div>
                        <p className="text-xs text-gray-500 uppercase font-semibold">Best Bowling Fig.</p>
                        <p className="text-sm font-bold text-gray-800 mt-1">C. Ackermann (6/8)</p>
                    </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 flex justify-between items-center">
                    <div>
                        <p className="text-xs text-gray-500 uppercase font-semibold">Fastest T20I Century</p>
                        <p className="text-sm font-bold text-gray-800 mt-1">David Miller (33 Balls)</p>
                    </div>
                </div>
            </div>
        </div>

      </div>
    </div>
  );
}
