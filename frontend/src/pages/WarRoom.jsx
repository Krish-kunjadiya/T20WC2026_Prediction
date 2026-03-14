import { useState } from 'react';
import Layout from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import { strategyAPI } from '../api';

const WarRoom = () => {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const send = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;
    const q = question;
    setMessages((prev) => [...prev, { from: 'user', text: q }]);
    setQuestion('');
    setLoading(true);
    try {
      const res = await strategyAPI.chat({ question: q });
      setMessages((prev) => [...prev, { from: 'bot', text: res.data.answer }]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">War Room – Strategy Copilot</h2>
          <p className="text-gray-600 mt-1">
            Ask tactical questions about bowling changes, match-ups, and field settings.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Conversation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80 overflow-y-auto space-y-3 border border-gray-100 rounded-lg p-3 bg-gray-50">
                  {messages.map((m, idx) => (
                    <div
                      key={idx}
                      className={`max-w-xl px-3 py-2 rounded-lg text-sm ${
                        m.from === 'user'
                          ? 'ml-auto bg-primary-600 text-white'
                          : 'mr-auto bg-white text-gray-900 shadow-sm'
                      }`}
                    >
                      {m.text}
                    </div>
                  ))}
                  {messages.length === 0 && (
                    <p className="text-center text-gray-400 text-xs mt-4">
                      Example: “The pitch is turning and we have 2 left-handed batters. Who should bowl the next over?”
                    </p>
                  )}
                </div>
                <form onSubmit={send} className="mt-4 flex gap-2">
                  <Input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Type your strategy question..."
                    className="flex-1"
                  />
                  <Button type="submit" disabled={loading}>
                    {loading ? 'Thinking...' : 'Ask'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          <div>
            <Card>
              <CardHeader>
                <CardTitle>Context (Coming soon)</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-gray-600 space-y-2">
                <p>
                  This panel will show structured cards from the GenAI agent, such as:
                </p>
                <ul className="list-disc list-inside">
                  <li>Recommended bowler with match-up stats</li>
                  <li>Win probability shift for each option</li>
                  <li>Key reasons behind the suggestion</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default WarRoom;

