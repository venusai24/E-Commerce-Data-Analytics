.PHONY: setup db-up db-down profile clean load warehouse kpis dq analyze export report all test lint fixture

setup:
	pip install -e ".[dev]"

db-up:
	docker compose up -d

db-down:
	docker compose down -v

profile:
	python -m olist_analytics profile

clean:
	python -m olist_analytics clean

load:
	python -m olist_analytics load-staging

warehouse:
	python -m olist_analytics build-warehouse

kpis:
	python -m olist_analytics build-kpis

dq:
	python -m olist_analytics dq-check

analyze:
	python -m olist_analytics analyze

export:
	python -m olist_analytics export

report:
	python -m olist_analytics report

all: db-up
	python -m olist_analytics run-all

test:
	pytest

lint:
	ruff check .
	ruff format --check .

fixture:
	python tests/fixtures/make_fixture.py --out tests/fixtures/generated
