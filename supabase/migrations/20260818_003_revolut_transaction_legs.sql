alter table public.revolut_accounts
  add column if not exists balance numeric,
  add column if not exists public boolean,
  add column if not exists created_at timestamptz,
  add column if not exists updated_at timestamptz;

alter table public.revolut_transactions
  add column if not exists request_id text,
  add column if not exists updated_at timestamptz,
  add column if not exists reason_code text,
  add column if not exists scheduled_for date,
  add column if not exists related_transaction_id text,
  add column if not exists merchant_name text,
  add column if not exists merchant_city text,
  add column if not exists merchant_category_code text,
  add column if not exists merchant_country text,
  add column if not exists card_id text;

create table if not exists public.revolut_transaction_legs (
  id text primary key,
  transaction_id text not null references public.revolut_transactions(id) on delete cascade,
  account_id text,
  amount numeric,
  fee numeric,
  currency text,
  bill_amount numeric,
  bill_currency text,
  description text,
  balance numeric,
  counterparty_json jsonb,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);

create index if not exists revolut_transaction_legs_transaction_idx
  on public.revolut_transaction_legs(transaction_id);
create index if not exists revolut_transaction_legs_account_idx
  on public.revolut_transaction_legs(account_id);

alter table public.revolut_transaction_legs enable row level security;

comment on table public.revolut_transaction_legs is
  'Individual account movements/legs belonging to Revolut Business transactions.';
