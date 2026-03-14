import re

with open('frontend/src/pages/Simulator.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = """        {result && (
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
        )}"""

pattern = re.compile(
    r"\{result && \(\s*<Card>\s*<CardHeader>\s*<CardTitle>Predicted Outcome</CardTitle>.*?</Card>\s*\)\}",
    re.DOTALL
)

new_text = pattern.sub(replacement, text)

with open('frontend/src/pages/Simulator.jsx', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Result mapped!")