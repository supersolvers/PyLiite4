# Demos

Three collections of GTK demos, ported to Python with PyLiite4. Run them from the repository root, with a PyLiite4 that
has the libraries they use, such as a bundled wheel:

```bash
python -m demos.gtk_demo
```

```bash
python -m demos.adwaita_demo
```

```bash
python -m demos.workbench
```

| Folder | Port of | License of the original |
| --- | --- | --- |
| `gtk_demo/` | GTK Demo (`gtk4-demo`), from GTK 4.22.4's `demos/gtk-demo` | LGPL-2.0-or-later, copyright the GTK authors |
| `adwaita_demo/` | Adwaita Demo (`adwaita-1-demo`), from libadwaita 1.9.4's `demo` | LGPL-2.1-or-later, copyright the libadwaita authors |
| `workbench/` | Workbench's demo library, from https://github.com/workbenchdev/Workbench | CC0-1.0 (public domain) |

The ports are distributed under PyLiite4's LGPL-3.0-only, as the originals' "or later" terms allow. GTK Demo's data
files in `gtk_demo/data/` are GTK's own, unchanged.

`tests/test_demos.py` opens every demo in its own process and fails on any Python exception or GLib critical.

## How the ports are written

A port does what the original does, in the same structure and with the same names, so the two can be read side by side.
Only what C or JavaScript needs and Python doesn't is dropped: reference counting, casts, `G_DEFINE_TYPE` boilerplate.

- Import from PyLiite4, never from `gi.repository`: `from PyLiite4 import Gtk, Adw, Gio`.
- Use PyLiite4's signal objects and keyword constructors: `button.clicked.connect(handler)`,
  `entry.notify["text"].connect(...)`, `Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)`.
- Annotate function signatures with PyLiite4 types.
- A C GObject subclass becomes a Python subclass with `__gtype_name__` set to the C type name; virtual methods become
  `do_*` methods, properties `GObject.Property`, signals `GObject.Signal`. A C composite widget with a `.ui` template
  uses `@Gtk.Template` with the same resource path.
- Deprecated API stays where the original uses it.

### GTK Demo

- One module per C file in `gtk_demo/demos/`, named after it with `-` replaced by `_`: `listview_weather.c` becomes
  `listview_weather.py`, `language-names.c` becomes `language_names.py`.
- The module docstring is the C file's header comment, minus the `/*` and ` * `: title line, optional `#Keywords:`
  line, blank line, description.
- A demo module defines `do(do_widget: Gtk.Widget) -> Gtk.Widget | None`, doing what `do_<name>()` does, including
  keeping its window in a module global and toggling it on a second call. A module without `do` is a helper.
- Data is loaded by the same resource paths as in C. `demos.gtk_demo.register_resources()` builds the GResource from
  `data/demo.gresource.xml`, swapping each `.c` file for its Python module, so the launcher's Source tab shows Python.

### Workbench

- One folder per demo in `workbench/library/`, named as in Workbench, holding `main.py`, `main.ui`, `main.json` and,
  where the original has them, `main.css`, `icons/` and data files.
- `main.ui` is the Blueprint file converted by hand to GtkBuilder XML. The first top-level object must have an `id`:
  it's the preview. Keep Blueprint's other ids, and its `translatable` strings.
- `main.py` is Workbench's Python version, or a port of the JavaScript one where there's no Python version. It
  starts with `from demos.workbench import workbench`, and uses `workbench.builder`, `workbench.window` and
  `workbench.resolve()` as Workbench demos do.
- `main.json` is Workbench's, plus `"requires"`: the namespaces beyond GTK and libadwaita that the demo needs, such as
  `["Soup"]`. Demos needing WebKit, Shumate, Spelling, Manette, Gom or Gly are kept, but listed as unable to run.
