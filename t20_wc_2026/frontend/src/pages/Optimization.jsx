import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../api';

const TAB_XI = 'xi';
const TAB_ORDER = 'order';
const TAB_SHAP = 'shap';

const Optimization = () => {
  const [activeTab, setActiveTab] = useState(TAB_XI);
  const [teams, setTeams] = useState(['All Teams']);

  const [xiTeam, setXiTeam] = useState('All Teams');
  const [xiRows, setXiRows] = useState([]);
  const [roleDistribution, setRoleDistribution] = useState([]);
  const [xiLoading, setXiLoading] = useState(false);

  const [orderTeam, setOrderTeam] = useState('All Teams');
  const [orderRows, setOrderRows] = useState([]);
  const [orderLoading, setOrderLoading] = useState(false);

  const [shapRows, setShapRows] = useState([]);
  const [shapAvailable, setShapAvailable] = useState(false);
  const [shapLoading, setShapLoading] = useState(false);

  useEffect(() => {
    const loadTeams = async () => {
      try {
        const { data } = await api.get('/optimization/teams');
        const list = data.teams || ['All Teams'];
        setTeams(list);
        if (list.length > 0) {
          setXiTeam(list[0]);
          setOrderTeam(list[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadTeams();
  }, []);

  const fetchOptimalXi = async () => {
    setXiLoading(true);
    try {
      const { data } = await api.get('/optimization/optimal-xi', { params: { country: xiTeam } });
      setXiRows(data.xi || []);
      setRoleDistribution(data.roleDistribution || []);
    } catch (err) {
      console.error(err);
      setXiRows([]);
      setRoleDistribution([]);
    } finally {
      setXiLoading(false);
    }
  };

  const fetchBattingOrder = async () => {
    setOrderLoading(true);
    try {
      const { data } = await api.get('/optimization/batting-order', { params: { country: orderTeam } });
      setOrderRows(data.battingOrder || []);
    } catch (err) {
      console.error(err);
      setOrderRows([]);
    } finally {
      setOrderLoading(false);
    }
  };

  const fetchShap = async () => {
    setShapLoading(true);
    try {
      const { data } = await api.get('/optimization/shap');
      setShapRows(data.shap || []);
      setShapAvailable(Boolean(data.available));
    } catch (err) {
      console.error(err);
      setShapRows([]);
      setShapAvailable(false);
    } finally {
      setShapLoading(false);
    }
  };

  const computeShap = async () => {
    setShapLoading(true);
    try {
      const { data } = await api.post('/optimization/shap/compute');
      setShapRows(data.shap || []);
      setShapAvailable(true);
    } catch (err) {
      console.error(err);
    } finally {
      setShapLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === TAB_XI && xiRows.length === 0) {
      fetchOptimalXi();
    }
    if (activeTab === TAB_ORDER && orderRows.length === 0) {
      fetchBattingOrder();
    }
    if (activeTab === TAB_SHAP && shapRows.length === 0 && !shapLoading) {
      fetchShap();
    }
  }, [activeTab]);

  const perfChartData = useMemo(
    () => [...xiRows].sort((a, b) => Number(a.perf_score || 0) - Number(b.perf_score || 0)),
    [xiRows]
  );

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">⚙️ Optimization Dashboard</h1>
        <p className="text-gray-500 mt-2">Playing XI Optimizer | Batting Order | SHAP Explainability</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-2 flex flex-wrap gap-2">
        <button onClick={() => setActiveTab(TAB_XI)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_XI ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          🏏 Optimal XI Selector
        </button>
        <button onClick={() => setActiveTab(TAB_ORDER)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_ORDER ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          📊 Batting Order
        </button>
        <button onClick={() => setActiveTab(TAB_SHAP)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_SHAP ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          🔍 SHAP Importance
        </button>
      </div>

      {activeTab === TAB_XI && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">🏏 Optimal Playing XI Selector</h2>
            <div className="flex items-end gap-3">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Select Team/Country</label>
                <select className="border border-gray-300 rounded-md p-2" value={xiTeam} onChange={(e) => setXiTeam(e.target.value)}>
                  {teams.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <button onClick={fetchOptimalXi} disabled={xiLoading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-60">
                {xiLoading ? 'Selecting...' : 'Select Optimal XI'}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6 overflow-auto">
            <table className="w-full text-sm min-w-[920px]">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left p-3">XI #</th>
                  <th className="text-left p-3">Player</th>
                  <th className="text-left p-3">Role</th>
                  <th className="text-left p-3">Runs</th>
                  <th className="text-left p-3">Bat Avg</th>
                  <th className="text-left p-3">SR</th>
                  <th className="text-left p-3">Wickets</th>
                  <th className="text-left p-3">Eco</th>
                  <th className="text-left p-3">Perf Score</th>
                </tr>
              </thead>
              <tbody>
                {xiRows.map((row) => (
                  <tr key={row.player_name} className="border-b border-gray-100">
                    <td className="p-3 font-semibold">{row.xi_rank}</td>
                    <td className="p-3 font-medium text-gray-900">{row.player_name}</td>
                    <td className="p-3">{row.role}</td>
                    <td className="p-3">{row.runs}</td>
                    <td className="p-3">{Number(row.batting_avg || 0).toFixed(1)}</td>
                    <td className="p-3">{Number(row.strike_rate || 0).toFixed(1)}</td>
                    <td className="p-3">{row.wickets}</td>
                    <td className="p-3">{Number(row.economy || 0).toFixed(1)}</td>
                    <td className="p-3 font-semibold text-emerald-700">{Number(row.perf_score || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="text-md font-semibold text-gray-800 mb-2">XI Composition by Role</h3>
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={roleDistribution} dataKey="count" nameKey="role" cx="50%" cy="50%" outerRadius={100} label>
                      {roleDistribution.map((item) => (
                        <Cell key={item.role} fill={item.role === 'Batter' ? '#3b82f6' : item.role === 'Bowler' ? '#ef4444' : item.role === 'All-Rounder' ? '#10b981' : '#94a3b8'} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="text-md font-semibold text-gray-800 mb-2">Player Performance Scores</h3>
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={perfChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="player_name" width={120} />
                    <Tooltip />
                    <Bar dataKey="perf_score" fill="#8b5cf6" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_ORDER && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">📊 Batting Order Optimizer</h2>
            <div className="flex items-end gap-3">
              <div>
                <label className="block text-sm text-gray-700 mb-1">Select Team/Country</label>
                <select className="border border-gray-300 rounded-md p-2" value={orderTeam} onChange={(e) => setOrderTeam(e.target.value)}>
                  {teams.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <button onClick={fetchBattingOrder} disabled={orderLoading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-60">
                {orderLoading ? 'Optimizing...' : 'Optimize Batting Order'}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-2">
            {orderRows.map((row) => {
              const pos = Number(row.batting_position || 0);
              const color = pos <= 2 ? 'border-emerald-500 bg-emerald-50' : pos <= 5 ? 'border-blue-500 bg-blue-50' : pos <= 7 ? 'border-red-500 bg-red-50' : 'border-gray-400 bg-gray-50';
              return (
                <div key={`${row.player_name}-${pos}`} className={`border-l-4 rounded-md p-3 ${color} flex justify-between items-center`}>
                  <div className="font-semibold text-gray-900">#{pos} {row.player_name}</div>
                  <div className="text-sm text-gray-600">{row.role_in_order} | SR {Number(row.sr || 0).toFixed(0)} | Avg {Number(row.avg || 0).toFixed(1)}</div>
                </div>
              );
            })}
          </div>

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <h3 className="text-md font-semibold text-gray-800 mb-2">Batting Position: Strike Rate vs Average</h3>
            <div className="h-[380px]">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" dataKey="sr" name="Strike Rate" />
                  <YAxis type="number" dataKey="avg" name="Average" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter data={orderRows} fill="#3b82f6" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_SHAP && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-100 p-6 flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">🔍 SHAP Feature Importance</h2>
            <button onClick={fetchShap} disabled={shapLoading} className="px-3 py-2 rounded-md bg-gray-200 text-gray-700 text-sm hover:bg-gray-300 disabled:opacity-60">
              Refresh
            </button>
            <button onClick={computeShap} disabled={shapLoading} className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60">
              {shapAvailable ? 'Recompute SHAP' : 'Compute SHAP Values'}
            </button>
            {shapLoading && <span className="text-sm text-gray-500">Processing...</span>}
          </div>

          {shapRows.length > 0 && (
            <>
              <div className="bg-white rounded-xl border border-gray-100 p-6">
                <div className="h-[420px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[...shapRows].sort((a, b) => Number(a.SHAP_Value || 0) - Number(b.SHAP_Value || 0))} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="Feature" width={170} />
                      <Tooltip />
                      <Bar dataKey="SHAP_Value" fill="#22c55e" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-100 p-6 overflow-auto">
                <table className="w-full text-sm min-w-[520px]">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left p-3">Feature</th>
                      <th className="text-left p-3">SHAP Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shapRows.map((row) => (
                      <tr key={row.Feature} className="border-b border-gray-100">
                        <td className="p-3 font-medium text-gray-900">{row.Feature}</td>
                        <td className="p-3">{Number(row.SHAP_Value || 0).toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Optimization;
