#!/usr/bin/env python3
"""Trade Bot SMC/ICT — Point d'entrée principal."""

from src.bot import TradingBot


def main():
    bot = TradingBot()
    bot.start()


if __name__ == "__main__":
    main()
