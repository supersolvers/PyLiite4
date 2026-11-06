"""Lists/Minesweeper
#Keywords: GtkGridView, GListModel, game

This demo shows how to develop a user interface for small game using a
grid view.

It demonstrates how to use the activate signal and single-press behavior
to implement rather different interaction behavior to a typical list.
"""

import os
import random

from PyLiite4 import Gio, GLib, GObject, Gtk

# The cell object


class SweeperCell(GObject.Object):
    """An object that holds the data for a cell in the game."""

    __gtype_name__ = "SweeperCell"

    minecount_labels = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

    def __init__(self) -> None:
        super().__init__()
        self.is_mine = False
        self.is_visible = False
        self.neighbor_mines = 0

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE, nick="label",
                      blurb="label to display for this row")
    def label(self) -> str:
        if not self.is_visible:
            return "?"

        if self.is_mine:
            return "💣"

        return self.minecount_labels[self.neighbor_mines]

    def reveal(self) -> None:
        if self.is_visible:
            return

        self.is_visible = True

        self.notify("label")


# The board object


class SweeperGame(GObject.Object, Gio.ListModel):
    """An object that holds the data for the game."""

    __gtype_name__ = "SweeperGame"

    def __init__(self) -> None:
        super().__init__()
        self.cells: list[SweeperCell] = []
        self._width = 0
        self._height = 0
        self._playing = False
        self._win = False

        self.new_game(8, 8, 10)

    @GObject.Property(type=GObject.TYPE_UINT, minimum=1, maximum=GLib.MAXUINT, default=8,
                      flags=GObject.ParamFlags.READABLE,
                      nick="height", blurb="height of the game grid")
    def height(self) -> int:
        return self._height

    @GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READABLE, nick="playing",
                      blurb="if the game is still going on")
    def playing(self) -> bool:
        return self._playing

    @GObject.Property(type=GObject.TYPE_UINT, minimum=1, maximum=GLib.MAXUINT, default=8,
                      flags=GObject.ParamFlags.READABLE,
                      nick="width", blurb="width of the game grid")
    def width(self) -> int:
        return self._width

    @GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READABLE, nick="win",
                      blurb="if the game was won")
    def win(self) -> bool:
        return self._win

    def do_get_item_type(self) -> GObject.GType:
        return SweeperGame.__gtype__

    def do_get_n_items(self) -> int:
        return self._width * self._height

    def do_get_item(self, position: int) -> SweeperCell | None:
        return self.cells[position] if position < len(self.cells) else None

    def reset_board(self, width: int, height: int) -> None:
        self.cells = [SweeperCell() for _ in range(width * height)]

        if self._width != width:
            self._width = width
            self.notify("width")
        if self._height != height:
            self._height = height
            self.notify("height")
        if not self._playing:
            self._playing = True
            self.notify("playing")
        if self._win:
            self._win = False
            self.notify("win")

    def place_mines(self, n_mines: int) -> None:
        for _ in range(n_mines):
            cell = self.cells[random.randrange(len(self.cells))]
            while cell.is_mine:
                cell = self.cells[random.randrange(len(self.cells))]

            cell.is_mine = True

    def get_cell(self, x: int, y: int) -> SweeperCell:
        return self.cells[y * self._width + x]

    def count_neighbor_mines(self, width: int, height: int) -> None:
        for y in range(height):
            for x in range(width):
                cell = self.get_cell(x, y)

                for y2 in range(max(1, y) - 1, min(height, y + 2)):
                    for x2 in range(max(1, x) - 1, min(width, x + 2)):
                        other = self.get_cell(x2, y2)

                        if other.is_mine:
                            cell.neighbor_mines += 1

    def new_game(self, width: int, height: int, n_mines: int) -> None:
        assert n_mines <= width * height

        n_items_before = self._width * self._height

        self.freeze_notify()

        self.reset_board(width, height)
        self.place_mines(n_mines)
        self.count_neighbor_mines(width, height)

        self.items_changed(0, n_items_before, width * height)

        self.thaw_notify()

    def end(self, win: bool) -> None:
        if self._playing:
            self._playing = False
            self.notify("playing")
            celebrate(win)

        if self._win != win:
            self._win = win
            self.notify("win")

    def check_finished(self) -> None:
        if not self._playing:
            return

        for cell in self.cells:
            # There's still a non-revealed cell that isn't a mine.
            if not cell.is_visible and not cell.is_mine:
                return

        self.end(True)

    def reveal_cell(self, position: int) -> None:
        if not self._playing:
            return

        cell = self.cells[position]
        cell.reveal()

        if cell.is_mine:
            self.end(False)

        self.check_finished()


# GTK_DATADIR in C: the data directory GTK was installed into.
GTK_DATADIR = next((path for path in GLib.get_system_data_dirs()
                    if os.path.isdir(os.path.join(path, "sounds", "freedesktop"))), "/usr/share")

# The streams that are playing; C keeps them alive with a reference until they end.
playing_streams: set[Gtk.MediaStream] = set()


def celebrate(win: bool) -> None:
    if win:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "complete.oga")
    else:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "suspend-error.oga")
    stream = Gtk.MediaFile.new_for_filename(path)
    stream.set_volume(1.0)
    stream.play()
    playing_streams.add(stream)
    stream.notify["ended"].connect(lambda stream, _pspec: playing_streams.discard(stream))


def minesweeper_cell_clicked_cb(gridview: Gtk.GridView, pos: int, game: SweeperGame) -> None:
    game.reveal_cell(pos)


def minesweeper_new_game_cb(button: Gtk.Button, game: SweeperGame) -> None:
    game.new_game(8, 8, 10)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    if window is None:
        builder = Gtk.Builder({"minesweeper_cell_clicked_cb": minesweeper_cell_clicked_cb,
                               "minesweeper_new_game_cb": minesweeper_new_game_cb})
        builder.add_from_resource("/listview_minesweeper/listview_minesweeper.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
    return window
