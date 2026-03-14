import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Database, Home, User, BarChart2, Mic, BrainCircuit, MessageSquare, Settings } from 'lucide-react';

const Layout = () => {
  const navItems = [
    { name: 'Home', path: '/', icon: Home },
    { name: 'Data Quality & EDA', path: '/data-quality', icon: Database },
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
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
