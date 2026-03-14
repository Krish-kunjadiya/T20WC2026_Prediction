import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import DataQuality from './pages/DataQuality';
import Coach from './pages/Coach';
import Analyst from './pages/Analyst';
import Commentator from './pages/Commentator';
import Strategist from './pages/Strategist';
import ML from './pages/ML';
import Chatbot from './pages/Chatbot';
import Optimization from './pages/Optimization';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/' element={<Layout />}>
          <Route index element={<Home />} />
          <Route path='data-quality' element={<DataQuality />} />
          <Route path='coach' element={<Coach />} />
          <Route path='analyst' element={<Analyst />} />
          <Route path='commentator' element={<Commentator />} />
          <Route path='strategist' element={<Strategist />} />
          <Route path='ml' element={<ML />} />
          <Route path='chatbot' element={<Chatbot />} />
          <Route path='optimization' element={<Optimization />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
