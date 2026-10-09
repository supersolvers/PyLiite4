"""Run one example as its own program, check its window, then quit it.

Usage: python tests/run_example.py examples/NAME/main.py

The example runs unchanged, as `python examples/NAME/main.py` would run it. Shortly after its window appears, a check
for that example drives it through GTK, then the application quits. Any Python exception or GLib critical fails the
run. Run by tests/test_examples.py, one process per example.
"""

import os
import runpy
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from PyLiite4 import Adw, Gio, GLib, Gtk
from PyLiite4.testing import WaitTimeout, wait_until

problems: list[str] = []


def record_exception(kind, value, trace):
    problems.append("".join(traceback.format_exception(kind, value, trace)))


def record_log(level, fields, *_rest):
    if level & (GLib.LogLevelFlags.LEVEL_CRITICAL | GLib.LogLevelFlags.LEVEL_ERROR):
        problems.append("a GLib critical or error, logged above")
    return GLib.log_writer_default(level, fields)


def spin(condition: Callable[[], object], seconds: float = 5) -> bool:
    # PyLiite4.testing's wait iterates as GTK's loop does, so an example's asyncio tasks go on meanwhile; Python's
    # MainContext.iteration would pause them.
    try:
        wait_until(condition, seconds)
    except WaitTimeout:
        pass
    return bool(condition())


def widgets(root: Gtk.Widget):
    yield root
    child = root.get_first_child()
    while child is not None:
        yield from widgets(child)
        child = child.get_next_sibling()


def find(root: Gtk.Widget, kind: type, label: str | None = None):
    for widget in widgets(root):
        if isinstance(widget, kind) and (label is None or getattr(widget, "get_label")() == label):
            return widget
    raise AssertionError(f"no {kind.__name__} {label or ''} in {root!r}")


def labels(root: Gtk.Widget) -> list[str]:
    return [widget.get_label() for widget in widgets(root) if isinstance(widget, Gtk.Label) and widget.get_mapped()]


def check_app(app: Gtk.Application, window: Gtk.Window) -> None:
    assert isinstance(window, Adw.ApplicationWindow)
    assert app.get_accels_for_action("app.quit") == ["<Control>q"]
    find(window, Gtk.MenuButton).activate()
    window.activate_action("win.greet", None)
    app.activate_action("about", None)
    assert spin(lambda: isinstance(window.get_visible_dialog(), Adw.AboutDialog)), "no about dialog"
    window.get_visible_dialog().force_close()
    app.activate_action("new-window", None)
    assert spin(lambda: len(app.get_windows()) == 2), "no second window"
    expected = os.environ.get("EXAMPLE_EXPECT_SIZE")
    if expected:
        # The test stores a size in GSettings first: a window that read it opens at that size.
        width, height = window.get_default_size()
        assert f"{width}x{height}" == expected, (width, height)


def check_template(app: Gtk.Application, window: Gtk.Window) -> None:
    value = find(window, Gtk.Label, "0")
    find(window, Gtk.Button, "+").emit("clicked")
    find(window, Gtk.Button, "+").emit("clicked")
    find(window, Gtk.Button, "−").emit("clicked")
    assert value.get_label() == "1", value.get_label()
    find(window, Gtk.Button, "Reset").emit("clicked")
    assert value.get_label() == "0", value.get_label()


def check_resources(app: Gtk.Application, window: Gtk.Window) -> None:
    theme = Gtk.IconTheme.get_for_display(window.get_display())
    assert theme.has_icon("example-heart-symbolic"), theme.get_resource_path()
    image = find(window, Gtk.Image)
    assert image.get_icon_name() == "example-heart-symbolic"
    # style.css gives the "heart" class a colour; the default would be the window's foreground.
    colour = image.get_color()
    assert (round(colour.red, 2), round(colour.green, 2), round(colour.blue, 2)) == (0.88, 0.11, 0.14), colour
    button = find(window, Gtk.Button, "Like")
    button.emit("clicked")
    assert find(window, Gtk.Label, "Liked 1 time")


def check_translations(app: Gtk.Application, window: Gtk.Window) -> None:
    expected = os.environ.get("EXAMPLE_EXPECT_TEXT")
    shown = [window.get_title(), *labels(window)]
    find(window, Gtk.Button).emit("clicked")
    shown += labels(window)
    print("shown:", shown)
    if expected:
        for text in expected.split("|"):
            assert any(text in line for line in shown), (text, shown)


def check_listview(app: Gtk.Application, window: Gtk.Window) -> None:
    view = find(window, Gtk.ColumnView)
    model = view.get_model()
    names = lambda: [model.get_item(i).name for i in range(model.get_n_items())]  # noqa: E731
    total = model.get_n_items()
    assert total > 5, total
    columns = view.get_columns()
    view.sort_by_column(columns.get_item(2), Gtk.SortType.DESCENDING)
    populations = [model.get_item(i).population for i in range(total)]
    assert populations == sorted(populations, reverse=True), populations
    view.sort_by_column(columns.get_item(0), Gtk.SortType.ASCENDING)
    assert names() == sorted(names(), key=str.casefold), names()
    find(window, Gtk.SearchEntry).set_text("an")
    assert spin(lambda: 0 < model.get_n_items() < total), model.get_n_items()
    assert all("an" in name.lower() for name in names()), names()
    find(window, Gtk.Switch).set_active(True)
    assert spin(lambda: all(model.get_item(i).population >= 5_000_000 for i in range(model.get_n_items())))
    assert spin(lambda: any(widget.get_label() == f"{model.get_n_items()} of {total} cities"
                            for widget in widgets(window) if isinstance(widget, Gtk.Label)))


def check_chat(app: Gtk.Application, window: Gtk.Window) -> None:
    view, entry = window.view, window.entry
    entry.set_text("What can you show?")
    window.send_button.emit("clicked")
    assert spin(lambda: window.task is None and "selection stays" in view.plain_text(), 20), view.plain_text()
    text = view.plain_text()
    assert "You: What can you show?" in text and "You asked\tLength\nWhat can you show?\t18 characters" in text, text
    # A second question, stopped as it streams.
    entry.set_text("Stop me")
    window.send_button.emit("clicked")
    assert spin(lambda: "RichView" in view.plain_text().rpartition("Stop me")[2])
    window.stop_button.emit("clicked")
    assert spin(lambda: window.task is None), "the reply didn't stop"
    assert view.plain_text().endswith("(stopped)"), view.plain_text()[-200:]


def check_preferences(app: Gtk.Application, window: Gtk.Window) -> None:
    app.activate_action("preferences", None)
    assert spin(lambda: window.get_visible_dialog() is not None), "no preferences dialog"
    dialog = window.get_visible_dialog()
    search = dialog.recorders["app.search"]
    assert search.accelerator == "<Control>f"
    search.accelerator = "<Control>k"
    assert app.get_accels_for_action("app.search") == ["<Control>k"]
    # Another action's shortcut is refused.
    assert not search.emit("validate", "<Control>q")
    assert search.emit("validate", "<Control>j")
    dialog.reset()
    assert app.get_accels_for_action("app.search") == ["<Control>f"]
    dialog.force_close()


CHECKS = {"app": check_app, "template": check_template, "resources": check_resources,
          "translations": check_translations, "listview": check_listview, "chat": check_chat,
          "preferences": check_preferences}


def main() -> int:
    path = Path(sys.argv[1]).resolve()
    check = CHECKS[path.parent.name]
    sys.excepthook = record_exception
    GLib.log_set_writer_func(record_log, None)
    state = {"checked": False}
    deadline = GLib.get_monotonic_time() + 20_000_000

    def run_check() -> bool:
        app = Gio.Application.get_default()
        if not isinstance(app, Gtk.Application) or not app.get_windows():
            if GLib.get_monotonic_time() < deadline:
                return GLib.SOURCE_CONTINUE
            if isinstance(app, Gio.Application):
                app.quit()
            return GLib.SOURCE_REMOVE
        window = app.get_windows()[0]
        try:
            assert spin(window.get_mapped), "the window wasn't shown"
            check(app, window)
            state["checked"] = True
        except BaseException:
            record_exception(*sys.exc_info())
        app.quit()
        return GLib.SOURCE_REMOVE

    # Polls until the example's application has a window: the example itself needs no changes.
    GLib.timeout_add(200, run_check)
    sys.argv = [str(path)]
    sys.path.insert(0, str(path.parent))
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exit:
        if exit.code:
            problems.append(f"the example exited with {exit.code}")
    if not state["checked"] and not problems:
        problems.append("the example's application never showed a window")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
