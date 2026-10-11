#!/usr/bin/env python3
"""Build a static HTML API reference for PyLiite4 from the same GObject Introspection data as the stubs.

Usage: tools/reference.py [--gir-dir DIR ...] [--output DIR]

It writes an index, a page per namespace (with its functions, constants and callbacks) and a page per class,
interface, record and enumeration, with a search box. Open build/reference/index.html in a browser.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate import (CORE, DESCRIPTIONS, GLIB, NAMESPACES, OVERRIDDEN, SKIPPED, Generator,  # noqa: E402
                      callable_usable, core, escape, tag)

KINDS = {"class": "Classes", "interface": "Interfaces", "record": "Records", "union": "Records",
         "enumeration": "Enumerations", "bitfield": "Flags"}
# The builtins the stubs import under private names.
ALIASES = re.compile(r"\b_(builtin_int|builtin_str|builtins\.|str|int|bool|float|bytes|list|dict|tuple|Any|Callable"
                     r"|Awaitable|Iterator|Coroutine)\b")
STYLE = """\
:root { --bg: #fff; --fg: #1d1d20; --muted: #5e5c64; --line: #deddda; --code: #f6f5f4; --link: #1c71d8; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #1d1d20; --fg: #f6f5f4; --muted: #9a9996; --line: #3d3846; --code: #2a2a2e; --link: #78aeed; }
}
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
header { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 10px 16px;
         border-bottom: 1px solid var(--line); }
header nav { flex: 1; } header input { width: min(320px, 100%); padding: 4px 8px; font: inherit; }
main { max-width: 960px; margin: 0 auto; padding: 0 16px 48px; overflow-wrap: break-word; }
a { color: var(--link); text-decoration: none; } a:hover { text-decoration: underline; }
code, pre { font-family: ui-monospace, monospace; font-size: 0.9em; background: var(--code); border-radius: 4px; }
code { padding: 0 3px; } pre { padding: 8px 12px; overflow-x: auto; }
.member { border-top: 1px solid var(--line); padding-top: 4px; margin-top: 16px; }
.member > code:first-child { display: block; background: none; padding: 0; font-weight: 600; white-space: pre-wrap; }
.muted { color: var(--muted); } ul.names { columns: 16em; padding-left: 1.2em; }
#results { list-style: none; padding: 0; } #results li { padding: 2px 0; }
"""
SEARCH = """\
const box = document.querySelector("#search"), results = document.querySelector("#results");
box.addEventListener("input", () => {
  const words = box.value.toLowerCase().split(/\\s+/).filter(Boolean);
  const found = words.length ? INDEX.filter(([name]) => words.every(w => name.toLowerCase().includes(w))) : [];
  found.sort((a, b) => a[0].length - b[0].length);
  results.replaceChildren(...found.slice(0, 100).map(([name, url, kind]) => {
    const item = document.createElement("li"), link = document.createElement("a");
    link.href = url; link.textContent = name;
    item.append(link, " ", Object.assign(document.createElement("span"), {className: "muted", textContent: kind}));
    return item;
  }));
  document.querySelector("#content").hidden = words.length > 0;
});
"""


def pretty(code):
    """A stub annotation as people write it: _str is str and _GTypeLike GObject.GType | type."""
    code = code.replace("_GTypeLike", "GObject.GType | type").replace("_cairo.", "cairo.")
    return ALIASES.sub(lambda m: {"builtin_int": "int", "builtin_str": "str", "builtins.": ""}.get(m.group(1),
                                                                                                    m.group(1)), code)


class Reference:
    def __init__(self, generator):
        self.generator = generator
        self.pages = {}  # Python name -> (namespace, element)
        for namespace in NAMESPACES:
            for element in self.generator.roots[namespace]:
                name = f"{namespace}.{element.get('name')}"
                if tag(element) in KINDS and self.visible(element, name):
                    self.pages[name] = (namespace, element)
        self.index = []

    def visible(self, element, qualified):
        return (element.get("name") and qualified not in SKIPPED and qualified not in OVERRIDDEN
                and (tag(element) == "class" or element.get("introspectable", "1") != "0")
                and not element.get(f"{{{GLIB}}}is-gtype-struct-for"))

    # Links --------------------------------------------------------------------------------------

    def url(self, target, here):
        """The page and anchor of a Python name such as Gtk.Widget.show, relative to here."""
        parts = target.split(".")
        for size in range(len(parts), 0, -1):
            page = ".".join(parts[:size])
            anchor = ".".join(parts[size:])
            if page in self.pages or (size == 1 and page in NAMESPACES):
                return ("" if page == here and anchor else f"{page}.html") + (f"#{anchor}" if anchor else "")
        return None

    def blocks(self, text, here, links):
        out = []
        for index, part in enumerate(re.split(r"```(\w*)\n?(.*?)```", text, flags=re.S)):
            if index % 3 == 1:
                continue
            if index % 3 == 2:
                out.append(f"<pre><code>{self.inline_links(html.escape(part.strip(chr(10))), here, links)}</code></pre>")
                continue
            for block in re.split(r"\n\s*\n", part):
                block = block.strip("\n")
                if not block.strip():
                    continue
                heading = re.match(r"(#{1,4})\s+(.*)", block)
                if heading and "\n" not in block:
                    out.append(f"<h4>{self.inline(heading.group(2), here, links)}</h4>")
                elif re.match(r"\s*([-*]|\d+\.)\s", block):
                    items = re.split(r"\n\s*(?:[-*]|\d+\.)\s+", "\n" + block.strip())[1:]
                    list_tag = "ol" if re.match(r"\s*\d", block) else "ul"
                    out.append(f"<{list_tag}>" + "".join(f"<li>{self.inline(i, here, links)}</li>" for i in items)
                               + f"</{list_tag}>")
                else:
                    out.append(f"<p>{self.inline(block, here, links)}</p>")
        return "\n".join(out)

    def inline(self, text, here, links):
        text = html.escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\[([^\]\x01]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
        return self.inline_links(text, here, links)

    def inline_links(self, text, here, links):
        def replace(match):
            kind, target, label = links[int(match.group(1))]
            url = self.url(target, here)
            return f'<a href="{url}">{html.escape(label)}</a>' if url else html.escape(label)
        return re.sub(r"\x01(\d+)\x02", replace, text)

    def code(self, code, here, namespace):
        """A signature, with its types linked to their pages."""
        def replace(match):
            name = match.group(0)
            url = self.url(name if "." in name else f"{namespace}.{name}", here)
            return f'<a href="{url}">{name}</a>' if url and name not in ("None",) else name
        return re.sub(r"\b[A-Z]\w*(?:\.[A-Z]\w*)?\b", replace, html.escape(pretty(code)))

    # Pages --------------------------------------------------------------------------------------

    def page(self, title, body):
        return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width, initial-scale=1">'
                f"<title>{html.escape(title)} - PyLiite4</title><link rel=stylesheet href=style.css></head>\n"
                f'<body><header><nav><a href="index.html">PyLiite4</a> {self.crumbs(title)}'
                '</nav><input id=search type=search placeholder="Search" aria-label="Search the reference"></header>\n'
                f'<main><ul id=results></ul><div id=content>\n<h1>{html.escape(title)}</h1>\n{body}\n</div></main>'
                '<script src="search-index.js"></script><script src="search.js"></script></body></html>\n')

    def crumbs(self, title):
        namespace = title.split(".")[0]
        return f'/ <a href="{namespace}.html">{namespace}</a>' if namespace in NAMESPACES else ""

    def doc_html(self, element, here, namespace, callable_=False):
        links = []

        def placeholder(kind, target, label):
            links.append((kind, target, label))
            return f"\x01{len(links) - 1}\x02"

        text = (self.generator.callable_doc(element, placeholder) if callable_
                else self.generator.doc(element, link=placeholder))
        return self.blocks(text, here, links) if text else ""

    def entry(self, anchor, signature, element, here, namespace, note="", callable_=True):
        self.index.append([f"{here}.{anchor}", f"{here}.html#{anchor}", note or "method"])
        return (f'<div class=member id="{html.escape(anchor)}"><code>{self.code(signature, here, namespace)}</code>'
                + (f' <span class=muted>{note}</span>' if note else "")
                + f"\n{self.doc_html(element, here, namespace, callable_)}</div>")

    def callables(self, element, namespace, here, extra_methods=()):
        """Sections for constructors, methods, static functions and virtual methods."""
        sections = []
        signature = self.generator.signature
        groups = [("Constructors", core(element, "constructor"), "cls", "classmethod"),
                  ("Methods", core(element, "method"), "self", ""),
                  ("Class methods", list(extra_methods), "cls", "classmethod"),
                  ("Static functions", core(element, "function"), None, "staticmethod"),
                  ("Virtual methods", core(element, "virtual-method"), "self", "override in a subclass")]
        for title, children, first, note in groups:
            entries = []
            for child in children:
                if not callable_usable(child):
                    continue
                prefix = "do_" if tag(child) == "virtual-method" else ""
                name = prefix + escape(child.get("shadows") or child.get("name"))
                text = signature(child, namespace, first, prefix=prefix).removeprefix("def ").removesuffix(": ...")
                entries.append(self.entry(name, text, child, here, namespace, note))
            if entries:
                sections.append(f"<h2>{title}</h2>\n" + "\n".join(entries))
        return sections

    def type_page(self, qualified):
        namespace, element = self.pages[qualified]
        generator, kind = self.generator, tag(element)
        self.index.append([qualified, f"{qualified}.html", kind])
        body = []
        info = generator.classes.get(qualified)
        if info:
            chain = [c.qualified for c in generator.ancestors(info)[1:] if c.kind == "class"]
            interfaces = sorted({c.qualified for c in generator.ancestors(info)[1:] if c.kind == "interface"})
            if chain:
                body.append("<p>Inherits from " + " → ".join(self.code(c, qualified, namespace) for c in chain)
                            + ".</p>")
            if interfaces:
                body.append("<p>Implements " + ", ".join(self.code(c, qualified, namespace) for c in interfaces)
                            + ".</p>")
            if info.prerequisites:
                body.append("<p>Requires " + ", ".join(self.code(c, qualified, namespace) for c in info.prerequisites)
                            + ".</p>")
        body.append(self.doc_html(element, qualified, namespace))
        if kind in ("enumeration", "bitfield"):
            members = [self.entry(m.get("name").replace("-", "_").upper(), m.get("name").replace("-", "_").upper(),
                                  m, qualified, namespace, "member", callable_=False)
                       for m in core(element, "member")]
            body.append("<h2>Members</h2>\n" + "\n".join(members))
        if info:
            properties = [self.entry(f"props.{p.get('name').replace('-', '_')}",
                                     f"{p.get('name').replace('-', '_')}: {generator.property_type(p, namespace)}",
                                     p, qualified, namespace, self.access(p), callable_=False)
                          for p in info.properties]
            if properties:
                body.append("<h2>Properties</h2>\n<p class=muted>Read and write these as <code>obj.props.name</code>"
                            " or, unless a method has the same name, <code>obj.name</code>.</p>\n"
                            + "\n".join(properties))
            signals = [self.entry(name, f"{escape(name)}: {generator.signal_type(signal, info.name, namespace)}",
                                  signal, qualified, namespace, "signal", callable_=False)
                       for name, signal in info.signals.items()]
            if signals:
                body.append("<h2>Signals</h2>\n<p class=muted>Connect a handler with <code>obj.name.connect(handler)"
                            '</code> or <code>obj.connect("name", handler)</code>.</p>\n' + "\n".join(signals))
        fields = [f for f in core(element, "field") if f.get("private") != "1"
                  and f.find(f"{{{CORE}}}callback") is None] if kind in ("record", "union") else []
        if fields:
            body.append("<h2>Fields</h2>\n" + "\n".join(
                self.entry(escape(f.get("name")), f"{escape(f.get('name'))}: {generator.py_type(f, namespace)}", f,
                           qualified, namespace, "field", callable_=False) for f in fields))
        struct = element.get(f"{{{GLIB}}}type-struct")
        record = next((e for e in generator.roots[namespace] if tag(e) == "record" and e.get("name") == struct), None)
        body += self.callables(element, namespace, qualified, core(record, "method") if record is not None else ())
        return self.page(qualified, "\n".join(body))

    def access(self, prop):
        if prop.get("construct-only") == "1":
            return "construct-only"
        readable, writable = prop.get("readable", "1") != "0", prop.get("writable") == "1"
        return "read/write" if readable and writable else "write-only" if writable else "read-only"

    def namespace_page(self, namespace):
        generator = self.generator
        ns = generator.roots[namespace]
        self.index.append([namespace, f"{namespace}.html", "namespace"])
        body = [f"<p>{html.escape(DESCRIPTIONS[namespace])}, version {generator.versions[namespace]}. "
                f"Import it with <code>from PyLiite4 import {namespace}</code>.</p>"]
        for kind in dict.fromkeys(KINDS.values()):
            names = sorted(name for name, (n, e) in self.pages.items() if n == namespace and KINDS[tag(e)] == kind)
            if names:
                body.append(f"<h2>{kind}</h2>\n<ul class=names>" + "".join(
                    f'<li><a href="{name}.html">{name.split(".", 1)[1]}</a></li>' for name in names) + "</ul>")
        functions, constants, callbacks = [], [], []
        for element in ns:
            name = element.get("name")
            if not name or not self.visible(element, f"{namespace}.{element.get('shadows') or name}"):
                continue
            if tag(element) == "function" and callable_usable(element):
                text = generator.signature(element, namespace).removeprefix("def ").removesuffix(": ...")
                functions.append(self.entry(escape(element.get("shadows") or name), text, element, namespace,
                                            namespace, "function"))
            elif tag(element) == "constant":
                constants.append(self.entry(escape(name), f"{escape(name)}: {generator.py_type(element, namespace)}",
                                            element, namespace, namespace, "constant", callable_=False))
            elif tag(element) in ("callback", "alias"):
                inputs, _, _ = generator.parameters(element, namespace)
                result = element.find(f"{{{CORE}}}return-value")
                returned = generator.py_type(result, namespace) if result is not None else "None"
                text = (f"{name} = {generator.py_type(element, namespace)}" if tag(element) == "alias" else
                        f"{name} = _Callable[[{', '.join(a for _, a, _ in inputs)}], {returned}]")
                callbacks.append(self.entry(name, text, element, namespace, namespace, tag(element),
                                            callable_=tag(element) == "callback"))
        for title, entries in (("Functions", functions), ("Constants", constants), ("Callbacks and aliases", callbacks)):
            if entries:
                body.append(f"<h2>{title}</h2>\n" + "\n".join(entries))
        return self.page(namespace, "\n".join(body))

    def index_page(self):
        items = "".join(f'<li><a href="{n}.html">{n}</a> <span class=muted>{html.escape(DESCRIPTIONS[n])}, '
                        f"version {self.generator.versions[n]}</span></li>" for n in NAMESPACES)
        return self.page("API reference", "<p>The classes and functions PyLiite4 provides, with GTK's documentation "
                         "in Python's terms. The same text is in the type stubs, for your editor.</p>\n"
                         f"<ul>{items}</ul>")

    def write(self, output):
        output.mkdir(parents=True, exist_ok=True)
        for namespace in NAMESPACES:
            (output / f"{namespace}.html").write_text(self.namespace_page(namespace))
        for qualified in sorted(self.pages):
            (output / f"{qualified}.html").write_text(self.type_page(qualified))
        (output / "index.html").write_text(self.index_page())
        (output / "style.css").write_text(STYLE)
        (output / "search.js").write_text(SEARCH)
        index = json.dumps(sorted(self.index), separators=(",", ":"))
        (output / "search-index.js").write_text(f"const INDEX = {index};\n")
        return len(self.pages) + len(NAMESPACES) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gir-dir", type=Path, action="append",
                        help="where to find GIR files; repeat to search several, in order (default: /usr/share/gir-1.0)")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent / "build" / "reference")
    args = parser.parse_args()
    reference = Reference(Generator(args.gir_dir or [Path("/usr/share/gir-1.0")]))
    pages = reference.write(args.output)
    print(f"{pages} pages in {args.output}")


if __name__ == "__main__":
    main()
