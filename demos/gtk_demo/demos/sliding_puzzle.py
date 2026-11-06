"""Sliding Puzzle
#Keywords: GdkPaintable, GdkGesture, GtkShortcutController, game

This demo demonstrates how to use gestures and paintables to create a
small sliding puzzle game.
"""

import os

from PyLiite4 import Gdk, GLib, GObject, Gtk

from .puzzlepiece import gtk_puzzle_piece_new
from .paintable_animated import gtk_nuclear_animation_new

GTK_DATADIR = "/usr/share"

window: Gtk.Window | None = None
frame: Gtk.AspectFrame | None = None
choices: Gtk.FlowBox | None = None
size_spin: Gtk.SpinButton | None = None
puzzle: Gdk.Paintable | None = None

solved = True
width = 3
height = 3
pos_x = 0
pos_y = 0

# The sounds that are playing, kept until they end.
playing: set[Gtk.MediaStream] = set()


def ended(stream: Gtk.MediaStream, pspec: GObject.ParamSpec) -> None:
    playing.discard(stream)


def celebrate(win: bool) -> None:
    if win:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "complete.oga")
    else:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "suspend-error.oga")
    stream = Gtk.MediaFile.new_for_filename(path)
    stream.set_volume(1.0)
    stream.play()

    playing.add(stream)
    stream.notify["ended"].connect(ended)


def move_puzzle(grid: Gtk.Grid, dx: int, dy: int) -> bool:
    global pos_x, pos_y

    # A solved puzzle doesn't move.
    if solved:
        return False

    # Nor does a move that would leave the grid.
    if ((dx < 0 and pos_x < -dx)
            or dx + pos_x >= width
            or (dy < 0 and pos_y < -dy)
            or dy + pos_y >= height):
        return False

    next_x = pos_x + dx
    next_y = pos_y + dy

    # The piece moves from the next image into the empty current one.
    pos = grid.get_child_at(pos_x, pos_y)
    next = grid.get_child_at(next_x, next_y)

    piece = next.get_paintable()
    pos.set_paintable(piece)
    next.set_paintable(None)

    pos_x = next_x
    pos_y = next_y

    return True


def shuffle_puzzle(grid: Gtk.Grid) -> None:
    # The number of random moves.
    n_steps = width * height * 50

    for i in range(n_steps):
        direction = GLib.random_int_range(0, 4)
        if direction == 0:
            move_puzzle(grid, -1, 0)
        elif direction == 1:
            move_puzzle(grid, 0, -1)
        elif direction == 2:
            move_puzzle(grid, 1, 0)
        elif direction == 3:
            move_puzzle(grid, 0, 1)
        else:
            raise AssertionError("not reached")


def check_solved(grid: Gtk.Grid) -> bool:
    global solved

    # A puzzle that is already solved needs no check.
    if solved:
        return True

    # The puzzle can't be solved unless the empty cell is in the bottom right.
    if pos_x != width - 1 or pos_y != height - 1:
        return False

    # Every piece has to be in its right position.
    for y in range(height):
        for x in range(width):
            picture = grid.get_child_at(x, y)
            piece = picture.get_paintable()

            # The empty cell has no piece to check.
            if piece is None:
                continue

            if piece.get_x() != x or piece.get_y() != y:
                return False

    solved = True

    # Filling the empty cell shows that the puzzle is done.
    picture = grid.get_child_at(0, 0)
    piece = picture.get_paintable()

    piece = gtk_puzzle_piece_new(piece.get_puzzle(), pos_x, pos_y, width, height)
    picture = grid.get_child_at(pos_x, pos_y)
    picture.set_paintable(piece)

    celebrate(True)

    return True


def puzzle_key_pressed(grid: Gtk.Widget, args: GLib.Variant | None) -> bool:
    dx, dy = args.unpack()

    if not move_puzzle(grid, dx, dy):
        # The error sound. The key still counts as handled, even though the puzzle didn't change.
        grid.error_bell()
        return True

    check_solved(grid)

    return True


def puzzle_button_pressed(gesture: Gtk.GestureClick, n_press: int, x: float, y: float, grid: Gtk.Grid) -> None:
    child = grid.pick(x, y, Gtk.PickFlags.DEFAULT)

    if child is None:
        grid.error_bell()
        return

    l, t, _, _ = grid.query_child(child)

    if l == pos_x and t == pos_y:
        grid.error_bell()
    elif l == pos_x:
        pos = pos_y
        for i in range(t, pos):
            if not move_puzzle(grid, 0, -1):
                grid.error_bell()
        for i in range(pos, t):
            if not move_puzzle(grid, 0, 1):
                grid.error_bell()
    elif t == pos_y:
        pos = pos_x
        for i in range(l, pos):
            if not move_puzzle(grid, -1, 0):
                grid.error_bell()
        for i in range(pos, l):
            if not move_puzzle(grid, 1, 0):
                grid.error_bell()
    else:
        grid.error_bell()

    check_solved(grid)


def add_move_binding(controller: Gtk.ShortcutController, keyval: int, kp_keyval: int, dx: int, dy: int) -> None:
    shortcut = Gtk.Shortcut(trigger=Gtk.AlternativeTrigger(first=Gtk.KeyvalTrigger(keyval=keyval, modifiers=0),
                                                           second=Gtk.KeyvalTrigger(keyval=kp_keyval, modifiers=0)),
                            action=Gtk.CallbackAction.new(puzzle_key_pressed),
                            arguments=GLib.Variant("(ii)", (dx, dy)))
    controller.add_shortcut(shortcut)


def start_puzzle(paintable: Gdk.Paintable) -> None:
    global solved, pos_x, pos_y

    grid = Gtk.Grid()
    grid.set_focusable(True)
    frame.set_child(grid)
    aspect_ratio = paintable.get_intrinsic_aspect_ratio()
    if aspect_ratio == 0.0:
        aspect_ratio = 1.0
    frame.set_ratio(aspect_ratio)
    frame.set_obey_child(False)

    # Shortcuts, so the arrow keys move the puzzle.
    controller = Gtk.ShortcutController()
    controller.set_scope(Gtk.ShortcutScope.LOCAL)
    add_move_binding(controller, Gdk.KEY_Left, Gdk.KEY_KP_Left, -1, 0)
    add_move_binding(controller, Gdk.KEY_Right, Gdk.KEY_KP_Right, 1, 0)
    add_move_binding(controller, Gdk.KEY_Up, Gdk.KEY_KP_Up, 0, -1)
    add_move_binding(controller, Gdk.KEY_Down, Gdk.KEY_KP_Down, 0, 1)
    grid.add_controller(controller)

    controller = Gtk.GestureClick()
    controller.pressed.connect(puzzle_button_pressed, grid)
    grid.add_controller(controller)

    # The cells all have the same size.
    grid.set_row_homogeneous(True)
    grid.set_column_homogeneous(True)

    solved = False
    pos_x = width - 1
    pos_y = height - 1

    # A picture for every cell.
    for y in range(height):
        for x in range(width):
            # The empty cell, where pieces slide in, shows nothing.
            if x == pos_x and y == pos_y:
                piece = None
            else:
                piece = gtk_puzzle_piece_new(paintable, x, y, width, height)
            picture = Gtk.Picture.new_for_paintable(piece)
            picture.set_content_fit(Gtk.ContentFit.FILL)
            grid.attach(picture, x, y, 1, 1)

    shuffle_puzzle(grid)


def reshuffle(button: Gtk.Button) -> None:
    if solved:
        start_puzzle(puzzle)
        grid = frame.get_child()
    else:
        grid = frame.get_child()
        shuffle_puzzle(grid)
    grid.grab_focus()


def reconfigure(button: Gtk.Button) -> None:
    global width, height, puzzle

    width = height = size_spin.get_value_as_int()

    selected = choices.get_selected_children()
    if not selected:
        child = choices.get_first_child()
    else:
        child = selected[0]

    image = child.get_child()
    puzzle = image.get_paintable()

    start_puzzle(puzzle)
    popover = size_spin.get_ancestor(Gtk.Popover)
    popover.popdown()
    grid = frame.get_child()
    grid.grab_focus()


def add_choice(container: Gtk.FlowBox, paintable: Gdk.Paintable) -> None:
    icon = Gtk.Image.new_from_paintable(paintable)
    icon.set_icon_size(Gtk.IconSize.LARGE)

    container.insert(icon, -1)


def widget_destroyed(widget: Gtk.Widget) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window, frame, choices, size_spin, puzzle

    if window is None:
        puzzle = Gdk.Texture.new_from_resource("/sliding_puzzle/portland-rose.jpg")

        tweaks = Gtk.Grid()
        tweaks.set_row_spacing(10)
        tweaks.set_column_spacing(10)
        tweaks.set_margin_start(10)
        tweaks.set_margin_end(10)
        tweaks.set_margin_top(10)
        tweaks.set_margin_bottom(10)

        choices = Gtk.FlowBox()
        choices.add_css_class("view")
        add_choice(choices, puzzle)
        add_choice(choices, gtk_nuclear_animation_new(True))
        media = Gtk.MediaFile.new_for_resource("/images/gtk-logo.webm")
        media.set_loop(True)
        media.set_muted(True)
        media.play()
        add_choice(choices, media)
        sw = Gtk.ScrolledWindow()
        sw.set_child(choices)
        tweaks.attach(sw, 0, 0, 2, 1)

        label = Gtk.Label(label="Size")
        label.set_xalign(0.0)
        tweaks.attach(label, 0, 1, 1, 1)
        size_spin = Gtk.SpinButton.new_with_range(2, 10, 1)
        size_spin.set_value(width)
        tweaks.attach(size_spin, 1, 1, 1, 1)

        apply = Gtk.Button(label="Apply")
        apply.set_halign(Gtk.Align.END)
        tweaks.attach(apply, 1, 2, 1, 1)
        apply.clicked.connect(reconfigure)

        popover = Gtk.Popover()
        popover.set_child(tweaks)

        tweak = Gtk.MenuButton()
        tweak.set_popover(popover)
        tweak.set_icon_name("open-menu-symbolic")

        restart = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        restart.clicked.connect(reshuffle)

        header = Gtk.HeaderBar()
        header.pack_start(restart)
        header.pack_end(tweak)
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Sliding Puzzle")
        window.set_titlebar(header)
        window.set_default_size(400, 300)
        window.destroy.connect(widget_destroyed)

        frame = Gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=puzzle.get_intrinsic_aspect_ratio(), obey_child=False)
        window.set_child(frame)

        start_puzzle(puzzle)

    result = window
    if not result.get_visible():
        result.set_visible(True)
    else:
        result.destroy()

    return result

