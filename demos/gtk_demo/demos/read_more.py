"""Read More
#Keywords: GtkInscription

A simple implementation of a widget that can either
display a lot of text or just the first few lines with a
"Read More" button.
"""

from PyLiite4 import GLib, Gtk

window: Gtk.Window | None = None


class ReadMore(Gtk.Widget):
    __gtype_name__ = "ReadMore"

    label: Gtk.Label | None
    inscription: Gtk.Inscription
    box: Gtk.Box | None
    show_more: bool

    def __init__(self) -> None:
        super().__init__()
        self.show_more = False

        self.label = Gtk.Label()
        self.label.set_xalign(0.0)
        self.label.set_yalign(0.0)
        self.label.set_wrap(True)
        self.label.set_width_chars(3)
        self.label.set_max_width_chars(30)
        self.label.set_parent(self)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.box.set_vexpand(False)
        self.box.set_parent(self)

        self.inscription = Gtk.Inscription()
        self.inscription.set_xalign(0.0)
        self.inscription.set_yalign(0.0)
        self.inscription.set_min_lines(3)
        self.inscription.set_nat_chars(30)
        self.inscription.set_vexpand(True)
        self.box.append(self.inscription)

        button = Gtk.Button.new_with_label("Read More")
        button.clicked.connect(self.read_more_clicked)
        self.box.append(button)

    def do_get_request_mode(self) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        other = Gtk.Orientation(1 - orientation)

        if self.show_more:
            min_check = GLib.MAXINT
        elif for_size >= 0:
            min_check = self.box.measure(other, -1)[0]
        else:
            min_check = -1

        if min_check > for_size:
            return self.label.measure(orientation, for_size)

        elif for_size >= 0:
            min_check = self.label.measure(other, -1)[0]
        else:
            min_check = -1

        if min_check > for_size:
            return self.box.measure(orientation, for_size)

        label_min, label_nat, label_min_baseline, label_nat_baseline = self.label.measure(orientation, for_size)
        box_min, box_nat, box_min_baseline, box_nat_baseline = self.box.measure(orientation, for_size)

        # FIXME: Figure out baselines!
        return min(label_min, box_min), min(label_nat, box_nat), -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        if self.show_more:
            show_more = True
        else:
            # check to see if we have enough space to show all text
            needed = self.label.measure(Gtk.Orientation.VERTICAL, width)[0]

            show_more = needed <= height

        self.label.set_child_visible(show_more)
        self.box.set_child_visible(not show_more)

        if show_more:
            self.label.allocate(width, height, baseline, None)
        else:
            self.box.allocate(width, height, baseline, None)

    def do_dispose(self) -> None:
        if self.label is not None:
            self.label.unparent()
            self.label = None
        if self.box is not None:
            self.box.unparent()
            self.box = None

        super().do_dispose()

    def read_more_clicked(self, button: Gtk.Button) -> None:
        self.show_more = True
        self.queue_resize()

    def set_text(self, text: str) -> None:
        self.label.set_label(text)
        self.inscription.set_text(text)


def read_more_new(text: str) -> ReadMore:
    self = ReadMore()

    self.set_text(text)

    return self


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Read More")
        window.destroy.connect(destroyed)

        readmore = read_more_new(
            "I'd just like to interject for a moment. What you're referring to as Linux, is in fact, GNU/Linux, or as I've recently taken to calling it, GNU plus Linux. Linux is not an operating system unto itself, but rather another free component of a fully functioning GNU system made useful by the GNU corelibs, shell utilities and vital system components comprising a full OS as defined by POSIX.\n"  # noqa: E501
            "\n"
            "Many computer users run a modified version of the GNU system every day, without realizing it. Through a peculiar turn of events, the version of GNU which is widely used today is often called \"Linux\", and many of its users are not aware that it is basically the GNU system, developed by the GNU Project.\n"  # noqa: E501
            "\n"
            "There really is a Linux, and these people are using it, but it is just a part of the system they use. Linux is the kernel: the program in the system that allocates the machine's resources to the other programs that you run. The kernel is an essential part of an operating system, but useless by itself; it can only function in the context of a complete operating system. Linux is normally used in combination with the GNU operating system: the whole system is basically GNU with Linux added, or GNU/Linux. All the so-called \"Linux\" distributions are really distributions of GNU/Linux.")  # noqa: E501
        window.set_child(readmore)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
