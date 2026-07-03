"""A widget to pick a component transfer function, used by image_filtering."""

from PyLiite4 import Gio, GObject, Gsk, Gtk

from .minigraph import MiniGraph

IDENTITY, LEVELS, LINEAR, GAMMA, DISCRETE, TABLE = range(6)


def template_ui() -> str:
    # PyGObject's templates can't connect swapped="yes" handlers. A template callback is a method, so it gets
    # the ComponentFilter anyway, and the template is loaded without the flag.
    data = Gio.resources_lookup_data("/image_filter/component_filter.ui", Gio.ResourceLookupFlags.NONE)
    return data.get_data().decode().replace(' swapped="yes"', "")


@Gtk.Template(string=template_ui())
class ComponentFilter(Gtk.Widget):
    __gtype_name__ = "ComponentFilter"

    box: Gtk.Box = Gtk.Template.Child()
    kind: Gtk.DropDown = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()
    levels: Gtk.SpinButton = Gtk.Template.Child()
    linear_m: Gtk.SpinButton = Gtk.Template.Child()
    linear_b: Gtk.SpinButton = Gtk.Template.Child()
    gamma_amp: Gtk.SpinButton = Gtk.Template.Child()
    gamma_exp: Gtk.SpinButton = Gtk.Template.Child()
    gamma_ofs: Gtk.SpinButton = Gtk.Template.Child()
    discrete_size: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value0: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value1: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value2: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value3: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value4: Gtk.SpinButton = Gtk.Template.Child()
    discrete_value5: Gtk.SpinButton = Gtk.Template.Child()
    graph: MiniGraph = Gtk.Template.Child()

    component_transfer: Gsk.ComponentTransfer

    def __init__(self, **properties: object) -> None:
        self.component_transfer = Gsk.ComponentTransfer.new_identity()
        self.filter_kind = IDENTITY
        super().__init__(**properties)

    @GObject.Property(type=Gsk.ComponentTransfer, flags=GObject.ParamFlags.READABLE)
    def transfer(self) -> Gsk.ComponentTransfer:
        return self.component_transfer

    @property
    def discrete_values(self) -> list[Gtk.SpinButton]:
        return [self.discrete_value0, self.discrete_value1, self.discrete_value2,
                self.discrete_value3, self.discrete_value4, self.discrete_value5]

    @Gtk.Template.Callback()
    def update_component_transfer(self, *args: object) -> None:
        page = ["identity", "levels", "linear", "gamma", "discrete", "discrete"]

        self.filter_kind = self.kind.get_selected()
        self.stack.set_visible_child_name(page[self.filter_kind])

        if self.filter_kind == IDENTITY:
            self.component_transfer = Gsk.ComponentTransfer.new_identity()
            self.graph.set_identity()
        elif self.filter_kind == LEVELS:
            n = self.levels.get_value_as_int()
            self.component_transfer = Gsk.ComponentTransfer.new_levels(n)
            self.graph.set_levels(n)
        elif self.filter_kind == LINEAR:
            m = self.linear_m.get_value()
            b = self.linear_b.get_value()
            self.component_transfer = Gsk.ComponentTransfer.new_linear(m, b)
            self.graph.set_linear(m, b)
        elif self.filter_kind == GAMMA:
            amp = self.gamma_amp.get_value()
            exp = self.gamma_exp.get_value()
            ofs = self.gamma_ofs.get_value()
            self.component_transfer = Gsk.ComponentTransfer.new_gamma(amp, exp, ofs)
            self.graph.set_gamma(amp, exp, ofs)
        elif self.filter_kind in (DISCRETE, TABLE):
            n = self.discrete_size.get_value_as_int()
            values = []
            for i in range(6):
                self.discrete_values[i].set_visible(i < n)
                values.append(self.discrete_values[i].get_value())
            if self.filter_kind == DISCRETE:
                self.component_transfer = Gsk.ComponentTransfer.new_discrete(values[:n])
                self.graph.set_discrete(n, values)
            else:
                self.component_transfer = Gsk.ComponentTransfer.new_table(values[:n])
                self.graph.set_table(n, values)
        else:
            raise AssertionError("not reached")

        self.notify("transfer")

    def get_component_transfer(self) -> Gsk.ComponentTransfer:
        return self.component_transfer


ComponentFilter.set_layout_manager_type(Gtk.BinLayout)


def component_filter_new() -> Gtk.Widget:
    return ComponentFilter()
