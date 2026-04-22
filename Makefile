.PHONY: build run shell clean validate

build:
	docker build -t dsml-kit .

run: build
	@if [ "$$(docker ps -aq -f name=^dsml$$)" ]; then \
		docker start -ai dsml; \
	else \
		docker run -it --gpus all -p 8888:8888 --name dsml dsml-kit; \
	fi

shell: build
	@if [ "$$(docker ps -aq -f name=^dsml$$)" ]; then \
		docker start -ai dsml; \
	else \
		docker run -it --gpus all -p 8888:8888 --name dsml dsml-kit /bin/bash; \
	fi

clean:
	-docker rm -f dsml 2>/dev/null || true
	-docker rmi dsml-kit 2>/dev/null || true

validate: build
	docker scout quickview dsml-kit
	docker scout cves dsml-kit