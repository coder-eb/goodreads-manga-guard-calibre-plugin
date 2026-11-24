.PHONY: zip test
PLUGIN_DIR = goodreads_manga_guard
VERSION = 0.1.0
ZIP = goodreads_manga_guard-v$(VERSION).zip

zip:
	rm -f $(ZIP)
	cd $(PLUGIN_DIR) && zip -qr ../$(ZIP) . -x '*.pyc' '__pycache__/*' '.DS_Store'
	@echo "Created $(ZIP)"

test:
	python -m pytest -q tests
