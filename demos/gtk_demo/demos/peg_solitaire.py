"""Peg Solitaire
#Keywords: GtkGridView, game, drag-and-drop, dnd

This demo demonstrates how to use drag-and-drop to implement peg solitaire.

"""

import os

from PyLiite4 import Gdk, GObject, Graphene, Gtk

GTK_DATADIR = "/usr/share"


class SolitairePeg(GObject.Object, Gdk.Paintable):
    """An object for the pegs that get moved around in the game.

    We implement the GdkPaintable interface for them, so we can use GtkPicture
    objects for the wholes we put the pegs into.
    """
    __gtype_name__ = "SolitairePeg"

    def __init__(self) -> None:
        super().__init__()
        self.x = 0
        self.y = 0

    # Here, we implement the functionality required by the GdkPaintable interface
    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # The snapshot function is the only function we need to implement.
        # It does the actual drawing of the paintable.
        snapshot.append_color(Gdk.RGBA(red=0.6, green=0.3, blue=0.0, alpha=1.0),
                              Graphene.Rect().init(0, 0, width, height))

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # The flags are very useful to let GTK know that this image
        # is never going to change.
        # This allows many optimizations and should therefore always
        # be set.
        return Gdk.PaintableFlags.STATIC_CONTENTS | Gdk.PaintableFlags.STATIC_SIZE

    def do_get_intrinsic_width(self) -> int:
        return 32

    def do_get_intrinsic_height(self) -> int:
        return 32

    # Add a little setter for the peg's position.
    # We want to track those so that we can check for legal moves
    # during drag-and-drop operations.
    def set_position(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def solitaire_peg_new() -> SolitairePeg:
    """And finally, we add a simple constructor."""
    return SolitairePeg()


# Helper for finding a win

# The sounds that are playing, kept until they end
playing: set[Gtk.MediaStream] = set()


def celebrate(win: bool) -> None:
    if win:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "complete.oga")
    else:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "suspend-error.oga")
    stream = Gtk.MediaFile.new_for_filename(path)
    stream.set_volume(1.0)
    stream.play()

    playing.add(stream)
    stream.notify["ended"].connect(lambda stream, pspec: playing.discard(stream))


def check_move(grid: Gtk.Grid, x: int, y: int, dx: int, dy: int) -> int:
    # We have a peg at x, y.
    # Check if we can move the peg to x + 2*dx, y + 2*dy
    image = grid.get_child_at(x + dx, y + dy)
    if not isinstance(image, Gtk.Image) or not isinstance(image.get_paintable(), SolitairePeg):
        return 0

    image = grid.get_child_at(x + 2 * dx, y + 2 * dy)
    if not isinstance(image, Gtk.Image) or isinstance(image.get_paintable(), SolitairePeg):
        return 0

    return 1


def check_for_end(grid: Gtk.Grid) -> None:
    pegs = 0
    moves = 0
    for x in range(7):
        for y in range(7):
            image = grid.get_child_at(x, y)
            if isinstance(image, Gtk.Image) and isinstance(image.get_paintable(), SolitairePeg):
                pegs += 1
                moves += check_move(grid, x, y, 1, 0)
                moves += check_move(grid, x, y, -1, 0)
                moves += check_move(grid, x, y, 0, 1)
                moves += check_move(grid, x, y, 0, -1)

            if pegs > 1 and moves > 0:
                break

    image = grid.get_child_at(3, 3)
    if pegs == 1 and isinstance(image.get_paintable(), SolitairePeg):
        celebrate(True)
    elif moves == 0:
        celebrate(False)


# DRAG AND DROP

def drag_prepare(source: Gtk.DragSource, x: float, y: float, image: Gtk.Image) -> Gdk.ContentProvider | None:
    """The user tries to start a drag operation.

    We check if the image contains a peg, and if so, we return the
    peg as the content to be dragged.
    """
    paintable = image.get_paintable()

    if not isinstance(paintable, SolitairePeg):
        return None

    value = GObject.Value(SolitairePeg, paintable)
    return Gdk.ContentProvider.new_for_value(value)


# The drags in progress and their pegs, as g_object_set_data() on the drag keeps them in C
drag_pegs: dict[Gdk.Drag, SolitairePeg] = {}


def drag_begin(source: Gtk.DragSource, drag: Gdk.Drag, image: Gtk.Image) -> None:
    """This notifies us that the drag has begun.

    We can now set up the icon and the widget for the ongoing drag.
    """
    paintable = image.get_paintable()

    # We guaranteed in the drag_prepare function above that we
    # only start a drag if a peg is available.
    # So let's make sure we did not screw that up.
    assert isinstance(paintable, SolitairePeg)

    # We use the peg as the drag icon.
    source.set_icon(paintable, -2, -2)

    # We also attach it to the drag operation as custom user data,
    # so that we can get it back later if the drag fails.
    drag_pegs[drag] = paintable

    # Because we are busy dragging the peg, we want to unset it
    # on the image.
    image.clear()


def drag_end(source: Gtk.DragSource, drag: Gdk.Drag, delete_data: bool, image: Gtk.Image) -> None:
    """This is called once a drag operation has ended (successfully or not).

    We want to undo what we did in drag_begin() above and react
    to a potential move of the peg.
    """
    peg = drag_pegs.pop(drag, None)

    # If the drag was successful, we should now delete the peg.
    # We did this in drag_begin() above to prepare for the drag, so
    # there's no need to do anything anymore.
    if delete_data:
        return

    # However, if the drag did not succeed, we need to undo what
    # we did in drag_begin() and reinsert the peg here.
    # Because we used it as the drag data
    image.set_from_paintable(peg)


def drop_accept(target: Gtk.DropTarget, drop: Gdk.Drop, image: Gtk.Image) -> bool:
    """Whenever a new drop operation starts, we need to check if we can accept it.

    The default check unfortunately is not good enough, because it only
    checks the data type. But we also need to check if our image can
    even accept data.
    """
    # First, check the drop is actually trying to drop a peg
    if not drop.get_formats().contain_gtype(SolitairePeg.__gtype__):
        return False

    # If the image already contains a peg, we cannot accept another one
    if isinstance(image.get_paintable(), SolitairePeg):
        return False

    return True


def drop_drop(target: Gtk.DropTarget, value: SolitairePeg, x: float, y: float, image: Gtk.Image) -> bool:
    grid = image.get_parent()
    # The value contains the data in the type we demanded.
    # We demanded a SolitairePeg, so that's what we get.
    peg = value

    # Make sure this was a legal move.
    # First, figure out the image's position in the grid.
    image_x, image_y, _, _ = grid.query_child(image)

    # If the peg was not moved 2 spaces horizontally or vertically,
    # this was not a valid jump. Reject it.
    if not ((abs(image_x - peg.x) == 2 and image_y == peg.y)
            or (abs(image_y - peg.y) == 2 and image_x == peg.x)):
        return False

    # Get the widget that was jumped over
    jumped = grid.get_child_at((image_x + peg.x) // 2, (image_y + peg.y) // 2)
    # If the jumped widget does not have a peg in it, this move
    # isn't valid.
    if not isinstance(jumped.get_paintable(), SolitairePeg):
        return False

    # Finally, we know it's a legal move.

    # Clear the peg of the jumped-over image
    jumped.clear()

    # Add the peg to this image
    peg.set_position(image_x, image_y)
    image.set_from_paintable(peg)

    # Maybe we have something to celebrate
    check_for_end(grid)

    # Success!
    return True


def remove_provider(window: Gtk.Window) -> None:
    provider = providers.pop(window, None)
    if provider is not None:
        Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), provider)


# The CSS providers of the windows, as g_object_set_data_full() keeps them in C
providers: dict[Gtk.Window, Gtk.CssProvider] = {}


def create_board(window: Gtk.Window) -> None:
    css = (".solitaire-field {"
           "  border: 1px solid lightgray;"
           "}")

    provider = Gtk.CssProvider()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

    grid = Gtk.Grid()
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_valign(Gtk.Align.CENTER)
    grid.set_row_spacing(6)
    grid.set_column_spacing(6)
    grid.set_row_homogeneous(True)
    grid.set_column_homogeneous(True)
    window.set_child(grid)

    for x in range(7):
        for y in range(7):
            if (x < 2 or x >= 5) and (y < 2 or y >= 5):
                continue

            image = Gtk.Image()
            image.add_css_class("solitaire-field")
            image.set_icon_size(Gtk.IconSize.LARGE)
            if x != 3 or y != 3:
                peg = solitaire_peg_new()
                peg.set_position(x, y)
                image.set_from_paintable(peg)

            grid.attach(image, x, y, 1, 1)

            # Set up the drag source.
            # This is rather straightforward: Set the supported actions
            # (in our case, pegs can only be moved) and connect all the
            # relevant signals.
            # And because all drag'n'drop handling is done via event controllers,
            # we need to add the controller to the widget.
            source = Gtk.DragSource()
            source.set_actions(Gdk.DragAction.MOVE)
            source.prepare.connect(drag_prepare, image)
            source.drag_begin.connect(drag_begin, image)
            source.drag_end.connect(drag_end, image)
            image.add_controller(source)

            # Set up the drop target.
            # This is more involved, because the game logic goes here.

            # First we specify the data we accept: pegs.
            # And we only want moves.
            target = Gtk.DropTarget.new(SolitairePeg.__gtype__, Gdk.DragAction.MOVE)
            # Then we connect our signals.
            target.accept.connect(drop_accept, image)
            target.drop.connect(drop_drop, image)
            # Finally, like above, we add it to the widget.
            image.add_controller(target)

    remove_provider(window)
    providers[window] = provider


def restart_game(button: Gtk.Button, window: Gtk.Window) -> None:
    create_board(window)


window: Gtk.Window | None = None


def window_destroyed(win: Gtk.Window) -> None:
    global window
    remove_provider(win)
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()

        restart = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        restart.clicked.connect(restart_game, window)

        header = Gtk.HeaderBar()
        header.pack_start(restart)
        window.set_display(do_widget.get_display())
        window.set_title("Peg Solitaire")
        window.set_titlebar(header)
        window.set_default_size(400, 300)
        window.destroy.connect(window_destroyed)

        create_board(window)

    result = window
    if not result.get_visible():
        result.set_visible(True)
    else:
        result.destroy()

    return result
