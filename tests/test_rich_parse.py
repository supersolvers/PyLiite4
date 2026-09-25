"""PyLiite4._rich, the parser behind RichView: HTML subset in, blocks of styled runs out. No display needed."""

from PyLiite4._rich import LINE_BREAK, Style, parse, plain


def kinds(markup):
    return [block.kind for block in parse(markup)]


def test_blocks():
    blocks = parse("<h3>Title</h3><p>One</p><p>Two</p><hr><pre>x = 1</pre>")
    assert [(block.kind, block.level) for block in blocks] == [("heading", 3), ("paragraph", 0), ("paragraph", 0),
                                                                ("rule", 0), ("pre", 0)]
    assert [plain(block.runs) for block in blocks] == ["Title", "One", "Two", "", "x = 1"]


def test_text_outside_blocks_is_a_paragraph():
    assert [(block.kind, plain(block.runs)) for block in parse("loose <b>text</b>")] == [("paragraph", "loose text")]


def test_inline_styles():
    runs = parse('<p>a <b>b</b> <i>c</i> <u>d</u> <s>e</s> <code>f</code> <span style="color:#f00; '
                 'font-family: \'Fira Code\', monospace; font-size: 12px">g</span></p>')[0].runs
    styles = {text: style for text, style in runs}
    assert styles["b"].bold and styles["c"].italic and styles["d"].underline and styles["e"].strike
    assert styles["f"].code
    assert styles["g"] == Style(fg="#f00", family="Fira Code,monospace", size_px=12.0)


def test_pango_markup():
    runs = parse('<span foreground="blue" weight="bold" style="italic" underline="single">x</span>'
                 '<tt>y</tt><big>z</big><sub>2</sub>')[0].runs
    styles = {text: style for text, style in runs}
    assert styles["x"] == Style(bold=True, italic=True, underline=True, fg="blue")
    assert styles["y"].code and styles["z"].scale == 1.2 and styles["2"].rise == -1


def test_links_need_an_allowed_scheme():
    runs = parse('<a href="https://a.org">a</a> <a href="javascript:x()">b</a> <a href="/relative">c</a> '
                 '<a href="ziggy-copy:3">d</a>')[0].runs
    # The refused links are plain text, one run with the spaces between them.
    assert [(text, style.link) for text, style in runs] == [("a", "https://a.org"), (" b c d", None)]
    runs = parse('<a href="ziggy-copy:3">d</a>', ("ziggy-copy",))[0].runs
    assert runs[0][1].link == "ziggy-copy:3"


def test_whitespace_and_entities():
    blocks = parse("<p>  several \n   spaces &amp; &lt;tags&gt; &#x2713;  </p><p>line<br>break</p>")
    assert plain(blocks[0].runs) == "several spaces & <tags> ✓"
    assert blocks[1].runs[0][0] == f"line{LINE_BREAK}break"


def test_preformatted_keeps_spacing():
    block = parse("<pre>\ndef f():\n    return 1\n</pre>")[0]
    assert plain(block.runs) == "def f():\n    return 1\n"
    block = parse('<p style="white-space: pre-wrap">a   b</p>')[0]
    assert plain(block.runs) == "a   b"


def test_lists():
    blocks = parse("<ul><li>a</li><li>b<ul><li>c</li></ul></li></ul><ol start='4'><li>d</li><li>e</li></ol>")
    assert [(block.kind, block.depth, block.marker, plain(block.runs)) for block in blocks] == [
        ("item", 1, "•", "a"), ("item", 1, "•", "b"), ("item", 2, "◦", "c"), ("item", 1, "4.", "d"),
        ("item", 1, "5.", "e")]


def test_quotes_and_indents():
    blocks = parse('<blockquote><p>a</p><blockquote><p>b</p></blockquote></blockquote>'
                   '<p style="margin-left: 12px">c</p>')
    assert [(block.quote, block.indent) for block in blocks] == [(1, 0), (2, 0), (0, 12)]


def test_tables():
    block = parse("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody>"
                  "<tr><td bgcolor='#eee'><b>1</b></td><td>two<br>lines<p>and a paragraph</p></td></tr>"
                  "</tbody></table>")[0]
    assert block.kind == "table"
    assert [[(cell.header, plain(cell.runs)) for cell in row] for row in block.rows] == [
        [(True, "A"), (True, "B")], [(False, "1"), (False, "two\nlines\nand a paragraph")]]
    assert block.rows[1][0].style.bg == "#eee" and block.rows[1][0].runs[0][1].bold


def test_dropped_and_unknown_tags():
    blocks = parse("<script>alert(1)</script><style>p{}</style><p>kept <blink>text</blink> "
                   "<img src='x.png' alt='[picture]'></p>")
    assert [plain(block.runs) for block in blocks] == ["kept text [picture]"]


def test_malformed_input_doesnt_fail():
    blocks = parse("<p>open <b>bold <i>both</p><p>after</b> plain</i><table><tr><td>unclosed")
    assert [block.kind for block in blocks] == ["paragraph", "paragraph", "table"]
    assert plain(blocks[1].runs) == "after plain"


def test_empty_blocks_are_skipped():
    assert kinds("<p> </p><p></p><div><br></div><h1></h1>") == []
