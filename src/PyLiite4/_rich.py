"""Parse RichView's HTML subset into blocks of styled runs.

Keep GTK out of this module: parsing produces the blocks, and Extras.RichView draws them.

The subset is Qt's rich text, roughly, plus Pango markup's own tags and span attributes:

- blocks: ``p``, ``div``, ``h1``-``h6``, ``ul``/``ol``/``li``, ``blockquote``, ``pre``, ``hr``, ``table`` with
  ``tr``, ``td``, ``th``, ``thead`` and ``tbody``; ``br`` breaks a line;
- inline: ``b``/``strong``, ``i``/``em``, ``u``, ``s``/``del``/``strike``, ``code``/``tt``/``kbd``, ``a href``,
  ``span``/``font``, ``big``, ``small``, ``sub``, ``sup``; ``img`` shows its ``alt`` text;
- styles, from a ``style`` attribute on any element: ``color``, ``background-color`` (also ``bgcolor``),
  ``font-family``, ``font-size``, ``font-weight``, ``font-style``, ``text-decoration``, ``margin-left``,
  ``white-space: pre``; and Pango's ``foreground``, ``background``, ``font_family``, ``weight``, ``style``,
  ``size``, ``underline``, ``strikethrough``.

Anything else is shown as its text, or dropped with its content for ``script``, ``style`` and the like. A link is a
link only when its scheme is one allowed; otherwise it is plain text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser

# Breaks a line inside a block, as Pango and GtkTextBuffer read U+2028, so one block stays one paragraph.
LINE_BREAK = " "


@dataclass(frozen=True)
class Style:
    """How a run of text looks. Colours are CSS colour strings, checked when rendered."""

    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    code: bool = False
    family: str | None = None
    size_px: float | None = None
    scale: float | None = None
    fg: str | None = None
    bg: str | None = None
    link: str | None = None
    rise: int = 0


Run = tuple[str, Style]


@dataclass(frozen=True)
class Cell:
    header: bool
    runs: tuple[Run, ...]
    style: Style = Style()


@dataclass(frozen=True)
class Block:
    """A paragraph, heading, list item, preformatted block, rule or table."""

    kind: str
    runs: tuple[Run, ...] = ()
    level: int = 0
    depth: int = 0
    marker: str = ""
    quote: int = 0
    indent: int = 0
    style: Style = Style()
    rows: tuple[tuple[Cell, ...], ...] = ()


_DROPPED = {"script", "style", "head", "title", "template", "iframe", "object", "embed", "noscript", "svg"}
_VOID = {"br", "hr", "img", "meta", "link", "input", "wbr", "col", "area", "base", "source"}
_BULLETS = ("•", "◦", "▪")
_SIZES = {"xx-small": 0.58, "x-small": 0.69, "small": 0.83, "medium": 1.0, "large": 1.2, "x-large": 1.44,
          "xx-large": 1.73, "smaller": 0.83, "larger": 1.2}
_WHITESPACE = re.compile(r"[ \t\r\n\f]+")


def _css(text: str | None) -> dict[str, str]:
    declarations = {}
    for part in (text or "").split(";"):
        name, colon, value = part.partition(":")
        if colon:
            declarations[name.strip().lower()] = value.strip()
    return declarations


def _length(value: str) -> tuple[float | None, float | None]:
    """A font size as (pixels, scale), one of them set."""
    value = value.strip().lower()
    if value in _SIZES:
        return None, _SIZES[value]
    match = re.fullmatch(r"([0-9.]+)\s*(px|pt|em|rem|%)?", value)
    if not match:
        return None, None
    number, unit = float(match.group(1)), match.group(2) or "px"
    if unit == "px":
        return number, None
    if unit == "pt":
        return number / 0.75, None
    return None, number / 100 if unit == "%" else number


def _styled(style: Style, declarations: dict[str, str]) -> Style:
    changes: dict[str, object] = {}
    for name, value in declarations.items():
        lowered = value.lower()
        if name in ("color", "foreground", "fgcolor"):
            changes["fg"] = value
        elif name in ("background-color", "background", "bgcolor"):
            changes["bg"] = value
        elif name in ("font-family", "font_family", "face"):
            changes["family"] = ",".join(part.strip().strip("'\"") for part in value.split(","))
        elif name in ("font-size", "size"):
            pixels, scale = _length(value)
            if name == "size" and pixels is not None and lowered.isdigit():
                # Pango's size is in 1024ths of a point.
                pixels, scale = int(lowered) / 1024 / 0.75, None
            if pixels is not None or scale is not None:
                changes["size_px"], changes["scale"] = pixels, scale
        elif name in ("font-weight", "weight"):
            changes["bold"] = lowered in ("bold", "bolder", "heavy", "ultrabold", "semibold") or \
                (lowered.isdigit() and int(lowered) >= 600)
        elif name in ("font-style", "style"):
            changes["italic"] = lowered in ("italic", "oblique")
        elif name == "text-decoration":
            changes["underline"] = "underline" in lowered
            changes["strike"] = "line-through" in lowered
        elif name == "underline":
            changes["underline"] = lowered not in ("none", "false")
        elif name == "strikethrough":
            changes["strike"] = lowered == "true"
    return replace(style, **changes) if changes else style  # type: ignore[arg-type]


@dataclass
class _Context:
    tag: str
    style: Style
    preserve: bool


@dataclass
class _Table:
    rows: list[list[Cell]] = field(default_factory=list)
    head: bool = False


class _Parser(HTMLParser):
    def __init__(self, link_schemes: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.link_schemes = link_schemes
        self.blocks: list[Block] = []
        self.stack: list[_Context] = [_Context("", Style(), False)]
        self.runs: list[Run] = []
        self.meta: dict[str, object] | None = None
        self.lists: list[list[object]] = []
        self.quote = 0
        self.dropped = 0
        self.tables: list[_Table] = []
        self.cell: tuple[bool, Style, list[Run]] | None = None
        self.fresh_pre = False

    # Text

    def target(self) -> list[Run]:
        return self.cell[2] if self.cell is not None else self.runs

    def at_line_start(self) -> bool:
        runs = self.target()
        return not runs or runs[-1][0].endswith(("\n", LINE_BREAK, " "))

    def add(self, text: str, style: Style | None = None) -> None:
        style = style or self.stack[-1].style
        if self.cell is None and self.meta is None:
            self.start("paragraph")
        runs = self.target()
        if runs and runs[-1][1] == style:
            runs[-1] = (runs[-1][0] + text, style)
        else:
            runs.append((text, style))

    def handle_data(self, data: str) -> None:
        if self.dropped:
            return
        if self.stack[-1].preserve:
            if self.fresh_pre and data.startswith("\n"):
                data = data[1:]
            self.fresh_pre = False
            if data:
                self.add(data.replace("\r\n", "\n").replace("\n", LINE_BREAK if self.cell is None else "\n"))
            return
        data = _WHITESPACE.sub(" ", data)
        if self.at_line_start():
            data = data.lstrip(" ")
        if data:
            self.add(data)

    def line_break(self) -> None:
        if self.cell is not None:
            self.add("\n")
        elif self.meta is not None:
            self.add(LINE_BREAK)

    # Blocks

    def start(self, kind: str, **meta: object) -> None:
        if self.cell is not None:
            # Blocks inside a table cell are lines of its text.
            if self.cell[2] and not self.cell[2][-1][0].endswith("\n"):
                self.add("\n")
            if kind == "item":
                self.add(f"{meta.get('marker', '•')} ")
            return
        self.flush()
        self.meta = {"kind": kind, "quote": self.quote, "depth": len(self.lists), **meta}

    def flush(self) -> None:
        if self.meta is None:
            return
        meta, runs = self.meta, self.runs
        self.meta, self.runs = None, []
        kind = str(meta["kind"])
        if kind != "pre":
            while runs and not runs[-1][0].rstrip(" " + LINE_BREAK):
                runs.pop()
            if runs:
                runs[-1] = (runs[-1][0].rstrip(" "), runs[-1][1])
        if not any(text.strip() for text, _ in runs) and kind != "pre":
            return
        if kind == "pre" and not runs:
            return
        self.blocks.append(Block(kind=kind, runs=tuple(runs), level=int(meta.get("level", 0)),  # type: ignore[call-overload]
                                 depth=int(meta.get("depth", 0)), marker=str(meta.get("marker", "")),  # type: ignore[call-overload]
                                 quote=int(meta.get("quote", 0)), indent=int(meta.get("indent", 0)),  # type: ignore[call-overload]
                                 style=meta.get("style", Style())))  # type: ignore[arg-type]

    # Tags

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROPPED:
            self.dropped += 1
            return
        if self.dropped:
            return
        attributes = {name.lower(): value or "" for name, value in attrs}
        # On a Pango span, style="italic" is Pango's attribute, not CSS.
        pango_style = tag in ("span", "font") and ":" not in attributes.get("style", ":")
        declarations = _css(None if pango_style else attributes.get("style"))
        if pango_style:
            declarations["font-style"] = attributes["style"]
        if "bgcolor" in attributes:
            declarations.setdefault("background-color", attributes["bgcolor"])
        if tag in ("span", "font"):
            for name in ("foreground", "fgcolor", "color", "background", "bgcolor", "font_family", "face",
                         "weight", "style", "size", "underline", "strikethrough"):
                if name in attributes and name != "style":
                    declarations.setdefault(name, attributes[name])
        parent = self.stack[-1]
        style = _styled(parent.style, {name: value for name, value in declarations.items()
                                       if name not in ("background-color", "background", "bgcolor")
                                       or tag not in ("p", "div", "pre", "td", "th", "table", "tr", "blockquote")})
        preserve = parent.preserve or declarations.get("white-space", "").startswith("pre")
        indent = int(_length(declarations["margin-left"])[0] or 0) if "margin-left" in declarations else 0
        block_style = _styled(Style(), declarations)

        if tag in ("p", "div"):
            self.start("paragraph", indent=indent, style=block_style)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.start("heading", level=int(tag[1]), indent=indent, style=block_style)
        elif tag in ("ul", "ol"):
            self.flush()
            start = attributes.get("start", "1")
            self.lists.append([tag, int(start) - 1 if start.isdigit() else 0])
        elif tag == "li":
            marker = "•"
            if self.lists:
                kind = self.lists[-1]
                if kind[0] == "ol":
                    kind[1] = int(kind[1]) + 1  # type: ignore[call-overload]
                    marker = f"{kind[1]}."
                else:
                    marker = _BULLETS[(len(self.lists) - 1) % len(_BULLETS)]
            self.start("item", marker=marker, indent=indent, style=block_style)
        elif tag == "blockquote":
            self.flush()
            self.quote += 1
        elif tag == "pre":
            self.start("pre", indent=indent, style=block_style)
            preserve, self.fresh_pre = True, True
        elif tag == "hr":
            if self.cell is not None:
                self.start("paragraph")
                self.add("———")
            else:
                self.flush()
                self.blocks.append(Block(kind="rule", quote=self.quote))
        elif tag == "br":
            self.line_break()
        elif tag == "table":
            self.flush()
            self.tables.append(_Table())
        elif tag == "thead" and self.tables:
            self.tables[-1].head = True
        elif tag == "tbody" and self.tables:
            self.tables[-1].head = False
        elif tag == "tr" and self.tables and len(self.tables) == 1:
            self.tables[-1].rows.append([])
        elif tag in ("td", "th") and self.tables and len(self.tables) == 1:
            self.finish_cell()
            if not self.tables[-1].rows:
                self.tables[-1].rows.append([])
            self.cell = (tag == "th" or self.tables[-1].head, block_style, [])
        elif tag in ("b", "strong"):
            style = replace(style, bold=True)
        elif tag in ("i", "em", "cite", "var", "dfn"):
            style = replace(style, italic=True)
        elif tag in ("u", "ins"):
            style = replace(style, underline=True)
        elif tag in ("s", "del", "strike"):
            style = replace(style, strike=True)
        elif tag in ("code", "tt", "kbd", "samp"):
            style = replace(style, code=not preserve)
        elif tag == "big":
            style = replace(style, scale=(style.scale or 1) * 1.2)
        elif tag == "small":
            style = replace(style, scale=(style.scale or 1) / 1.2)
        elif tag in ("sub", "sup"):
            style = replace(style, scale=(style.scale or 1) * 0.8, rise=-1 if tag == "sub" else 1)
        elif tag == "a":
            href = attributes.get("href", "").strip()
            scheme = href.partition(":")[0].lower() if ":" in href else ""
            if scheme and scheme in self.link_schemes:
                style = replace(style, link=href)
        elif tag == "img":
            alt = attributes.get("alt", "")
            if alt:
                self.add(alt)
        if tag not in _VOID:
            self.stack.append(_Context(tag, style, preserve))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def finish_cell(self) -> None:
        if self.cell is not None and self.tables:
            header, style, runs = self.cell
            while runs and not runs[-1][0].strip():
                runs.pop()
            if runs:
                runs[-1] = (runs[-1][0].rstrip(), runs[-1][1])
            self.tables[-1].rows[-1].append(Cell(header, tuple(runs), style))
            self.cell = None

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROPPED:
            self.dropped = max(0, self.dropped - 1)
            return
        if self.dropped or tag in _VOID:
            return
        if any(context.tag == tag for context in self.stack[1:]):
            while self.stack[-1].tag != tag:
                self.stack.pop()
            self.stack.pop()
        if tag in ("p", "div", "li", "pre") or tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if self.cell is None:
                self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            if self.lists:
                self.lists.pop()
        elif tag == "blockquote":
            self.flush()
            self.quote = max(0, self.quote - 1)
        elif tag in ("td", "th"):
            self.finish_cell()
        elif tag == "table" and self.tables:
            self.finish_cell()
            table = self.tables.pop()
            rows = tuple(tuple(row) for row in table.rows if row)
            if rows:
                self.blocks.append(Block(kind="table", rows=rows, quote=self.quote))

    def close(self) -> None:
        super().close()
        self.finish_cell()
        while self.tables:
            self.handle_endtag("table")
        self.flush()


def parse(markup: str, link_schemes: tuple[str, ...] = ("http", "https", "mailto")) -> list[Block]:
    """The blocks of ``markup``, in order."""
    parser = _Parser(tuple(scheme.lower() for scheme in link_schemes))
    parser.feed(markup)
    parser.close()
    return parser.blocks


def plain(runs: tuple[Run, ...]) -> str:
    """The text of some runs, with line breaks as newlines."""
    return "".join(text for text, _ in runs).replace(LINE_BREAK, "\n")
