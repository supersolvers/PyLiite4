"""A child widget for the layout manager demo."""

from PyLiite4 import Gdk, Graphene, Gtk


class DemoChild(Gtk.Widget):
    """This is a trivial child widget just for demo purposes.
    It draws a 32x32 square in fixed color.
    """

    __gtype_name__ = "DemoChild"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.color = Gdk.RGBA()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        snapshot.append_color(self.color, Graphene.Rect().init(0, 0, width, height))

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        return 32, 32, -1, -1


def demo_child_new(color: str) -> Gtk.Widget:
    self = DemoChild(tooltip_text=color)

    self.color.parse(color)

    return self
