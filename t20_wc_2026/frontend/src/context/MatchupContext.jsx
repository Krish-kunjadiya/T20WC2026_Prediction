import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api from '../api';
import { useGender } from './GenderContext';

const MATCHUP_STORAGE_KEY = 't20wc:selectedMatchup';

const MatchupContext = createContext(null);

const normalizeTeams = (rawTeams) => {
  const uniqueTeams = Array.from(new Set((rawTeams || []).map((team) => String(team || '').trim()).filter(Boolean)));
  return uniqueTeams.sort((a, b) => a.localeCompare(b));
};

const readStoredMatchup = () => {
  if (typeof window === 'undefined') {
    return { team: '', opponent: '' };
  }

  try {
    const raw = window.localStorage.getItem(MATCHUP_STORAGE_KEY);
    if (!raw) {
      return { team: '', opponent: '' };
    }
    const parsed = JSON.parse(raw);
    return {
      team: String(parsed?.team || '').trim(),
      opponent: String(parsed?.opponent || '').trim(),
    };
  } catch (err) {
    return { team: '', opponent: '' };
  }
};

const persistMatchup = (team, opponent) => {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(
    MATCHUP_STORAGE_KEY,
    JSON.stringify({
      team: String(team || '').trim(),
      opponent: String(opponent || '').trim(),
    }),
  );
};

const normalizeMatchup = (teams, preferredTeam, preferredOpponent) => {
  if (!teams.length) {
    return { team: '', opponent: '' };
  }

  const team = teams.includes(preferredTeam) ? preferredTeam : teams[0];

  let opponent = '';
  if (teams.includes(preferredOpponent) && preferredOpponent !== team) {
    opponent = preferredOpponent;
  } else {
    opponent = teams.find((candidate) => candidate !== team) || '';
  }

  return { team, opponent };
};

export const MatchupProvider = ({ children }) => {
  const { gender } = useGender();

  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeamState] = useState('');
  const [selectedOpponent, setSelectedOpponentState] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const applyMatchup = useCallback((availableTeams, preferredTeam, preferredOpponent) => {
    const nextMatchup = normalizeMatchup(availableTeams, preferredTeam, preferredOpponent);
    setSelectedTeamState(nextMatchup.team);
    setSelectedOpponentState(nextMatchup.opponent);
    persistMatchup(nextMatchup.team, nextMatchup.opponent);
    return nextMatchup;
  }, []);

  const refreshTeams = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const { data } = await api.get('/teams');
      const nextTeams = normalizeTeams(data?.teams || []);
      setTeams(nextTeams);

      const stored = readStoredMatchup();
      applyMatchup(nextTeams, stored.team, stored.opponent);
    } catch (err) {
      console.error(err);
      setError('Unable to load matchup teams.');
      setTeams([]);
      setSelectedTeamState('');
      setSelectedOpponentState('');
    } finally {
      setLoading(false);
    }
  }, [applyMatchup]);

  useEffect(() => {
    refreshTeams();
  }, [refreshTeams, gender]);

  const setSelectedTeam = useCallback(
    (team) => {
      const nextMatchup = normalizeMatchup(teams, String(team || '').trim(), selectedOpponent);
      setSelectedTeamState(nextMatchup.team);
      setSelectedOpponentState(nextMatchup.opponent);
      persistMatchup(nextMatchup.team, nextMatchup.opponent);
    },
    [teams, selectedOpponent],
  );

  const setSelectedOpponent = useCallback(
    (opponent) => {
      const nextMatchup = normalizeMatchup(teams, selectedTeam, String(opponent || '').trim());
      setSelectedTeamState(nextMatchup.team);
      setSelectedOpponentState(nextMatchup.opponent);
      persistMatchup(nextMatchup.team, nextMatchup.opponent);
    },
    [teams, selectedTeam],
  );

  const setMatchup = useCallback(
    (team, opponent) => {
      const nextMatchup = normalizeMatchup(teams, String(team || '').trim(), String(opponent || '').trim());
      setSelectedTeamState(nextMatchup.team);
      setSelectedOpponentState(nextMatchup.opponent);
      persistMatchup(nextMatchup.team, nextMatchup.opponent);
    },
    [teams],
  );

  const value = useMemo(
    () => ({
      teams,
      selectedTeam,
      selectedOpponent,
      setSelectedTeam,
      setSelectedOpponent,
      setMatchup,
      refreshTeams,
      loading,
      error,
      hasPair: Boolean(selectedTeam && selectedOpponent && selectedTeam !== selectedOpponent),
    }),
    [teams, selectedTeam, selectedOpponent, setSelectedTeam, setSelectedOpponent, setMatchup, refreshTeams, loading, error],
  );

  return <MatchupContext.Provider value={value}>{children}</MatchupContext.Provider>;
};

export const useMatchup = () => {
  const context = useContext(MatchupContext);
  if (!context) {
    throw new Error('useMatchup must be used within a MatchupProvider');
  }
  return context;
};
