.PHONY: database registry app

DB_NAME := tournament_db
DB_USER := tournament_user
DB_PASSWORD := tournament_pass

database:
	mkdir -p database && \
	docker run --rm \
		--name pgsql \
		-p 5432:5432 \
		-e POSTGRES_PASSWORD=admin_pass \
		-e DB_PASSWORD=$(DB_PASSWORD) \
		-e DB_USER=$(DB_USER) \
		-e DB_NAME=$(DB_NAME) \
		-v ./scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh \
		-v ./database:/var/lib/postgresql/data \
		--user $(shell id -u):$(shell id -g) \
		postgres:17.4

registry:
	docker run --rm \
		--name registry \
		-p 5000:5000 \
		-v ./registry:/var/lib/registry \
		registry:2

app:
	uvicorn main:app --reload
