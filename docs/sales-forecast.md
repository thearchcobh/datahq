# Daily sales forecast

The source planning model is `The_Arch_Revised_Rotas_4h_Admin_Tue_Deliveries.xlsx` (4 September 2026), Assumptions tab: comparable prior-year sales within proposed opening hours × weekday-specific recent year-on-year trend. The earlier Weekly Staffing workbook used a single 0.821 multiplier. These fixed September multipliers are replaced by daily recalculation, not carried forward indefinitely.

## Baseline

All amounts exclude VAT. Sales are aggregated into Irish half-hour bins. Compare the same weekday 364 days earlier, smoothing over ±2 weeks. Match named Irish bank holidays to their previous occurrence. Exclude holiday days from ordinary comparisons. Where closures (including renovation periods) leave too few observations, use up to five nearby same-weekday observations within six weeks and flag the proxy. Require historical scheduled hours to cover at least 85% of the proposed hours. Missing observations are never interpreted as zero takings. Closed planned days forecast zero; missing planned hours or no comparable history forecast null.

Recompute weekday growth ratios over 70 completed days, using matching hours. Shrink weekday ratios toward the overall median with four pseudo-observations; bound the final factor to 0.5–1.5. This is deliberately less volatile than following yesterday's takings. Opening hours are taken from `analytics_opening_hours_daily`, not assumed from the old spreadsheet. Half-hour allocation is approximate for quarter-hour schedules.

## Separate adjustments

Cruise exposures are port-specific (Cobh, Ringaskiddy, Cork City), then cruise-line and ship deviations. Include overlap with café hours, capped at 12 hours, and passenger-capacity exposure. Require 20 port/capacity days, 12 line days or 8 ship days before fitting a term. Use strongly regularised joint regression; ship effects are deviations from the line/port effects, not an additional full uplift. Capacity is a proxy, never actual passenger disembarkations. Missing capacity can be inferred from another record for the same ship, marked in output; otherwise its capacity term is omitted. Missing departure times do not get invented. Archived inactive calls are retained; cancelled calls from the latest season are excluded.

Weather features are deviations from prior-year seasonal norms (±30 calendar days): temperature, precipitation and wind, 08:00–22:00 Irish time. Fit jointly with cruise features to reduce confounding. Subtract comparator exposures so effects already embedded in the seasonal baseline are not counted twice. Cruise adjustments are capped at ±25%; weather at ±8%, with weather tapered over its 14-day forecast horizon. No unsupported extrapolation beyond the weather horizon.

Four rolling 28-day holdouts gate each adjustment family. Cruise requires ≥2% relative weighted-error improvement and improvement in at least three folds; weather ≥1% and three folds. Each gate is recomputed daily. An enabled family is not proof of causation or of an independently significant effect for every individual ship. Sparse ship terms remain shrunk toward the broader pattern.

Historical forecast weather and cruise schedule vintages were not retained. Historical validation of these effects is therefore **conditional on realised weather/recorded visits**, not a claim of fully realistic advance forecast performance. Source calendars are also today's reconstructed history. New runs retain future weather and cruise input snapshots so true advance accuracy can be measured from deployment onward. Do not infer cruise calendar completeness from an empty future feed: beyond the last listed call, keep the cruise adjustment zero and flag missing coverage. This also means the baseline retains typical historical cruise influence until a complete future calendar is available.

## Storage and refresh

`arch_forecast_runs` archives each run, coefficients, holdout results, source sync times and input snapshot. `arch_forecast_current` holds the latest complete payload. Publishing is transactional, service-role-only, and rejects older snapshots. Both tables use RLS with no client policies. Dashboard access stays behind its existing dedicated key.

GitHub refreshes after successful weather/cruise workflows and at 06:17 UTC daily (07:17 Irish summer time / 06:17 winter time). Multiple updates are intentional when feeds finish at different times. Source-age gates retain the previous forecast on failure; the dashboard flags old snapshots. The horizon is 230 days; dates beyond the stored opening calendar remain unavailable. The model forecasts demand; it does not edit rosters or opening hours.

The displayed range uses the 80th percentile of absolute log errors in holdouts, widening with lead time. It is an **empirical planning range**, not a calibrated 80% guarantee. Events and unscheduled closures are not yet modelled. Daily actuals and weekly labour definitions are unchanged.

## Run

`PYTHONPATH=src python -m datahq.forecast` with the existing server-side Supabase environment. Offline evaluation: `python -m datahq.forecast --input input.json --output forecast.json --as-of YYYY-MM-DD`. Offline mode never publishes. Unit tests: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_forecast*.py'`.
