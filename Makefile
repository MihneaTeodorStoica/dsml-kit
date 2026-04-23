.PHONY: build run clean validate publish

IMAGE := docker.io/mihneateodorstoica/dsml-kit
CONTAINER := dsml
DOCKERFILE ?= Dockerfile
BUILD_CONTEXT ?= .
HOST_PORT ?= 8888
CONTAINER_PORT ?= 8888
DATE_TAG := $(shell date +%F)

COMPOSE = IMAGE=$(IMAGE) \
          CONTAINER=$(CONTAINER) \
          DOCKERFILE=$(DOCKERFILE) \
          BUILD_CONTEXT=$(BUILD_CONTEXT) \
          HOST_PORT=$(HOST_PORT) \
          CONTAINER_PORT=$(CONTAINER_PORT) \
          docker compose

build:
	$(COMPOSE) build --pull

run:
	@$(COMPOSE) up --build -d && clear && $(COMPOSE) logs -f app

clean:
	-$(COMPOSE) down --remove-orphans
	-docker rm -f $(CONTAINER) 2>/dev/null || true
	-docker image rm $(IMAGE):latest 2>/dev/null || true

validate: build
	docker scout quickview $(IMAGE):latest
	docker scout cves $(IMAGE):latest

publish: build
	docker image tag $(IMAGE):latest $(IMAGE):$(DATE_TAG)
	docker image push $(IMAGE):$(DATE_TAG)
	docker image push $(IMAGE):latest
