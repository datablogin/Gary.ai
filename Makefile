.PHONY: verify preview coverage
verify:
	uv run pytest -q
	git diff --check

preview:
	uv run python -m gary.preview

coverage:
	uv run python -m gary.coverage_probe
