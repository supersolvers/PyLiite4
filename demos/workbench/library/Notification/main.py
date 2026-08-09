from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

application = workbench.window.get_application()
builder = workbench.builder

# https://gjs-docs.gnome.org/gio20/gio.notification
notification = Gio.Notification()

notification.set_title("Lunch is ready")
notification.set_body(
    "Today we have pancakes and salad, and fruit and cake for dessert",
)
notification.set_default_action("app.notification-reply")
notification.add_button("Accept", "app.notification-accept")
notification.add_button("Decline", "app.notification-decline")

icon = Gio.ThemedIcon(name="object-rotate-right-symbolic")
notification.set_icon(icon)

button_simple: Gtk.Button = builder.get_object("button_simple")
button_simple.clicked.connect(lambda _: application.send_notification("lunch-is-ready", notification))

action_reply = Gio.SimpleAction(name="notification-reply")
action_reply.activate.connect(lambda *_: print("Reply"))
application.add_action(action_reply)

action_accept = Gio.SimpleAction(name="notification-accept")
action_accept.activate.connect(lambda *_: print("Accept"))
application.add_action(action_accept)

action_decline = Gio.SimpleAction(name="notification-decline")
action_decline.activate.connect(lambda *_: print("Decline"))
application.add_action(action_decline)
