"""Printing/Printing

GtkPrintOperation offers a simple API to support printing
in a cross-platform way.
"""

import math
from dataclasses import dataclass, field

from PyLiite4 import Gio, GLib, Gtk, Pango

try:
    from PyLiite4 import PangoCairo
except ImportError:
    # PyLiite4 doesn't wrap PangoCairo, though bundled wheels carry its typelib: bind it the way PyLiite4's modules do.
    from types import ModuleType

    from PyLiite4 import _runtime

    PangoCairo = ModuleType("PangoCairo")
    _runtime.bind(PangoCairo.__dict__, "PangoCairo", "1.0", (), {})

# In points
HEADER_HEIGHT = 10 * 72 / 25.4
HEADER_GAP = 3 * 72 / 25.4


@dataclass
class PrintData:
    resourcename: str
    font_size: float

    lines_per_page: int = 0
    lines: list[str] = field(default_factory=list)
    num_lines: int = 0
    num_pages: int = 0


def begin_print(operation: Gtk.PrintOperation, context: Gtk.PrintContext, data: PrintData) -> None:
    height = context.get_height() - HEADER_HEIGHT - HEADER_GAP

    data.lines_per_page = math.floor(height / data.font_size)

    bytes = Gio.resources_lookup_data(data.resourcename, Gio.ResourceLookupFlags.NONE)

    data.lines = bytes.get_data().decode().split("\n")

    data.num_lines = len(data.lines)
    data.num_pages = (data.num_lines - 1) // data.lines_per_page + 1

    operation.set_n_pages(data.num_pages)


def draw_page(operation: Gtk.PrintOperation, context: Gtk.PrintContext, page_nr: int, data: PrintData) -> None:
    cr = context.get_cairo_context()
    width = context.get_width()

    cr.rectangle(0, 0, width, HEADER_HEIGHT)

    cr.set_source_rgb(0.8, 0.8, 0.8)
    cr.fill_preserve()

    cr.set_source_rgb(0, 0, 0)
    cr.set_line_width(1)
    cr.stroke()

    layout = context.create_pango_layout()

    desc = Pango.FontDescription.from_string("sans 14")
    layout.set_font_description(desc)

    layout.set_text(data.resourcename, -1)
    text_width, text_height = layout.get_pixel_size()

    if text_width > width:
        layout.set_width(int(width))
        layout.set_ellipsize(Pango.EllipsizeMode.START)
        text_width, text_height = layout.get_pixel_size()

    cr.move_to((width - text_width) / 2, (HEADER_HEIGHT - text_height) / 2)
    PangoCairo.show_layout(cr, layout)

    page_str = "%d/%d" % (page_nr + 1, data.num_pages)
    layout.set_text(page_str, -1)

    layout.set_width(-1)
    text_width, text_height = layout.get_pixel_size()
    cr.move_to(width - text_width - 4, (HEADER_HEIGHT - text_height) / 2)
    PangoCairo.show_layout(cr, layout)

    layout = context.create_pango_layout()

    desc = Pango.FontDescription.from_string("monospace")
    desc.set_size(int(data.font_size * Pango.SCALE))
    layout.set_font_description(desc)

    cr.move_to(0, HEADER_HEIGHT + HEADER_GAP)
    line = page_nr * data.lines_per_page
    i = 0
    while i < data.lines_per_page and line < data.num_lines:
        layout.set_text(data.lines[line], -1)
        PangoCairo.show_layout(cr, layout)
        cr.rel_move_to(0, data.font_size)
        line += 1
        i += 1


def end_print(operation: Gtk.PrintOperation, context: Gtk.PrintContext, data: PrintData) -> None:
    data.lines = []


def do(do_widget: Gtk.Widget) -> None:
    operation = Gtk.PrintOperation()
    data = PrintData(resourcename="/sources/printing.py", font_size=12.0)

    operation.begin_print.connect(begin_print, data)
    operation.draw_page.connect(draw_page, data)
    operation.end_print.connect(end_print, data)

    operation.set_use_full_page(False)
    operation.set_unit(Gtk.Unit.POINTS)
    operation.set_embed_page_setup(True)
    # Unlike C, don't block in the print dialog's own main loop, which would hold up the rest of the demo
    # until the dialog closes. The operation keeps itself alive until it's done.
    operation.set_allow_async(True)

    settings = Gtk.PrintSettings()

    settings.set(Gtk.PRINT_SETTINGS_OUTPUT_BASENAME, "gtk-demo")
    operation.set_print_settings(settings)

    try:
        operation.run(Gtk.PrintOperationAction.PRINT_DIALOG, do_widget)
    except GLib.Error as error:
        dialog = Gtk.AlertDialog(message=error.message)
        dialog.show(do_widget)

    return None
