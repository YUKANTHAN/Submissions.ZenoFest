create table if not exists public.event_submissions (
  id uuid primary key default gen_random_uuid(),
  team_id text not null,
  team_name text,
  email text not null,
  tech_event text,
  submitted_at timestamptz default now(),
  form_data jsonb
);

alter table public.event_submissions enable row level security;

drop policy if exists "anon insert only" on public.event_submissions;
create policy "anon insert only"
  on public.event_submissions
  for insert to anon
  with check (true);

drop policy if exists "authed users can read" on public.event_submissions;
create policy "authed users can read"
  on public.event_submissions
  for select to authenticated
  using (true);

drop policy if exists "authed users can insert" on public.event_submissions;
create policy "authed users can insert"
  on public.event_submissions
  for insert to authenticated
  with check (true);

drop policy if exists "authed users can update" on public.event_submissions;
create policy "authed users can update"
  on public.event_submissions
  for update to authenticated
  using (true);

drop policy if exists "authed users can delete" on public.event_submissions;
create policy "authed users can delete"
  on public.event_submissions
  for delete to authenticated
  using (true);

-- Table privileges (RLS policies control WHICH rows; GRANTs control WHETHER a
-- role can touch the table at all). Without these the API returns
-- "permission denied for table event_submissions".
grant insert on public.event_submissions to anon;
grant select, insert, update, delete on public.event_submissions to authenticated;
grant select, insert, update, delete on public.event_submissions to service_role;