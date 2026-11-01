"""Click through demos whose .ui files connect signals with object=, with real input through PyLiite4.testing."""

from pathlib import Path

from test_testing import run_pytest

ROOT = Path(__file__).resolve().parent.parent

DEMOS = f"""
    import sys

    sys.path.insert(0, {str(ROOT)!r})

    from PyLiite4 import Gtk
    from demos import gtk_demo


    import gc

    import pytest


    @pytest.fixture
    def open_demo(gtkbot):
        opened = []

        def open_demo(module):
            gtk_demo.register_resources()
            parent = gtkbot.show(Gtk.Window())
            opened.append(module)
            return gtkbot.show(module.do(parent))

        yield open_demo
        # The demos keep their window in a global, as GTK Demo does in C. Left there, it would be freed while Python
        # shuts down, after the Python list model under minesweeper's grid, and GTK aborts on the half-gone model.
        gtkbot.close()
        for module in opened:
            if hasattr(module, "window"):
                module.window = None
        gc.collect()
        gtkbot.iterate()


    def test_fishbowl_previous_and_next(gtkbot, open_demo):
        from demos.gtk_demo.demos import fishbowl

        window = open_demo(fishbowl)
        # The two arrow buttons, which come first; their handlers get the button and the bowl.
        previous, following = gtkbot.find_all(window, Gtk.Button,
                                              predicate=lambda button: isinstance(button.get_child(), Gtk.Image))[:2]
        # Next, then back: previous from the first type wraps to the last, which needs GtkSource.
        first = fishbowl.selected_widget_type
        gtkbot.input.click(following)
        assert fishbowl.selected_widget_type == first + 1
        gtkbot.input.click(previous)
        assert fishbowl.selected_widget_type == first


    def test_minesweeper_new_game_and_reveal(gtkbot, open_demo, monkeypatch):
        from demos.gtk_demo.demos import listview_minesweeper

        # A revealed mine plays a sound: kept off the desktop's audio, and off GTK's critical where no sound theme
        # is installed.
        celebrated = []
        monkeypatch.setattr(listview_minesweeper, "celebrate", celebrated.append)
        window = open_demo(listview_minesweeper)
        view = gtkbot.find(window, Gtk.GridView)
        game = view.get_model().get_model()
        # The new game button's handler gets the button and the game.
        gtkbot.input.click(gtkbot.find(window, Gtk.Button, label="New Game"))
        assert game.props.playing
        assert game.get_item(0).props.label == "?"
        # A single click activates a cell, whose handler gets the view, the position and the game.
        cell = gtkbot.wait_until(lambda: next(iter(gtkbot.find_all(view, Gtk.Label,
                                                                    predicate=lambda label: label.get_width() > 0)), None))
        gtkbot.input.click(cell)
        assert game.get_item(0).props.label != "?"
        assert celebrated == ([False] if game.get_item(0).is_mine else [])
"""


def test_demo_handlers_with_real_clicks(tmp_path):
    result = run_pytest(tmp_path, {"test_demo_clicks.py": DEMOS}, "--gtk")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "2 passed" in result.stdout
