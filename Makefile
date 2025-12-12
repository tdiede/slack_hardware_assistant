# Makefile shortcuts for Docker-based development

.PHONY: up down build restart logs ps stop db stop_db venv run

# Build images and start all services
up:
	docker compose up --build -d backend

# Stop and remove containers, networks, and volumes created by docker-compose
# (except named volumes like postgres_data)
down:
	docker compose down

# Build images without starting containers
build:
	docker build -t backend .

# Restart backend service
restart:
	docker compose restart backend


# Generic Docker commands
logs:
	docker compose logs -f
ps:
	docker compose ps -a


# Makefile shortcuts for virtual environment-based development
# Start Postgres database in Docker

db:
	docker compose up -d db
	@echo "Postgres database is running."

stop_db:
	docker stop db
	@echo "Postgres database has been stopped."

venv:
	python -m venv venv
	@echo "Virtual environment created. Now activate it with `source venv/bin/activate` and install dependencies using `make install`."

install:
	pip install -r requirements.txt
	@echo "Dependencies installed."

run: db
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
	@echo "FastAPI application is running at http://0.0.0.0:8000"
