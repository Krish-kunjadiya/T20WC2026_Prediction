import React from 'react';
import Layout from '../components/Layout';
import { Card } from '../components/Card';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';

const kpis = [
  { label: 'Total Matches Analyzed', value: '1,245', change: '+12 this week' },
  { label: 'Average 1st Innings Score', value: '162.4', change: '+2.1 vs last year' },
  { label: 'Highest Successful Chase', value: '259/4', change: 'SA vs WI' },
  { label: 'Batting 1st Win Rate', value: '47.8%', change: '-1.2% trend' },
];

const teamWinStats = [
  { name: 'IND', wins: 85, matches: 120 },
  { name: 'AUS', wins: 82, matches: 120 },
  { name: 'ENG', wins: 78, matches: 120 },
  { name: 'PAK', wins: 75, matches: 120 },
  { name: 'SA', wins: 70, matches: 120 },
];

const tossDecisions = [
  { name: 'Bat First', value: 45 },
  { name: 'Field First', value: 55 },
];

const scoringTrends = [
  { year: '2020', avgScore: 154 },
  { year: '2021', avgScore: 158 },
  { year: '2022', avgScore: 161 },
  { year: '2023', avgScore: 164 },
  { year: '2024', avgScore: 167 },
  { year: '2025', avgScore: 172 },
];

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function Dashboard() {
  return (
    <Layout>
      <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Tournament Dashboard</h2>
        <p className="text-gray-500">Overview of T20 global statistics and KPI metrics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => (
          <Card key={idx} className="p-4 flex flex-col justify-center">
            <div className="text-sm font-medium text-gray-500">{kpi.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{kpi.value}</div>
            <div className="text-xs text-primary-600 mt-1 font-medium">{kpi.change}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Top Teams Win/Match Ratio</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={teamWinStats} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="wins" fill="#3b82f6" name="Wins" radius={[4, 4, 0, 0]} />
                <Bar dataKey="matches" fill="#e5e7eb" name="Total Matches" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Average 1st Innings Score Trend</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scoringTrends} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" />
                <YAxis domain={['dataMin - 10', 'auto']} />
                <Tooltip />
                <Line type="monotone" dataKey="avgScore" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} name="Avg Score" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-4 flex flex-col justify-center items-center">
          <h3 className="text-lg font-semibold mb-2 self-start w-full">Toss Decisions (Global)</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={tossDecisions}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {tossDecisions.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Match Venues Heatmap (Mock)</h3>
          <div className="h-64 bg-gray-100 rounded flex items-center justify-center border border-dashed border-gray-300 relative overflow-hidden">
              <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "url('https://upload.wikimedia.org/wikipedia/commons/e/ec/World_map_blank_without_borders.svg')", backgroundSize: 'cover', backgroundPosition: 'center' }}></div>
              <p className="text-gray-500 z-10 font-medium">Interactive Map Integration Here</p>
          </div>
        </Card>
      </div>
      </div>
    </Layout>
  );
}
