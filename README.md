# Grace Daily Devotional

A simple devotional website built with Python and Flask, with Supabase support for persistent user data.

## Features

- Daily devotional landing page
- Reflection journal entries
- Prayer request board
- Supabase-backed persistence when configured
- Local JSON fallback so the app still works in development without a database

## Quick start

1. Create a virtual environment:
   python -m venv .venv
   .venv\Scripts\activate
2. Install dependencies:
   pip install -r requirements.txt
3. Copy environment variables:
   copy .env.example .env
4. Update the values in `.env` with your Supabase credentials.
   Set `ADMIN_EMAIL` to the email address that should manage devotional posts.
5. Start the app:
   python app.py
6. Open http://127.0.0.1:5000

## Supabase setup

You need these values from your Supabase project:

- `SUPABASE_URL` — your project URL, like `https://xyzcompany.supabase.co`
- `SUPABASE_KEY` — the anon public key for the site
- Optional: the service role key only for server-only writes, not for client auth in a public app

### Auth configuration

In Supabase Dashboard:

1. Go to Authentication > Settings
2. Enable Email sign-in
3. Set your site URL and redirect URLs if you want OAuth redirect support
4. Leave email sign-up enabled for the app’s sign-up page

### Database tables

Create these tables in Supabase SQL editor:

```sql
create table if not exists journal_entries (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  reflection text not null,
  created_at timestamptz default now()
);

create table if not exists prayer_requests (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  request text not null,
  created_at timestamptz default now()
);
```

For a user profile table, you can also add:

```sql
create table if not exists profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text,
  created_at timestamptz default now()
);
```

## Gemini AI chat

This app includes a ready-to-use chat endpoint for Google Gemini. Add your API key in `.env`:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash
```

Then open the AI chat page in the browser and start testing conversations.

## Deploy to Vercel

Import this repository into Vercel using the Python/Flask framework preset. Set these environment variables in the Vercel project settings for Production (and Preview if desired):

- `SECRET_KEY` — a long, random value used to sign Flask sessions
- `ADMIN_EMAIL` — the email address authorized to create devotional posts
- `SUPABASE_URL` and `SUPABASE_KEY` — the Supabase project URL and publishable key
- `GEMINI_API_KEY` — your Gemini API key; keep it in Vercel environment settings, never in Git
- `GEMINI_MODEL` — the model available to your Gemini key

The Flask entrypoint is `main.py`; static assets are served from `public/`. The function timeout is set to 90 seconds to accommodate the app's 60-second Gemini request timeout.

## Local fallback

If `SUPABASE_URL` and `SUPABASE_KEY` are missing, the app stores entries in a JSON file under `data/devotional_store.json` so you can still test the site.
