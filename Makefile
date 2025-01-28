install:
	@if [ ! -d ".venv" ]; then \
        python3.9 -m venv .venv; \
        . .venv/bin/activate; \
    fi
	@.venv/bin/python3.9 -m pip install -e . --no-cache-dir
	@oc --install-completion


build:
	@.venv/bin/python3.9 .docker/dockerfile.py --python=$(if $(python),$(python),3.9) --runtime=$(if $(runtime),$(runtime),cuda)

build-min:
	@.venv/bin/python3.9 .docker/dockerfile.py --python=$(if $(python),$(python),3.9) --runtime=$(if $(runtime),$(runtime),cuda) --min

build-all:
	@for python in 3.7 3.8 3.9 3.10 3.11 3.12 3.13; do \
        for runtime in cuda cpu; do \
            .venv/bin/python3.9 .docker/dockerfile.py --python=$$python --runtime=$$runtime; \
            .venv/bin/python3.9 .docker/dockerfile.py --python=$$python --runtime=$$runtime --min; \
        done \
    done

