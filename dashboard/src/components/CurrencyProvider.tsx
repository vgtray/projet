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

const FALLBACK_EXCHANGE_RATE = 0.92;

export function CurrencyProvider({ children }: CurrencyProviderProps) {
  const [accountCurrency, setAccountCurrency] = useState<Currency>('USD');
  const [displayCurrency, setDisplayCurrencyState] = useState<DisplayCurrency>('USD');
  const [rate, setRate] = useState(FALLBACK_EXCHANGE_RATE);

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
    async function fetchExchangeRate() {
      if (displayCurrency === accountCurrency) {
        setRate(1);
        return;
      }

      try {
        const res = await fetch('https://api.exchangerate.host/latest?base=USD&symbols=EUR');
        const data = await res.json();
        if (data.success !== false && data.rates?.EUR) {
          setRate(data.rates.EUR);
        }
      } catch (e) {
        console.error('Failed to fetch exchange rate, using fallback:', e);
        setRate(FALLBACK_EXCHANGE_RATE);
      }
    }
    fetchExchangeRate();
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
