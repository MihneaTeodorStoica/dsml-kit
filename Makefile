.PHONY: build build-dev pull prepare-workspace run start run-dev run-image logs shell stop clean clean-all nuke test validate freeze publish env

-include .env

IMAGE_NAME ?= ghcr.io/mihneateodorstoica/dsml-kit
DSML_TAG ?= latest
DSML_MODE ?= image
GPU_ENABLED ?= false
WORKSPACE_DIR ?= ./workspace
DSML_MODE_VALUE := $(strip $(DSML_MODE))
GPU_ENABLED_VALUE := $(strip $(GPU_ENABLED))
HOST_UID_VALUE := $(strip $(or $(HOST_UID),$(shell id -u)))
HOST_GID_VALUE := $(strip $(or $(HOST_GID),$(shell id -g)))
override HOST_UID := $(HOST_UID_VALUE)
override HOST_GID := $(HOST_GID_VALUE)
export HOST_UID
export HOST_GID
IMAGE := $(IMAGE_NAME):$(DSML_TAG)
DATE_TAG := $(shell date +%F)
COMPOSE_FILES := -f compose.yaml
ifeq ($(GPU_ENABLED_VALUE),true)
COMPOSE_FILES += -f compose.gpu.yaml
endif
COMPOSE := docker compose $(COMPOSE_FILES)
COMPOSE_DEV := docker compose $(COMPOSE_FILES) -f compose.dev.yaml

build: env
	@if [ "$(DSML_MODE_VALUE)" = "dev" ]; then \
		$(COMPOSE_DEV) build; \
	else \
		printf "DSML_MODE=%s uses published image; nothing to build locally.\n" "$(DSML_MODE_VALUE)"; \
	fi

build-dev: env
	$(COMPOSE_DEV) build

pull: env
	@if [ "$(DSML_MODE_VALUE)" = "dev" ]; then \
		printf "DSML_MODE=dev builds locally; skipping pull.\n"; \
	else \
		$(COMPOSE) pull app; \
	fi

prepare-workspace: env
	@workspace="$(WORKSPACE_DIR)"; \
	mkdir -p "$$workspace"; \
	workspace_abs=$$(cd "$$workspace" && pwd -P); \
	if [ -w "$$workspace_abs" ]; then \
		chmod -R u+rwX "$$workspace_abs" >/dev/null 2>&1 || true; \
	else \
		printf "Repairing workspace permissions for %s:%s at '%s'.\n" "$(HOST_UID)" "$(HOST_GID)" "$$workspace_abs"; \
		docker run --rm --user root -v "$$workspace_abs:/workspace" busybox:1.37 sh -c 'chown -R $(HOST_UID):$(HOST_GID) /workspace && chmod -R u+rwX /workspace' >/dev/null 2>&1 || true; \
	fi

run: prepare-workspace
	@if [ "$(DSML_MODE_VALUE)" = "dev" ]; then \
		$(COMPOSE_DEV) up --build; \
	else \
		$(COMPOSE) up; \
	fi

start: prepare-workspace
	@if [ "$(DSML_MODE_VALUE)" = "dev" ]; then \
		$(COMPOSE_DEV) up --build -d; \
	else \
		$(COMPOSE) up -d; \
	fi

run-dev: env
	@$(MAKE) run DSML_MODE=dev

run-image: env
	@$(MAKE) run DSML_MODE=image

logs:
	$(COMPOSE) logs -f app

shell:
	$(COMPOSE) exec --user "$(HOST_UID):$(HOST_GID)" app bash

stop:
	-$(COMPOSE) stop

clean:
	@$(COMPOSE) down --remove-orphans >/dev/null 2>&1 || true

clean-all: clean
	@if docker image inspect "$(IMAGE)" >/dev/null 2>&1; then \
		docker image rm "$(IMAGE)" >/dev/null 2>&1 || true; \
		printf "Removed image %s\n" "$(IMAGE)"; \
	else \
		printf "Image %s not present locally; nothing to remove.\n" "$(IMAGE)"; \
	fi

nuke:
	@workspace="$(WORKSPACE_DIR)"; \
	case "$$workspace" in \
		""|"/"|".") \
			printf "Refusing to delete unsafe WORKSPACE_DIR value '%s'.\n" "$$workspace"; \
			exit 0; \
			;; \
	esac; \
	printf "WARNING: delete compose resources and workspace '%s'?\n" "$$workspace"; \
	printf "Type 'Yes, do as I say!' to continue: "; \
	read -r confirm; \
	if [ "$$confirm" != "Yes, do as I say!" ]; then \
		printf "Aborted.\n"; \
		exit 0; \
	fi; \
	$(COMPOSE) down --remove-orphans >/dev/null 2>&1 || true; \
	if [ -e "$$workspace" ]; then \
		rm -rf "$$workspace" >/dev/null 2>&1 || true; \
		printf "Deleted workspace '%s'.\n" "$$workspace"; \
	else \
		printf "Workspace '%s' not present; nothing to delete.\n" "$$workspace"; \
	fi

test:
	docker build -t dsml-kit:validate .
	DSML_TEST_IMAGE=dsml-kit:validate DSML_TEST_IMAGE_NAME=dsml-kit DSML_TEST_TAG=validate python3 -m pytest tests

validate: test env
	@if [ "$(DSML_MODE_VALUE)" = "dev" ]; then \
		$(COMPOSE_DEV) build; \
		docker scout quickview $(IMAGE); \
		docker scout cves $(IMAGE); \
	else \
		printf "DSML_MODE=image validates published image %s.\n" "$(IMAGE)"; \
		docker scout quickview $(IMAGE); \
		docker scout cves $(IMAGE); \
	fi

freeze:
	docker run --rm --entrypoint python $(IMAGE) -m pip freeze

publish: build-dev
	docker image tag $(IMAGE) ghcr.io/mihneateodorstoica/dsml-kit:$(DATE_TAG)
	docker image push ghcr.io/mihneateodorstoica/dsml-kit:$(DATE_TAG)
	docker image push $(IMAGE)

env:
	@[ -f .env ] || { \
		TOKEN=$$(openssl rand -hex 32); \
		cp .env.example .env; \
		sed -i "s|^IMAGE_NAME=.*|IMAGE_NAME=$(IMAGE_NAME)|" .env; \
		sed -i "s|^JUPYTER_TOKEN=.*|JUPYTER_TOKEN=$$TOKEN|" .env; \
		printf "Generated .env\n"; \
	}
