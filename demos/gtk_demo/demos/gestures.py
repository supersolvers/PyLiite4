"""Gestures
#Keywords: GtkGesture

Perform gestures on touchscreens and other input devices. This
demo reacts to long presses and swipes from all devices, plus
multi-touch rotate and zoom gestures.
"""

import math

from PyLiite4 import Gdk, Gtk, cairo

rotate: Gtk.GestureRotate | None = None
zoom: Gtk.GestureZoom | None = None
swipe_x = 0.0
swipe_y = 0.0
long_pressed = False


def touchpad_swipe_gesture_begin(gesture: Gtk.Gesture, sequence: Gdk.EventSequence | None,
                                 widget: Gtk.Widget) -> bool:
    # Touchscreen events, which come with a sequence, are denied here.
    if sequence is not None:
        gesture.set_state(Gtk.EventSequenceState.DENIED)
    return sequence is None


def swipe_gesture_swept(gesture: Gtk.GestureSwipe, velocity_x: float, velocity_y: float,
                        widget: Gtk.Widget) -> None:
    global swipe_x, swipe_y
    swipe_x = velocity_x / 10
    swipe_y = velocity_y / 10
    widget.queue_draw()


def long_press_gesture_pressed(gesture: Gtk.GestureLongPress, x: float, y: float, widget: Gtk.Widget) -> None:
    global long_pressed
    long_pressed = True
    widget.queue_draw()


def long_press_gesture_end(gesture: Gtk.Gesture, sequence: Gdk.EventSequence | None, widget: Gtk.Widget) -> None:
    global long_pressed
    long_pressed = False
    widget.queue_draw()


def rotation_angle_changed(gesture: Gtk.GestureRotate, angle: float, delta: float, widget: Gtk.Widget) -> None:
    widget.queue_draw()


def zoom_scale_changed(gesture: Gtk.GestureZoom, scale: float, widget: Gtk.Widget) -> None:
    widget.queue_draw()


def drawing_area_draw(area: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    if swipe_x != 0 or swipe_y != 0:
        cr.save()
        cr.set_line_width(6)
        cr.move_to(width // 2, height // 2)
        cr.rel_line_to(swipe_x, swipe_y)
        cr.set_source_rgba(1, 0, 0, 0.5)
        cr.stroke()
        cr.restore()

    if rotate.is_recognized() or zoom.is_recognized():
        _, x_center, y_center = zoom.get_bounding_box_center()

        matrix = cr.get_matrix()
        matrix.translate(x_center, y_center)

        cr.save()

        angle = rotate.get_angle_delta()
        matrix.rotate(angle)

        scale = zoom.get_scale_delta()
        matrix.scale(scale, scale)

        cr.set_matrix(matrix)
        cr.rectangle(-100, -100, 200, 200)

        pat = cairo.LinearGradient(-100, 0, 200, 0)
        pat.add_color_stop_rgb(0, 0, 0, 1)
        pat.add_color_stop_rgb(1, 1, 0, 0)
        cr.set_source(pat)
        cr.fill()

        cr.restore()

    if long_pressed:
        cr.save()
        cr.arc(width // 2, height // 2, 50, 0, 2 * math.pi)

        cr.set_source_rgba(0, 1, 0, 0.5)
        cr.stroke()

        cr.restore()


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, rotate, zoom
    if window is None:
        window = Gtk.Window()
        window.set_default_size(400, 400)
        window.set_title("Gestures")
        window.close_request.connect(close_request)

        drawing_area = Gtk.DrawingArea()
        window.set_child(drawing_area)

        drawing_area.set_draw_func(drawing_area_draw)

        # Swipe
        gesture = Gtk.GestureSwipe()
        gesture.swipe.connect(swipe_gesture_swept, drawing_area)
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drawing_area.add_controller(gesture)

        # Three-finger swipe for touchpads
        gesture = Gtk.GestureSwipe(n_points=3)
        gesture.begin.connect(touchpad_swipe_gesture_begin, drawing_area)
        gesture.swipe.connect(swipe_gesture_swept, drawing_area)
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drawing_area.add_controller(gesture)

        # Long press
        gesture = Gtk.GestureLongPress()
        gesture.pressed.connect(long_press_gesture_pressed, drawing_area)
        gesture.end.connect(long_press_gesture_end, drawing_area)
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drawing_area.add_controller(gesture)

        # Rotate
        rotate = gesture = Gtk.GestureRotate()
        gesture.angle_changed.connect(rotation_angle_changed, drawing_area)
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drawing_area.add_controller(gesture)

        # Zoom
        zoom = gesture = Gtk.GestureZoom()
        gesture.scale_changed.connect(zoom_scale_changed, drawing_area)
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drawing_area.add_controller(gesture)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
