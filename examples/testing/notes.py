"""A notes window for tests/test_notes.py to drive."""

from PyLiite4 import Adw, Gio, Gtk


class NotesWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title="Notes", default_width=420, default_height=480)
        self.add_button = Gtk.Button(label="Add", sensitive=False, css_classes=["suggested-action"])
        self.add_button.clicked.connect(lambda button: self.add_note())
        self.entry = Gtk.Entry(placeholder_text="New note", hexpand=True)
        self.entry.changed.connect(lambda entry: self.add_button.set_sensitive(bool(entry.get_text().strip())))
        self.entry.activate.connect(lambda entry: self.add_note())
        top = Gtk.Box(spacing=6, margin_top=12, margin_start=12, margin_end=12)
        top.append(self.entry)
        top.append(self.add_button)

        self.notes = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                                 margin_start=12, margin_end=12, valign=Gtk.Align.START)
        self.count = Gtk.Label(label="No notes", css_classes=["dim-label"], margin_bottom=12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(top)
        box.append(Gtk.ScrolledWindow(child=self.notes, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
        box.append(self.count)
        view = Adw.ToolbarView(content=box)
        view.add_top_bar(Adw.HeaderBar())
        self.set_content(view)

        # Ctrl+N puts the cursor in the entry, from anywhere in the window.
        focus = Gio.SimpleAction(name="new-note")
        focus.activate.connect(lambda action, parameter: self.focus_entry())
        self.add_action(focus)
        application.set_accels_for_action("win.new-note", ["<Control>n"])

    def focus_entry(self) -> None:
        self.entry.grab_focus()

    def add_note(self) -> None:
        text = self.entry.get_text().strip()
        if not text:
            return
        row = Adw.ActionRow(title=text)
        remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove", valign=Gtk.Align.CENTER,
                            css_classes=["flat"])
        remove.update_property([Gtk.AccessibleProperty.LABEL], [f"Remove “{text}”"])
        remove.clicked.connect(lambda button: self.remove_note(row))
        row.add_suffix(remove)
        self.notes.append(row)
        self.entry.set_text("")
        self.update_count()

    def remove_note(self, row: Adw.ActionRow) -> None:
        self.notes.remove(row)
        self.update_count()

    def titles(self) -> list[str]:
        titles = []
        row = self.notes.get_first_child()
        while row is not None:
            if isinstance(row, Adw.ActionRow):
                titles.append(row.get_title())
            row = row.get_next_sibling()
        return titles

    def update_count(self) -> None:
        count = len(self.titles())
        self.count.set_label("No notes" if count == 0 else "1 note" if count == 1 else f"{count} notes")
