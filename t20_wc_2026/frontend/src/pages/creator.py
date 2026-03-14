import os

pages = ['Coach', 'Analyst', 'Commentator', 'Strategist', 'ML', 'Chatbot', 'Optimization']
base = r'C:\Users\DELL\OneDrive\Desktop\kenexai\T20WC2026_Prediction\t20_wc_2026\frontend\src\pages'
os.makedirs(base, exist_ok=True)

for p in pages:
    content = f"""import React from 'react';

export default function {p}() {{
  return (
    <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">{p} Module</h2>
      <p className="text-gray-600">Advanced {p.lower()} analytics, tools, and insights will be populated here.</p>
    </div>
  );
}}
"""
    with open(os.path.join(base, f'{p}.jsx'), 'w', encoding='utf-8') as f:
        f.write(content)

print("All missing pages successfully generated!")
