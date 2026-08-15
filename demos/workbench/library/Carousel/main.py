from PyLiite4 import Adw, GObject, Gtk

from demos.workbench import workbench

root_box: Gtk.Box = workbench.builder.get_object("root_box")
carousel: Adw.Carousel = workbench.builder.get_object("carousel")
ls_switch: Adw.SwitchRow = workbench.builder.get_object("ls_switch")
sw_switch: Adw.SwitchRow = workbench.builder.get_object("sw_switch")
indicator_row: Adw.ComboRow = workbench.builder.get_object("indicator_row")
orientation_row: Adw.ComboRow = workbench.builder.get_object("orientation_row")

carousel.page_changed.connect(lambda *_: print("Page Changed"))

# Scroll Wheel Switch
sw_switch.set_active(carousel.get_allow_scroll_wheel())

sw_switch.notify["active"].connect(lambda *_: carousel.set_allow_scroll_wheel(sw_switch.get_active()))

# Long Swipe Switch
ls_switch.set_active(carousel.get_allow_long_swipes())

ls_switch.notify["active"].connect(lambda *_: carousel.set_allow_long_swipes(ls_switch.get_active()))

indicators: Adw.CarouselIndicatorDots | Adw.CarouselIndicatorLines
if indicator_row.get_selected() == 0:
    indicators = Adw.CarouselIndicatorDots(carousel=carousel)
else:
    indicators = Adw.CarouselIndicatorLines(carousel=carousel)

indicators.set_orientation(carousel.get_orientation())
root_box.append(indicators)


def on_indicator_selected(_widget: Adw.ComboRow, _item: GObject.ParamSpec) -> None:
    global indicators
    root_box.remove(indicators)

    if indicator_row.get_selected() == 0:
        indicators = Adw.CarouselIndicatorDots(carousel=carousel)
    else:
        indicators = Adw.CarouselIndicatorLines(carousel=carousel)

    indicators.set_orientation(carousel.get_orientation())
    root_box.append(indicators)


def on_orientation_selected(_widget: Adw.ComboRow, _item: GObject.ParamSpec) -> None:
    if orientation_row.get_selected() == 0:
        root_box.set_orientation(Gtk.Orientation.VERTICAL)
        carousel.set_orientation(Gtk.Orientation.HORIZONTAL)
        indicators.set_orientation(Gtk.Orientation.HORIZONTAL)
    else:
        root_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        carousel.set_orientation(Gtk.Orientation.VERTICAL)
        indicators.set_orientation(Gtk.Orientation.VERTICAL)


indicator_row.notify["selected-item"].connect(on_indicator_selected)
orientation_row.notify["selected-item"].connect(on_orientation_selected)
