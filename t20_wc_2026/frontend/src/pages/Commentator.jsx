import React from 'react';
import { Mic, Activity, Clock } from 'lucide-react';

const Commentator = () => {
  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Mic className="text-blue-600" /> Match Commentator View
        </h1>
        <p className="text-gray-500 mt-2">Persona: Live Commentator | Focus: Milestones, momentum shifts, and live timeline.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="flex items-center gap-2 font-semibold text-gray-800 border-b pb-4 mb-4">
              <Activity size={18} className="text-red-500" /> Live Match Worm
            </h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg text-gray-400 text-sm">
              [ Match flow chart goes here. Select a match from side panel ]
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="flex items-center gap-2 font-semibold text-gray-800 border-b pb-4 mb-4">
              <Clock size={18} className="text-blue-500" /> Key Match Events
            </h3>
            <div className="space-y-4">
               {[1,2,3].map(i => (
                 <div key={i} className="flex gap-4 p-3 hover:bg-gray-50 rounded-lg transition-colors border border-transparent hover:border-gray-100">
                    <div className="font-bold text-blue-600 w-12 pt-1">{i*5}.4</div>
                    <div>
                      <div className="font-semibold text-gray-900">Huge Six!</div>
                      <div className="text-sm text-gray-500">Batsman absolutely smashes that over long on. The crowd goes wild.</div>
                    </div>
                 </div>
               ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="font-semibold text-gray-800 mb-4">Select Match</h3>
            <select className="flex w-full p-2 border border-gray-300 rounded mb-4">
              <option>IND vs AUS - Final</option>
              <option>ENG vs SA - Semi Final</option>
            </select>
            <div className="bg-blue-50 text-blue-800 text-sm p-4 rounded-lg font-medium">
              Match Status: IND won by 4 wickets
            </div>
          </div>
          <div className="bg-slate-900 text-white rounded-xl shadow-sm p-6">
             <h3 className="font-semibold mb-4 opacity-90">Commentary Notes</h3>
             <ul className="space-y-3 text-sm opacity-80 list-disc list-inside">
               <li>Pitch is turning square in the second innings.</li>
               <li>Batsman struggling against pace variations.</li>
             </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Commentator;
