#!/bin/sh
# Extract the translatable strings into the .pot template, merge them into each po/LANG.po, and compile those to
# locale/LANG/LC_MESSAGES. Needs GNU gettext: xgettext, msgmerge and msgfmt.
#
# To start a new language, run this once, then: msginit -i po/pyliite4-translations.pot -l fr -o po/fr.po
set -eu
cd "$(dirname "$0")"
domain=pyliite4-translations

# xgettext knows _(), gettext() and ngettext() in Python, and translatable="yes" in GtkBuilder .ui files.
xgettext --from-code=UTF-8 --add-comments=Translators --package-name=$domain --msgid-bugs-address= \
    --output=po/$domain.pot main.py window.ui

for po in po/*.po; do
    [ -e "$po" ] || continue
    language=$(basename "$po" .po)
    msgmerge --quiet --update --backup=none "$po" po/$domain.pot
    mkdir -p "locale/$language/LC_MESSAGES"
    msgfmt --check --output-file="locale/$language/LC_MESSAGES/$domain.mo" "$po"
done
