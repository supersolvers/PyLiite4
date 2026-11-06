"""OpenGL/Shadertoy
#Keywords: GtkGLArea

Generate pixels using a custom fragment shader.

The names of the uniforms are compatible with the shaders on shadertoy.com, so
many of the shaders there work here too.
"""

from PyLiite4 import Gio, Gtk

from .gtkshadertoy import GtkShadertoy, gtk_shadertoy_new

demo_window: Gtk.Window | None = None
shadertoy: GtkShadertoy | None = None
textbuffer: Gtk.TextBuffer | None = None


def run() -> None:
    start, end = textbuffer.get_bounds()
    text = textbuffer.get_text(start, end, False)

    shadertoy.set_image_shader(text)


def run_clicked_cb(button: Gtk.Button) -> None:
    run()


def load_clicked_cb(button: Gtk.Button, path: str) -> None:
    initial_shader = Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE)
    textbuffer.set_text(initial_shader.get_data().decode(), -1)

    run()


def clear_clicked_cb(button: Gtk.Button) -> None:
    textbuffer.set_text("", 0)


def close_window(widget: Gtk.Widget) -> None:
    global demo_window, shadertoy, textbuffer
    demo_window = None
    shadertoy = None
    textbuffer = None


def new_shadertoy(path: str) -> GtkShadertoy:
    toy = gtk_shadertoy_new()
    shader = Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE)
    toy.set_image_shader(shader.get_data().decode())

    return toy


def new_button(path: str) -> Gtk.Button:
    button = Gtk.Button()
    button.clicked.connect(load_clicked_cb, path)

    toy = new_shadertoy(path)
    toy.set_size_request(64, 36)
    button.set_child(toy)

    return button


def create_shadertoy_window(do_widget: Gtk.Widget) -> Gtk.Window:
    global shadertoy, textbuffer

    window = Gtk.Window()
    window.set_display(do_widget.get_display())
    window.set_title("Shadertoy")
    window.set_default_size(690, 740)
    window.destroy.connect(close_window)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_spacing(6)
    window.set_child(box)

    aspect = Gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=1.77777, obey_child=False)
    aspect.set_hexpand(True)
    aspect.set_vexpand(True)
    box.append(aspect)

    shadertoy = new_shadertoy("/shadertoy/alienplanet.glsl")
    aspect.set_child(Gtk.GraphicsOffload(child=shadertoy))

    sw = Gtk.ScrolledWindow()
    sw.set_min_content_height(250)
    sw.set_has_frame(True)
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.set_hexpand(True)
    box.append(sw)

    textview = Gtk.TextView()
    textview.set_monospace(True)
    textview.set_properties(left_margin=20, right_margin=20, top_margin=20, bottom_margin=20)
    sw.set_child(textview)

    textbuffer = textview.get_buffer()
    textbuffer.set_text(shadertoy.get_image_shader(), -1)

    centerbox = Gtk.CenterBox()
    box.append(centerbox)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    hbox.set_spacing(6)
    centerbox.set_start_widget(hbox)

    button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
    button.set_tooltip_text("Restart the demo")
    button.set_valign(Gtk.Align.CENTER)
    button.clicked.connect(run_clicked_cb)
    hbox.append(button)

    button = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
    button.set_tooltip_text("Clear the text view")
    button.set_valign(Gtk.Align.CENTER)
    button.clicked.connect(clear_clicked_cb)
    hbox.append(button)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    hbox.set_spacing(6)
    centerbox.set_end_widget(hbox)

    button = new_button("/shadertoy/alienplanet.glsl")
    hbox.append(button)

    button = new_button("/shadertoy/mandelbrot.glsl")
    hbox.append(button)

    button = new_button("/shadertoy/neon.glsl")
    hbox.append(button)

    button = new_button("/shadertoy/cogs.glsl")
    hbox.append(button)

    button = new_button("/shadertoy/glowingstars.glsl")
    hbox.append(button)

    return window


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global demo_window

    if demo_window is None:
        demo_window = create_shadertoy_window(do_widget)

    window = demo_window
    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
