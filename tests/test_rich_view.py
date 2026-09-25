"""PyLiite4.Extras.RichView, driven with real input in the isolated session of PyLiite4.testing."""

from test_testing import run_pytest

VIEW = """
    import time

    from PyLiite4 import Gdk, Gtk, Pango
    from PyLiite4.Extras import RichView

    SAMPLE = (
        "<h2>Title</h2>"
        "<p>Some <b>bold</b> and a <a href='https://example.org/a'>first link</a>.<br>Second line.</p>"
        "<ul><li>one</li><li>two</li></ul>"
        "<blockquote><p>quoted</p></blockquote>"
        "<pre>x = 1\\ny = 2</pre>"
        "<hr>"
        "<table><tr><th>Name</th><th>Value</th></tr><tr><td>Alpha</td><td>1</td></tr></table>"
        "<p>End with <a href='javascript:bad()'>not a link</a>.</p>"
    )


    def shown(gtkbot, markup=SAMPLE, width=420):
        view = RichView(left_margin=8, right_margin=8)
        view.set_markup(markup)
        gtkbot.show(Gtk.Window(child=view, default_width=width, default_height=500))
        gtkbot.wait_until(lambda: view.get_width() > 0)
        return view


    def offset_of(view, text):
        buffer = view.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True).index(text)


    def point_at(view, offset):
        rect = view.get_iter_location(view.get_buffer().get_iter_at_offset(offset))
        return view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x + 2, rect.y + rect.height // 2)


    def test_text_as_copied(gtkbot):
        view = shown(gtkbot)
        assert view.plain_text() == (
            "Title\\nSome bold and a first link.\\nSecond line.\\n• one\\n• two\\nquoted\\nx = 1\\ny = 2\\n———\\n"
            "Name\\tValue\\nAlpha\\t1\\nEnd with not a link.")


    def test_styles_become_tags(gtkbot):
        view = shown(gtkbot)
        buffer = view.get_buffer()
        bold = buffer.get_iter_at_offset(offset_of(view, "bold"))
        assert any(tag.props.weight == Pango.Weight.BOLD for tag in bold.get_tags())
        title = buffer.get_start_iter()
        assert view.get_tag("h2") in title.get_tags()
        link = buffer.get_iter_at_offset(offset_of(view, "first link"))
        assert view.get_tag("link") in link.get_tags()
        assert view.get_tag("link").props.underline == Pango.Underline.SINGLE
        refused = buffer.get_iter_at_offset(offset_of(view, "not a link"))
        assert view.get_tag("link") not in refused.get_tags()


    def test_clicking_a_link(gtkbot):
        view = shown(gtkbot)
        activated = []
        view.activate_link.connect(lambda view, uri: activated.append(uri) or True)
        gtkbot.input.click(view, at=point_at(view, offset_of(view, "first link") + 3))
        assert activated == ["https://example.org/a"]
        # Not on a link: nothing.
        gtkbot.input.click(view, at=point_at(view, offset_of(view, "Some")))
        assert activated == ["https://example.org/a"]


    def test_hovering_a_link(gtkbot):
        view = shown(gtkbot)
        # Off any link first: the pointer is wherever the last test left it.
        gtkbot.input.move(view, at=point_at(view, offset_of(view, "Some")))
        hovered = []
        view.hover_link.connect(lambda view, uri: hovered.append(uri))
        gtkbot.input.move(view, at=point_at(view, offset_of(view, "first link") + 3))
        assert hovered == ["https://example.org/a"] and view.get_cursor().get_name() == "pointer"
        gtkbot.input.move(view, at=point_at(view, offset_of(view, "Some")))
        assert hovered == ["https://example.org/a", None] and view.get_cursor() is None


    def test_dragging_over_a_link_selects_rather_than_opens(gtkbot):
        view = shown(gtkbot)
        activated = []
        view.activate_link.connect(lambda view, uri: activated.append(uri) or True)
        gtkbot.input.drag(view, start=point_at(view, offset_of(view, "first")),
                          end=point_at(view, offset_of(view, "link.") + 4))
        assert activated == [] and view.get_buffer().get_has_selection()


    def test_extra_link_schemes(gtkbot):
        view = RichView(link_schemes=["ziggy-copy"])
        view.set_markup("<p><a href='ziggy-copy:2'>Copy</a> <a href='https://x.org'>web</a></p>")
        gtkbot.show(Gtk.Window(child=view))
        buffer = view.get_buffer()
        assert view.get_tag("link") in buffer.get_iter_at_offset(0).get_tags()
        assert view.get_tag("link") not in buffer.get_iter_at_offset(6).get_tags()


    def test_copying_gives_tables_as_tab_separated_text(gtkbot):
        view = shown(gtkbot)
        buffer = view.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(offset_of(view, "y = 2")), buffer.get_end_iter())
        view.emit("copy-clipboard")
        copied = []
        clipboard = view.get_clipboard()
        clipboard.read_text_async(None, lambda source, result: copied.append(clipboard.read_text_finish(result)))
        gtkbot.wait_until(lambda: copied)
        assert copied == ["y = 2\\n———\\nName\\tValue\\nAlpha\\t1\\nEnd with not a link."]


    def test_streaming_keeps_the_selection_and_earlier_blocks(gtkbot):
        view = shown(gtkbot, "<p>First paragraph, finished.</p><p>Second</p>")
        buffer = view.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(0), buffer.get_iter_at_offset(5))
        inserted = []
        buffer.connect("insert-text", lambda buffer, where, text, length: inserted.append(text))
        for more in (" grows", " and grows", " and grows<b> bold</b>"):
            view.set_markup(f"<p>First paragraph, finished.</p><p>Second{more}</p>")
        assert "First" not in "".join(inserted)
        assert [bound.get_offset() for bound in buffer.get_selection_bounds()] == [0, 5]
        assert view.plain_text() == "First paragraph, finished.\\nSecond and grows bold"
        # Fewer blocks than before works too.
        view.set_markup("<p>First paragraph, finished.</p>")
        assert view.plain_text() == "First paragraph, finished."


    def test_tables_fit_a_narrow_view(gtkbot):
        long = " ".join(["word"] * 60)
        view = shown(gtkbot, f"<p>Before</p><table><tr><td>{long}</td><td>{long}</td></tr></table>", width=300)
        table = gtkbot.find(view, Gtk.Grid)
        gtkbot.wait_until(lambda: 0 < table.get_width() <= view.get_width())
        # The table doesn't hold the view's minimum width up.
        assert view.measure(Gtk.Orientation.HORIZONTAL, -1)[0] < 200


    def test_links_in_tables(gtkbot):
        view = shown(gtkbot, "<table><tr><td><a href='https://example.org/t'>in a cell</a></td></tr></table>")
        activated = []
        view.activate_link.connect(lambda view, uri: activated.append(uri) or True)
        label = gtkbot.find(view, Gtk.Label, predicate=lambda label: "in a cell" in label.get_text())
        gtkbot.input.click(label)
        assert activated == ["https://example.org/t"]


    def test_from_a_ui_file(gtkbot):
        builder = Gtk.Builder.new_from_string(
            '<interface><object class="PyLiite4RichView" id="view">'
            '<property name="markup">&lt;p&gt;From &lt;b&gt;XML&lt;/b&gt;&lt;/p&gt;</property>'
            '</object></interface>', -1)
        view = builder.get_object("view")
        assert isinstance(view, RichView) and view.plain_text() == "From XML" and not view.get_editable()


    def test_streaming_a_long_reply_stays_quick(gtkbot):
        # A reply re-rendered every 90 ms as it streams, as Ziggy does: each update re-renders only its end.
        view = shown(gtkbot, "")
        paragraphs = [f"<p>Paragraph {n} with <b>some</b> <code>code</code> and a <a href='https://x.org/{n}'>link</a>"
                      f" in it, long enough to wrap over a couple of lines in a narrow view.</p>" for n in range(150)]
        view.set_markup("".join(paragraphs[:140]))
        times = []
        for n in range(140, 150):
            for words in range(1, 6):
                started = time.perf_counter()
                view.set_markup("".join(paragraphs[:n]) + "<p>" + " streamed" * words + "</p>")
                gtkbot.iterate()
                times.append(time.perf_counter() - started)
        assert sum(times) / len(times) < 0.05, f"{sum(times) / len(times):.3f} s per update"
"""


def test_rich_view(tmp_path):
    result = run_pytest(tmp_path, {"test_inner_rich.py": VIEW}, "--gtk")
    assert result.returncode == 0, result.stdout[-8000:] + result.stderr[-2000:]
    assert "12 passed" in result.stdout, result.stdout[-3000:]
