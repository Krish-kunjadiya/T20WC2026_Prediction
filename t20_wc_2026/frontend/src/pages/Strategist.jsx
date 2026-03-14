import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';

const Strategist = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState({
    pointsTable: [],
    qualificationData: [],
    runsMarginDistribution: [],
    wicketsMarginDistribution: [],
  });

  const [team, setTeam] = useState('');
  const [marginRuns, setMarginRuns] = useState(20);
  const [simLoading, setSimLoading] = useState(false);
  const [simulation, setSimulation] = useState(null);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/strategist/overview');
      setOverview(data);
      if (!team && data.pointsTable?.length) {
        setTeam(data.pointsTable[0].Team);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const pointsTable = overview.pointsTable || [];
  const qualData = overview.qualificationData || [];
  const runMargins = overview.runsMarginDistribution || [];
  const wicketMargins = overview.wicketsMarginDistribution || [];

  const selectedTeamRank = useMemo(() => {
    const row = pointsTable.find((r) => r.Team === team);
    return row ? row.Rank : null;
  }, [pointsTable, team]);

  const simulateNrr = async () => {
    if (!team) return;
    setSimLoading(true);
    try {
      const { data } = await api.get('/strategist/nrr-simulate', {
        params: { team, margin_runs: marginRuns },
      });
      setSimulation(data);
    } catch (err) {
      console.error(err);
      setSimulation(null);
    } finally {
      setSimLoading(false);
    }
  };

  if (loading) {
    return <div className="text-gray-500">Loading strategist dashboard from live data...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">🏆 Tournament Strategist Dashboard</h1>
        <p className="text-gray-500 mt-2">Persona: Tournament Strategist | Focus: Standings, NRR, Qualification</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">📋 Current Points Table</h2>
        <div className="overflow-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead className="bg-gray-50 text-gray-700 border-b border-gray-200">
              <tr>
                <th className="text-left p-3">Rank</th>
                <th className="text-left p-3">Team</th>
                <th className="text-left p-3">P</th>
                <th className="text-left p-3">W</th>
                <th className="text-left p-3">L</th>
                <th className="text-left p-3">Pts</th>
                <th className="text-left p-3">NRR</th>
              </tr>
            </thead>
            <tbody>
              {pointsTable.map((row) => (
                <tr
                  key={row.Team}
                  className={`border-b border-gray-100 ${row.Rank <= 4 ? 'bg-emerald-50' : 'bg-white'}`}
                >
                  <td className="p-3 font-semibold text-gray-700">{row.Rank}</td>
                  <td className="p-3 font-medium text-gray-900">{row.Team}</td>
                  <td className="p-3">{row.P}</td>
                  <td className="p-3">{row.W}</td>
                  <td className="p-3">{row.L}</td>
                  <td className="p-3 font-semibold">{row.Pts}</td>
                  <td className="p-3">{Number(row.NRR).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-500 mt-3">Top 4 teams are highlighted as projected knockout qualifiers.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">🧮 NRR Impact Simulator</h2>
          <p className="text-sm text-gray-500">How much a win margin can shift projected standings.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Select Team</label>
              <select
                value={team}
                onChange={(e) => setTeam(e.target.value)}
                className="w-full border border-gray-300 rounded-md p-2"
              >
                {pointsTable.map((r) => (
                  <option key={r.Team} value={r.Team}>
                    {r.Team}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Win by Runs</label>
              <input
                type="range"
                min="1"
                max="100"
                value={marginRuns}
                onChange={(e) => setMarginRuns(Number(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">{marginRuns} runs</p>
            </div>
          </div>

          <button
            onClick={simulateNrr}
            disabled={simLoading || !team}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-60"
          >
            {simLoading ? 'Simulating...' : 'Simulate NRR Impact'}
          </button>

          {simulation && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                <p className="text-xs text-gray-500">Current NRR</p>
                <p className="text-lg font-semibold text-gray-900">{simulation.currentNrr.toFixed(3)}</p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                <p className="text-xs text-gray-500">Projected NRR</p>
                <p className="text-lg font-semibold text-emerald-700">{simulation.projectedNrr.toFixed(3)}</p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                <p className="text-xs text-gray-500">Projected Rank</p>
                <p className="text-lg font-semibold text-gray-900">#{simulation.projectedRank}</p>
                <p className="text-xs text-gray-500">Current #{selectedTeamRank ?? simulation.currentRank}</p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">🎯 Qualification Probability</h2>
          <p className="text-sm text-gray-500 mb-4">Top 8 qualification probability (%) by current Pts + NRR blend.</p>
          <div className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="team" angle={-25} textAnchor="end" height={70} interval={0} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="qualPct" radius={[6, 6, 0, 0]}>
                  {qualData.map((entry) => (
                    <Cell key={entry.team} fill={entry.qualPct >= 50 ? '#10b981' : '#f59e0b'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📊 Distribution of Win by Runs</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={runMargins}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="margin" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📊 Distribution of Win by Wickets</h2>
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wicketMargins}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="margin" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Strategist;
