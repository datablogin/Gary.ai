.PHONY: verify preview coverage review
verify:
	uv run pytest -q
	git diff --check

preview:
	uv run python -m gary.preview

coverage:
	uv run python -m gary.coverage_probe

review:
	uv run python -m gary.review_preview build
