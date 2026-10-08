"""The demo's pages, in sidebar order.

Each module has ``NAME``, ``TITLE``, ``ICON`` and ``SUMMARY``, and ``build(window)``, which returns the page's widget.
"""

from . import async_tasks, fonts, rich_text, shortcuts, signals, source_editor, tips

PAGES = [rich_text, tips, shortcuts, fonts, signals, async_tasks, source_editor]
