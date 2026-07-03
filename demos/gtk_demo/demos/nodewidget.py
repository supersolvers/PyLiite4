"""NodeWidget, a widget drawing a render node loaded from a resource, used by the Fishbowl demo."""

from PyLiite4 import Gio, Graphene, Gsk, Gtk


class NodeWidget(Gtk.Widget):
    __gtype_name__ = "NodeWidget"

    node: Gsk.RenderNode

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        snapshot.append_node(self.node)


def node_widget_new(resource: str) -> Gtk.Widget:
    self = NodeWidget()

    bytes = Gio.resources_lookup_data(resource, Gio.ResourceLookupFlags.NONE)
    node = Gsk.RenderNode.deserialize(bytes, None)

    bounds: Graphene.Rect = node.get_bounds()
    scale = min(100.0 / bounds.size.width, 100.0 / bounds.size.height)
    transform = Gsk.Transform.new().scale(scale, scale)
    self.node = Gsk.TransformNode.new(node, transform)

    return self
