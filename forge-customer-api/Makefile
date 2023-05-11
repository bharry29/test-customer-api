DB_PASS_PROD := $(shell aws secretsmanager get-secret-value --secret-id forge-api-db-pass --query SecretString --output text --no-cli-pager)

help:
	@echo "'make build' or 'make run-prod'"

build:
	docker build -t forge-api:latest .

run-prod: build
	@export DB_PASS=$(DB_PASS_PROD); \
	docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up
