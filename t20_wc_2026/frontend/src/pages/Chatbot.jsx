import React, { useState } from 'react';
import { MessageSquare, Send } from 'lucide-react';
import api from '../api';

const Chatbot = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hello! I am your AI Cricket Assistant. Ask me anything about T20 WC stats, player forms, or tactical matchups.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    setMessages(prev => [...prev, { role: 'user', text: input }]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post('/chat', { prompt: input });
      setMessages(prev => [...prev, { role: 'assistant', text: res.data.response }]);
    } catch(err) {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Error connecting to RAG backend.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-10 flex flex-col h-[calc(100vh-8rem)]">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare className="text-blue-600" /> AI Cricket Assistant
        </h1>
        <p className="text-gray-500 mt-2">LLM-powered conversational agent for cricket data.</p>
      </div>

      <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((m, i) => (
             <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
               <div className={`max-w-[70%] rounded-2xl p-4 ${m.role === 'user' ? 'bg-blue-600 text-white rounded-br-sm' : 'bg-gray-100 text-gray-800 rounded-bl-sm'}`}>
                 {m.text}
               </div>
             </div>
          ))}
          {loading && (
             <div className="flex justify-start">
               <div className="bg-gray-100 text-gray-800 rounded-2xl p-4 animate-pulse">Thinking...</div>
             </div>
          )}
        </div>
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center gap-4">
          <input 
            type="text"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500"
            placeholder="Ask about top scorers, win probabilities, or matchups..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button onClick={handleSend} disabled={loading} className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg transition-colors disabled:opacity-50">
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
