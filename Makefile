.PHONY: install run analytics demo docker-up docker-down docker-logs env

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cp -n .env.example .env || true

env:
	cp -n .env.example .env || true
	@echo "Edit .env and set TELEGRAM_BOT_TOKEN from @BotFather"

run:
	PYTHONPATH=src .venv/bin/python -m gatum_agent.main run

analytics:
	PYTHONPATH=src .venv/bin/python -m gatum_agent.main analytics --format text

demo:
	./scripts/demo.sh

docker-up:
	docker compose up --build -d
	@echo "API: http://localhost:8000/health"
	@echo "Logs: make docker-logs"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f agent
