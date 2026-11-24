# Setup

Two accounts needed — both free tier, both yours to own. I can't create
accounts or paste in secrets for you, so this part's manual, but it's quick.

## 1. Supabase (the database)

1. Go to supabase.com, sign up, "New project". Pick any name/region, set a
   database password (save it somewhere, you likely won't need it again).
2. Once it's ready: **SQL Editor** → New query → paste the entire contents of
   [`db/schema.sql`](db/schema.sql) → Run.
3. **Project Settings → API**. You need three values:
   - `Project URL` → this is `SUPABASE_URL`
   - `anon` `public` key → safe to put directly in `docs/index.html` (that's what it's for)
   - `service_role` key → **secret**, never put this in the dashboard or commit it. Goes into GitHub Actions secrets and your local `.env` only.

## 2. GitHub (the repo + the daily cron + the dashboard hosting)

1. Create a new repo (private or public, your call — GitHub Pages on the free
   plan works the same either way, and the dashboard itself is gated by
   Supabase sign-in regardless — see step 4 below).
2. Push this project to it:
   ```bash
   git remote add origin <your-repo-url>
   git branch -M main
   git push -u origin main
   ```
3. **Repo → Settings → Secrets and variables → Actions → New repository secret**.
   Add two:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. **Repo → Settings → Pages**. Source: "Deploy from a branch", branch `main`,
   folder `/docs` (GitHub's branch-deploy option only supports `/` or `/docs`,
   never an arbitrary folder name — that's why this project's dashboard
   folder is called `docs` rather than something more descriptive). Save.
   GitHub gives you a URL like `https://<you>.github.io/<repo>/` — that's
   the link to share.
5. Edit `docs/index.html`, fill in `SUPABASE_URL` and `SUPABASE_ANON_KEY`
   at the top of the `<script>` block, commit, push.
6. **Repo → Actions tab** — the daily workflow is already there
   (`.github/workflows/daily-scrape.yml`), scheduled for 06:00 Yerevan time.
   You can also click "Run workflow" to trigger it immediately instead of
   waiting for tomorrow.

## 3. Try it

- Trigger the Actions workflow manually once, check the run logs for each
  site's product count.
- Open your GitHub Pages URL — you should see rows.
- Run the weekly manual pass locally (see README) for Zigzag/Eldorado/
  AllSell/Ozon/Homemart/Wildberries — those need a human to clear a
  challenge at least once before they'll have any data at all.

## 4. Access control (sign-in gate)

The dashboard requires a real Supabase Auth session before it'll show any
data — it's enforced in Postgres (RLS), not just in the page's own JS, so
the public anon key genuinely can't read anything by itself. Two settings
need to be set in the Supabase dashboard (not something doable via the REST
API, so this is a manual click):

1. **Authentication → URL Configuration.** Set `Site URL` to your GitHub
   Pages URL (e.g. `https://g-dzav.github.io/Armenia-Air-Purifier-Prices/`)
   and add the same URL under `Redirect URLs`. Without this, the sign-in
   email's magic link won't be allowed to redirect back to the dashboard.
2. **Authentication → Sign In / Providers → Email.** Turn **off** "Allow new
   users to sign up" — otherwise anyone who finds the link can type in their
   own email and let themselves in, which defeats the point. With it off,
   only people you've explicitly added can sign in.
3. **Authentication → Users → Add user → Send invite.** Add an email for
   each person who should have access (yourself included). They'll get a
   Supabase invite email; after that, typing their email into the
   dashboard's sign-in box sends them a one-time magic link each time they
   want in (no password to manage).
4. Re-run the full [`db/schema.sql`](db/schema.sql) once more in the SQL
   editor — it now requires a signed-in session to read any table, where it
   used to allow anyone with the anon key.

## Ongoing cost

Supabase free tier and GitHub Actions/Pages free tier both comfortably cover
a project this size (a handful of sites, once a day, small tables). Nothing
here should hit a paywall unless this grows a lot.
