const fs = require('fs');
const path = require('path');
const pages = ['Coach', 'Analyst', 'Commentator', 'Strategist', 'ML', 'Chatbot', 'Optimization'];
const dir = 'C:/Users/DELL/OneDrive/Desktop/kenexai/T20WC2026_Prediction/t20_wc_2026/frontend/src/pages';
if(!fs.existsSync(dir)) fs.mkdirSync(dir, {recursive: true});

pages.forEach(p => {
    const content = `import React from 'react';

export default function ${p}() {
  return (
    <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">${p} Module</h2>
      <p className="text-gray-600">Advanced ${p.toLowerCase()} analytics, tools, and insights will be populated here.</p>
    </div>
  );
}
`;
    fs.writeFileSync(path.join(dir, `${p}.jsx`), content);
});
console.log('Successfully created all missing pages!');
