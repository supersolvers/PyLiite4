"""Video Player
#Keywords: GtkVideo, GtkMediaStream, GtkMediaFile, GdkPaintable
#Keywords: GtkMediaControls

This is a simple video player using just GTK widgets.
"""

from PyLiite4 import Gdk, Gio, GLib, Gtk

window: Gtk.Window | None = None


def open_dialog_response_cb(dialog: Gtk.FileDialog, result: Gio.AsyncResult, video: Gtk.Video) -> None:
    try:
        file = dialog.open_finish(result)
    except GLib.Error:
        file = None
    if file is not None:
        video.set_file(file)


def open_clicked_cb(button: Gtk.Widget, video: Gtk.Video) -> None:
    dialog = Gtk.FileDialog()
    dialog.set_title("Select a video")

    filters = Gio.ListStore(item_type=Gtk.FileFilter)

    filter = Gtk.FileFilter()
    filter.add_pattern("*")
    filter.set_name("All Files")
    filters.append(filter)

    filter = Gtk.FileFilter()
    filter.add_mime_type("image/*")
    filter.set_name("Images")
    filters.append(filter)

    filter = Gtk.FileFilter()
    filter.add_mime_type("video/*")
    filter.set_name("Video")
    filters.append(filter)

    dialog.set_default_filter(filter)

    dialog.set_filters(filters)

    dialog.open(button.get_root(), None, open_dialog_response_cb, video)


def logo_clicked_cb(button: Gtk.Widget, video: Gtk.Video) -> None:
    file = Gio.File.new_for_uri("resource:///images/gtk-logo.webm")
    video.set_file(file)


def bbb_clicked_cb(button: Gtk.Widget, video: Gtk.Video) -> None:
    file = Gio.File.new_for_uri("https://download.blender.org/peach/trailer/trailer_400p.ogg")
    video.set_file(file)


def fullscreen_clicked_cb(button: Gtk.Widget) -> None:
    widget_window = button.get_root()

    widget_window.fullscreen()


def toggle_fullscreen(widget: Gtk.Widget, args: GLib.Variant | None) -> bool:
    surface = widget.get_surface()
    state = surface.get_state()

    if state & Gdk.ToplevelState.FULLSCREEN:
        widget.unfullscreen()
    else:
        widget.fullscreen()

    return True


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Video Player")
        window.set_default_size(600, 400)
        window.destroy.connect(destroyed)

        video = Gtk.Video()
        video.set_autoplay(True)
        video.set_graphics_offload(Gtk.GraphicsOffloadEnabled.ENABLED)
        window.set_child(video)

        title = Gtk.HeaderBar()
        window.set_titlebar(title)

        button = Gtk.Button.new_with_mnemonic("_Open")
        button.clicked.connect(open_clicked_cb, video)
        title.pack_start(button)

        button = Gtk.Button()
        image = Gtk.Image.new_from_resource("/cursors/images/gtk_logo_cursor.png")
        image.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[button]])
        image.set_pixel_size(24)
        button.set_child(image)
        button.clicked.connect(logo_clicked_cb, video)
        button.update_property([Gtk.AccessibleProperty.LABEL], ["GTK Logo"])
        title.pack_start(button)

        button = Gtk.Button()
        image = Gtk.Image.new_from_resource("/video-player/bbb.png")
        image.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[button]])
        image.set_pixel_size(24)
        button.set_child(image)
        button.clicked.connect(bbb_clicked_cb, video)
        button.update_property([Gtk.AccessibleProperty.LABEL], ["Big Buck Bunny"])
        title.pack_start(button)

        fullscreen_button = Gtk.Button.new_from_icon_name("view-fullscreen-symbolic")
        fullscreen_button.clicked.connect(fullscreen_clicked_cb)
        fullscreen_button.update_property([Gtk.AccessibleProperty.LABEL], ["Fullscreen"])

        title.pack_end(fullscreen_button)

        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        window.add_controller(controller)
        controller.add_shortcut(Gtk.Shortcut.new(Gtk.KeyvalTrigger.new(Gdk.KEY_F11, 0),
                                                 Gtk.CallbackAction.new(toggle_fullscreen)))

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
