# The Arch labour widget

Install Scriptable on iPhone. Save `Arch-Labour.js` in iCloud Drive / Scriptable, or paste its contents into a new Scriptable script. Run it once and enter the dedicated widget token. Add a medium Scriptable Home Screen widget, edit it and select this script. Tap the widget to run the script and fetch again (subject to iOS refreshing the Home Screen).

Personal installation copies may embed the dedicated token in INSTALL_TOKEN. Treat such a file as private: it grants read-only access to this summary, not database access. Keep it out of git. Token is stored in Scriptable Keychain. To revoke/rotate, generate a new 32-byte random hex token, replace TOKEN_HASH in the function with its SHA-256 and redeploy. Update/remove the Keychain entry on the device when rotating.

## Calculation

- Today and Monday-to-date, Europe/Dublin dates and DST.
- Sum of loaded labour divided by sum of VAT-exclusive item sales; never an average of daily percentages.
- Uses the existing analytics payroll settings: wage, annual leave accrual, weekly PRSI thresholds, pension assumptions and employee overrides. This is an operational estimate, not final payroll. PRSI classification may change as the week progresses.
- Includes open timecards only up to the earlier sales/timecard sync watermark. Subtracts recorded unpaid breaks (the historical labour view currently does not subtract these). Missing wages/rates suppress the percentage; zero sales displays a dash.
- Uses existing sales-line trading dates and opening-hours overnight labour attribution. Item sales follow the existing reporting convention; this is not a bank-receipts or refund-adjusted cash measure.
- Stale after 90 minutes; offline cache is explicitly labelled. Source timestamps use Irish time. An old cached date is displayed explicitly instead of being called today.
- Open shifts longer than 18 hours produce a review warning. Missing/incorrect clock-outs and wage settings still need correction in Square.
- Green <=32%, amber >32% to 35%, red >35%; stale or incomplete data uses amber. 35% is a display threshold, not a separate business target.

## Backend

`supabase/functions/arch-labour-widget/index.ts` is a read-only GET endpoint. It authenticates a dedicated 256-bit token by comparing SHA-256 before any database query. `verify_jwt=false` is required because custom authentication is implemented in the handler. No CORS/public financial endpoint, staff names, raw records or service-role keys are returned. Responses use Cache-Control: no-store. The server uses its existing service-role environment credential, and all database requests are fixed read-only queries. No database schema or RLS modifications.

Run `node tests/labour-widget.test.mjs`. Deployment must include index.ts and calculate.mjs. Verify missing/wrong tokens return 401 and the authorized request returns only the summary. iOS widget layout and refresh cadence require an actual device check.
