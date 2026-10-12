.PHONY: verify preview coverage review review-cycle3 preview-cycle3 training-prepare training-diagnostics
verify:
	uv run pytest -q
	git diff --check

preview:
	uv run python -m gary.preview

coverage:
	uv run python -m gary.coverage_probe

review:
	uv run python -m gary.review_preview build

review-cycle3:
	uv run python -m gary.review_preview cycle3

preview-cycle3:
	uv run python -m gary.preview --cycle-3

training-prepare:
	uv run python -m gary.training_preview prepare

training-diagnostics:
	uv run python -m gary.training_preview diagnostics
