import re

with open('frontend/src/pages/Simulator.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = """          <Card>
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
          </Card>"""

pattern = re.compile(
    r"<Card>\s*<CardHeader>\s*<CardTitle>Pre-match setup</CardTitle>.*?</form>\s*\{\(tossAdvice \|\| targetInfo\) && \(.*?</CardContent>\s*</Card>",
    re.DOTALL
)

new_text = pattern.sub(replacement, text)
with open('frontend/src/pages/Simulator.jsx', 'w', encoding='utf-8') as f:
    f.write(new_text)
