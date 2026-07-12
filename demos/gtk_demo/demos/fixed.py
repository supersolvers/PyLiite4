"""Fixed Layout / Cube
#Keywords: GtkLayoutManager

GtkFixed is a container that allows placing and transforming
widgets manually.

This demo uses a GtkFixed to create a cube out of child widgets.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Graphene, Gsk, Gtk

# This enumeration determines the paint order
FACE_BACK = 0
FACE_LEFT = 1
FACE_BOTTOM = 2
FACE_RIGHT = 3
FACE_TOP = 4
FACE_FRONT = 5
N_FACES = 6


class Face:
    def __init__(self, css_class: str) -> None:
        self.face: Gtk.Widget | None = None
        self.css_class = css_class


# Map face widgets to CSS classes
faces = [Face("")] * N_FACES
faces[FACE_BACK] = Face("back")
faces[FACE_LEFT] = Face("left")
faces[FACE_RIGHT] = Face("right")
faces[FACE_TOP] = Face("top")
faces[FACE_BOTTOM] = Face("bottom")
faces[FACE_FRONT] = Face("front")


def create_faces() -> Gtk.Widget:
    fixed = Gtk.Fixed()
    face_size = 200

    fixed.set_overflow(Gtk.Overflow.VISIBLE)

    w = face_size / 2.
    h = face_size / 2.
    d = face_size / 2.
    p = face_size * 3.

    for i in range(N_FACES):
        # Add a face
        faces[i].face = Gtk.Frame()
        faces[i].face.set_size_request(face_size, face_size)
        faces[i].face.add_css_class(faces[i].css_class)
        fixed.put(faces[i].face, 0, 0)

        # Set up the transformation for each face
        transform = Gsk.Transform.new().translate(Graphene.Point().init(w, h))
        transform = transform.perspective(p)
        transform = transform.rotate_3d(-30., Graphene.Vec3.x_axis())
        transform = transform.rotate_3d(135., Graphene.Vec3.y_axis())
        transform = transform.translate_3d(Graphene.Point3D().init(0, 0, -face_size / 6.))

        if i == FACE_FRONT:
            transform = transform.rotate_3d(0., Graphene.Vec3.y_axis())
        elif i == FACE_BACK:
            transform = transform.rotate_3d(-180., Graphene.Vec3.y_axis())
        elif i == FACE_RIGHT:
            transform = transform.rotate_3d(90., Graphene.Vec3.y_axis())
        elif i == FACE_LEFT:
            transform = transform.rotate_3d(-90., Graphene.Vec3.y_axis())
        elif i == FACE_TOP:
            transform = transform.rotate_3d(90., Graphene.Vec3.x_axis())
        elif i == FACE_BOTTOM:
            transform = transform.rotate_3d(-90., Graphene.Vec3.x_axis())

        transform = transform.translate_3d(Graphene.Point3D().init(0, 0, d))
        transform = transform.translate_3d(Graphene.Point3D().init(-w, -h, 0))

        fixed.set_child_transform(faces[i].face, transform)

    return fixed


# The window, held weakly: GTK keeps a window until it is destroyed.
demo_window: Callable[[], Gtk.Window | None] = lambda: None
provider: Gtk.CssProvider | None = None


def close_window(widget: Gtk.Window) -> None:
    global provider

    # Reset the state
    for i in range(N_FACES):
        faces[i].face = None

    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), provider)
    provider = None


def create_demo_window(do_widget: Gtk.Widget) -> Gtk.Window:
    global provider

    window = Gtk.Window()
    window.set_display(do_widget.get_display())
    window.set_title("Fixed Layout ‐ Cube")
    window.set_default_size(600, 400)
    window.destroy.connect(close_window)

    sw = Gtk.ScrolledWindow()
    window.set_child(sw)

    fixed = Gtk.Fixed()
    sw.set_child(fixed)
    fixed.set_halign(Gtk.Align.CENTER)
    fixed.set_valign(Gtk.Align.CENTER)

    cube = create_faces()
    fixed.put(cube, 0, 0)
    fixed.set_overflow(Gtk.Overflow.VISIBLE)

    provider = Gtk.CssProvider()
    provider.load_from_resource("/fixed/fixed.css")
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

    return window


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global demo_window

    window = demo_window()
    if window is None:
        window = create_demo_window(do_widget)
        demo_window = window.weak_ref()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
