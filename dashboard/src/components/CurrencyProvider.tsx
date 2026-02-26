'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Currency = 'USD' | 'EUR';
type DisplayCurrency = 'USD' | 'EUR';

interface CurrencyContextType {
  accountCurrency: Currency;
  displayCurrency: DisplayCurrency;
  setDisplayCurrency: (currency: DisplayCurrency) => void;
  rate: number;
}

const CurrencyContext = createContext<CurrencyContextType>({
  accountCurrency: 'USD',
  displayCurrency: 'USD',
  setDisplayCurrency: () => {},
  rate: 1,
});

export function useCurrency() {
  return useContext(CurrencyContext);
}

interface CurrencyProviderProps {
  children: ReactNode;
}

const EXCHANGE_RATE = 0.92;

export function CurrencyProvider({ children }: CurrencyProviderProps) {
  const [accountCurrency, setAccountCurrency] = useState<Currency>('USD');
  const [displayCurrency, setDisplayCurrencyState] = useState<DisplayCurrency>('USD');
  const [rate, setRate] = useState(1);

  useEffect(() => {
    async function fetchCurrency() {
      try {
        const res = await fetch('/api/bot?type=account');
        const data = await res.json();
        if (data.currency) {
          setAccountCurrency(data.currency as Currency);
        }
      } catch (e) {
        console.error('Failed to fetch account currency:', e);
      }
    }
    fetchCurrency();
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem('displayCurrency') as DisplayCurrency | null;
    if (saved) {
      setDisplayCurrencyState(saved);
    }
  }, []);

  useEffect(() => {
    if (displayCurrency === 'EUR' && accountCurrency === 'USD') {
      setRate(EXCHANGE_RATE);
    } else if (displayCurrency === 'USD' && accountCurrency === 'EUR') {
      setRate(1 / EXCHANGE_RATE);
    } else {
      setRate(1);
    }
  }, [displayCurrency, accountCurrency]);

  const setDisplayCurrency = (currency: DisplayCurrency) => {
    setDisplayCurrencyState(currency);
    localStorage.setItem('displayCurrency', currency);
  };

  return (
    <CurrencyContext.Provider
      value={{
        accountCurrency,
        displayCurrency,
        setDisplayCurrency,
        rate,
      }}
    >
      {children}
    </CurrencyContext.Provider>
  );
}
