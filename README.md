# APEX V4 — Paper Intelligence Terminal

A mobile-first installable PWA with a scheduled, **rule-based paper trading** engine. Not four independent AI models; no LLM or live order execution. No profitability claims.

## Setup (recommended: new repository)
1. Unzip and upload **the contents** to a new GitHub repository, preserving `.github/workflows/trading_bot.yml` and `docs/`.
2. In GitHub repository **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions**. The workflow commits its simulated state and public dashboard snapshot. Keep this repo separate from any live trading code.
3. Go to **Actions → APEX V4 Paper Scanner → Run workflow**. Check the logs; first scan needs access to Kraken public data.
4. In **Settings → Pages**, choose **Deploy from a branch**, branch **main**, folder **/docs**. Wait for the Pages URL shown in Settings.
5. Open the Pages URL in Safari on iPhone → Share → **Add to Home Screen**.
6. On the app's **Settings** page you can use its same-origin `data.json` automatically, or paste a different HTTPS snapshot feed URL.

## Important limitations
- **GitHub Pages is public**, even if your repository is private on some plans. The feed includes simulated trades and balances; never put keys, secrets, private financial data or identifying information in it.
- The workflow saves state by committing `paper_state.json` after each run. This creates a durable audit trail but can encounter Git push conflicts if you edit concurrently. Review errors and rerun; never assume failed scans updated state.
- GitHub scheduled workflows are best-effort and may be delayed or disabled after inactivity. App refreshes every 60 seconds **while open**, but market data changes only after a successful scan.
- The app uses heuristic signals, not trained predictive AI. Score is not win probability. Fees/slippage are illustrative. No real orders.
- Initial simulated balance is A$100; 10 AUD max new position, 2 positions maximum, A$3 daily and A$10 peak-equity drawdown risk halts. Risk halt prevents new entries, but exits remain possible.
- Market API data may fail, be delayed, or be incomplete. Backtest and forward-test thoroughly before considering real funds.
- On some iPhones the SVG icon may fall back to a generic icon; app functionality is unaffected.
