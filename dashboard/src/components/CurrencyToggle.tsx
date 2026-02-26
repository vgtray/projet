'use client';

import { useCurrency } from './CurrencyProvider';

export function CurrencyToggle() {
  const { displayCurrency, setDisplayCurrency, accountCurrency } = useCurrency();

  if (accountCurrency === displayCurrency) {
    return null;
  }

  return (
    <button
      onClick={() => setDisplayCurrency(displayCurrency === 'USD' ? 'EUR' : 'USD')}
      className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-zinc-800 hover:bg-zinc-700 rounded-md transition-colors"
      title={`Afficher en ${displayCurrency === 'USD' ? 'EUR' : 'USD'}`}
    >
      <span className="text-zinc-400">{displayCurrency}</span>
      <span className="text-zinc-600">→</span>
      <span className="text-emerald-400">{displayCurrency === 'USD' ? 'EUR' : 'USD'}</span>
    </button>
  );
}

export function useConvertCurrency() {
  const { displayCurrency, rate } = useCurrency();

  const convert = (value: number): number => {
    return Math.round(value * rate * 100) / 100;
  };

  const format = (value: number, showSign = true): string => {
    const converted = convert(value);
    const sign = showSign && converted > 0 ? '+' : '';
    return `${sign}${converted.toFixed(2)} ${displayCurrency}`;
  };

  const symbol = displayCurrency === 'USD' ? '$' : '€';

  return { convert, format, symbol, displayCurrency, rate };
}
