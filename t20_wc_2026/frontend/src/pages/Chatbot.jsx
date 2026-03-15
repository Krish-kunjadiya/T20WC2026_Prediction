import React, { useEffect, useState } from 'react';
import { MessageSquare, Send } from 'lucide-react';
import api from '../api';
import { useMatchup } from '../context/MatchupContext';

const TAB_CHAT = 'chat';
const TAB_PREVIEW = 'preview';
const TAB_INSIGHTS = 'insights';

const sampleQuestions = [
  'Who are the top wicket takers?',
  "What is India's win rate?",
  'Which team scores most in powerplay?',
  'Who is the best death over bowler?',
  'Compare India and Australia stats',
  'Which venue has highest average score?',
];

const insightPrompts = {
  '🏆 Tournament Summary': 'Summarize the key highlights and patterns from this T20 World Cup tournament data in 3 bullet points.',
  '⚡ Best Powerplay Teams': 'Which teams have the best powerplay performance? Give specific stats.',
  '💀 Best Death Over Teams': 'Analyze which teams perform best in death overs (16-20) based on the data.',
  '🎯 Bowling Heroes': 'Who are the most impactful bowlers in this tournament based on wickets and economy?',
  '🏏 Batting Champions': 'Who are the most dominant batters in this tournament? Focus on runs and strike rate.',
  '🔮 Final Prediction': 'Based on all the tournament data, which team looks most likely to win the T20 World Cup 2026 and why?',
};

const Chatbot = () => {
  const {
    teams,
    selectedTeam,
    selectedOpponent,
    setSelectedTeam,
    setSelectedOpponent,
    loading: matchupLoading,
  } = useMatchup();
  const [activeTab, setActiveTab] = useState(TAB_CHAT);

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        "Hi! I'm CricAI, your T20 World Cup 2026 analyst. I have access to match results, player stats, team records, and venue data from this tournament.",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const [venues, setVenues] = useState([]);
  const [venue, setVenue] = useState('Neutral Venue');
  const [preview, setPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const [insightResults, setInsightResults] = useState({});
  const [insightLoadingKey, setInsightLoadingKey] = useState('');

  useEffect(() => {
    const loadMeta = async () => {
      try {
        const { data } = await api.get('/venues');
        const loadedVenues = data.venues || [];
        setVenues(loadedVenues);
        if (loadedVenues.length > 0) {
          setVenue(loadedVenues[0]);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadMeta();
  }, []);

  const askCricAI = async (promptText) => {
    const clean = String(promptText || '').trim();
    if (!clean || loading) return;

    const userMsg = { role: 'user', text: clean };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const payloadHistory = nextMessages.slice(0, -1).map((m) => ({
        role: m.role,
        content: m.text,
      }));
      const { data } = await api.post('/chat', {
        prompt: clean,
        chat_history: payloadHistory,
      });
      setMessages((prev) => [...prev, { role: 'assistant', text: data.response }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'assistant', text: 'RAG backend error. Please check Gemini/Chroma service.' }]);
    } finally {
      setLoading(false);
    }
  };

  const generatePreview = async () => {
    if (!selectedTeam || !selectedOpponent) return;
    setPreviewLoading(true);
    try {
      const { data } = await api.post('/chat/preview', {
        team_a: selectedTeam,
        team_b: selectedOpponent,
        venue,
      });
      setPreview(data.preview || 'No preview generated.');
    } catch (err) {
      console.error(err);
      setPreview('Preview generation failed. Please check API and Gemini key.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const downloadPreview = () => {
    if (!preview) return;
    const blob = new Blob([`${selectedTeam} vs ${selectedOpponent} @ ${venue}\n\n${preview}`], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `preview_${selectedTeam}_vs_${selectedOpponent}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const generateInsight = async (title, prompt) => {
    setInsightLoadingKey(title);
    try {
      const { data } = await api.post('/chat', { prompt });
      setInsightResults((prev) => ({ ...prev, [title]: data.response || '' }));
    } catch (err) {
      console.error(err);
      setInsightResults((prev) => ({ ...prev, [title]: 'Unable to generate insight right now.' }));
    } finally {
      setInsightLoadingKey('');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare className="text-blue-600" /> 💬 CricAI - Powered by Gemini
        </h1>
        <p className="text-gray-500 mt-2">RAG Chatbot | Match Preview Generator | AI Insights</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-2 flex flex-wrap gap-2">
        <button onClick={() => setActiveTab(TAB_CHAT)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_CHAT ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          🤖 CricAI Chatbot
        </button>
        <button onClick={() => setActiveTab(TAB_PREVIEW)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_PREVIEW ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          📋 Match Preview
        </button>
        <button onClick={() => setActiveTab(TAB_INSIGHTS)} className={`px-3 py-2 rounded-md text-sm font-medium ${activeTab === TAB_INSIGHTS ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
          💡 Quick Insights
        </button>
      </div>

      {activeTab === TAB_CHAT && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-100 p-4">
            <p className="text-sm text-gray-600 mb-3">Try asking:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {sampleQuestions.map((q) => (
                <button key={q} onClick={() => askCricAI(q)} className="text-left px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-sm text-gray-700">
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 flex flex-col h-[520px] overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {loading && <div className="text-sm text-gray-500">CricAI is analyzing...</div>}
            </div>
            <div className="border-t border-gray-100 p-3 bg-gray-50 flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && askCricAI(input)}
                className="flex-1 border border-gray-300 rounded-md px-3 py-2"
                placeholder="Ask CricAI anything about T20 WC 2026..."
                disabled={loading}
              />
              <button onClick={() => askCricAI(input)} disabled={loading} className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-60">
                <Send size={18} />
              </button>
              <button
                onClick={() =>
                  setMessages([
                    {
                      role: 'assistant',
                      text: 'Chat cleared. Ask me anything about T20 WC 2026.',
                    },
                  ])
                }
                className="px-3 py-2 rounded-md bg-gray-200 text-gray-700 text-sm hover:bg-gray-300"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === TAB_PREVIEW && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">📋 AI Match Preview Generator</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-700 mb-1">Team A</label>
              <select
                className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                disabled={matchupLoading || teams.length === 0}
              >
                {teams.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Team B</label>
              <select
                className="w-full border border-gray-300 rounded-md p-2 disabled:bg-gray-100"
                value={selectedOpponent}
                onChange={(e) => setSelectedOpponent(e.target.value)}
                disabled={matchupLoading || teams.length <= 1}
              >
                {teams.filter((t) => t !== selectedTeam).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Venue</label>
              <select className="w-full border border-gray-300 rounded-md p-2" value={venue} onChange={(e) => setVenue(e.target.value)}>
                {venues.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={generatePreview} disabled={previewLoading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-60">
              {previewLoading ? 'Generating...' : 'Generate Match Preview'}
            </button>
            <button onClick={downloadPreview} disabled={!preview} className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300 disabled:opacity-60">
              Download Preview
            </button>
          </div>

          {preview && (
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
              <h3 className="font-semibold text-gray-900 mb-2">{selectedTeam} vs {selectedOpponent}</h3>
              <p className="text-xs text-gray-500 mb-3">{venue}</p>
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">{preview}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === TAB_INSIGHTS && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {Object.entries(insightPrompts).map(([title, prompt]) => (
            <div key={title} className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
              <h3 className="font-semibold text-gray-900">{title}</h3>
              <button
                onClick={() => generateInsight(title, prompt)}
                disabled={insightLoadingKey === title}
                className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
              >
                {insightLoadingKey === title ? 'Generating...' : 'Generate Insight'}
              </button>
              <div className="text-sm text-gray-700 whitespace-pre-wrap">
                {insightResults[title] || 'No insight generated yet.'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Chatbot;
