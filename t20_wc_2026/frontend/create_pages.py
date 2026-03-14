import os
pages = ['Home', 'DataQuality', 'Coach', 'Analyst', 'Commentator', 'Strategist', 'ML', 'Chatbot', 'Optimization']
base = r'C:\Users\DELL\OneDrive\Desktop\kenexai\T20WC2026_Prediction\t20_wc_2026\frontend\src\pages'
os.makedirs(base, exist_ok=True)
for p in pages:
    content = f"""import React from 'react';

const {p} = () => {{
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 whitespace-pre-wrap">{p} Dashboard</h2>
      <p className="text-gray-600">This module is part of the T20 WC 2026 Analytics suite.</p>
    </div>
  );
}};

export default {p};
"""
    with open(os.path.join(base, f'{p}.jsx'), 'w', encoding='utf-8') as f:
        f.write(content)
