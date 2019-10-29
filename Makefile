.PHONY: discover
SHELL := /bin/bash

isort:
	isort --recursive

flake8:
	flake8 . --ignore=E501 --count --statistics

run-tap:
	@echo "Running Wonolo tap.."
	@tap-wonolo --config=config/wonolo.config.json --catalog=catalog.json
