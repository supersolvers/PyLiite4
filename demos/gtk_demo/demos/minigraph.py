"""A small graph of a component transfer function, used by component_filter."""

import math

from PyLiite4 import Gdk, Graphene, Gsk, Gtk

IDENTITY, LEVELS, LINEAR, GAMMA, DISCRETE, TABLE = range(6)


class MiniGraph(Gtk.Widget):
    __gtype_name__ = "MiniGraph"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.filter_kind = IDENTITY
        # The fields of C's union of per-kind structs
        self.n = 0
        self.m = 0.0
        self.b = 0.0
        self.amp = 0.0
        self.exp = 0.0
        self.ofs = 0.0
        self.values = [0.0] * 6

    def create_path(self, size: int) -> Gsk.Path:
        builder = Gsk.PathBuilder.new()

        if self.filter_kind == IDENTITY:
            builder.move_to(0, size)
            builder.line_to(size, 0)

        elif self.filter_kind == LEVELS:
            x1 = 0.0
            for i in range(self.n):
                x0 = x1
                x1 = (i + 1) / self.n
                x = (x0 + x1) / 2
                y = (math.floor(x * self.n) + 0.5) / self.n

                builder.move_to(x0 * size, (1 - y) * size)
                builder.line_to(x1 * size, (1 - y) * size)

        elif self.filter_kind == LINEAR:
            y0 = self.b
            y1 = self.m + self.b

            if y0 <= 0:
                if y1 <= 0:
                    builder.move_to(0, size)
                    builder.line_to(size, size)
                elif y1 <= 1:
                    x0 = -self.b / self.m

                    builder.move_to(0, size)
                    builder.line_to(x0 * size, size)
                    builder.line_to(size, (1 - y1) * size)
                else:
                    x0 = -self.b / self.m
                    x1 = (1 - self.b) / self.m

                    builder.move_to(0, size)
                    builder.line_to(x0 * size, size)
                    builder.line_to(x1 * size, 0)
                    builder.line_to(size, 0)
            elif y0 <= 1:
                if y1 <= 0:
                    x0 = -self.b / self.m

                    builder.move_to(0, (1 - y0) * size)
                    builder.line_to(x0 * size, size)
                    builder.line_to(size, size)
                elif y1 <= 1:
                    builder.move_to(0, (1 - y0) * size)
                    builder.line_to(size, (1 - y1) * size)
                else:
                    x1 = (1 - self.b) / self.m

                    builder.move_to(0, (1 - y0) * size)
                    builder.line_to(x1 * size, 0)
                    builder.line_to(size, 0)
            else:
                if y1 <= 0:
                    x0 = (1 - self.b) / self.m
                    x1 = -self.b / self.m

                    builder.move_to(0, 0)
                    builder.line_to(x0 * size, 0)
                    builder.line_to(x1 * size, size)
                    builder.line_to(size, size)
                elif y1 <= 1:
                    x0 = (1 - self.b) / self.m

                    builder.move_to(0, 0)
                    builder.line_to(x0 * size, 0)
                    builder.line_to(size, (1 - y1) * size)
                else:
                    builder.move_to(0, 0)
                    builder.line_to(size, 0)

        elif self.filter_kind == GAMMA:
            for i in range(size + 1):
                x = i / size
                y = self.amp * math.pow(x, self.exp) + self.ofs
                y = min(max(y, 0), 1)

                if i == 0:
                    builder.move_to(x * size, (1 - y) * size)
                else:
                    builder.line_to(x * size, (1 - y) * size)

        elif self.filter_kind == DISCRETE:
            x1 = 0.0
            for i in range(self.n):
                x0 = x1
                x1 = (i + 1) / self.n
                y = self.values[i]

                builder.move_to(x0 * size, (1 - y) * size)
                builder.line_to(x1 * size, (1 - y) * size)

        elif self.filter_kind == TABLE:
            for i in range(self.n):
                x = i / (self.n - 1)
                y = self.values[i]

                if i == 0:
                    builder.move_to(x * size, (1 - y) * size)
                else:
                    builder.line_to(x * size, (1 - y) * size)

        else:
            raise AssertionError("not reached")

        return builder.to_path()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        size = min(width, height)

        snapshot.save()
        snapshot.translate(Graphene.Point().init((width - size) // 2, (height - size) // 2))

        snapshot.append_color(Gdk.RGBA(red=1, green=1, blue=1, alpha=1), Graphene.Rect().init(0, 0, size, size))
        border = Gdk.RGBA(red=0, green=0, blue=0, alpha=0.75)
        outline = Gsk.RoundedRect()
        outline.init_from_rect(Graphene.Rect().init(0, 0, size, size), 0)
        snapshot.append_border(outline, [1, 1, 1, 1], [border, border, border, border])

        path = self.create_path(size)

        stroke = Gsk.Stroke.new(2)

        snapshot.append_stroke(path, stroke, Gdk.RGBA(red=0, green=0, blue=1, alpha=1))

        snapshot.restore()

    def set_identity(self) -> None:
        self.filter_kind = IDENTITY

        self.queue_draw()

    def set_levels(self, levels: int) -> None:
        self.filter_kind = LEVELS
        self.n = levels

        self.queue_draw()

    def set_linear(self, m: float, b: float) -> None:
        self.filter_kind = LINEAR
        self.m = m
        self.b = b

        self.queue_draw()

    def set_gamma(self, amp: float, exp: float, ofs: float) -> None:
        self.filter_kind = GAMMA
        self.amp = amp
        self.exp = exp
        self.ofs = ofs

        self.queue_draw()

    def set_discrete(self, n: int, values: list[float]) -> None:
        self.filter_kind = DISCRETE
        self.n = min(n, 6)
        for i in range(self.n):
            self.values[i] = values[i]

        self.queue_draw()

    def set_table(self, n: int, values: list[float]) -> None:
        self.filter_kind = TABLE
        self.n = min(n, 6)
        for i in range(self.n):
            self.values[i] = values[i]

        self.queue_draw()


def mini_graph_new() -> Gtk.Widget:
    return MiniGraph()
