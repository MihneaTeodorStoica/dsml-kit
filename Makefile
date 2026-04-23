.PHONY: build run logs shell stop clean validate publish token

IMAGE := ghcr.io/mihneateodorstoica/dsml-kit:latest
DATE_TAG := $(shell date +%F)

build:
	docker compose build

run: token
	JUPYTER_TOKEN=$$(cat token.txt) docker compose up --build

logs:
	docker compose logs -f app

shell:
	docker compose exec app bash

stop:
	-docker compose stop

clean:
	-docker compose down --remove-orphans
	-rm -f token.txt

validate: build
	docker scout quickview $(IMAGE)
	docker scout cves $(IMAGE)

publish: build
	docker image tag $(IMAGE) ghcr.io/mihneateodorstoica/dsml-kit:$(DATE_TAG)
	docker image push ghcr.io/mihneateodorstoica/dsml-kit:$(DATE_TAG)
	docker image push $(IMAGE)

token:
	@[ -f token.txt ] || (openssl rand -hex 32 > token.txt && echo "Generated token.txt")