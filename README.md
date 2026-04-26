# Discretionary backtester for options strategies

## Problem
Trading view offers Bar Replay, so that you can go back in history and click on any candle, and hit buy/sell to simulate 'how much return I would have generated if I had a set of trades'.
But the caveat is, this is only for 1D time frame, also if you look at index, and take a trade in derivatives (another scrip) this functionality would have been useless.

## Solution
Instead of buy/sell, what if you could have DEPLOY either iron condor/strangle strategies?
This software can simulate that.
You click next candle, enter deploy whenever you want (if you want to trade intraday/positional it is upto you).

### Assumptions
1. Entry is taken at 9.16 AM.
2. Exit is done at either 3.29 PM, or next day 9.16 AM
3. This is for nifty options, exclusively.
4. Data is updated from Dhan APIs. There is another repo which downloads and maintains correct data.
