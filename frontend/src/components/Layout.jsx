import { NavLink } from 'react-router-dom';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen flex bg-gray-100">
      <aside className="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col">
        <div className="px-6 py-4 border-b border-gray-100">
          <h1 className="text-xl font-bold text-primary-600">
            T20WC 2026
          </h1>
          <p className="text-xs text-gray-500">
            Strategy Command Center
          </p>
        </div>
        <nav className="flex-1 px-4 py-4 space-y-1">
          <NavItem to="/" label="Simulator" />
          <NavItem to="/players" label="Player Analytics" />
          <NavItem to="/war-room" label="War Room" />
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 md:px-8">
          <div className="md:hidden">
            <span className="font-semibold text-primary-600">T20WC 2026</span>
          </div>
          <div className="text-xs md:text-sm text-gray-500">
            ICC Men's T20 World Cup 2026 – Analytics & Strategy
          </div>
        </header>
        <main className="flex-1 px-4 md:px-8 py-6">
          {children}
        </main>
      </div>
    </div>
  );
};

const NavItem = ({ to, label }) => (
  <NavLink
    to={to}
    end
    className={({ isActive }) =>
      `flex items-center px-3 py-2 rounded-lg text-sm font-medium ${
        isActive
          ? 'bg-primary-50 text-primary-700'
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
      }`
    }
  >
    {label}
  </NavLink>
);

export default Layout;

