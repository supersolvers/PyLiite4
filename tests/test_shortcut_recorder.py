"""PyLiite4.Extras.ShortcutRecorder, driven with real key presses in the isolated session of PyLiite4.testing."""

from test_testing import run_pytest

RECORDER = """
    from PyLiite4 import Gio, Gtk
    from PyLiite4.Extras import ShortcutRecorder


    def same(first, second):
        return Gtk.accelerator_parse(first)[1:] == Gtk.accelerator_parse(second)[1:]


    def shown(gtkbot, **properties):
        recorder = ShortcutRecorder(**properties)
        other = Gtk.Button(label="Other")
        box = Gtk.Box(spacing=12)
        box.append(recorder)
        box.append(other)
        gtkbot.show(box)
        return recorder, other


    def test_records_a_combination(gtkbot):
        recorder, _ = shown(gtkbot, accelerator="<Control>s")
        assert recorder.get_child().get_visible_child_name() == "shortcut"
        gtkbot.input.click(recorder)
        assert recorder.recording and recorder.has_focus()
        assert recorder.get_child().get_visible_child_name() == "prompt"
        assert gtkbot.announcements == ["Press a shortcut…"]
        gtkbot.input.key(recorder, "<Control><Shift>k")
        assert not recorder.recording
        assert same(recorder.accelerator, "<Control><Shift>k")
        assert recorder.get_child().get_visible_child().get_accelerator() == recorder.accelerator
        assert Gtk.accelerator_parse(recorder.accelerator)[0]


    def test_keycaps_without_libadwaita(gtkbot):
        # Adw.ShortcutLabel draws keycaps only with libadwaita's style sheet; without it the recorder adds its own.
        recorder, _ = shown(gtkbot, accelerator="<Control>k")
        caps = gtkbot.find_all(recorder, Gtk.Label, predicate=lambda label: label.has_css_class("keycap"))
        assert [cap.get_label() for cap in caps] == ["Ctrl", "K"]
        gtkbot.wait_until(lambda: all(cap.get_width() > 0 for cap in caps))
        for cap in caps:
            # The border box, padding and border included, which get_width() leaves out.
            found, bounds = cap.compute_bounds(cap.get_parent())
            assert found and bounds.get_height() >= 25 and bounds.get_width() >= cap.get_layout().get_pixel_size()[0] + 12


    def test_escape_cancels_and_backspace_clears(gtkbot):
        recorder, _ = shown(gtkbot, accelerator="<Control>s")
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "Escape")
        assert not recorder.recording and recorder.accelerator == "<Control>s"
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "BackSpace")
        assert not recorder.recording and recorder.accelerator == ""


    def test_waits_through_modifiers_alone(gtkbot):
        recorder, _ = shown(gtkbot)
        gtkbot.input.click(recorder)
        gtkbot.input.key_down(recorder, "Control_L")
        gtkbot.input.key_up(recorder, "Control_L")
        assert recorder.recording
        gtkbot.input.key(recorder, "<Alt>F4")
        assert same(recorder.accelerator, "<Alt>F4")


    def test_plain_letters_need_a_modifier(gtkbot):
        recorder, _ = shown(gtkbot)
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "a")
        gtkbot.input.key(recorder, "<Shift>a")
        assert recorder.recording and recorder.accelerator == ""
        # Keys that type nothing are fine alone.
        gtkbot.input.key(recorder, "F5")
        assert same(recorder.accelerator, "F5")
        recorder.require_modifier = False
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "a")
        assert same(recorder.accelerator, "a")


    def test_validate_can_refuse(gtkbot):
        recorder, _ = shown(gtkbot)
        seen = []
        recorder.validate.connect(lambda recorder, accelerator: seen.append(accelerator) or not same(accelerator, "<Control>q"))
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "<Control>q")
        assert recorder.recording and recorder.accelerator == ""
        gtkbot.input.key(recorder, "<Control>w")
        assert same(recorder.accelerator, "<Control>w") and len(seen) == 2


    def test_window_shortcuts_wait_while_recording(gtkbot, gtk_app):
        quits = []
        action = Gio.SimpleAction(name="quit")
        action.connect("activate", lambda action, parameter: quits.append(True))
        gtk_app.add_action(action)
        gtk_app.set_accels_for_action("app.quit", ["<Control>q"])
        recorder = ShortcutRecorder()
        window = Gtk.ApplicationWindow(application=gtk_app, child=recorder)
        gtkbot.show(window)
        gtkbot.input.click(recorder)
        gtkbot.input.key(recorder, "<Control>q")
        assert same(recorder.accelerator, "<Control>q") and quits == []
        gtkbot.input.key(window, "<Control>q")
        assert quits == [True]


    def test_focus_leaving_cancels(gtkbot):
        recorder, other = shown(gtkbot, accelerator="F1")
        gtkbot.input.click(recorder)
        assert recorder.recording
        gtkbot.input.click(other)
        assert not recorder.recording and recorder.accelerator == "F1"


    def test_clicking_again_cancels(gtkbot):
        recorder, _ = shown(gtkbot)
        gtkbot.input.click(recorder)
        gtkbot.input.click(recorder)
        assert not recorder.recording


    def test_from_a_ui_file(gtkbot):
        builder = Gtk.Builder.new_from_string(
            '<interface><object class="PyLiite4ShortcutRecorder" id="recorder">'
            '<property name="accelerator">&lt;Control&gt;o</property>'
            '<property name="placeholder">None</property></object></interface>', -1)
        recorder = builder.get_object("recorder")
        assert isinstance(recorder, ShortcutRecorder) and recorder.accelerator == "<Control>o"
        recorder.clear()
        gtkbot.show(recorder)
        assert recorder.get_child().get_visible_child().get_disabled_text() == "None"
"""


def test_shortcut_recorder(tmp_path):
    result = run_pytest(tmp_path, {"test_inner_recorder.py": RECORDER}, "--gtk")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "10 passed" in result.stdout, result.stdout[-3000:]
