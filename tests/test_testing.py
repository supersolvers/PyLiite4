"""PyLiite4.testing, the pytest plugin: each test runs an inner pytest, since GTK initialises once per process."""

import json
import os
import subprocess
import sys
import textwrap
import time
from importlib import metadata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Loaded through its entry point when PyLiite4 is installed, otherwise named; naming it twice is an error.
PLUGIN = [] if metadata.entry_points(group="pytest11", name="pyliite4") else ["-p", "PyLiite4.testing"]


def run_pytest(tmp_path, files, *arguments, env=None):
    for name, text in files.items():
        (tmp_path / name).write_text(textwrap.dedent(text))
    environment = {**os.environ, **(env or {})}
    environment.pop("PYTEST_ADDOPTS", None)
    # The inner run starts elsewhere, so a relative PYTHONPATH wouldn't find the PyLiite4 this run uses.
    import PyLiite4
    environment["PYTHONPATH"] = os.pathsep.join([str(Path(PyLiite4.__file__).resolve().parent.parent),
                                                 *filter(None, [environment.get("PYTHONPATH")])])
    return subprocess.run([sys.executable, "-m", "pytest", *PLUGIN, "-q", "--no-header", "-p", "no:cacheprovider",
                           "-W", "ignore::DeprecationWarning", "-rA", *arguments],
                          cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=300)


ISOLATION = """
    import json, os
    from PyLiite4 import Gtk


    def test_environment():
        keys = ("DISPLAY", "PYLIITE4_TESTING_DISPLAY", "WAYLAND_DISPLAY", "GDK_BACKEND", "GTK_A11Y", "GDK_DEBUG",
                "GSETTINGS_BACKEND", "DBUS_SESSION_BUS_ADDRESS", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR")
        with open(os.environ["REPORT"], "w") as report:
            json.dump({key: os.environ.get(key) for key in keys}, report)


    def test_accessibility_is_recorded(gtkbot):
        label = Gtk.Label(label="Title", accessible_role=Gtk.AccessibleRole.HEADING)
        label.update_state([Gtk.AccessibleState.HIDDEN], [True])
        assert Gtk.test_accessible_has_role(label, Gtk.AccessibleRole.HEADING)
        assert Gtk.test_accessible_has_state(label, Gtk.AccessibleState.HIDDEN)
"""

# Imports Gtk before any test, which the plugin must still isolate.
CONFTEST = """
    from PyLiite4 import Gtk  # noqa: F401
"""


def test_isolates_the_session(tmp_path):
    report = tmp_path / "report.json"
    result = run_pytest(tmp_path, {"test_isolation.py": ISOLATION, "conftest.py": CONFTEST}, "--gtk",
                        env={"REPORT": str(report), "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
                             "XDG_CONFIG_HOME": "/nonexistent"})
    assert result.returncode == 0, result.stdout + result.stderr
    seen = json.loads(report.read_text())
    assert seen["DISPLAY"] == seen["PYLIITE4_TESTING_DISPLAY"] != os.environ.get("DISPLAY")
    assert seen["WAYLAND_DISPLAY"] is None and seen["GDK_BACKEND"] == "x11"
    assert seen["GTK_A11Y"] == "test" and "no-portals" in seen["GDK_DEBUG"]
    assert seen["GSETTINGS_BACKEND"] == "memory"
    assert seen["DBUS_SESSION_BUS_ADDRESS"] != "unix:path=/nonexistent"
    assert seen["XDG_CONFIG_HOME"].startswith(os.path.realpath(os.environ.get("TMPDIR", "/tmp")))
    # The display and bus end with the run, and the temporary directories go with them, once the watcher sees it
    # has exited.
    def cleaned():
        # Xvfb removes its socket as it ends.
        return not Path(seen["XDG_RUNTIME_DIR"]).exists() and not Path(f"/tmp/.X11-unix/X{seen['DISPLAY'][1:]}").exists()
    for _ in range(50):
        if cleaned():
            break
        time.sleep(0.1)
    assert cleaned()


def test_does_nothing_unless_enabled(tmp_path):
    result = run_pytest(tmp_path, {"test_off.py": """
        import os


        def test_untouched():
            assert "PYLIITE4_TESTING_DISPLAY" not in os.environ


        def test_fixture_says_how(gtkbot):
            pass
    """})
    assert "1 passed" in result.stdout and "1 error" in result.stdout, result.stdout
    assert "pass --gtk, or set gtk = true" in result.stdout


INPUT = """
    import pytest
    from PyLiite4 import Gdk, Gio, Gtk
    from PyLiite4.testing import InteractionError, WaitTimeout


    def area(gtkbot, **properties):
        widget = Gtk.DrawingArea(content_width=200, content_height=100, focusable=True, **properties)
        gtkbot.show(widget)
        return widget


    def test_click_reaches_gestures(gtkbot):
        widget = area(gtkbot)
        presses = []
        gesture = Gtk.GestureClick(button=0)
        gesture.connect("pressed", lambda g, n, x, y: presses.append(
            (n, g.get_current_button(), bool(g.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK),
             round(x), round(y))))
        widget.add_controller(gesture)
        gtkbot.input.click(widget, at=(10, 20))
        gtkbot.input.click(widget, button=3, modifiers="<Control>")
        assert presses == [(1, 1, False, 10, 20), (1, 3, True, 100, 50)]


    def test_double_click(gtkbot):
        widget = area(gtkbot)
        presses = []
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", lambda g, n, x, y: presses.append(n))
        widget.add_controller(gesture)
        gtkbot.input.double_click(widget)
        assert presses == [1, 2]


    def test_drag_and_scroll(gtkbot):
        widget = area(gtkbot)
        ends, scrolls = [], []
        drag = Gtk.GestureDrag()
        drag.connect("drag-end", lambda g, x, y: ends.append((round(x), round(y))))
        widget.add_controller(drag)
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", lambda c, dx, dy: scrolls.append((dx, dy)) or True)
        widget.add_controller(scroll)
        gtkbot.input.drag(widget, start=(20, 20), end=(120, 60))
        assert ends == [(100, 40)]
        gtkbot.input.scroll(widget, dy=2)
        gtkbot.input.scroll(widget, dy=-1, dx=1)
        assert sum(dy for _, dy in scrolls) == 1 and sum(dx for dx, _ in scrolls) == 1


    def test_press_and_release_separately(gtkbot):
        widget = area(gtkbot)
        events = []
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", lambda *a: events.append("pressed"))
        gesture.connect("released", lambda *a: events.append("released"))
        widget.add_controller(gesture)
        gtkbot.input.press(widget)
        assert events == ["pressed"]
        gtkbot.input.release(widget)
        assert events == ["pressed", "released"]


    def test_keys_reach_key_controllers(gtkbot):
        widget = area(gtkbot)
        keys = []
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", lambda c, keyval, code, state: keys.append(
            ("down", Gdk.keyval_name(keyval), bool(state & Gdk.ModifierType.CONTROL_MASK))) and False)
        controller.connect("key-released", lambda c, keyval, code, state: keys.append(("up", Gdk.keyval_name(keyval))))
        widget.add_controller(controller)
        gtkbot.input.key(widget, "<Control>s")
        assert widget.has_focus()
        assert ("down", "s", True) in keys and ("up", "s") in keys
        keys.clear()
        gtkbot.input.key_down(widget, "Escape")
        assert keys == [("down", "Escape", False)]
        gtkbot.input.key_up(widget, "Escape")
        assert keys[-1] == ("up", "Escape")


    def test_typing(gtkbot):
        entry, view = Gtk.Entry(), Gtk.TextView()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(entry)
        box.append(view)
        gtkbot.show(box)
        gtkbot.input.type(entry, "Grüße, Zoë! ✓ 123 ~")
        assert entry.get_text() == "Grüße, Zoë! ✓ 123 ~"
        gtkbot.input.key(entry, "<Control>a")
        gtkbot.input.type(entry, "x")
        assert entry.get_text() == "x"
        gtkbot.input.type(view, "one\\ntwo")
        buffer = view.get_buffer()
        assert buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False) == "one\\ntwo"


    def test_application_accelerator(gtkbot, gtk_app):
        activated = []
        action = Gio.SimpleAction(name="save")
        action.connect("activate", lambda a, p: activated.append(True))
        gtk_app.add_action(action)
        gtk_app.set_accels_for_action("app.save", ["<Control>s"])
        window = Gtk.ApplicationWindow(application=gtk_app, child=Gtk.Entry())
        gtkbot.show(window)
        gtkbot.input.key(window, "<Control>s")
        assert activated == [True]


    def test_popover_contents(gtkbot):
        clicked = []
        inner = Gtk.Button(label="Inside")
        inner.connect("clicked", lambda b: clicked.append(True))
        popover = Gtk.Popover(child=inner)
        menu = Gtk.MenuButton(label="Open", popover=popover)
        gtkbot.show(menu)
        gtkbot.input.click(menu)
        gtkbot.wait_until(lambda: inner.get_mapped())
        gtkbot.input.click(inner)
        assert clicked == [True]


    def test_what_a_user_could_not_do(gtkbot):
        covered = Gtk.Button(label="Covered")
        overlay = Gtk.Overlay(child=covered)
        overlay.add_overlay(Gtk.Label(label="On top"))
        hidden = Gtk.Button(label="Hidden", visible=False)
        insensitive = Gtk.Button(label="Off", sensitive=False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for widget in (overlay, hidden, insensitive):
            box.append(widget)
        gtkbot.show(box)
        with pytest.raises(InteractionError, match="Label.*is there"):
            gtkbot.input.click(covered)
        with pytest.raises(InteractionError, match="hidden"):
            gtkbot.input.click(hidden)
        with pytest.raises(InteractionError, match="insensitive"):
            gtkbot.input.click(insensitive)


    def test_signal_helpers(gtkbot):
        button = Gtk.Button(label="Go")
        gtkbot.show(button)
        with gtkbot.expect_signal(button, "clicked"):
            gtkbot.click(button)
        with pytest.raises(WaitTimeout, match="'clicked'"):
            gtkbot.wait_signal(button, "clicked", timeout=0.2)


    def test_windows_are_closed_between_tests():
        assert [w for w in Gtk.Window.list_toplevels() if w.get_visible()] == []
"""


def test_real_input(tmp_path):
    result = run_pytest(tmp_path, {"test_input.py": INPUT}, "--gtk")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "11 passed" in result.stdout, result.stdout[-3000:]


PROBLEMS = """
    import pytest
    from PyLiite4 import GObject, Gtk


    def test_warning_fails():
        GObject.Object().disconnect(12345)


    def test_callback_exception_fails(gtkbot):
        button = Gtk.Button()
        button.connect("clicked", lambda b: 1 / 0)
        gtkbot.show(button)
        gtkbot.input.click(button)


    def test_expected_warning_taken(gtk_log):
        GObject.Object().disconnect(12345)
        assert gtk_log.take("no handler with id")


    @pytest.mark.gtk_log_ignore("no handler with id")
    def test_ignored_warning():
        GObject.Object().disconnect(12345)
"""


def test_fails_on_glib_warnings_and_callback_exceptions(tmp_path):
    result = run_pytest(tmp_path, {"test_problems.py": PROBLEMS}, "--gtk")
    assert "2 failed, 2 passed" in result.stdout, result.stdout[-6000:]
    assert "FAILED test_problems.py::test_warning_fails" in result.stdout
    assert "FAILED test_problems.py::test_callback_exception_fails" in result.stdout
    assert "ZeroDivisionError" in result.stdout


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="needs a display to inherit, as under xvfb-run")
def test_real_input_refuses_other_displays(tmp_path):
    result = run_pytest(tmp_path, {"test_refuse.py": """
        import pytest
        from PyLiite4 import Gtk
        from PyLiite4.testing import InteractionError


        def test_refused(gtkbot):
            button = Gtk.Button()
            gtkbot.show(button)
            with pytest.raises(InteractionError, match="refusing real input"):
                gtkbot.input.click(button)
    """}, "--gtk", "--gtk-display=inherit")
    assert result.returncode == 0, result.stdout[-4000:]
