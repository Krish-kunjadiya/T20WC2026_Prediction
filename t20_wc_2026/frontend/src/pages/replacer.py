import os

content = """import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  ComposedChart, AreaChart, Area, ScatterChart, Scatter, ZAxis, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, PieChart, Pie, Cell, Label
} from 'recharts';

// Mock Data for Advanced Plots
const evolutionData = [
  { year: 2012, avgScore: 145, strikeRate: 125, boundaryPct: 15 },
  { year: 2014, avgScore: 151, strikeRate: 130, boundaryPct: 16 },
  { year: 2016, avgScore: 155, strikeRate: 133, boundaryPct: 17.5 },
  { year: 2021, avgScore: 162, strikeRate: 138, boundaryPct: 19 },
  { year: 2022, avgScore: 168, strikeRate: 143, boundaryPct: 20.5 },
  { year: 2024, avgScore: 175, strikeRate: 148, boundaryPct: 22 },
];

const survivalData = [
  { over: 0, wktProb: 0.05, expRuns: 6 },
  { over: 5, wktProb: 0.12, expRuns: 8 },
  { over: 10, wktProb: 0.25, expRuns: 7.5 },
  { over: 15, wktProb: 0.45, expRuns: 9 },
  { over: 20, wktProb: 0.85, expRuns: 11 },
];

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

const winDistributionData = [
  { name: 'Bat First Win', value: 45 },
  { name: 'Bowl First Win', value: 52 },
  { name: 'Tie/No Result', value: 3 },
];
const COLORS = ['#3b82f6', '#10b981', '#94a3b8'];

export default function MainDashboard() {
  const [kpis, setKpis] = useState({ total_matches: 0, total_teams: 0, avg_first_innings_score: 0 });

  useEffect(() => {
    fetch('http://localhost:8000/dashboard/kpis')
      .then(res => res.json())
      .then(data => setKpis(data))
      .catch(console.error);
  }, []);

  return (
    <div className="p-6 bg-gray-50 min-h-screen text-gray-900 flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-gray-200 pb-5 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-800">
            Global T20 Intelligence
          </h1>
          <p className="text-gray-500 mt-1">Cross-era Insights, Predictive Matrices, & Executive Summaries</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
            <p className="text-sm font-medium text-gray-500">Historical Matches</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{kpis.total_matches || "2,134"}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
            <p className="text-sm font-medium text-gray-500">Avg Par Score</p>
            <p className="text-2xl font-bold text-teal-600 mt-1">{kpis.avg_first_innings_score || "165"}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm min-w-[140px]">
             <p className="text-sm font-medium text-gray-500">Global Teams</p>
             <p className="text-2xl font-bold text-purple-600 mt-1">{kpis.total_teams || "120"}</p>
          </div>
        </div>
      </div>

      {/* Grid Layout Row 1: Time Series & Survival */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Evolution Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-4 text-gray-800">The Evolution of T20 (Risk vs Return)</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={evolutionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="year" stroke="#64748b" />
                <YAxis yAxisId="left" stroke="#3b82f6" />
                <YAxis yAxisId="right" orientation="right" stroke="#10b981" />
                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                <Legend iconType="circle" />
                <Bar yAxisId="left" dataKey="avgScore" fill="#3b82f6" name="Avg Par Score" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="strikeRate" stroke="#10b981" strokeWidth={3} name="Global Strike Rate" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Phase Survival */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-4 text-gray-800">Phase Survival & Over-by-Over Mapping</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={survivalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="over" stroke="#64748b" />
                <YAxis stroke="#64748b" />
                <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                <Legend iconType="circle" />
                <Area type="monotone" dataKey="expRuns" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.2} name="Expected Runs per Over" />
                <Area type="monotone" dataKey="wktProb" stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} name="Wicket Probability %" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Grid Layout Row 2: Advanced Archetypes & Player distributions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Radar Chart: Team Archetype */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Elite Team Archetypes</h2>
          <p className="text-xs text-gray-500 mb-4">Champion Profiles vs Global Benchmarks</p>
          <div className="h-[280px]">
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

        {/* Scatter Chart: Player Clustering */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm lg:col-span-2">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Batter Segmentation & Value Matrix</h2>
          <p className="text-xs text-gray-500 mb-4">Risk Absorption (Average) vs Scoring Velocity (Strike Rate) sized by Volume</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" dataKey="average" name="Batting Avg" unit="" stroke="#64748b">
                    <Label value="Batting Average" position="insideBottomRight" offset={-5} style={{ fill: '#64748b', fontSize: '12px' }} />
                </XAxis>
                <YAxis type="number" dataKey="strikeRate" name="Strike Rate" unit="" stroke="#64748b" />
                <ZAxis type="number" dataKey="runs" range={[100, 800]} name="Total Runs" />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ borderRadius: '8px' }} />
                <Legend iconType="circle" />
                <Scatter name="Openers" data={playerScatterData.filter(d => d.type === 'Opener')} fill="#0ea5e9" />
                <Scatter name="Anchors" data={playerScatterData.filter(d => d.type === 'Anchor')} fill="#f59e0b" />
                <Scatter name="Finishers" data={playerScatterData.filter(d => d.type === 'Finisher')} fill="#f43f5e" />
                <Scatter name="Aggressors" data={playerScatterData.filter(d => d.type === 'Aggressor')} fill="#8b5cf6" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Grid Layout Row 3: Summaries & KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Win Record Pie Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-bold mb-2 text-gray-800">Global Match Resolution</h2>
          <p className="text-xs text-gray-500 flex-1 mb-4">Historical Toss to Match Outcome Rates</p>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={winDistributionData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {winDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Global Record Factoids */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm lg:col-span-2">
            <h2 className="text-lg font-bold mb-4 text-gray-800">Executive Summary & Tournament Trivia</h2>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Highest Team Total</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">278 / 3</p>
                    <p className="text-xs text-blue-600 mt-1">Afghanistan vs Ireland</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Best Bowling Fig.</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">6 / 8</p>
                    <p className="text-xs text-blue-600 mt-1">Colin Ackermann vs Malaysia</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Max Sixes (Innings)</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">22</p>
                    <p className="text-xs text-blue-600 mt-1">West Indies vs Ireland</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Fastest Century</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">33 Balls</p>
                    <p className="text-xs text-blue-600 mt-1">David Miller</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Par Score (Knockouts)</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">172.5</p>
                    <p className="text-xs text-blue-600 mt-1">Historical Semi & Finals</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-500 uppercase font-semibold">Highest Chase</p>
                    <p className="text-xl font-bold text-gray-800 mt-1">245 / 5</p>
                    <p className="text-xs text-blue-600 mt-1">Bulgaria vs Serbia</p>
                </div>
            </div>
        </div>

      </div>

    </div>
  );
}
"""

with open(r'C:\Users\DELL\OneDrive\Desktop\kenexai\T20WC2026_Prediction\t20_wc_2026\frontend\src\pages\MainDashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("MainDashboard updated fully!")
