from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

dialog: Adw.PreferencesDialog = workbench.builder.get_object("dialog")
dm_switch: Adw.SwitchRow = workbench.builder.get_object("dm_switch")
subpage: Adw.NavigationPage = workbench.builder.get_object("subpage")
subpage_row: Adw.ActionRow = workbench.builder.get_object("subpage_row")
subpage_button: Gtk.Button = workbench.builder.get_object("subpage_button")
toast_button: Gtk.Button = workbench.builder.get_object("toast_button")
button: Gtk.Button = workbench.builder.get_object("button")

style_manager = Adw.StyleManager.get_default()

dm_switch.set_active(style_manager.get_dark())

# When the Switch is toggled, set the color scheme
dm_switch.notify["active"].connect(
    lambda *_: style_manager.set_color_scheme(
        Adw.ColorScheme.FORCE_DARK
        if dm_switch.get_active()
        else Adw.ColorScheme.FORCE_LIGHT
    ),
)

# Preferences dialogs can display subpages
subpage_row.activated.connect(lambda *_: dialog.push_subpage(subpage))

subpage_button.clicked.connect(lambda *_: dialog.pop_subpage())

toast_button.clicked.connect(
    lambda *_: dialog.add_toast(
        Adw.Toast(
            title="Preferences dialogs can display toasts",
        )
    ),
)

button.clicked.connect(lambda *_: dialog.present(workbench.window))
