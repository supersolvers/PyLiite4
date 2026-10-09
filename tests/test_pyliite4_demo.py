"""The PyLiite4 Demo, page by page, with real input through PyLiite4.testing: a showcase of the plugin too."""

from pathlib import Path

from test_testing import run_pytest

ROOT = Path(__file__).resolve().parent.parent

DEMO = f"""
    import sys

    import pytest

    sys.path.insert(0, {str(ROOT)!r})
    sys.path.insert(0, {str(ROOT / "tests")!r})

    from PyLiite4 import Adw, Gtk
    from PyLiite4.Extras import RichView, ShortcutRecorder, Tip
    from demos import pyliite4_demo
    from demos.pyliite4_demo.pages import async_tasks, fonts, rich_text, shortcuts, signals, source_editor, tips
    from tiny_font import tiny_font


    @pytest.fixture
    def gtk_app_class():
        return Adw.Application


    @pytest.fixture
    def demo(gtkbot, gtk_app):
        window = pyliite4_demo.open_window(gtk_app)
        gtkbot.add(window)
        gtkbot.wait_until(window.get_mapped)
        toasts = []
        # The pages call window.toast(); keep what they say.
        window.toast = toasts.append
        window.toasts_shown = toasts
        return window


    def page(gtkbot, window, module):
        pyliite4_demo.show_page(window, module.NAME)
        found = gtkbot.find(window, module.Page)
        # Until the crossfade ends, input doesn't reach the new page.
        gtkbot.wait_until(lambda: found.get_mapped() and found.get_width() > 0
                          and not window.stack.get_transition_running())
        return found


    def shown_tip(gtkbot):
        from PyLiite4 import Extras

        # show_tip() keeps one tip for the application.
        return gtkbot.wait_until(lambda: Extras._shared_tip if Extras._shared_tip is not None
                                 and Extras._shared_tip.get_mapped() else None)


    def test_every_page_opens(gtkbot, demo):
        names = pyliite4_demo.page_names(demo)
        assert names == ["rich-text", "tips", "shortcuts", "fonts", "signals", "async", "source"]
        for name in names:
            pyliite4_demo.show_page(demo, name)
            assert demo.stack.get_visible_child_name() == name
            gtkbot.wait(0.05)


    def test_the_sidebar_switches_pages(gtkbot, demo):
        row = next(row for row in gtkbot.find_all(demo.sidebar, Gtk.ListBoxRow) if row.get_name() == "signals")
        gtkbot.wait_until(lambda: row.get_width() > 0)
        gtkbot.input.click(row)
        assert demo.stack.get_visible_child_name() == "signals"
        assert demo.content_page.get_title() == signals.TITLE


    def test_formatted_text_streams_and_links_work(gtkbot, demo):
        text = page(gtkbot, demo, rich_text)
        view = text.view
        gtkbot.input.click(text.stream_button)
        assert not text.stream_button.get_sensitive()
        gtkbot.wait_until(lambda: text.stream_button.get_sensitive(), timeout=15)
        assert view.plain_text().startswith("Rich text from markup") and "Copying gives tables" in view.plain_text()
        opened = []
        # Kept from opening a browser: a handler returning True stops the default.
        view.activate_link.connect(lambda view, uri: opened.append(uri) or True)
        buffer = view.get_buffer()
        whole = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        rect = view.get_iter_location(buffer.get_iter_at_offset(whole.index("documentation") + 2))
        at = view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x + 2, rect.y + rect.height // 2)
        gtkbot.input.move(view, at=at)
        assert text.hovered.get_label() == "https://docs.gtk.org/gtk4/"
        gtkbot.input.click(view, at=at)
        assert opened == ["https://docs.gtk.org/gtk4/"]
        assert demo.toasts_shown == ["Opening https://docs.gtk.org/gtk4/"]


    def test_tips(gtkbot, demo):
        tip_page = page(gtkbot, demo, tips)
        gtkbot.input.click(tip_page.switch)
        tip = shown_tip(gtkbot)
        assert tip.text == "Switched on" and tip.get_parent() is tip_page.switch
        gtkbot.input.click(tip_page.area, at=(40, 30))
        tip = shown_tip(gtkbot)
        assert tip.text == "Clicked at 40, 30" and tip.get_parent() is tip_page.area
        gtkbot.input.click(tip_page.copy_button)
        tip = shown_tip(gtkbot)
        assert tip.use_markup and tip.plain_text() == "Copied demo-token-•••• to the clipboard"
        assert "Switched on" in gtkbot.announcements


    def test_recording_a_shortcut_and_using_it(gtkbot, demo, gtk_app):
        keys = page(gtkbot, demo, shortcuts)
        greet = keys.recorders["win.demo-greet"]
        assert gtk_app.get_accels_for_action("win.demo-greet") == ["<Control>g"]
        gtkbot.input.click(greet)
        gtkbot.input.key(greet, "<Control>e")
        assert greet.accelerator == "<Control>e"
        assert gtk_app.get_accels_for_action("win.demo-greet") == ["<Control>e"]
        gtkbot.input.key(demo, "<Control>e")
        assert demo.toasts_shown == ["Hello from a shortcut"]


    def test_a_shortcut_already_in_use_is_refused(gtkbot, demo):
        keys = page(gtkbot, demo, shortcuts)
        greet = keys.recorders["win.demo-greet"]
        gtkbot.input.click(greet)
        gtkbot.input.key(greet, "<Control>Page_Down")
        assert greet.recording and greet.accelerator == "<Control>g"
        assert shown_tip(gtkbot).text == "Already used for “Next page”"
        gtkbot.input.key(greet, "Escape")
        # The next-page shortcut itself moves to the next page.
        gtkbot.input.key(demo, "<Control>Page_Down")
        assert demo.stack.get_visible_child_name() == "fonts"


    def test_fonts(gtkbot, demo):
        font_page = page(gtkbot, demo, fonts)
        assert font_page.load(tiny_font("Demo Tiny Font")) == ["Demo Tiny Font"]
        row = font_page.rows["Demo Tiny Font"]
        assert 'font_family="Demo Tiny Font"' in row.get_subtitle()
        assert demo.toasts_shown == ["Registered Demo Tiny Font"]
        assert font_page.load(b"not a font") == []


    def test_signals_and_properties(gtkbot, demo):
        model = page(gtkbot, demo, signals)
        hot = next(button for button in gtkbot.find_all(model, Gtk.Button) if button.get_label() == "Set 35 °C")
        gtkbot.input.click(hot)
        assert model.thermostat.temperature == 35.0 and model.scale.get_value() == 35.0
        assert model.banner.get_revealed() and model.events == ["overheated(35.0)"]
        # Once the banner has finished sliding in.
        revealer = gtkbot.find(model.banner, Gtk.Revealer)
        gtkbot.wait_until(revealer.get_child_revealed)
        gtkbot.input.click(gtkbot.find(model.banner, Gtk.Button))
        assert model.thermostat.temperature == 20.0 and not model.banner.get_revealed()
        # Muted: the change goes through, the handler is blocked for it.
        gtkbot.input.click(model.mute)
        # The switch takes a moment to change state after the click.
        gtkbot.wait_until(model.mute.get_active)
        gtkbot.input.click(hot)
        assert model.thermostat.temperature == 35.0 and model.events == ["overheated(35.0)"]


    def test_async_requests_cancelling_and_threads(gtkbot, demo):
        tasks = page(gtkbot, demo, async_tasks)
        gtkbot.input.click(tasks.fetch_button)
        gtkbot.wait_until(lambda: tasks.status.get_label().startswith("200 from /now"))
        gtkbot.input.click(tasks.slow_button)
        assert tasks.cancel_button.get_sensitive()
        gtkbot.input.click(tasks.cancel_button)
        gtkbot.wait_until(lambda: tasks.status.get_label() == "Cancelled")
        gtkbot.input.click(tasks.thread_button)
        gtkbot.wait_until(lambda: "primes below five million" in tasks.status.get_label(), timeout=20)
        assert tasks.status.get_label().startswith("348,513 primes")


    def test_source_editor(gtkbot, demo):
        pyliite4_demo.show_page(demo, source_editor.NAME)
        try:
            from PyLiite4 import GtkSource
        except (ImportError, ValueError):
            assert gtkbot.find(demo, Adw.StatusPage, predicate=lambda status: "GtkSourceView" in status.get_title())
            return
        editor = gtkbot.find(demo, source_editor.Page)
        assert editor.buffer.get_language().get_id() == "python"
        assert "class Page" in editor.buffer.get_text(editor.buffer.get_start_iter(), editor.buffer.get_end_iter(), True)
        gtkbot.input.type(editor.view, "# typed\\n")
        assert editor.position.get_label() == "Line 2, column 1"
"""


def test_pyliite4_demo(tmp_path):
    result = run_pytest(tmp_path, {"test_inner_demo.py": DEMO}, "--gtk")
    assert result.returncode == 0, result.stdout[-8000:] + result.stderr[-2000:]
    assert "10 passed" in result.stdout, result.stdout[-3000:]
