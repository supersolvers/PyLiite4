from PyLiite4 import Adw, Gio, GLib, Gtk

from demos.workbench import workbench

overlay: Adw.ToastOverlay = workbench.builder.get_object("overlay")

button_simple: Gtk.Button = workbench.builder.get_object("button_simple")


def simple(_button: Gtk.Button) -> None:
    toast = Adw.Toast(title="Toasts are delicious!", timeout=1)

    def on_dismissed(_toast: Adw.Toast) -> None:
        button_simple.sensitive = True

    toast.dismissed.connect(on_dismissed)
    overlay.add_toast(toast)
    button_simple.sensitive = False


button_simple.clicked.connect(simple)


def advanced(_button: Gtk.Button) -> None:
    message_id = "42"
    toast = Adw.Toast(
        title="Message sent",
        button_label="Undo",
        action_name="win.undo",
        action_target=GLib.Variant.new_string(message_id),
        priority=Adw.ToastPriority.HIGH,
    )
    overlay.add_toast(toast)


workbench.builder.get_object("button_advanced").clicked.connect(advanced)

action_console = Gio.SimpleAction(name="undo", parameter_type=GLib.VariantType("s"))


def on_activate(_self: Gio.SimpleAction, target: GLib.Variant) -> None:
    value = target.unpack()
    print(f"undo {value}")


action_console.activate.connect(on_activate)
workbench.window.add_action(action_console)
