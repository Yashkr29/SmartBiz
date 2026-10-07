# SmartBiz backend (FastAPI)

    python -m venv venv && venv\Scripts\activate      # Windows (use source venv/bin/activate on Mac/Linux)
    pip install -r requirements.txt
    python seed.py                                    # optional demo data
    uvicorn app.main:app --reload

API docs with a built-in tester: http://localhost:8000/docs
Settings live in a `.env` file: copy `.env.example` to `.env` and fill it in. With no `.env` the API uses a local SQLite file.

## Supabase (PostgreSQL)
1. Create a project at supabase.com. In the SQL Editor, paste `supabase/schema.sql` (change the `smartbiz_ai` password first) and run it.
2. Project Settings > Database > Connection string > copy the URI into `DATABASE_URL` in `.env` (replace [YOUR-PASSWORD] with your database password).
3. Run `uvicorn app.main:app --reload`, then register your first account (it becomes Admin).
