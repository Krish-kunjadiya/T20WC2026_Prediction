import React, { createContext, useContext, useMemo, useState } from 'react';
import { getActiveGender, normalizeGender, setActiveGender } from '../api';

const GenderContext = createContext(null);

export const GenderProvider = ({ children }) => {
  const [gender, setGenderState] = useState(getActiveGender());

  const setGender = (nextGender) => {
    const normalized = normalizeGender(nextGender);
    setActiveGender(normalized);
    setGenderState(normalized);
  };

  const value = useMemo(
    () => ({
      gender,
      setGender,
      isMale: gender === 'male',
      isFemale: gender === 'female',
    }),
    [gender],
  );

  return <GenderContext.Provider value={value}>{children}</GenderContext.Provider>;
};

export const useGender = () => {
  const context = useContext(GenderContext);
  if (!context) {
    throw new Error('useGender must be used within a GenderProvider');
  }
  return context;
};
