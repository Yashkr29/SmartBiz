# SmartBiz

A business management system for small businesses. Customers, products, inventory, orders, payments, suppliers and expenses live in one connected system, with an AI assistant that answers questions about your business in plain English.

> SmartBiz uses React and Tailwind CSS for the frontend, FastAPI and Python for RESTful backend services, PostgreSQL (Supabase) for relational data, and an LLM-based AI layer with LangChain and Gemini for natural-language business analytics.

## Features

- **Order lifecycle:** New, Confirmed, In Production, Ready, Delivered. Stages move one step at a time.
- **Automatic inventory:** stock is deducted when an order is created and restored if an undelivered order is deleted.
- **Advance and pending payments:** every order tracks money received and money still owed.
- **Dashboard:** total sales, active orders, pending payments, low-stock products, expenses, estimated profit and a 7-day orders chart.
- **AI business Q&A:** ask "Who owes me the most?" and get an answer from your real data.
- **Your own workspace:** every account starts with an empty dashboard. Customers, products, orders, payments and expenses belong to the account that created them, and nobody else can see or change them (the AI assistant is limited the same way).
- **CSV import:** bring in customers, products, suppliers and expenses from Excel (saved as CSV). Columns such as "Customer Name", "Mobile", "Qty" or "MRP" are matched automatically, you see a preview with row-by-row errors before anything is saved, and a template can be downloaded from each page.
- **Validation and business rules:** no overselling stock, no advance above the order total, no overpayment, no negative stock.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Recharts, Axios |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL on Supabase (SQLite for quick local tests) |
| Authentication | JWT tokens, bcrypt password hashing |
| AI | LangChain with Google Gemini, text-to-SQL |

## Project structure

```
smartbiz-backend/
├── .env.example            settings template
├── requirements.txt
├── requirements-dev.txt    test tools (pytest)
├── tests/                  automated API, import, AI and upgrade tests
├── supabase/schema.sql     Supabase tables, rules, views, security
└── app/
    ├── main.py             app start, CORS, routes under /api
    ├── database.py         database connection
    ├── models.py           database tables
    ├── schemas.py          request/response validation
    ├── security.py         passwords, JWT, admin/staff checks
    ├── ai.py               Gemini question-to-query pipeline and safety checks
    ├── upgrade.py          upgrades older databases to per-account data
    └── routers/            auth.py, crud.py, orders.py, insights.py, imports.py (CSV)

smartbiz-frontend/
├── .env.example            backend address
├── package.json
└── src/
    ├── main.jsx, App.jsx   entry, routes, login state, layout
    ├── api.js, ui.jsx      API setup, shared helpers
    └── pages/              Landing, Login, Dashboard, Orders, Lists, ImportCsv, Assistant
```

## How it fits together

```
React pages  ->  FastAPI routes  ->  SQLAlchemy models  ->  Supabase PostgreSQL

AI question:  Assistant page -> /api/ai/ask -> Gemini writes a query
              -> safety checks -> read-only run -> Gemini writes the answer
```

Main data flow: Customer, Order, Inventory, Payment, Expense, Dashboard and profit.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- A free Supabase project (supabase.com)
- A Gemini API key from aistudio.google.com (optional, for the AI assistant)

## Setup

### 1. Database (Supabase)

1. Create a Supabase project and note the database password.
2. Open **SQL Editor**, paste the contents of `smartbiz-backend/supabase/schema.sql`, change the `smartbiz_ai` password on the role line, and run it.
3. Open **Project Settings, Database, Connection string, URI** and copy the Session pooler string. You will paste it into `.env` next.

### 2. Backend

```
cd smartbiz-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On Mac or Linux use `source venv/bin/activate` instead of the activate line above.

Copy `.env.example` to `.env` and fill it in:

```
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_DB_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GOOGLE_API_KEY=<your Gemini key, or leave empty for basic mode>
```

If the password contains symbols like `@` or `#`, URL-encode them (`@` becomes `%40`).

Start the server:

```
uvicorn app.main:app --reload
```

The API runs at http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.

### 3. Frontend

In a second terminal:

```
cd smartbiz-frontend
npm install
npm run dev
```

Open http://localhost:5173. If your backend is not at `localhost:8000`, copy `.env.example` to `.env` and change `VITE_API_URL`.

### 4. First use

1. Click **Get started**, choose **Sign up** and create your account. You get your own empty dashboard.
2. Add customers and products, or open **Customers** / **Inventory** and use **Import CSV** (click **Download template** to see the expected columns).
3. Create an order from the **Orders** page, record payments and move it through the stages.

There is no demo seed data: every account starts empty.

### CSV import

- Supported pages: Customers, Inventory (products), Suppliers, Expenses. In Excel use File, Save As, CSV (UTF-8).
- Required columns: customers and suppliers need a name; products need a name and SKU; expenses need a title and amount. Other columns are optional.
- Comma, semicolon or tab separated files work. Amounts may include `₹`, `Rs.` and commas (`₹1,25,000`). Dates may be `2026-11-05`, `05/11/2026` (day first) or Excel date numbers.
- Products with a SKU you already have are updated (stock, price and so on). Customers, suppliers and expenses that already exist are skipped, so uploading the same file twice is safe.
- Limits: 5 MB and 5,000 rows per file. Rows with problems are listed by row number and left out; the rest are imported.

### Running the tests

```
cd smartbiz-backend
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a temporary SQLite database and a fake AI model, so they never touch Supabase or call Gemini.

## Environment variables (backend)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase connection string. Leave empty to use a local SQLite file. |
| `SECRET_KEY` | Private key used to sign login tokens. Generate your own and keep it secret. |
| `CORS_ORIGINS` | Websites allowed to call the API. Add your deployed frontend address when you deploy. |
| `GOOGLE_API_KEY` | Gemini key. Without it the assistant answers a few fixed question types (basic mode). |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.8-flash`. |
| `GEMINI_FALLBACK_MODEL` | Optional. Used automatically when the main model is overloaded or slow. Defaults to `gemini-flash-lite-latest`; set it empty to disable. |
| `GEMINI_TIMEOUT` | Optional. Seconds per Gemini call, default 25. |
| `TZ_OFFSET_MINUTES` | Optional. Business time zone for the dashboard's daily chart, in minutes from UTC. Default 330 (India). |
| `AI_DATABASE_URL` | Optional. Connects the AI as the read-only `smartbiz_ai` database role. |

## API overview

All routes start with `/api`. Everything except register, login and health needs a login token, and only returns the logged-in account's own data.

| Area | Routes |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Customers, Suppliers, Products, Expenses | `GET /{name}` (optional `?q=` search), `POST /{name}`, `PUT /{name}/{id}`, `DELETE /{name}/{id}` |
| CSV import | `POST /import/{customers,products,suppliers,expenses}?commit=false` (preview) or `?commit=true` (save), multipart field `file` |
| Orders | `GET /orders`, `GET /orders/{id}`, `POST /orders`, `POST /orders/{id}/payments`, `POST /orders/{id}/advance`, `DELETE /orders/{id}` |
| Insights | `GET /dashboard`, `POST /ai/ask` |
| Health | `GET /health` |

## AI assistant and safety

1. Gemini turns your question into one database query.
2. The query is checked before it runs. Only a single `SELECT` is allowed, and anything that writes data, touches the `users` table or names a schema directly (`public.`, `auth.`) is refused.
3. The query is wrapped so every table name means "this account's rows only". One business can never see another's data through the assistant.
4. It runs read-only with a 5 second limit and a 50 row cap. With `AI_DATABASE_URL` set, the database itself also blocks writes.
5. Gemini writes a short answer from the returned rows. A "Show how I found this" toggle in the chat shows the query used.

Your question and the matching result rows are sent to Google. Use made-up data for demos until you use a paid key, and check Google's current terms for free keys.

If the main Gemini model is overloaded (503) or times out, the fallback model answers instead. If the key is missing or every model fails, the assistant falls back to basic keyword answers. The badge under each reply shows which mode answered and why.

## Troubleshooting

| Problem | Fix |
|---|---|
| `npm start` says Missing script | Use `npm run dev`. |
| PowerShell blocks `venv\Scripts\activate` | Run `Set-ExecutionPolicy -Scope Process Bypass`, then activate again. |
| "could not translate host name" | Use the Session pooler connection string, not the direct one. Direct needs IPv6. |
| "password authentication failed" | Re-check the database password and URL-encode symbols. |
| Browser shows a CORS error | Make sure the frontend address is in `CORS_ORIGINS`, then restart the backend. |
| Pages say "Cannot reach the server" | The backend is not running, or `VITE_API_URL` points to the wrong address. |
| Assistant badge says "Basic mode" | Check `GOOGLE_API_KEY` and read the backend terminal for the Gemini error. `503 UNAVAILABLE` or `504 DEADLINE_EXCEEDED` mean Google is overloaded; try again later. |
| "tenant/user postgres.xxxx not found" | The Supabase pooler does not know this project. Check the project is not paused, and copy the connection string again from Supabase (the host may be `aws-1-...` instead of `aws-0-...`). |
| Old data disappeared after updating | Data is now per account. Rows created before the update have no owner and are hidden. See the clean-up section at the end of `supabase/schema.sql`. |
| Logged out unexpectedly | Tokens last 12 hours, and changing `SECRET_KEY` signs everyone out. |

## Deployment

The intended setup is Vercel for the frontend, Render or Railway for the backend and Supabase for the database. When deploying:

1. Set the backend environment variables on the host (never commit `.env`).
2. Add the deployed frontend address to `CORS_ORIGINS`.
3. Set `VITE_API_URL` on the frontend host to the deployed backend address ending in `/api`.

## Current limitations and roadmap

- CSV import covers customers, products, suppliers and expenses. Orders are created in the app so stock and payments stay consistent. `.xlsx` files must be saved as CSV first.
- One login per business. Inviting staff into the same workspace is not built yet.
- There is no separate Payments page. Payments are recorded from each order.
- Tables are created on startup and upgraded by `app/upgrade.py`. Moving to Alembic migrations is still to do.
- The AI assistant answers one question at a time and does not remember earlier messages.
