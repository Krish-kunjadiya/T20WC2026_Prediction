import { Routes, Route, Navigate } from 'react-router-dom';
import Simulator from './pages/Simulator';
import PlayerAnalytics from './pages/PlayerAnalytics';
import WarRoom from './pages/WarRoom';

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<Simulator />} />
      <Route path="/players" element={<PlayerAnalytics />} />
      <Route path="/war-room" element={<WarRoom />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;

