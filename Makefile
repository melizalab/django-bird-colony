run:
	make configure
	.venv/bin/python3 manage.py migrate
	.venv/bin/python3 manage.py runserver && rm -r .venv

configure:
	[ -f ".env" ] || cp .env.example .env
	[ -f ".venv/" ] || python3 -m venv .venv
	uv sync
	.venv/bin/python3 manage.py collectstatic --no-input

load-fixture-sandbox:
	[ -f ".venv/" ] || python3 -m venv .venv
	uv sync
	.venv/bin/python3 manage.py loaddata birds/fixtures/bird_colony_sandbox.json

load-fixture-starter-kit:
	[ -f ".venv/" ] || python3 -m venv .venv
	uv sync
	.venv/bin/python3 manage.py loaddata birds/fixtures/bird_colony_starter_kit.json
