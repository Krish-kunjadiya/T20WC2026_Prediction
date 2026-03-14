import React from 'react';
import { Database, User, Activity, Users } from 'lucide-react';

const Home = () => {
  const metrics = [
    { label: 'Matches', value: '110', icon: Database, color: 'text-indigo-600', bg: 'bg-indigo-100' },
    { label: 'Players', value: '299', icon: User, color: 'text-blue-600', bg: 'bg-blue-100' },
    { label: 'Deliveries', value: '45,656', icon: Activity, color: 'text-emerald-600', bg: 'bg-emerald-100' },
    { label: 'Teams', value: '20', icon: Users, color: 'text-amber-600', bg: 'bg-amber-100' },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🏆 ICC T20 WC 2026 - Prediction Platform
        </h1>
        <p className="text-gray-600 text-lg mb-2">
          Kenexai Hackathon 2k26 | KD&A-10 | CHARUSAT
        </p>
        <p className="text-gray-500">
          Use the <strong>sidebar pages</strong> to navigate dashboards.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m) => (
          <div key={m.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col items-center text-center">
            <div className={`p-4 rounded-full ${m.bg} ${m.color} mb-4`}>
              <m.icon size={28} strokeWidth={2} />
            </div>
            <h3 className="text-gray-500 font-medium">{m.label}</h3>
            <p className="text-3xl font-bold text-gray-900 mt-1">{m.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 text-blue-800">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          <span>👉</span> Select a page from the sidebar to begin
        </h3>
        <ul className="mt-4 space-y-2 list-disc list-inside px-4 text-blue-700">
          <li><strong>Data Quality & EDA:</strong> Quality scorecard, EDA charts</li>
          <li><strong>Coach:</strong> Player analysis, form, matchups</li>
          <li><strong>Analyst:</strong> Match comparisons, venue insights</li>
          <li><strong>Commentator:</strong> Live stats, match timeline</li>
          <li><strong>Strategist:</strong> Phase-wise planning, matchup strategies</li>
          <li><strong>ML Predictions:</strong> Win probability and score predictor</li>
          <li><strong>AI Chatbot:</strong> LLM/RAG based cricket assistant</li>
          <li><strong>Team Optimization:</strong> Multi-objective player selection</li>
        </ul>
      </div>
    </div>
  );
};

export default Home;
