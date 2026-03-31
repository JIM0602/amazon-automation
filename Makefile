.PHONY: test run lint install clean

install:
	pip install -r requirements.txt

test:
	pytest tests/ --mock-external-apis -v

lint:
	ruff check src/ tests/

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
