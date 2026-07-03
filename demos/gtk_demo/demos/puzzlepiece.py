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

    # This is the function that draws the puzzle piece.
    # It just draws a rectangular cutout of the puzzle by clipping
    # away the rest.
    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        snapshot.push_clip(Graphene.Rect().init(0, 0, width, height))

        snapshot.translate(Graphene.Point().init(- width * self.x, - height * self.y))
        self.puzzle.snapshot(snapshot, width * self.width, height * self.height)

        snapshot.pop()

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # The flags are the same as the ones of the puzzle.
        # If the puzzle changes in some way, so do the pieces.
        return self.puzzle.get_flags()

    def do_get_intrinsic_width(self) -> int:
        # We can compute our width relative to the puzzle.
        # This logic even works for the case where the puzzle
        # has no width, because the 0 return value is unchanged.
        # Round up the value.
        return (self.puzzle.get_intrinsic_width() + self.width - 1) // self.width

    def do_get_intrinsic_height(self) -> int:
        # Do the same thing we did for the width with the height.
        return (self.puzzle.get_intrinsic_height() + self.height - 1) // self.height

    def do_get_intrinsic_aspect_ratio(self) -> float:
        # We can compute our aspect ratio relative to the puzzle.
        # This logic again works for the case where the puzzle
        # has no aspect ratio, because the 0 return value is unchanged.
        return self.puzzle.get_intrinsic_aspect_ratio() * self.height / self.width

    def puzzle_invalidate_contents(self, puzzle: Gdk.Paintable) -> None:
        self.invalidate_contents()

    def puzzle_invalidate_size(self, puzzle: Gdk.Paintable) -> None:
        self.invalidate_size()

    # Here are the accessors that we need to inspect the puzzle
    # pieces in other code.
    def get_puzzle(self) -> Gdk.Paintable:
        return self.puzzle

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y


def gtk_puzzle_piece_new(puzzle: Gdk.Paintable, x: int, y: int, width: int, height: int) -> GtkPuzzlePiece:
    """And finally, we add a constructor. The other examples use it."""
    # These are sanity checks, so that we get warnings if we accidentally
    # do anything stupid.
    assert isinstance(puzzle, Gdk.Paintable)
    assert width > 0
    assert height > 0
    assert x < width
    assert y < height

    self = GtkPuzzlePiece()

    self.puzzle = puzzle
    # Bound methods, so the connections end with the piece, as g_signal_connect_swapped() to it would
    puzzle.invalidate_contents.connect(self.puzzle_invalidate_contents)
    puzzle.invalidate_size.connect(self.puzzle_invalidate_size)
    self.x = x
    self.y = y
    self.width = width
    self.height = height

    return self

