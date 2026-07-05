"""Error States

GtkLabel and GtkEntry can indicate errors if you set the .error
style class on them.

This examples shows how this can be used in a dialog for input validation.

It also shows how pass callbacks and objects to GtkBuilder with
GtkBuilderScope and gtk_builder_expose_object().
"""

from collections.abc import Callable

from PyLiite4 import GObject, Gtk


def validate_more_details(entry: Gtk.Entry, pspec: GObject.ParamSpec, details: Gtk.Entry) -> None:
    if len(entry.get_text()) > 0 and len(details.get_text()) == 0:
        entry.set_tooltip_text("Must have details first")
        entry.add_css_class("error")
        entry.update_state([Gtk.AccessibleState.INVALID], [Gtk.AccessibleInvalidState.TRUE])
    else:
        entry.set_tooltip_text("")
        entry.remove_css_class("error")
        entry.reset_state(Gtk.AccessibleState.INVALID)


def mode_switch_state_set(sw: Gtk.Switch, state: bool, scale: Gtk.Scale) -> bool:
    label = sw.error_label

    if not state or scale.get_value() > 50:
        label.set_visible(False)
        sw.set_state(state)
        sw.reset_relation(Gtk.AccessibleRelation.ERROR_MESSAGE)
        sw.reset_state(Gtk.AccessibleState.INVALID)
    else:
        label.set_visible(True)
        sw.update_relation([Gtk.AccessibleRelation.ERROR_MESSAGE], [[label]])
        sw.update_state([Gtk.AccessibleState.INVALID], [Gtk.AccessibleInvalidState.TRUE])

    return True


def level_scale_value_changed(range: Gtk.Range, sw: Gtk.Switch) -> None:
    label = sw.error_label

    if sw.get_active() and not sw.get_state() and range.get_value() > 50:
        label.set_visible(False)
        sw.set_state(True)
    elif sw.get_state() and range.get_value() <= 50:
        sw.set_state(False)

    sw.reset_relation(Gtk.AccessibleRelation.ERROR_MESSAGE)
    sw.reset_state(Gtk.AccessibleState.INVALID)


class BuilderCScope(GObject.Object, Gtk.BuilderScope):
    """What gtk_builder_cscope_new() and gtk_builder_cscope_add_callback() do: callbacks by name.

    PyGObject's own Gtk.Builder scope refuses swapped="yes", which errorstates.ui uses.
    """

    __gtype_name__ = "PyDemoErrorstatesBuilderCScope"

    def __init__(self) -> None:
        super().__init__()
        self.callbacks: dict[str, Callable[..., object]] = {}

    def add_callback(self, callback: Callable[..., object]) -> None:
        self.callbacks[callback.__name__] = callback

    def do_create_closure(self, builder: Gtk.Builder, function_name: str, flags: Gtk.BuilderClosureFlags,
                          object: GObject.Object | None) -> Callable[..., object]:
        callback = self.callbacks[function_name]
        if object is None:
            return callback
        if flags & Gtk.BuilderClosureFlags.SWAPPED:
            return lambda instance, *args: callback(object, *args, instance)
        return lambda instance, *args: callback(instance, *args, object)


# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        toplevel = do_widget.get_root()

        scope = BuilderCScope()
        scope.add_callback(validate_more_details)
        scope.add_callback(mode_switch_state_set)
        scope.add_callback(level_scale_value_changed)
        builder = Gtk.Builder()
        builder.set_scope(scope)
        builder.expose_object("toplevel", toplevel)
        builder.add_from_resource("/errorstates/errorstates.ui")

        window = builder.get_object("dialog")

        window.set_display(do_widget.get_display())
        window_ref = window.weak_ref()

        sw = builder.get_object("mode_switch")
        label = builder.get_object("error_label")
        sw.error_label = label

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
