"""Assistant

Demonstrates a sample multi-step assistant with GtkAssistant. Assistants
are used to divide an operation into several simpler sequential steps,
and to guide the user through these steps.
"""

from collections.abc import Callable

from PyLiite4 import GLib, Gtk

progress_bar: Gtk.ProgressBar | None = None


def apply_changes_gradually(data: Gtk.Assistant) -> bool:
    fraction = progress_bar.get_fraction()
    fraction += 0.05

    if fraction < 1.0:
        progress_bar.set_fraction(fraction)
        return GLib.SOURCE_CONTINUE
    else:
        # Close automatically once changes are fully applied.
        data.destroy()
        return GLib.SOURCE_REMOVE


def on_assistant_apply(widget: Gtk.Assistant) -> None:
    # A timer simulates changes that take a few seconds to apply.
    GLib.timeout_add(100, apply_changes_gradually, widget)


def on_assistant_close_cancel(widget: Gtk.Assistant) -> None:
    widget.destroy()


def on_assistant_prepare(widget: Gtk.Assistant, page: Gtk.Widget) -> None:
    current_page = widget.get_current_page()
    n_pages = widget.get_n_pages()

    title = f"Sample assistant ({current_page + 1} of {n_pages})"
    widget.set_title(title)

    # The fourth page (counting from zero) is the progress page. The user clicked Apply to get here, so the assistant
    # commits: the changes up to this point are permanent and can't be cancelled or revisited.
    if current_page == 3:
        widget.commit()


def on_entry_changed(widget: Gtk.Entry, data: Callable[[], Gtk.Assistant]) -> None:
    assistant = data()
    page_number = assistant.get_current_page()
    current_page = assistant.get_nth_page(page_number)
    text = widget.get_text()

    if text:
        assistant.set_page_complete(current_page, True)
    else:
        assistant.set_page_complete(current_page, False)


def create_page1(assistant: Gtk.Assistant) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)

    label = Gtk.Label(label="You must fill out this entry to continue:")
    box.append(label)

    entry = Gtk.Entry()
    entry.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])
    entry.set_activates_default(True)
    entry.set_valign(Gtk.Align.CENTER)
    box.append(entry)
    # Passed weakly: a strong reference from a child's handler would keep the assistant alive after it's destroyed.
    entry.changed.connect(on_entry_changed, assistant.weak_ref())

    assistant.append_page(box)
    assistant.set_page_title(box, "Page 1")
    assistant.set_page_type(box, Gtk.AssistantPageType.INTRO)


def create_page2(assistant: Gtk.Assistant) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)

    checkbutton = Gtk.CheckButton.new_with_label("This is optional data, you may continue "
                                                 "even if you do not check this")
    checkbutton.set_valign(Gtk.Align.CENTER)
    box.append(checkbutton)

    assistant.append_page(box)
    assistant.set_page_complete(box, True)
    assistant.set_page_title(box, "Page 2")


def create_page3(assistant: Gtk.Assistant) -> None:
    label = Gtk.Label(label="This is a confirmation page, press 'Apply' to apply changes")

    assistant.append_page(label)
    assistant.set_page_type(label, Gtk.AssistantPageType.CONFIRM)
    assistant.set_page_complete(label, True)
    assistant.set_page_title(label, "Confirmation")


def create_page4(assistant: Gtk.Assistant) -> None:
    global progress_bar

    progress_bar = Gtk.ProgressBar()
    progress_bar.set_halign(Gtk.Align.FILL)
    progress_bar.set_valign(Gtk.Align.CENTER)
    progress_bar.set_hexpand(True)
    progress_bar.set_margin_start(40)
    progress_bar.set_margin_end(40)

    assistant.append_page(progress_bar)
    assistant.set_page_type(progress_bar, Gtk.AssistantPageType.PROGRESS)
    assistant.set_page_title(progress_bar, "Applying changes")

    progress_bar.update_property([Gtk.AccessibleProperty.LABEL], ["Applying changes"])

    # Keeps the assistant window from being closed while it's "busy" applying changes.
    assistant.set_page_complete(progress_bar, False)


# The assistant, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
assistant_ref: Callable[[], Gtk.Assistant | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Assistant:
    global assistant_ref

    assistant = assistant_ref()
    if assistant is None:
        assistant = Gtk.Assistant()

        assistant.set_default_size(-1, 300)

        assistant.set_display(do_widget.get_display())
        assistant_ref = assistant.weak_ref()

        create_page1(assistant)
        create_page2(assistant)
        create_page3(assistant)
        create_page4(assistant)

        assistant.cancel.connect(on_assistant_close_cancel)
        assistant.close.connect(on_assistant_close_cancel)
        assistant.apply.connect(on_assistant_apply)
        assistant.prepare.connect(on_assistant_prepare)

    if not assistant.get_visible():
        assistant.set_visible(True)
    else:
        assistant.destroy()

    return assistant
