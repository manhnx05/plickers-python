.PHONY: help install install-dev test test-coverage lint format clean run-web run-scanner evaluate generate-db generate-cards

help:
	@echo "Plickers Python - Available Commands:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run code linters"
	@echo "  make format           - Format code with black"
	@echo "  make clean            - Clean generated files"
	@echo "  make run-web          - Start web application"
	@echo "  make run-scanner      - Start standalone scanner"
	@echo "  make evaluate         - Evaluate detection accuracy"
	@echo "  make generate-db      - Generate card database"
	@echo "  make generate-cards   - Generate Plickers PDF (1 card/page)"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	python test_all.py

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term

lint:
	flake8 src/ --max-line-length=120 --exclude=__pycache__
	mypy src/ --ignore-missing-imports

format:
	black src/ test_all.py run_*.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	rm -rf build dist *.egg-info

run-web:
	python run_web.py

run-scanner:
	python run_scanner.py

evaluate:
	python src/scripts/evaluate.py

generate-db:
	python src/scripts/generate_db.py

generate-cards:
	python src/scripts/generate_single_card.py
