-- Keep detailed operational history to the current and previous calendar year.
-- Remove bulky source payloads where normalized fields already cover reporting needs.

alter table public.revolut_balances
  add column if not exists balance_date date;

update public.revolut_balances
set balance_date = captured_at::date
where balance_date is null;

alter table public.revolut_balances
  alter column balance_date set default current_date,
  alter column balance_date set not null;

create unique index if not exists revolut_balances_account_date_uidx
  on public.revolut_balances(account_id, balance_date);

alter table public.square_orders drop column if exists raw_json;
alter table public.square_order_items drop column if exists raw_json;

alter table public.revolut_accounts drop column if exists raw_json;
alter table public.revolut_balances drop column if exists raw_json;
alter table public.revolut_transactions drop column if exists raw_json;
alter table public.revolut_transaction_legs drop column if exists raw_json;

-- January 1 of the previous calendar year. On 2026-08-18 this is 2025-01-01.
with cutoff as (
  select date_trunc('year', now()) - interval '1 year' as starts_at
)
delete from public.square_orders
where created_at < (select starts_at from cutoff);

with cutoff as (
  select date_trunc('year', now()) - interval '1 year' as starts_at
)
delete from public.square_timecards
where start_at < (select starts_at from cutoff);

with cutoff as (
  select date_trunc('year', now()) - interval '1 year' as starts_at
)
delete from public.revolut_transactions
where created_at < (select starts_at from cutoff);

with cutoff as (
  select (date_trunc('year', now()) - interval '1 year')::date as starts_on
)
delete from public.revolut_balances
where balance_date < (select starts_on from cutoff);
