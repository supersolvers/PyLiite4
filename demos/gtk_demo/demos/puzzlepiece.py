"""Paintable/A simple paintable

GdkPaintable is an interface used by GTK for drawings of any sort
that do not require layouting or positioning.

This demo code gives a simple example on how a paintable can
be created.

Paintables can be used in many places inside GTK widgets, but the
most common usage is inside GtkImage and that's what we're going
to do here.
"""

from PyLiite4 import Gdk, GObject, Graphene


class GtkPuzzlePiece(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkPuzzlePiece"

    def __init__(self) -> None:
        super().__init__()
        self.puzzle: Gdk.Paintable | None = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

    # Draws the puzzle piece: a rectangular cutout of the puzzle, with the rest clipped away.
    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        snapshot.push_clip(Graphene.Rect().init(0, 0, width, height))

        snapshot.translate(Graphene.Point().init(- width * self.x, - height * self.y))
        self.puzzle.snapshot(snapshot, width * self.width, height * self.height)

        snapshot.pop()

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # The flags are the puzzle's: if the puzzle changes in some way, so do the pieces.
        return self.puzzle.get_flags()

    def do_get_intrinsic_width(self) -> int:
        # The width is relative to the puzzle's, rounded up. This works even when the puzzle has no width, since a
        # 0 stays 0.
        return (self.puzzle.get_intrinsic_width() + self.width - 1) // self.width

    def do_get_intrinsic_height(self) -> int:
        # The same as the width.
        return (self.puzzle.get_intrinsic_height() + self.height - 1) // self.height

    def do_get_intrinsic_aspect_ratio(self) -> float:
        # The aspect ratio is relative to the puzzle's. This also works when the puzzle has no aspect ratio, since a
        # 0 stays 0.
        return self.puzzle.get_intrinsic_aspect_ratio() * self.height / self.width

    def puzzle_invalidate_contents(self, puzzle: Gdk.Paintable) -> None:
        self.invalidate_contents()

    def puzzle_invalidate_size(self, puzzle: Gdk.Paintable) -> None:
        self.invalidate_size()

    # Accessors, for other code to inspect the puzzle pieces
    def get_puzzle(self) -> Gdk.Paintable:
        return self.puzzle

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y


def gtk_puzzle_piece_new(puzzle: Gdk.Paintable, x: int, y: int, width: int, height: int) -> GtkPuzzlePiece:
    """And finally, we add a constructor. The other examples use it."""
    # Sanity checks, which catch a caller's mistakes early.
    assert isinstance(puzzle, Gdk.Paintable)
    assert width > 0
    assert height > 0
    assert x < width
    assert y < height

    self = GtkPuzzlePiece()

    self.puzzle = puzzle
    # Bound methods, so the connections end with the piece, as g_signal_connect_swapped() to it would.
    puzzle.invalidate_contents.connect(self.puzzle_invalidate_contents)
    puzzle.invalidate_size.connect(self.puzzle_invalidate_size)
    self.x = x
    self.y = y
    self.width = width
    self.height = height

    return self

