-- Sharma Interior Construction - row level security
--
-- Run this AFTER schema.sql, in the Supabase SQL Editor.
--
-- Without RLS, Supabase's anon key - which ships in the admin's JavaScript
-- and is therefore public - grants full read AND write on every table.
-- These policies keep reads open (the site content is published anyway,
-- and the build needs to read it) while restricting every write to a
-- signed-in user.

begin;

-- settings
alter table public.settings enable row level security;
drop policy if exists "settings_read" on public.settings;
drop policy if exists "settings_write" on public.settings;
create policy "settings_read"  on public.settings for select using (true);
create policy "settings_write" on public.settings for all to authenticated
  using (true) with check (true);

-- services
alter table public.services enable row level security;
drop policy if exists "services_read" on public.services;
drop policy if exists "services_write" on public.services;
create policy "services_read"  on public.services for select using (true);
create policy "services_write" on public.services for all to authenticated
  using (true) with check (true);

-- projects
alter table public.projects enable row level security;
drop policy if exists "projects_read" on public.projects;
drop policy if exists "projects_write" on public.projects;
create policy "projects_read"  on public.projects for select using (true);
create policy "projects_write" on public.projects for all to authenticated
  using (true) with check (true);

-- team
alter table public.team enable row level security;
drop policy if exists "team_read" on public.team;
drop policy if exists "team_write" on public.team;
create policy "team_read"  on public.team for select using (true);
create policy "team_write" on public.team for all to authenticated
  using (true) with check (true);

-- testimonials
alter table public.testimonials enable row level security;
drop policy if exists "testimonials_read" on public.testimonials;
drop policy if exists "testimonials_write" on public.testimonials;
create policy "testimonials_read"  on public.testimonials for select using (true);
create policy "testimonials_write" on public.testimonials for all to authenticated
  using (true) with check (true);

-- faqs
alter table public.faqs enable row level security;
drop policy if exists "faqs_read" on public.faqs;
drop policy if exists "faqs_write" on public.faqs;
create policy "faqs_read"  on public.faqs for select using (true);
create policy "faqs_write" on public.faqs for all to authenticated
  using (true) with check (true);

-- jobs
alter table public.jobs enable row level security;
drop policy if exists "jobs_read" on public.jobs;
drop policy if exists "jobs_write" on public.jobs;
create policy "jobs_read"  on public.jobs for select using (true);
create policy "jobs_write" on public.jobs for all to authenticated
  using (true) with check (true);

-- page_seo
alter table public.page_seo enable row level security;
drop policy if exists "page_seo_read" on public.page_seo;
drop policy if exists "page_seo_write" on public.page_seo;
create policy "page_seo_read"  on public.page_seo for select using (true);
create policy "page_seo_write" on public.page_seo for all to authenticated
  using (true) with check (true);

-- media
alter table public.media enable row level security;
drop policy if exists "media_read" on public.media;
drop policy if exists "media_write" on public.media;
create policy "media_read"  on public.media for select using (true);
create policy "media_write" on public.media for all to authenticated
  using (true) with check (true);

-- redirects
alter table public.redirects enable row level security;
drop policy if exists "redirects_read" on public.redirects;
drop policy if exists "redirects_write" on public.redirects;
create policy "redirects_read"  on public.redirects for select using (true);
create policy "redirects_write" on public.redirects for all to authenticated
  using (true) with check (true);

commit;

-- ------------------------------------------------------------------
-- Storage bucket for admin uploads
-- ------------------------------------------------------------------

insert into storage.buckets (id, name, public)
values ('media', 'media', true)
on conflict (id) do nothing;

drop policy if exists "media_read"   on storage.objects;
drop policy if exists "media_insert" on storage.objects;
drop policy if exists "media_update" on storage.objects;
drop policy if exists "media_delete" on storage.objects;

create policy "media_read" on storage.objects
  for select using (bucket_id = 'media');

create policy "media_insert" on storage.objects
  for insert to authenticated with check (bucket_id = 'media');

create policy "media_update" on storage.objects
  for update to authenticated using (bucket_id = 'media');

create policy "media_delete" on storage.objects
  for delete to authenticated using (bucket_id = 'media');
