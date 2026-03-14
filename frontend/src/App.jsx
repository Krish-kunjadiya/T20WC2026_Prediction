import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Simulator from './pages/Simulator';
import LiveState from './pages/LiveState';
import PlayerAnalytics from './pages/PlayerAnalytics';
import WarRoom from './pages/WarRoom';

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/simulator" element={<Simulator />} />
      <Route path="/live-state" element={<LiveState />} />
      <Route path="/players" element={<PlayerAnalytics />} />
      <Route path="/war-room" element={<WarRoom />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;

