"""A composite entry built from GtkText, which can show tags and other widgets inside the entry area.

Port of GTK Demo's demotaggedentry.c, copyright (C) 2019 Red Hat, Inc., by Matthias Clasen; LGPL-2.0-or-later.
"""

from PyLiite4 import Gdk, GLib, GObject, Gtk

_EXPLICIT = GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY


class DemoTaggedEntry(Gtk.Widget, Gtk.Editable):
    __gtype_name__ = "DemoTaggedEntry"

    # C calls its GtkText child "text", which here is GtkEditable's "text" property. C installs GtkEditable's
    # properties with gtk_editable_install_properties() and forwards them with gtk_editable_delegate_get/
    # set_property(); PyGObject can't override an interface property, so they're declared and forwarded by hand.
    text = GObject.Property(type=str, default="", flags=_EXPLICIT,
                            getter=lambda self: self.text_widget.get_text(),
                            setter=lambda self, value: self.text_widget.set_text(value))
    cursor_position = GObject.Property(type=int, minimum=0, maximum=65535, default=0,
                                       flags=GObject.ParamFlags.READABLE,
                                       getter=lambda self: self.text_widget.get_position())
    enable_undo = GObject.Property(type=bool, default=True, flags=_EXPLICIT,
                                   getter=lambda self: self.text_widget.get_enable_undo(),
                                   setter=lambda self, value: self.text_widget.set_enable_undo(value))
    selection_bound = GObject.Property(type=int, minimum=0, maximum=65535, default=0,
                                       flags=GObject.ParamFlags.READABLE,
                                       getter=lambda self: self.text_widget.get_property("selection-bound"))
    editable = GObject.Property(type=bool, default=True, flags=_EXPLICIT,
                                getter=lambda self: self.text_widget.get_editable(),
                                setter=lambda self, value: self.text_widget.set_editable(value))
    width_chars = GObject.Property(type=int, minimum=-1, maximum=GLib.MAXINT32, default=-1, flags=_EXPLICIT,
                                   getter=lambda self: self.text_widget.get_width_chars(),
                                   setter=lambda self, value: self.text_widget.set_width_chars(value))
    max_width_chars = GObject.Property(type=int, minimum=-1, maximum=GLib.MAXINT32, default=-1, flags=_EXPLICIT,
                                       getter=lambda self: self.text_widget.get_max_width_chars(),
                                       setter=lambda self, value: self.text_widget.set_max_width_chars(value))
    xalign = GObject.Property(type=GObject.TYPE_FLOAT, minimum=0.0, maximum=1.0, default=0.0, flags=_EXPLICIT,
                              getter=lambda self: self.text_widget.get_alignment(),
                              setter=lambda self, value: self.text_widget.set_alignment(value))

    def __init__(self) -> None:
        self.text_widget: Gtk.Text | None = None
        super().__init__()

        self.text_widget = Gtk.Text()
        self.text_widget.set_hexpand(True)
        self.text_widget.set_vexpand(True)
        self.text_widget.set_parent(self)
        self.init_delegate()
        self.text_widget.set_width_chars(6)
        self.text_widget.set_max_width_chars(6)
        self.add_css_class("tagged")

        provider = Gtk.CssProvider()
        provider.load_from_resource("/tagged_entry/tagstyle.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

        self.update_property([Gtk.AccessibleProperty.LABEL], ["Tagged Entry"])

    def do_dispose(self) -> None:
        if self.text_widget is not None:
            self.finish_delegate()

        while (child := self.get_first_child()) is not None:
            child.unparent()

        self.text_widget = None

        super().do_dispose()

    def do_grab_focus(self) -> bool:
        return self.text_widget.grab_focus()

    def do_get_delegate(self) -> Gtk.Editable:
        return self.text_widget

    def add_tag(self, tag: Gtk.Widget) -> None:
        tag.set_parent(self)

    def insert_tag_after(self, tag: Gtk.Widget, sibling: Gtk.Widget | None) -> None:
        tag.insert_after(self, sibling)

    def remove_tag(self, tag: Gtk.Widget) -> None:
        tag.unparent()


DemoTaggedEntry.set_layout_manager_type(Gtk.BoxLayout)
DemoTaggedEntry.set_css_name("entry")
DemoTaggedEntry.set_accessible_role(Gtk.AccessibleRole.TEXT_BOX)


def demo_tagged_entry_new() -> DemoTaggedEntry:
    return DemoTaggedEntry()


class DemoTaggedEntryTag(Gtk.Widget):
    __gtype_name__ = "DemoTaggedEntryTag"

    clicked = GObject.Signal(flags=GObject.SignalFlags.RUN_FIRST)
    button_clicked = GObject.Signal(name="button-clicked", flags=GObject.SignalFlags.RUN_FIRST)

    def __init__(self, **properties: object) -> None:
        self.box: Gtk.Box | None = None
        self.label_widget: Gtk.Label | None = None
        self.button: Gtk.Button | None = None
        super().__init__()

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.box.set_parent(self)
        # C calls this child "label", which here is the "label" property.
        self.label_widget = Gtk.Label(label="")
        self.box.append(self.label_widget)

        gesture = Gtk.GestureClick()
        gesture.released.connect(self.on_released)
        self.add_controller(gesture)

        for name, value in properties.items():
            self.set_property(name, value)

    def on_released(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        self.clicked.emit()

    def do_dispose(self) -> None:
        if self.box is not None:
            self.box.unparent()
            self.box = None

        super().do_dispose()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        return self.box.measure(orientation, for_size)

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        self.box.allocate(width, height, baseline, None)

    def get_label(self) -> str:
        return self.label_widget.get_label()

    def set_label(self, label: str) -> None:
        self.label_widget.set_label(label)

    label = GObject.Property(type=str, nick="Label", blurb="Label",
                             getter=get_label, setter=set_label)

    def on_button_clicked(self, button: Gtk.Button) -> None:
        self.button_clicked.emit()

    def set_has_close_button(self, has_close_button: bool) -> None:
        if (self.button is not None) == has_close_button:
            return

        if not has_close_button and self.button is not None:
            self.box.remove(self.button)
            self.button = None
        elif has_close_button and self.button is None:
            image = Gtk.Image.new_from_icon_name("window-close-symbolic")
            image.set_property("accessible-role", Gtk.AccessibleRole.PRESENTATION)
            self.button = Gtk.Button()
            self.button.update_property([Gtk.AccessibleProperty.LABEL], ["Close"])
            self.button.set_child(image)
            self.button.set_halign(Gtk.Align.CENTER)
            self.button.set_valign(Gtk.Align.CENTER)
            self.button.set_has_frame(False)
            self.box.append(self.button)
            self.button.clicked.connect(self.on_button_clicked)

        self.notify("has-close-button")

    def get_has_close_button(self) -> bool:
        return self.button is not None

    has_close_button = GObject.Property(type=bool, default=False, nick="Has close button",
                                        blurb="Whether this tag has a close button", flags=_EXPLICIT,
                                        getter=get_has_close_button, setter=set_has_close_button)


DemoTaggedEntryTag.set_css_name("tag")


def demo_tagged_entry_tag_new(label: str) -> DemoTaggedEntryTag:
    return DemoTaggedEntryTag(label=label)
