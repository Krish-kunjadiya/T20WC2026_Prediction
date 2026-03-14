import React from 'react';
import { Target, Users, Settings } from 'lucide-react';

const Strategist = () => {
  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Target className="text-indigo-600" /> Match Strategist
        </h1>
        <p className="text-gray-500 mt-2">Persona: Strategist | Focus: Specific Matchups, Conditions & Pitch</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col items-center justify-center text-center">
          <div className="p-4 bg-indigo-100 text-indigo-600 rounded-full mb-4">
            <Users size={32} />
          </div>
          <h3 className="font-semibold text-lg text-gray-900">Player H2H Matchups</h3>
          <p className="text-sm text-gray-500 mt-2">Analyze historic batsman vs bowler data</p>
          <button className="mt-6 text-sm text-indigo-600 font-medium hover:underline">Select Players →</button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col items-center justify-center text-center">
          <div className="p-4 bg-emerald-100 text-emerald-600 rounded-full mb-4">
            <Settings size={32} />
          </div>
          <h3 className="font-semibold text-lg text-gray-900">Venue Characteristics</h3>
          <p className="text-sm text-gray-500 mt-2">Par scores, pace vs spin splits, and dew impact</p>
          <button className="mt-6 text-sm text-emerald-600 font-medium hover:underline">Select Venue →</button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col items-center justify-center text-center">
          <div className="p-4 bg-amber-100 text-amber-600 rounded-full mb-4">
            <Target size={32} />
          </div>
          <h3 className="font-semibold text-lg text-gray-900">Phase Planning</h3>
          <p className="text-sm text-gray-500 mt-2">Resource allocation across Powerplay, Mid, and Death</p>
          <button className="mt-6 text-sm text-amber-600 font-medium hover:underline">Optimize Phase →</button>
        </div>
      </div>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 opacity-60 flex items-center justify-center h-64 border-dashed">
         <p className="text-lg font-medium text-gray-500">Select a tool above to configure strategy.</p>
      </div>
    </div>
  );
};

export default Strategist;
