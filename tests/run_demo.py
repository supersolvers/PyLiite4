"""Open one demo, let it run for a moment, and fail on any Python exception or GLib critical.

Usage: python tests/run_demo.py gtk_demo NAME | workbench NAME | adwaita_demo [PAGE] | pyliite4_demo [PAGE]

Run by tests/test_demos.py, one process per demo, so a crash or leftover state stays with its demo.
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyLiite4 import Adw, Gio, GLib, Gtk  # noqa: E402

SECONDS = 1.5
problems: list[str] = []


def record_exception(kind, value, trace):
    problems.append("".join(traceback.format_exception(kind, value, trace)))


def record_log(level, fields, *_rest):
    if level & (GLib.LogLevelFlags.LEVEL_CRITICAL | GLib.LogLevelFlags.LEVEL_ERROR):
        problems.append("a GLib critical or error, logged above")
    return GLib.log_writer_default(level, fields)


def open_demo(app: Gtk.Application, suite: str, name: str | None) -> Gtk.Window | None:
    if suite == "gtk_demo":
        from demos import gtk_demo
        gtk_demo.register_resources()
        demo = next(demo for demo in gtk_demo.all_demos() if demo.name == name)
        parent = Gtk.ApplicationWindow(application=app, title="GTK Demo")
        parent.present()
        widget = demo.run(parent)
        return widget if isinstance(widget, Gtk.Window) else None
    if suite == "workbench":
        from demos import workbench
        return workbench.run(next(demo for demo in workbench.demos() if demo.name == name), app)
    if suite == "adwaita_demo":
        from demos import adwaita_demo
        window = adwaita_demo.open_window(app)
        for page in [name] if name else adwaita_demo.page_names(window):
            adwaita_demo.show_page(window, page)
        return window
    if suite == "pyliite4_demo":
        from demos import pyliite4_demo
        window = pyliite4_demo.open_window(app)
        for page in [name] if name else pyliite4_demo.page_names(window):
            pyliite4_demo.show_page(window, page)
        return window
    raise SystemExit(f"unknown suite {suite}")


def main() -> int:
    suite, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    sys.excepthook = record_exception
    GLib.log_set_writer_func(record_log, None)
    # An Adw.Application, so libadwaita's style sheet is loaded as in the demos' own launchers.
    app = Adw.Application(application_id="org.example.PyLiite4Demos", flags=Gio.ApplicationFlags.NON_UNIQUE)
    shown = {}

    def activated(app):
        app.hold()
        try:
            shown["window"] = open_demo(app, suite, name)
        except BaseException:
            record_exception(*sys.exc_info())
            app.release()
            app.quit()
            return
        GLib.timeout_add(int(SECONDS * 1000), lambda: (shown.update(visible=bool(
            shown["window"] is None or shown["window"].get_visible())), app.release(), app.quit()) and False)

    app.activate.connect(activated)
    app.run([])
    if not problems and shown.get("visible") is False:
        problems.append("the demo's window wasn't visible")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
