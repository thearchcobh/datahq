alter table public.square_orders
  add column if not exists source_name text,
  add column if not exists ticket_name text,
  add column if not exists customer_id text,
  add column if not exists total_tip_money_amount bigint;

alter table public.square_order_items
  add column if not exists item_type text,
  add column if not exists note text;

alter table public.square_timecards
  add column if not exists status text,
  add column if not exists job_id text;

create table if not exists public.square_catalogue_categories (
  id text primary key,
  name text,
  is_deleted boolean not null default false,
  version bigint,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index if not exists square_catalogue_categories_name_idx
  on public.square_catalogue_categories(name);

create table if not exists public.square_catalogue_variations (
  id text primary key,
  item_id text,
  name text,
  price_amount bigint,
  price_currency text,
  is_deleted boolean not null default false,
  version bigint,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index if not exists square_catalogue_variations_item_idx
  on public.square_catalogue_variations(item_id);
create index if not exists square_catalogue_variations_name_idx
  on public.square_catalogue_variations(name);

create table if not exists public.square_scheduled_shifts (
  id text primary key,
  team_member_id text,
  location_id text,
  job_id text,
  start_at timestamptz,
  end_at timestamptz,
  notes text,
  status text,
  version bigint,
  created_at timestamptz,
  updated_at timestamptz,
  raw_json jsonb not null,
  synced_at timestamptz not null default now()
);
create index if not exists square_scheduled_shifts_member_start_idx
  on public.square_scheduled_shifts(team_member_id, start_at);
create index if not exists square_scheduled_shifts_location_start_idx
  on public.square_scheduled_shifts(location_id, start_at);

alter table public.square_catalogue_categories enable row level security;
alter table public.square_catalogue_variations enable row level security;
alter table public.square_scheduled_shifts enable row level security;

comment on table public.square_timecards is
  'Actual worked shifts/clock-ins from Square Labor Timecards.';
comment on table public.square_scheduled_shifts is
  'Published planned roster from Square Scheduled Shifts.';
