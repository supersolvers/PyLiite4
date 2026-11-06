from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

scrolled_window: Gtk.ScrolledWindow = workbench.builder.get_object("scrolled_window")
container: Gtk.Box = workbench.builder.get_object("container")
toggle_orientation: Gtk.ToggleButton = workbench.builder.get_object("toggle_orientation")
button_start: Gtk.Button = workbench.builder.get_object("button_start")
button_end: Gtk.Button = workbench.builder.get_object("button_end")
auto_scrolling = False

button_start.sensitive = False

scrollbars = {
    Gtk.Orientation.HORIZONTAL: scrolled_window.get_hscrollbar(),
    Gtk.Orientation.VERTICAL: scrolled_window.get_vscrollbar(),
}


def on_toggled(_button: Gtk.ToggleButton) -> None:
    if toggle_orientation.get_active():
        container.set_orientation(Gtk.Orientation.HORIZONTAL)
    else:
        container.set_orientation(Gtk.Orientation.VERTICAL)


def on_animation_done(_animation: Adw.Animation) -> None:
    global auto_scrolling
    auto_scrolling = False


def create_scrollbar_anim(scrollbar: Gtk.Scrollbar, direction: int) -> Adw.TimedAnimation:
    # A direction of 0 animates to the start, and 1 to the end.
    adjustment = scrollbar.get_adjustment()
    target = Adw.PropertyAnimationTarget.new(adjustment, "value")
    animation = Adw.TimedAnimation(
        widget=scrollbar,
        value_from=adjustment.get_value(),
        value_to=adjustment.get_upper() - adjustment.get_page_size() if direction else 0,
        duration=1000,
        easing=Adw.Easing.LINEAR,
        target=target,
    )

    animation.done.connect(on_animation_done)
    return animation


def on_button_clicked(_button: Gtk.Button, direction: int) -> None:
    global auto_scrolling
    auto_scrolling = True
    scrollbar = scrollbars[container.get_orientation()]
    anim = create_scrollbar_anim(scrollbar, direction)
    anim.play()


def populate_container(container: Gtk.Box, label: str) -> None:
    item = Adw.Bin(
        margin_top=6,
        margin_bottom=6,
        margin_start=6,
        margin_end=6,
        child=Gtk.Label(
            label=label,
            width_request=100,
            height_request=100,
        ),
        css_classes=["card"],
    )
    container.append(item)


def on_value_changed(adj: Gtk.Adjustment) -> None:
    if adj.get_value() == adj.get_lower():
        button_end.set_sensitive(True)
        button_start.set_sensitive(False)
    elif adj.get_value() == adj.get_upper() - adj.get_page_size():
        button_end.set_sensitive(False)
        button_start.set_sensitive(True)
    else:
        # The buttons are insensitive while the scrollbar is auto-scrolling.
        button_end.set_sensitive(not auto_scrolling)
        button_start.set_sensitive(not auto_scrolling)


toggle_orientation.toggled.connect(on_toggled)

num_items = 20
for i in range(num_items):
    populate_container(container, f"Item {i + 1}")


for _orientation, scrollbar in scrollbars.items():
    adj = scrollbar.get_adjustment()
    adj.value_changed.connect(on_value_changed)

scrolled_window.edge_reached.connect(lambda _window, _position: print("Edge Reached"))

button_start.clicked.connect(on_button_clicked, 0)
button_end.clicked.connect(on_button_clicked, 1)
