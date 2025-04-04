install:
	uv sync
dev:
	uv run flask --debug --app page_analyzer:app run
start:
	PORT ?= 8000
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app
build:
	./build.sh
render-start:
	source .venv/bin/activate && gunicorn -w 5 -b 0.0.0.0:10000 page_analyzer:app
lint:
	flake8 .