from PyLiite4 import Adw, GObject, Gtk

from demos.workbench import workbench

drop_down: Adw.ComboRow = workbench.builder.get_object("drop_down")


def on_selected_item(*_args: object) -> None:
    selected_item = drop_down.selected_item.get_string()
    print(selected_item)


drop_down.notify["selected-item"].connect(on_selected_item)

expression = Gtk.ClosureExpression.new(
    GObject.TYPE_STRING,
    lambda obj: obj.string,
    None,
)
drop_down.expression = expression
