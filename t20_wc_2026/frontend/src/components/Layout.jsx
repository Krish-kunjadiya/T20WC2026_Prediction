import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Database, Home, User, BarChart2, Mic, BrainCircuit, MessageSquare, Settings } from 'lucide-react';
import { useGender } from '../context/GenderContext';
import { useMatchup } from '../context/MatchupContext';

const Layout = () => {
  const { gender, setGender } = useGender();
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: Home },
    { name: 'Coach', path: '/coach', icon: User },
    { name: 'Analyst', path: '/analyst', icon: BarChart2 },
    { name: 'Commentator', path: '/commentator', icon: Mic },
    { name: 'Strategist', path: '/strategist', icon: BrainCircuit },
    { name: 'ML Predictions', path: '/ml', icon: BrainCircuit },
    { name: 'AI Chatbot', path: '/chatbot', icon: MessageSquare },
    { name: 'Team Optimization', path: '/optimization', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            🏆 T20 WC 2026
          </h1>
        </div>
        <nav className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`
                }
              >
                <Icon size={18} />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-gray-200 p-4 space-y-4">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Tournament Dataset</p>
          <div className="grid grid-cols-2 gap-2 bg-gray-100 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setGender('male')}
              className={`rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
                gender === 'male' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:bg-white'
              }`}
            >
              Male
            </button>
            <button
              type="button"
              onClick={() => setGender('female')}
              className={`rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
                gender === 'female' ? 'bg-pink-600 text-white shadow-sm' : 'text-gray-600 hover:bg-white'
              }`}
            >
              Female
            </button>
          </div>
          <p className="mt-2 text-[11px] leading-4 text-gray-500">
            All insights and predictions use the selected tournament stream.
          </p>

          <div className="pt-2 border-t border-gray-200">
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Global Matchup</p>
            <div className="space-y-2">
              <div>
                <label className="block text-[11px] font-semibold text-gray-600 mb-1">Team</label>
                <select
                  className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm disabled:bg-gray-100"
                  value={selectedTeam}
                  onChange={(event) => setSelectedTeam(event.target.value)}
                  disabled={matchupLoading || teams.length === 0}
                >
                  {teams.map((team) => (
                    <option key={team} value={team}>{team}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-600 mb-1">Opponent</label>
                <select
                  className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm disabled:bg-gray-100"
                  value={selectedOpponent}
                  onChange={(event) => setSelectedOpponent(event.target.value)}
                  disabled={matchupLoading || teams.length <= 1}
                >
                  {teams.filter((team) => team !== selectedTeam).map((team) => (
                    <option key={team} value={team}>{team}</option>
                  ))}
                </select>
              </div>

              <p className="text-[11px] leading-4 text-gray-500">
                Used as the shared default across matchup-driven pages.
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-8">
          <Outlet key={gender} />
        </div>
      </main>
    </div>
  );
};

export default Layout;
