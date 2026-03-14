import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import Input from '../components/Input';
import { playerAPI } from '../api';

const PlayerAnalytics = () => {
  const [team, setTeam] = useState('');
  const [players, setPlayers] = useState([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await playerAPI.list(team ? { team } : undefined);
        setPlayers(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, [team]);

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Player Impact Analytics</h2>
          <p className="text-gray-600 mt-1">
            Explore impact scores and roles to compare players and plan match-ups.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              label="Team"
              placeholder="e.g., India"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Players</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <Th>Name</Th>
                    <Th>Team</Th>
                    <Th>Role</Th>
                    <Th>Batting</Th>
                    <Th>Bowling</Th>
                    <Th>Impact</Th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {players.map((p) => (
                    <tr key={p.id}>
                      <Td>{p.name}</Td>
                      <Td>{p.team}</Td>
                      <Td>{p.role}</Td>
                      <Td>{p.batting_style || '-'}</Td>
                      <Td>{p.bowling_style || '-'}</Td>
                      <Td className="font-semibold text-primary-600">
                        {p.impact_score != null ? p.impact_score.toFixed(2) : '-'}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {players.length === 0 && (
                <p className="text-center text-gray-500 text-xs py-4">
                  No players loaded yet. Run the ETL pipeline to populate data.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

const Th = ({ children }) => (
  <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
    {children}
  </th>
);

const Td = ({ children }) => (
  <td className="px-4 py-2 text-gray-700 whitespace-nowrap">{children}</td>
);

export default PlayerAnalytics;

