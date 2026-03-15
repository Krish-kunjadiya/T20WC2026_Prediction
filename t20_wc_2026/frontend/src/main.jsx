import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { GenderProvider } from './context/GenderContext.jsx'
import { MatchupProvider } from './context/MatchupContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <GenderProvider>
      <MatchupProvider>
        <App />
      </MatchupProvider>
    </GenderProvider>
  </StrictMode>,
)
