import React, { useState } from 'react';
import { Settings, CheckCircle2, Shield, Zap } from 'lucide-react';

const Optimization = () => {
  const [team, setTeam] = useState('India');

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="text-purple-600" /> Team Optimization Engine
        </h1>
        <p className="text-gray-500 mt-2">Multi-objective player selection (knapsack problem) to maximize Runs & Wickets within budget.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
          <h3 className="font-semibold text-gray-800">Parameters</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Squad Team</label>
            <select className="w-full border border-gray-300 rounded p-2 text-sm" value={team} onChange={e=>setTeam(e.target.value)}>
              <option>India</option>
              <option>Australia</option>
              <option>England</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Team Budget (Virtual)</label>
            <input type="range" className="w-full" min="10" max="100" defaultValue="50" />
            <div className="flex justify-between text-xs text-gray-500 mt-1"><span>$10M</span><span>$100M</span></div>
          </div>
          
          <div>
             <label className="block text-sm font-medium text-gray-700 mb-1">Constraints</label>
             <div className="space-y-2 mt-2">
               <label className="flex items-center gap-2 text-sm"><input type="checkbox" defaultChecked /> Max 4 Overseas</label>
               <label className="flex items-center gap-2 text-sm"><input type="checkbox" defaultChecked /> Min 5 Bowlers</label>
               <label className="flex items-center gap-2 text-sm"><input type="checkbox" defaultChecked /> Require 1 Wicketkeeper</label>
             </div>
          </div>

          <button className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium p-3 rounded-lg transition">
            Run Optimizer
          </button>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="grid grid-cols-3 gap-4">
             <div className="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-3">
               <div className="p-3 bg-purple-100 text-purple-600 rounded-full"><Zap size={20} /></div>
               <div>
                 <div className="text-sm text-gray-500">Projected Run Rate</div>
                 <div className="text-xl font-bold">175 - 190</div>
               </div>
             </div>
             <div className="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-3">
               <div className="p-3 bg-blue-100 text-blue-600 rounded-full"><Shield size={20} /></div>
               <div>
                 <div className="text-sm text-gray-500">Bowling Strength</div>
                 <div className="text-xl font-bold">A+ (Pace Heavy)</div>
               </div>
             </div>
             <div className="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-3">
               <div className="p-3 bg-green-100 text-green-600 rounded-full"><CheckCircle2 size={20} /></div>
               <div>
                 <div className="text-sm text-gray-500">Constraint Check</div>
                 <div className="text-sm font-bold text-green-600 mt-1">All Valid Constraints Met</div>
               </div>
             </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-0 overflow-hidden">
             <table className="w-full text-left text-sm whitespace-nowrap">
               <thead className="bg-gray-50 border-b border-gray-100 text-gray-700">
                 <tr>
                   <th className="p-4 font-semibold">Role</th>
                   <th className="p-4 font-semibold">Player</th>
                   <th className="p-4 font-semibold">Rating</th>
                   <th className="p-4 font-semibold">Cost</th>
                 </tr>
               </thead>
               <tbody className="divide-y divide-gray-100 text-gray-600">
                  <tr><td className="p-4"><span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-semibold">BAT</span></td><td className="p-4 font-medium text-gray-900">Virat Kohli</td><td className="p-4">9.2</td><td className="p-4">$15M</td></tr>
                  <tr><td className="p-4"><span className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-semibold">ALL</span></td><td className="p-4 font-medium text-gray-900">Hardik Pandya</td><td className="p-4">9.5</td><td className="p-4">$18M</td></tr>
                  <tr><td className="p-4"><span className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs font-semibold">BOWL</span></td><td className="p-4 font-medium text-gray-900">Jasprit Bumrah</td><td className="p-4">9.8</td><td className="p-4">$17M</td></tr>
               </tbody>
             </table>
             <div className="p-4 text-center text-sm text-gray-500 border-t border-gray-100 bg-gray-50 hover:bg-gray-100 transition cursor-pointer">
               Load Full 11 Data...
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Optimization;
