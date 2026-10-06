"""Tests of notes.py, driving the window as a person does: real clicks, typing and shortcuts."""

from collections.abc import Iterator

import pytest
from notes import NotesWindow

from PyLiite4 import Adw, Gtk
from PyLiite4.testing import GtkBot


@pytest.fixture
def gtk_app_class() -> type[Gtk.Application]:
    # gtk_app makes an application of this class for each test.
    return Adw.Application


@pytest.fixture
def window(gtkbot: GtkBot, gtk_app: Adw.Application) -> Iterator[NotesWindow]:
    window = NotesWindow(gtk_app)
    gtkbot.show(window)
    yield window


def test_typing_and_enter_adds_a_note(gtkbot: GtkBot, window: NotesWindow) -> None:
    gtkbot.input.type(window.entry, "Buy milk\n")
    assert window.titles() == ["Buy milk"]
    assert window.entry.get_text() == ""
    assert window.count.get_label() == "1 note"


def test_add_is_off_until_there_is_text(gtkbot: GtkBot, window: NotesWindow) -> None:
    assert not window.add_button.get_sensitive()
    gtkbot.input.type(window.entry, "Call Sam")
    assert window.add_button.get_sensitive()
    gtkbot.input.click(window.add_button)
    assert window.titles() == ["Call Sam"]
    assert not window.add_button.get_sensitive()


def test_removing_a_note(gtkbot: GtkBot, window: NotesWindow) -> None:
    for text in ("One\n", "Two\n", "Three\n"):
        gtkbot.input.type(window.entry, text)
    assert window.count.get_label() == "3 notes"
    second = window.notes.get_row_at_index(1)
    assert second is not None
    gtkbot.input.click(gtkbot.find(second, Gtk.Button))
    assert window.titles() == ["One", "Three"]
    assert window.count.get_label() == "2 notes"


def test_ctrl_n_moves_to_the_entry(gtkbot: GtkBot, window: NotesWindow) -> None:
    window.set_focus(None)
    gtkbot.input.key(window, "<Control>n")
    gtkbot.wait_until(lambda: window.entry.get_focus_child() is not None)


def test_remove_buttons_are_labelled_for_screen_readers(gtkbot: GtkBot, window: NotesWindow) -> None:
    gtkbot.input.type(window.entry, "Water plants\n")
    remove = gtkbot.find(window, Gtk.Button, predicate=lambda button: button.get_tooltip_text() == "Remove")
    assert Gtk.test_accessible_has_property(remove, Gtk.AccessibleProperty.LABEL)
