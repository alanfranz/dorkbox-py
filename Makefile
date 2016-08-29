.PHONY: test clean distclean bpython freeze upgrade

SHELL := /bin/bash
# override VIRTUALENV or PYTHON as needed. If you override VIRTUALENV
# PYTHON may not be interpreted, depending on what you set.
PYTHON ?= $(shell which python3.5)
VIRTUALENV ?= $(shell which virtualenv) -p $(PYTHON)
FIND := $(shell which gfind || which find)

devenv: setup.py requirements.txt Makefile
	test -r devenv || $(VIRTUALENV) devenv
	touch -t 197001010000 devenv
	source devenv/bin/activate && python devenv/bin/pip install -r requirements.txt && python devenv/bin/pip install --editable . --upgrade
	touch devenv

bpython: devenv devenv/bin/bpython
	source devenv/bin/activate ; python devenv/bin/pip install bpython

freeze: distclean devenv Makefile
	# TODO: we should improve, if the project name includes grep-regexp-active chars, it could match improperly
	source devenv/bin/activate && PROJECT_NAME=$$(devenv/bin/python setup.py --name) && python devenv/bin/pip freeze | grep -v "$${PROJECT_NAME}$$" > requirements.txt

upgrade: devenv Makefile
	source devenv/bin/activate && python devenv/bin/pip install --upgrade --editable .
	@echo "Upgrade performed, you'll probably want to perform a freeze as well once your tests are successful"

test: devenv
	devenv/bin/unit discover -v

clean:
	rm -rf tmp build dist
	$(FIND) \( -name '*.pyc*' -o -name '*.pyo' \) -delete
	$(FIND) -type d -name "__pycache__" -delete
	find packaging -path '*/out/*' -delete
	find packaging -path '*/test-logs/*' -delete

distclean: clean
	rm -rf devenv *.egg-info
