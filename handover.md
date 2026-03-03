# Handover Document

## Local Execution
1. Install dependencies: `pip install -r requirements.txt`
2. Setup `.env` file.
3. Run API: `python api_server.py`
4. Run Worker: `python main_worker.py`

## Testing
Run `pytest -q` or `python test_integration.py`.

## Deployment
- **Backend**: Deploy to Render as two separate services (Web for API, Background Worker for main_worker).
- **Database**: Use the provided `schema.sql` in Supabase.
- **Frontend**: Deploy Next.js app to Vercel.

## Documentation
- Prompts: `prompts.md`
- Schema: `schema.sql`
