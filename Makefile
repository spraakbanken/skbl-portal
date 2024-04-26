.PHONY: run-dev
venv:
	test -d venv || python3 -m venv venv
	venv/bin/pip install pip-tools

install: venv venv/req.installed
venv/req.installed: skbl/requirements.txt
	venv/bin/pip install -r $<
	@touch $@

run-dev: install
	venv/bin/python run.py

.PHONY: update-translation-template
update-translation-template: skbl/translations/messages.pot

.PHONY: skbl/translations/messages.pot
skbl/translations/messages.pot:
	venv/bin/pybabel extract -F babel.cfg  --output=$@ --project="SKBL-portal" .

.PHONY: update-swedish-translation
update-swedish-translation: skbl/translations/sv/LC_MESSAGES/messages.po

skbl/translations/sv/LC_MESSAGES/messages.po: skbl/translations/messages.pot
	venv/bin/pybabel update --output-file=$@ --input-file=$< --locale=sv

.PHONY: compile-swedish-translations
compile-swedish-translations: skbl/translations/sv/LC_MESSAGES/messages.mo

skbl/translations/sv/LC_MESSAGES/messages.mo: skbl/translations/sv/LC_MESSAGES/messages.po
	venv/bin/pybabel compile --output-file=$@ --input-file=$< --locale=sv

.PHONY: generate-lockfile
generate-lockfile: skbl/requirements.txt

skbl/requirements.txt: pyproject.toml
	pdm export -o $@ --without-hashes