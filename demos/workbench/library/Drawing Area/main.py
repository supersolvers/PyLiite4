import math

from PyLiite4 import Gtk, cairo

from demos.workbench import workbench

drawing_area: Gtk.DrawingArea = workbench.builder.get_object("drawing_area")
scale_rotate: Gtk.Scale = workbench.builder.get_object("scale")

triangle = [[100, 100], [0, -100], [-100, 100]]
angle = 0


def draw(_self: Gtk.DrawingArea, cr: cairo.Context, _width: int, _height: int) -> None:
    # Draw triangle in context
    cr.translate(150, 150)
    cr.rotate(angle)

    cr.move_to(triangle[2][0], triangle[2][1])
    for vertex in triangle:
        cr.line_to(vertex[0], vertex[1])

    cr.set_source_rgba(1, 0, 1, 1)
    cr.stroke()


def on_angle_changed(_self: Gtk.Scale) -> None:
    global angle
    angle = math.radians(scale_rotate.get_value())

    drawing_area.queue_draw()


drawing_area.set_draw_func(draw)
scale_rotate.value_changed.connect(on_angle_changed)

# https://www.cairographics.org/tutorial/
