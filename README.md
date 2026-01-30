# Majha Sarkari Setu (Majhi Naukri style)

## Run locally (Windows)
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

## Admin
- URL: /admin/login
- Default username: admin
- Password comes from env var `ADMIN_PASSWORD`

### Set password (Windows PowerShell)
```powershell
$env:ADMIN_PASSWORD="YourStrongPassword"
$env:SECRET_KEY="any-random-long-string"
python app.py
```

If you do not set `ADMIN_PASSWORD`, admin login will be blocked for safety.

## Deploy (Render.com quick)
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Environment Variables:
  - `ADMIN_PASSWORD` = set strong password
  - `SECRET_KEY` = set random long string

## Notes
- Database: SQLite file `database.db` auto-creates on first run.
- Categories are: Job, Result, Scheme (you can add more from admin).
