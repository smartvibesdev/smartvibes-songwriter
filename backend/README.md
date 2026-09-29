# Backend

FastAPI app, run on AWS Lambda via Mangum (`app.main.handler`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000/health
pytest
```
