.PHONY: test clean distclean bpython freeze upgrade

SHELL := /bin/bash
# override VIRTUALENV or PYTHON as needed. If you override VIRTUALENV
# PYTHON may not be interpreted, depending on what you set.
# WARNING: you MUST ALWAYS set the proper PYTHON even though
# you may override VIRTUALENV - it will let the script detect
# changes in the python interpreter and recreate the devenv on such change.
# you'll thank me later.
PYTHON ?= $(shell which python3)
VIRTUALENV ?= $(shell which virtualenv) -p $(PYTHON)
FIND := $(shell which gfind || which find)

devenv: setup.py requirements.txt Makefile devenv/bin/python
	touch -t 197001010000 devenv
	source devenv/bin/activate && python devenv/bin/pip install -r requirements.txt && python devenv/bin/pip install --editable . --upgrade
	touch devenv

devenv/bin/python: $(PYTHON)
	rm -rf devenv
	$(VIRTUALENV) devenv

bpython: devenv
	source devenv/bin/activate && python devenv/bin/pip install bpython

freeze: distclean devenv
	# TODO: we should improve, if the project name includes grep-regexp-active chars, it could match improperly
	source devenv/bin/activate && PROJECT_NAME=$$(devenv/bin/python setup.py --name) && python devenv/bin/pip freeze | grep -v "$${PROJECT_NAME}$$" > requirements.txt

upgrade: devenv
	source devenv/bin/activate && python devenv/bin/pip install --upgrade --editable .
	@echo "Upgrade performed, you'll probably want to perform a freeze as well once your tests are successful"

test: devenv
	devenv/bin/unit discover -v

clean:
	rm -rf tmp build dist
	$(FIND) \( -name '*.pyc*' -o -name '*.pyo' \) -delete
	$(FIND) -type d -name "__pycache__" -delete
	$(FIND) packaging -path '*/out/*' -delete
	$(FIND) packaging -path '*/test-logs/*' -delete

distclean: clean
	rm -rf devenv *.egg-info
