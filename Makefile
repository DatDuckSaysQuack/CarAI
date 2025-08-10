.PHONY: up down logs shell llm-serve test

up:
	@echo "Starting services (placeholder)"

down:
	@echo "Stopping services (placeholder)"

logs:
	@echo "Tailing logs (placeholder)"

shell:
	@if [ -z "$(SERVICE)" ]; then echo "Usage: make shell SERVICE=name"; exit 1; fi; \
	echo "Entering shell for $(SERVICE) (placeholder)"

llm-serve:
	python apps/orchestrator/main.py

test:
	pytest
