create extension if not exists pgcrypto;

create table public.sync_state (
  source text primary key,
  last_cursor text,
  last_synced_at timestamptz,
  updated_at timestamptz not null default now()
);

create table public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running','success','failed')),
  records_read integer not null default 0,
  records_written integer not null default 0,
  error_message text,
  metadata jsonb not null default '{}'::jsonb
);
create index sync_runs_source_started_idx on public.sync_runs(source, started_at desc);

create table public.square_orders (
  id text primary key,
  location_id text,
  state text,
  created_at timestamptz,
  updated_at timestamptz,
  closed_at timestamptz,
  total_money_amount bigint,
  total_tax_money_amount bigint,
  total_discount_money_amount bigint,
  total_service_charge_money_amount bigint,
  currency text,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index square_orders_updated_idx on public.square_orders(updated_at desc);
create index square_orders_location_idx on public.square_orders(location_id, created_at desc);

create table public.square_order_items (
  id text primary key,
  order_id text not null references public.square_orders(id) on delete cascade,
  uid text,
  catalog_object_id text,
  variation_name text,
  item_name text,
  quantity numeric,
  base_price_money_amount bigint,
  gross_sales_money_amount bigint,
  total_tax_money_amount bigint,
  total_discount_money_amount bigint,
  total_money_amount bigint,
  currency text,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index square_order_items_order_idx on public.square_order_items(order_id);
create index square_order_items_catalog_idx on public.square_order_items(catalog_object_id);

create table public.square_catalogue_items (
  id text primary key,
  type text,
  name text,
  category_id text,
  is_deleted boolean not null default false,
  version bigint,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index square_catalogue_items_name_idx on public.square_catalogue_items(name);

create table public.square_team_members (
  id text primary key,
  given_name text,
  family_name text,
  status text,
  created_at timestamptz,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);

create table public.square_timecards (
  id text primary key,
  team_member_id text,
  location_id text,
  start_at timestamptz,
  end_at timestamptz,
  job_title text,
  hourly_rate_amount bigint,
  currency text,
  created_at timestamptz,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index square_timecards_member_start_idx on public.square_timecards(team_member_id, start_at desc);
create index square_timecards_location_start_idx on public.square_timecards(location_id, start_at desc);

create table public.revolut_accounts (
  id text primary key,
  name text,
  state text,
  currency text,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);

create table public.revolut_transactions (
  id text primary key,
  type text,
  state text,
  created_at timestamptz,
  completed_at timestamptz,
  reference text,
  amount numeric,
  currency text,
  account_id text,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index revolut_transactions_created_idx on public.revolut_transactions(created_at desc);
create index revolut_transactions_account_idx on public.revolut_transactions(account_id, created_at desc);

create table public.revolut_balances (
  id uuid primary key default gen_random_uuid(),
  account_id text not null,
  balance numeric not null,
  currency text not null,
  captured_at timestamptz not null default now(),
  raw_json jsonb not null default '{}'::jsonb
);
create index revolut_balances_account_captured_idx on public.revolut_balances(account_id, captured_at desc);

alter table public.sync_state enable row level security;
alter table public.sync_runs enable row level security;
alter table public.square_orders enable row level security;
alter table public.square_order_items enable row level security;
alter table public.square_catalogue_items enable row level security;
alter table public.square_team_members enable row level security;
alter table public.square_timecards enable row level security;
alter table public.revolut_accounts enable row level security;
alter table public.revolut_transactions enable row level security;
alter table public.revolut_balances enable row level security;

comment on table public.sync_state is 'Per-source incremental sync cursor / watermark.';
comment on table public.sync_runs is 'Audit log for scheduled ingestion jobs.';
