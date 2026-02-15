import gc
import weakref

import pytest

from PyLiite4 import BoundSignal, Signal, SignalMethod
from PyLiite4 import Gio, GObject, Gtk


def test_connect_emit_passes_sender():
    button = Gtk.Button(label="x")
    calls = []
    button.clicked.connect(lambda sender: calls.append(sender))
    button.clicked.emit()
    assert calls == [button]


def test_user_data_and_after_order():
    button = Gtk.Button()
    calls = []
    button.clicked.connect(lambda _, tag: calls.append(tag), "late", after=True)
    button.clicked.connect(lambda _, tag: calls.append(tag), "early")
    button.clicked.emit()
    assert calls == ["early", "late"]


def test_disconnect_by_id_and_callback():
    button = Gtk.Button()
    calls = []

    def callback(_):
        calls.append(1)

    handler = button.clicked.connect(callback)
    button.clicked.disconnect(handler)
    button.clicked.connect(callback)
    button.clicked.disconnect(callback)
    button.clicked.emit()
    assert calls == []
    with pytest.raises(ValueError):
        button.clicked.disconnect(callback)


def test_bound_method_disconnect():
    class Receiver:
        def __init__(self):
            self.count = 0

        def on_clicked(self, _):
            self.count += 1

    button, receiver = Gtk.Button(), Receiver()
    button.clicked.connect(receiver.on_clicked)
    button.clicked.disconnect(receiver.on_clicked)
    button.clicked.emit()
    assert receiver.count == 0


def test_blocked():
    button = Gtk.Button()
    calls = []
    handler = button.clicked.connect(lambda _: calls.append(1))
    with button.clicked.blocked(handler):
        button.clicked.emit()
    assert calls == []
    button.clicked.emit()
    assert calls == [1]


def test_detail():
    button = Gtk.Button()
    calls = []
    button.notify["label"].connect(lambda _, spec: calls.append(spec.name))
    button.set_tooltip_text("not the label")
    button.set_label("new")
    assert calls == ["label"]


def test_name_is_both_method_and_signal():
    window = Gtk.Box()
    calls = []
    assert isinstance(window.hide, SignalMethod)
    window.hide.connect(lambda _: calls.append("hidden"))
    window.set_visible(True)
    window.hide()
    assert window.get_visible() is False


def test_unbound_method_still_callable():
    box = Gtk.Box()
    Gtk.Widget.set_visible(box, False)
    Gtk.Widget.show(box)
    assert box.get_visible()


def test_objects_created_by_gtk_have_signals():
    builder = Gtk.Builder.new_from_string(
        '<interface><object class="GtkSwitch" id="switch"/><object class="GtkEntry" id="entry"/></interface>', -1)
    assert isinstance(builder.get_object("switch").state_set, BoundSignal)
    # "changed" comes from the Gtk.Editable interface.
    assert isinstance(builder.get_object("entry").changed, BoundSignal)


def test_method_signal_from_namespace_not_imported_directly():
    store = Gio.ListStore.new(GObject.Object)
    calls = []
    store.items_changed.connect(lambda _, position, removed, added: calls.append((position, removed, added)))
    store.append(GObject.Object())
    assert calls == [(0, 0, 1)]


def test_missing_attribute_raises():
    with pytest.raises(AttributeError, match="no_such"):
        Gtk.Button().no_such_attribute
    assert not hasattr(Gtk.Button(), "_private")


def test_user_defined_signal():
    class Counter(GObject.Object):
        changed = Signal(int, str)
        cleared = Signal()

    counter = Counter()
    calls = []
    counter.changed.connect(lambda _, number, text: calls.append((number, text)))
    counter.cleared.connect(lambda _: calls.append("cleared"))
    counter.changed.emit(3, "x")
    counter.cleared.emit()
    assert calls == [(3, "x"), "cleared"]
    assert isinstance(counter.changed, BoundSignal)


def test_subclass_override_wins():
    class Quiet(Gtk.Box):
        def hide(self):
            return "mine"

    assert Quiet().hide() == "mine"


def test_star_import_and_dir():
    namespace = {}
    exec("from PyLiite4.Gtk import *", namespace)
    assert namespace["Button"] is Gtk.Button
    assert "Button" in dir(Gtk)


def test_bound_method_does_not_keep_receiver_alive():
    class Receiver:
        calls = []

        def on_clicked(self, _):
            self.calls.append(1)

    button, receiver = Gtk.Button(), Receiver()
    gone = weakref.ref(receiver)
    button.clicked.connect(receiver.on_clicked)
    button.clicked.emit()
    assert Receiver.calls == [1]
    del receiver
    gc.collect()
    assert gone() is None
    button.clicked.emit()
    assert Receiver.calls == [1]
    assert button._pyliite4_handlers == []


def test_gobject_receiver_stays_connected_while_it_lives():
    class Target(Gtk.Box):
        calls = []

        def on_clicked(self, _):
            self.calls.append(1)

    parent, button = Gtk.Box(), Gtk.Button()
    target = Target()
    parent.append(target)
    button.clicked.connect(target.on_clicked)
    del target
    gc.collect()
    # The parent still holds the GObject, so the connection must survive.
    button.clicked.emit()
    assert Target.calls == [1]
    parent.remove(parent.get_first_child())
    gc.collect()
    button.clicked.emit()
    assert Target.calls == [1]


def test_lambda_is_held_strongly():
    button = Gtk.Button()
    calls = []
    button.clicked.connect(lambda _: calls.append(1))
    gc.collect()
    button.clicked.emit()
    assert calls == [1]


def test_method_on_sender_does_not_leak():
    class Self(Gtk.Button):
        def __init__(self):
            super().__init__()
            self.count = 0
            self.clicked.connect(self.on_clicked)

        def on_clicked(self, _):
            self.count += 1

    widget = Self()
    widget.clicked.emit()
    assert widget.count == 1


def test_property_attributes():
    button = Gtk.Button(label="a")
    assert button.label == "a"
    button.label = "b"
    assert button.get_label() == "b"
    box = Gtk.Box(margin_top=4)
    assert box.margin_top == 4
    box.margin_top = 5
    assert box.get_margin_top() == 5
    # Comes from the Gtk.Orientable interface.
    box.orientation = Gtk.Orientation.VERTICAL
    assert box.get_orientation() == Gtk.Orientation.VERTICAL


def test_property_notify_fires_on_attribute_set():
    button = Gtk.Button()
    calls = []
    button.notify["label"].connect(lambda *_: calls.append(1))
    button.label = "x"
    assert calls == [1]


def test_read_only_and_construct_only_properties_raise():
    widget = Gtk.Box()
    with pytest.raises(AttributeError, match="can't be set"):
        widget.scale_factor = 2
    with pytest.raises(AttributeError, match="can't be set"):
        Gio.ListStore.new(GObject.Object).item_type = GObject.Object
    assert widget.scale_factor >= 1


def test_methods_and_plain_attributes_are_not_properties():
    class Custom(Gtk.Box):
        pass

    custom = Custom()
    custom.anything = 3
    assert custom.anything == 3
    with pytest.raises(AttributeError):
        custom.no_such
    # A signal and method called "hide" still win over everything else.
    assert isinstance(custom.hide, SignalMethod)
