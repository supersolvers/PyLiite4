# Workbench renders the SVG with librsvg, through Rsvg.Handle. PyLiite4 doesn't provide the Rsvg namespace, so this
# port uses GdkPixbuf's SVG loader, which is librsvg too, to render the image at the size of the drawing area.
from PyLiite4 import Gdk, GdkPixbuf, Gio, Gtk, cairo

from demos.workbench import workbench

drawing_area: Gtk.DrawingArea = workbench.builder.get_object("drawing_area")
svg = Gio.File.new_for_uri(workbench.resolve("image.svg")).get_path()

_format, width, height = GdkPixbuf.Pixbuf.get_file_info(svg)
print("SVG intrisic size", {"width": width, "height": height})


def draw(_self: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    print("drawing SVG at", {"width": width, "height": height})
    # Like Rsvg.Handle.render_document(), fit the document in the viewport, keeping its aspect ratio
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(svg, width, height, True)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, (width - pixbuf.get_width()) / 2, (height - pixbuf.get_height()) / 2)
    cr.paint()


drawing_area.set_draw_func(draw)
