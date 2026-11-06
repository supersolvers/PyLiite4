from PyLiite4 import Gtk

from demos.workbench import workbench

linkbutton: Gtk.LinkButton = workbench.builder.get_object("linkbutton")


def on_activate_link(button: Gtk.LinkButton) -> bool:
    print(f"About to activate {button.get_uri()}")

    # Returning True says the link was handled here; False lets the default behavior continue.
    return False


linkbutton.notify["visited"].connect(lambda _widget, _params: print("The link has been visited"))
linkbutton.activate_link.connect(on_activate_link)
