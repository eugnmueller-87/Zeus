# Execution Agent — Order Management Skills

## Mission
Execution is the only agent that touches real money. Every other agent can fail gracefully — Execution's failure mode is a real financial loss or a missed opportunity. Precision, speed, and reliability are the only metrics that matter here.

## Interactive Brokers API (ib_insync) — Key Concepts

### Connection Management
IB Gateway must be running before Execution can connect.
Paper trading port: 7497 (always use this first)
Live trading port: 7496 (only after extensive paper trading validation)
Client ID: each connection needs a unique client ID. Execution uses 1, Monitor uses 2.
Never reuse client IDs simultaneously — this causes connection conflicts.

Connection is persistent but can drop. The _get_connection() method handles reconnection.
If connection drops during an active trade: IB will manage the bracket orders autonomously — the trade is not lost.

### Order Types Used
Bracket Order: the only order type ZEUS uses. It places three linked orders simultaneously:
1. Entry order (Market or Limit)
2. Take-profit limit order (above entry for longs, below for shorts)
3. Stop-loss stop order (below entry for longs, above for shorts)

The bracket ensures the stop-loss and take-profit are always in place — even if the execution agent crashes after placing the order.

### Market Data
reqMktData() fetches live bid/ask. Use midpoint() for the entry price.
Always cancel market data subscription (cancelMktData) immediately after getting the price — IB has subscription limits.
If midpoint() returns None (outside market hours or illiquid), fall back to last or close.
Never place an order if price cannot be determined — return an error result.

### SMART Routing
Use exchange="SMART" for US stocks — IB routes to the best available exchange automatically.
For European stocks on XETRA: use exchange="XETRA", currency="EUR".
For ETFs: use exchange="SMART", but verify the ETF trades on US exchanges.

## Position Sizing Execution
The position_size_pct from SizedSignal is a percentage of total account equity.
qty = floor(account_equity × position_size_pct / fill_price)
Minimum quantity: 1 share. Never place a 0-share order.
For penny stocks (< $5): increase minimum to 100 shares or skip the trade.

## Stop-Loss and Take-Profit Calculation
Default: 3% stop-loss, 6% take-profit (2:1 R/R)
For LONG trades: stop = entry × 0.97, target = entry × 1.06
For SHORT trades: stop = entry × 1.03, target = entry × 0.94

Rounding: always round to 2 decimal places for US stocks (penny precision).
For European stocks: round to 4 decimal places.

## Long vs Short Determination
Current logic: SUPPLIER_DISRUPTION → SHORT (disruptions hurt downstream companies)
All other categories → LONG

This is simplified. Future enhancement: ZEUS's LLM reasoning should specify direction explicitly in the SizedSignal, not infer it from category.

## Error Handling
Order rejection by IB: can happen due to insufficient margin, market closed, or invalid parameters.
On rejection: log the full error, return error TradeResult, do NOT retry automatically.
ZEUS will handle the retry decision based on the error type.

Pre-market/post-market trading: IB supports extended hours, but liquidity is poor.
Default: only place orders during regular market hours unless signal severity is CRITICAL.
Future setting: extended_hours_trading in config.

## German Tax Considerations (Abgeltungsteuer)
German capital gains are subject to Abgeltungsteuer (25% flat rate + solidarity surcharge).
Short-term vs long-term holding periods do not change the tax rate (unlike the US).
Loss offsetting: losses in one security can offset gains in another within the same year.
ZEUS does not implement tax optimization in Phase 1. All trades are made on pre-tax basis.
Tax lot tracking: IBKR handles this automatically in the account statements.

## Order Confirmation and Logging
After placing a bracket order, log:
- Order ID (parent order)
- Symbol, side, quantity
- Entry price (fill_price from midpoint)
- Stop-loss and take-profit prices
- Timestamp

This data flows into the DecisionTrace and is stored in the knowledge base for Pattern learning.
