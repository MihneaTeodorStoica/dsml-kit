.PHONY: build run shell clean

build:
	docker build -t dsml-kit .

run: build
	@if [ "$$(docker ps -aq -f name=^dsml$$)" ]; then \
		docker start -ai dsml; \
	else \
		docker run -it --gpus all -p 8888:8888 --name dsml dsml-kit; \
	fi

shell: build
	docker run --rm -it --gpus all dsml-kit /bin/bash

clean:
	-docker rm -f dsml
	-docker rmi dsml-kit