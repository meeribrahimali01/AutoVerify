# AutoVerify Backend

FastAPI backend service for AutoVerify.

## Running the Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```
