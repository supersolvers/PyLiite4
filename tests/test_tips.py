"""PyLiite4.Extras.Tip and show_tip, driven with real input in the isolated session of PyLiite4.testing."""

from test_testing import run_pytest

TIPS = """
    import pytest

    from PyLiite4 import Gtk
    from PyLiite4.Extras import Tip, hide_tip, show_tip


    def two_buttons(gtkbot):
        first, second = Gtk.Button(label="First"), Gtk.Button(label="Second")
        box = Gtk.Box(spacing=40)
        box.append(first)
        box.append(second)
        gtkbot.show(box)
        return first, second


    @pytest.fixture(autouse=True)
    def no_tip_left():
        yield
        hide_tip()


    def test_shows_like_a_tooltip(gtkbot):
        first, _ = two_buttons(gtkbot)
        tip = show_tip(first, "Switched on", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        assert isinstance(tip, Tip) and tip.get_parent() is first
        assert tip.has_css_class("pyliite4-tip") and not tip.get_has_arrow() and not tip.get_autohide()
        assert tip.get_child().get_label() == "Switched on"
        assert Gtk.test_accessible_has_role(tip, Gtk.AccessibleRole.TOOLTIP)
        assert gtkbot.announcements == ["Switched on"]


    def test_dark_like_a_tooltip_over_gtk_theme(gtkbot):
        # GTK adds its theme above the THEME priority; the tip's look must still win there.
        from PyLiite4 import Gdk, Graphene

        first, _ = two_buttons(gtkbot)
        tip = show_tip(first, "Dark", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        # The bubble is the popover's contents widget; a popover is a surface of its own, which a paintable skips.
        contents = tip.get_first_child()
        # Mapped comes before the first allocation, until which it has no size.
        gtkbot.wait_until(lambda: contents.get_width() > 0)
        snapshot = Gtk.Snapshot()
        Gtk.WidgetPaintable(widget=contents).snapshot(snapshot, contents.get_width(), contents.get_height())
        bounds = Graphene.Rect().init(0, 0, contents.get_width(), contents.get_height())
        texture = tip.get_native().get_renderer().render_texture(snapshot.to_node(), bounds)
        downloader = Gdk.TextureDownloader.new(texture)
        downloader.set_format(Gdk.MemoryFormat.R8G8B8A8)
        data, stride = downloader.download_bytes()
        pixels = data.get_data()
        # In the padding just left of the text: the tip's background.
        label = tip.get_child()
        point = Graphene.Point()
        point.x, point.y = -4, label.get_height() / 2
        _, inside = label.compute_point(contents, point)
        offset = int(inside.y) * stride + int(inside.x) * 4
        red, green, blue, alpha = pixels[offset:offset + 4]
        assert alpha > 150 and max(red, green, blue) < 60, (red, green, blue, alpha)


    def test_takes_no_focus_so_typing_goes_on(gtkbot):
        entry = Gtk.Entry()
        gtkbot.show(entry)
        gtkbot.input.type(entry, "ab")
        tip = show_tip(entry, "Typing holds", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        assert entry.get_root().is_active() and entry.get_focus_child() is not None
        # A key press hides the tip, as with tooltips, and still reaches the entry.
        gtkbot.input.type(entry, "c")
        assert entry.get_text() == "abc"
        gtkbot.wait_until(lambda: not tip.get_visible())


    def test_hides_after_its_timeout(gtkbot):
        first, _ = two_buttons(gtkbot)
        tip = show_tip(first, "Brief", timeout=100)
        gtkbot.wait_until(tip.get_mapped)
        gtkbot.wait_until(lambda: not tip.get_visible(), timeout=2)


    def test_hides_when_the_pointer_leaves(gtkbot):
        first, second = two_buttons(gtkbot)
        gtkbot.input.move(first)
        tip = show_tip(first, "Over the first", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        gtkbot.input.move(second)
        gtkbot.wait_until(lambda: not tip.get_visible())


    def test_a_click_elsewhere_hides_it_and_still_clicks(gtkbot):
        first, second = two_buttons(gtkbot)
        clicked = []
        second.connect("clicked", lambda button: clicked.append(True))
        tip = show_tip(first, "Click away", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        gtkbot.input.click(second)
        gtkbot.wait_until(lambda: not tip.get_visible())
        assert clicked == [True]


    def test_at_a_point_with_markup(gtkbot):
        first, _ = two_buttons(gtkbot)
        tip = show_tip(first, "<b>Bold</b> move", (10, 5), use_markup=True, timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        found, rect = tip.get_pointing_to()
        assert found and (rect.x, rect.y, rect.width, rect.height) == (10, 5, 1, 1)
        assert tip.plain_text() == "Bold move"
        assert gtkbot.announcements == ["Bold move"]


    def test_one_tip_moves_between_widgets(gtkbot):
        first, second = two_buttons(gtkbot)
        tip = show_tip(first, "Here", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        assert show_tip(second, "There", timeout=0) is tip
        gtkbot.wait_until(tip.get_mapped)
        assert tip.get_parent() is second and tip.get_child().get_label() == "There"


    def test_nothing_on_a_hidden_widget(gtkbot):
        # Handlers that react to changes can call it without checking.
        first, _ = two_buttons(gtkbot)
        tip = show_tip(first, "Up", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        assert not show_tip(Gtk.Button(), "Nowhere").get_visible()


    def test_its_widget_can_go_while_it_is_up(gtkbot):
        # A popover left on a finalized parent makes GTK warn, which fails the test.
        button = Gtk.Button(label="Going")
        window = gtkbot.show(button)
        tip = show_tip(button, "Still here", timeout=0)
        gtkbot.wait_until(tip.get_mapped)
        window.destroy()
        gtkbot.iterate()
        assert tip.get_parent() is None and not tip.get_visible()
"""


def test_tips(tmp_path):
    result = run_pytest(tmp_path, {"test_inner_tips.py": TIPS}, "--gtk")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "10 passed" in result.stdout, result.stdout[-3000:]
