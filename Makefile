.PHONY: install setup download-spansh import-spansh run-pipeline lint lint-fix type check lint-fix-check download-eddn-models gen-eddn-models models

CURRENT_UID=$(shell id -u)
CURRENT_GID=$(shell id -g)

## Setup

install:
	poetry install

setup: install install-models up alembic-upgrade
setup-container: install-models alembic-upgrade
	mkdir -p app_logs
	mkdir -p setup_logs

# Also need to create config.yaml and optionally .env PG_PORT override file
run-prod:
	build up

## Discord
discord-bot:
	python src/ekaine/interfaces/discord/bot.py

## EDDN
eddn-listener:
	poetry run cli ingestion eddn-listener

eddn-listener-v:
	poetry run cli ingestion eddn-listener -v

eddn-listener-vv:
	poetry run cli ingestion eddn-listener -vv

## Data DL/Import

download-spansh:
	poetry run cli ingestion download-spansh

import-spansh:
	poetry run cli ingestion import-spansh

import-spansh-v:
	poetry run cli ingestion import-spansh -v

import-spansh-vv:
	poetry run cli ingestion import-spansh -vv

run-pipeline: download-spansh import-spansh-v

hydrate-db:
	./tools/scripts/hydrate_postgres.sh

## Code Quality

lint:
	poetry run sqlfluff lint --dialect postgres . --verbose
	poetry run yamllint **/*.yaml
	poetry run lint_metadata
	poetry run black --check src/
	poetry run isort --check-only src/
	poetry run flake8 src/ -v

lint-fix:
	poetry run sqlfluff fix --dialect postgres . --verbose
	poetry run yamlfix **/*.yaml
	poetry run lint_metadata
	poetry run black src/
	poetry run isort src/

type:
	poetry run mypy src/

check: lint type

lint-fix-check:
	poetry run sqlfluff fix --dialect postgres . --verbose
	poetry run yamlfix **/*.yaml
	poetry run lint_metadata
	poetry run black src/
	poetry run isort src/
	poetry run flake8 src/ -v
	poetry run mypy src/

## Docker (Builds/Images)
.PHONY: build_app
build_app:
	docker build -f tools/docker/ekaine/Dockerfile \
		--no-cache \
		--tag='remiscarlet/ekaine' \
		.

.PHONY: build_nginx
build_nginx:
	   docker build -f tools/docker/ekaine-nginx-proxy/Dockerfile \
			   --no-cache \
			   --build-arg HOST_UID=${CURRENT_UID} \
			   --build-arg HOST_GID=${CURRENT_GID} \
			   --tag='remiscarlet/ekaine-nginx-proxy' \
			   .


.PHONY: build_smallstep_ca
build_smallstep_ca:
	mkdir -p tools/docker/ekaine_ca/certs
	mkdir -p tools/docker/ekaine_ca/config
	mkdir -p tools/docker/ekaine_ca/db
	mkdir -p tools/docker/ekaine_ca/secrets
	docker build -f tools/docker/ekaine_ca/Dockerfile \
			--no-cache \
			--build-arg HOST_UID=${CURRENT_UID} \
			--build-arg HOST_GID=${CURRENT_GID} \
			--tag='remiscarlet/ekaine_ca' \
			.

build: build_app build_smallstep_ca

## Docker (Dev Only)

pg-shell: # "Lightweight" PG shell for convenience
	poetry run pgcli "postgresql://ekaine:ekaine_pw@localhost:5432/ekaine"

nuke-db:
	docker stop ekaine_db
	docker rm ekaine_db

up:
	mkdir -p tools/docker/step_ca/secrets
	mkdir -p tools/docker/step_ca/certs
	docker compose -f tools/docker/docker-compose.yaml up --build -d

down:
	docker compose -f tools/docker/docker-compose.yaml down

up-db:
	docker compose -f tools/docker/docker-compose.yaml up --build -d postgres

down-db:
	docker compose -f tools/docker/docker-compose.yaml stop postgres

up-app:
	docker compose -f tools/docker/docker-compose.yaml up --build -d app

down-app:
	docker compose -f tools/docker/docker-compose.yaml stop app

## Alembic

alembic-downgrade-one:
	poetry run alembic downgrade -1

alembic-upgrade:
	poetry run alembic upgrade head

alembic-revision:
	poetry run alembic revision --autogenerate

## Code Gen

download-eddn-models:
	mkdir -p data
	git clone https://github.com/EDCD/EDDN.git -b live data/eddn/ 2>/dev/null || true
	git -C data/eddn pull

gen-eddn-models:
	./tools/scripts/generate_eddn_models.sh

gen-metadata-models:
	./tools/scripts/generate_metadata_models.sh

download-gen-models: download-eddn-models gen-eddn-models gen-metadata-models

gen-eddn-model-mappings:
	poetry run generate_eddn_schema_mapping

install-models: download-gen-models gen-eddn-model-mappings
models: install-models

clean-models:
	rm -f src/gen/eddn_schema_to_model_mapping.json
	rm -rf src/gen/generate_eddn_models
	rm -rf src/gen/eddn_models
	rm -rf data/eddn
	rm -rf data/eddn_schemas_patched

# make nuke-db; make up-db; sleep 1; make alembic-upgrade; make alembic-revision; make alembic-upgrade;
# openssl pkey -in in.key -out out.key.pem