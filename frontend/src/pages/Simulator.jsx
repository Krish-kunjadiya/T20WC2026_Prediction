import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import Layout from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';  
import Input from '../components/Input';
import Button from '../components/Button';
import { simulatorAPI } from '../api';

const Simulator = () => {
  const [options, setOptions] = useState({ teams: [], venues: [] });

  useEffect(() => {
    simulatorAPI.getFormOptions().then(res => {
      setOptions(res.data);
    }).catch(err => console.error("Could not load options", err));
  }, []);

  const teamOptions = options.teams;
  const venueOptions = options.venues;

  const [form, setForm] = useState({
    team_a: '',
    team_b: '',
    venue: '',
    toss_winner: '',
    toss_decision: 'bat',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [liveForm, setLiveForm] = useState({
    batting_team: '',
    bowling_team: '',
    venue: '',
    runs: '',
    wickets: '',
    overs: '',
    target: '',
  });
  const [liveResult, setLiveResult] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [tossAdvice, setTossAdvice] = useState(null);
  const [tossLoading, setTossLoading] = useState(false);
  const [targetInfo, setTargetInfo] = useState(null);
  const [targetLoading, setTargetLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleLiveChange = (e) => {
    const { name, value } = e.target;
    setLiveForm((prev) => ({ ...prev, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await simulatorAPI.predictMatch(form);
      setResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const onLiveSubmit = async (e) => {
    e.preventDefault();
    setLiveLoading(true);
    try {
      const payload = {
        ...liveForm,
        runs: Number(liveForm.runs),
        wickets: Number(liveForm.wickets),
        overs: Number(liveForm.overs),
        target: Number(liveForm.target),
      };
      const res = await simulatorAPI.liveState(payload);
      setLiveResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLiveLoading(false);
    }
  };

  const onTossAdvice = async () => {
    if (!form.team_a || !form.team_b || !form.venue) return;
    setTossLoading(true);
    try {
      const res = await simulatorAPI.tossDecision({
        team: form.team_a,
        opponent: form.team_b,
        venue: form.venue,
      });
      setTossAdvice(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setTossLoading(false);
    }
  };

  const onTargetInfo = async () => {
    if (!form.venue) return;
    setTargetLoading(true);
    try {
      const res = await simulatorAPI.targetScore({ venue: form.venue });
      setTargetInfo(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setTargetLoading(false);
    }
  };

  useEffect(() => {
    if (form.team_a && form.team_b && form.venue) {
      onTossAdvice();
      onTargetInfo();
    }
  }, [form.team_a, form.team_b, form.venue]);

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Tournament Overview – Match Simulator
          </h2>
          <p className="text-gray-600 mt-1">
            Select two teams and a venue to estimate pre-match win probabilities.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Card>
            <CardHeader>
              <CardTitle>Pre-match setup</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={onSubmit}
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Team A</label>
                  <select name="team_a" value={form.team_a} onChange={handleChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select Team A</option>
                    {teamOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Team B</label>
                  <select name="team_b" value={form.team_b} onChange={handleChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select Team B</option>
                    {teamOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Venue</label>
                  <select name="venue" value={form.venue} onChange={handleChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select Venue</option>
                    {venueOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>

                {(tossLoading || targetLoading) && (
                  <div className="md:col-span-2 text-sm text-blue-600 mt-2">
                    Analysing venue conditions & computing insights...
                  </div>
                )}

                {(tossAdvice && targetInfo) && (
                  <>
                    <div className="md:col-span-2 bg-slate-50 p-4 rounded-lg mt-2 mb-2 border border-slate-200">
                      <h3 className="text-md font-semibold text-gray-800 mb-2">Venue Insights</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-gray-700">
                            <strong>Toss prediction:</strong> Highest win chance is <span className="text-blue-600 font-bold">{tossAdvice.recommended_decision.toUpperCase()}</span> ({(tossAdvice.confidence * 100).toFixed(1)}% confidence)
                          </p>
                          <div className="mt-4 h-32">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={[
                                { name: 'Par', score: Math.round(targetInfo.par_score) },
                                { name: 'Safe', score: Math.round(targetInfo.recommended_target_high) }
                              ]} layout="vertical" margin={{ top: 0, right: 20, left: -20, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" fontSize={12} domain={[0, 'dataMax + 20']} />
                                <YAxis dataKey="name" type="category" fontSize={12} />
                                <Tooltip />
                                <Bar dataKey="score" fill="#4f46e5" radius={[0, 4, 4, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                        <div className="flex flex-col justify-center text-sm text-gray-600">
                          <p><strong>Par Score:</strong> {targetInfo.par_score.toFixed(1)}</p>
                          <p><strong>Safe Target:</strong> {targetInfo.recommended_target_low.toFixed(1)} - {targetInfo.recommended_target_high.toFixed(1)}</p>
                          <p className="mt-2 italic">Based on historical scoring patterns at this venue.</p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Toss Winner</label>
                      <select name="toss_winner" value={form.toss_winner} onChange={handleChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                        <option value="">Select Toss Winner</option>
                        {[form.team_a, form.team_b].filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Toss Decision</label>
                      <select name="toss_decision" value={form.toss_decision} onChange={handleChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                        <option value="bat">Bat</option>
                        <option value="bowl">Bowl</option>
                      </select>
                    </div>
                    
                    <div className="md:col-span-2 flex justify-end mt-2">
                      <Button type="submit" disabled={loading}>
                        {loading ? 'Simulating...' : 'Predict winner'}
                      </Button>
                    </div>
                  </>
                )}
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Live state – Win probability</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={onLiveSubmit}
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Batting team</label>
                  <select name="batting_team" value={liveForm.batting_team} onChange={handleLiveChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select Batting team</option>
                    {teamOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bowling team</label>
                  <select name="bowling_team" value={liveForm.bowling_team} onChange={handleLiveChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select Bowling team</option>
                    {teamOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Venue</label>
                  <select name="venue" value={liveForm.venue} onChange={handleLiveChange} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500">
                    <option value="">Select Venue</option>
                    {venueOptions?.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <Input
                  label="Runs scored"
                  name="runs"
                  type="number"
                  value={liveForm.runs}
                  onChange={handleLiveChange}
                  required
                />
                <Input
                  label="Wickets lost"
                  name="wickets"
                  type="number"
                  value={liveForm.wickets}
                  onChange={handleLiveChange}
                  required
                />
                <Input
                  label="Overs completed"
                  name="overs"
                  type="number"
                  step="0.1"
                  value={liveForm.overs}
                  onChange={handleLiveChange}
                  required
                />
                <Input
                  label="Target"
                  name="target"
                  type="number"
                  value={liveForm.target}
                  onChange={handleLiveChange}
                  required
                />
                <div className="md:col-span-2 flex justify-end">
                  <Button type="submit" disabled={liveLoading}>
                    {liveLoading ? 'Calculating...' : 'Update win probability'}
                  </Button>
                </div>
              </form>

              {liveResult && (
                <div className="mt-4 space-y-2 text-sm">
                  <p className="font-semibold text-gray-900">
                    Batting win probability:{' '}
                    <span className="text-primary-600">
                      {(liveResult.win_probability_batting * 100).toFixed(1)}%
                    </span>
                  </p>
                  <p className="font-semibold text-gray-900">
                    Bowling win probability:{' '}
                    <span className="text-gray-700">
                      {(liveResult.win_probability_bowling * 100).toFixed(1)}%
                    </span>
                  </p>
                  <p className="text-xs text-gray-500">{liveResult.explanation}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

                {result && (
          <Card>
            <CardHeader>
              <CardTitle>Predicted Outcome</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col md:flex-row items-center gap-6">
                <div className="flex-1 w-full flex flex-col items-center">
                  <p className="text-xl font-semibold text-gray-900 mb-2">
                    Predicted Winner: <span className="text-primary-600">{result.winner}</span>
                  </p>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: form.team_a || 'Team A', value: parseFloat((result.win_probability_team_a * 100).toFixed(1)) },
                            { name: form.team_b || 'Team B', value: parseFloat((result.win_probability_team_b * 100).toFixed(1)) }
                          ]}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          <Cell key="cell-0" fill="#4f46e5" />
                          <Cell key="cell-1" fill="#ec4899" />
                        </Pie>
                        <Tooltip formatter={(value) => `${value}%`} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="flex-1 w-full">
                  <h4 className="text-md font-semibold text-gray-800 mb-3">Key Factors</h4>
                  <ul className="space-y-4 text-sm text-gray-700 bg-gray-50 p-4 rounded-lg">
                    {result.reasons.map((r, idx) => (
                      <li key={idx} className="flex gap-3 items-start leading-relaxed">
                        <span className="text-primary-600 font-bold mt-1">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default Simulator;

