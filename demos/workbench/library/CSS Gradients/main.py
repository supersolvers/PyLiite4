from PyLiite4 import Adw, Gdk, Gtk, GtkSource

from demos.workbench import workbench

Adw.init()
GtkSource.init()


combo_row_gradient_type: Adw.ComboRow = workbench.builder.get_object(
    "combo_row_gradient_type",
)
spin_row_angle: Adw.SpinRow = workbench.builder.get_object("spin_row_angle")
button_color_1: Gtk.ColorDialogButton = workbench.builder.get_object("button_color_1")
button_color_2: Gtk.ColorDialogButton = workbench.builder.get_object("button_color_2")
button_color_3: Gtk.ColorDialogButton = workbench.builder.get_object("button_color_3")
button_copy_css: Gtk.Button = workbench.builder.get_object("button_copy_css")
overlay: Gtk.Overlay = workbench.builder.get_object("overlay")

# Workbench's Blueprint declares this view; it's built here because GtkSource's types exist only once it's imported.
gtksource_buffer = GtkSource.Buffer(highlight_syntax=True)
source_view = GtkSource.View(
    top_margin=6,
    bottom_margin=6,
    left_margin=6,
    right_margin=6,
    editable=False,
    monospace=True,
    buffer=gtksource_buffer,
)
overlay.set_child(source_view)


def generate_css() -> str:
    angle_string = spin_row_angle.get_value()
    first_color_string = button_color_1.get_rgba().to_string()
    second_color_string = button_color_2.get_rgba().to_string()
    third_color_string = button_color_3.get_rgba().to_string()

    css = ""
    if combo_row_gradient_type.get_selected() == 0:
        css = f"""
.background-gradient {{
  background-image: linear-gradient(
    {angle_string}deg,
    {first_color_string},
    {second_color_string},
    {third_color_string}
  );
}}"""
    elif combo_row_gradient_type.get_selected() == 1:
        css = f"""
.background-gradient {{
  background-image: radial-gradient(
    {first_color_string},
    {second_color_string},
    {third_color_string}
  );
}}"""
    elif combo_row_gradient_type.get_selected() == 2:
        css = f"""
.background-gradient {{
  background-image: conic-gradient(
    from {angle_string}deg,
    {first_color_string},
    {second_color_string},
    {third_color_string}
  );
}}"""

    return css.lstrip()


def update_css_provider(css: str) -> None:
    display = Gdk.Display.get_default()

    css_provider = Gtk.CssProvider()
    css_provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(
        display,
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def update(*_args: object) -> None:
    spin_row_angle.set_sensitive(combo_row_gradient_type.get_selected() != 1)
    css = generate_css()
    gtksource_buffer.set_text(css, -1)
    update_css_provider(css)


combo_row_gradient_type.notify["selected"].connect(update)
spin_row_angle.notify["value"].connect(update)
button_color_1.notify["rgba"].connect(update)
button_color_2.notify["rgba"].connect(update)
button_color_3.notify["rgba"].connect(update)

update()


clipboard = Gdk.Display.get_default().get_clipboard()

button_copy_css.clicked.connect(
    lambda *_args: clipboard.set(
        gtksource_buffer.get_text(
            gtksource_buffer.get_start_iter(), gtksource_buffer.get_end_iter(), False
        )
    ),
)

scheme_manager = GtkSource.StyleSchemeManager.get_default()


def update_color_scheme() -> None:
    scheme = scheme_manager.get_scheme(
        "Adwaita-dark" if style_manager.get_dark() else "Adwaita"
    )
    gtksource_buffer.set_style_scheme(scheme)


style_manager = Adw.StyleManager.get_default()
style_manager.notify["dark"].connect(lambda *_args: update_color_scheme())

update_color_scheme()

language_manager = GtkSource.LanguageManager.get_default()
css_language = language_manager.get_language("css")
gtksource_buffer.set_language(css_language)
