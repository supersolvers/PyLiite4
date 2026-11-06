from PyLiite4 import Adw, Gio, Gtk

from demos.workbench import workbench

button_confirmation: Gtk.Button = workbench.builder.get_object("button_confirmation")
button_error: Gtk.Button = workbench.builder.get_object("button_error")
button_advanced: Gtk.Button = workbench.builder.get_object("button_advanced")


def on_response_selected(_dialog: Adw.AlertDialog, task: Gio.AsyncResult) -> None:
    response = _dialog.choose_finish(task)
    print(f'Selected "{response}" response.')


def on_response_selected_advanced(_dialog: Adw.AlertDialog, task: Gio.AsyncResult) -> None:
    response = _dialog.choose_finish(task)
    entry: Gtk.PasswordEntry = _dialog.get_extra_child()
    if response == "login":
        print(f'Selected "{response}" response with password "{entry.get_text()}"')
    else:
        print(f'Selected "{response}" response.')


def create_confirmation_dialog(*_args: object) -> None:
    dialog = Adw.AlertDialog(
        heading="Replace File?",
        body="A file named `example.png` already exists. Do you want to replace it?",
        close_response="cancel",
    )

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("replace", "Replace")

    # The DESTRUCTIVE appearance draws attention to the potentially damaging consequences of this action.
    dialog.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)

    dialog.choose(workbench.window, None, on_response_selected)


def create_error_dialog(*_args: object) -> None:
    dialog = Adw.AlertDialog(
        heading="Critical Error",
        body="You did something you should not have",
        close_response="okay",
    )

    dialog.add_response("okay", "Okay")

    dialog.choose(workbench.window, None, on_response_selected)


def create_advanced_dialog(*_args: object) -> None:
    dialog = Adw.AlertDialog(
        heading="Login",
        body="A valid password is needed to continue",
        close_response="cancel",
    )

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("login", "Login")

    # The SUGGESTED appearance marks important responses, such as the affirmative action.
    dialog.set_response_appearance("login", Adw.ResponseAppearance.SUGGESTED)

    entry = Gtk.PasswordEntry(show_peek_icon=True)
    dialog.set_extra_child(entry)

    dialog.choose(workbench.window, None, on_response_selected_advanced)


button_confirmation.clicked.connect(create_confirmation_dialog)
button_error.clicked.connect(create_error_dialog)
button_advanced.clicked.connect(create_advanced_dialog)
