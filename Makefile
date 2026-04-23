.PHONY: build run clean validate publish

IMAGE ?= docker.io/mihneateodorstoica/dsml-kit
TAG ?= latest
DATE_TAG := $(shell date +%F)

build:
	docker compose build --pull

run:
	@docker compose up --build -d && clear && docker compose logs -f app

clean:
	-docker compose down --remove-orphans
	-docker image rm $(IMAGE):$(TAG) 2>/dev/null || true

validate: build
	docker scout quickview $(IMAGE):$(TAG)
	docker scout cves $(IMAGE):$(TAG)

publish: build
	docker image tag $(IMAGE):latest $(IMAGE):$(DATE_TAG)
	docker image push $(IMAGE):$(DATE_TAG)
	docker image push $(IMAGE):$(TAG)
