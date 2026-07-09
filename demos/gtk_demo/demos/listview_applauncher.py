"""Lists/Application launcher
#Keywords: GtkListItemFactory, GListModel

This demo uses the GtkListView widget as a fancy application launcher.

It is also a very small introduction to listviews.
"""

from PyLiite4 import Gio, GLib, Gtk


def create_application_list() -> Gio.ListModel:
    """This is the function that creates the GListModel that we need.
    GTK list widgets need a GListModel to display, as models support change
    notifications.
    Unfortunately various older APIs do not provide list models, so we create
    our own.
    """
    # We use a GListStore here, which is a simple array-like list implementation
    # for manual management.
    # List models need to know what type of data they provide, so we need to
    # provide the type here. As we want to do a list of applications, GAppInfo
    # is the object we provide.
    store = Gio.ListStore(item_type=Gio.AppInfo)

    apps = Gio.AppInfo.get_all()

    for app in apps:
        store.append(app)

    return store


def setup_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    """This is the function we use for setting up new listitems to display.
    We add just an GtkImage and a GtkLabel here to display the application's
    icon and name, as this is just a simple demo.
    """
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    image = Gtk.Image()
    image.update_property([Gtk.AccessibleProperty.LABEL], ["App icon"])
    image.set_icon_size(Gtk.IconSize.LARGE)
    box.append(image)
    label = Gtk.Label(label="")
    box.append(label)
    list_item.set_child(box)


def bind_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    """Here we need to prepare the listitem for displaying its item. We get the
    listitem already set up from the previous function, so we can reuse the
    GtkImage widget we set up above.
    We get the item - which we know is a GAppInfo because it comes out of
    the model we set up above, grab its icon and display it.
    """
    image = list_item.get_child().get_first_child()
    label = image.get_next_sibling()
    app_info = list_item.get_item()

    icon = app_info.get_icon()
    # C passes a missing icon to gtk_image_set_from_gicon(), which clears the image, but the introspection data
    # doesn't allow None there
    if icon is not None:
        image.set_from_gicon(icon)
    else:
        image.clear()
    label.set_label(app_info.get_display_name())
    list_item.set_accessible_label(app_info.get_display_name())


# In more complex code, we would also need functions to unbind and teardown
# the listitem, but this is simple code, so the default implementations are
# enough. If we had connected signals, this step would have been necessary.
#
# The GtkSignalListItemFactory documentation contains more information about
# this step.


def activate_cb(list: Gtk.ListView, position: int) -> None:
    """This function is called whenever an item in the list is activated. This is
    the simple way to allow reacting to the Enter key or double-clicking on a
    listitem.
    Of course, it is possible to use far more complex interactions by turning
    off activation and adding buttons or other widgets in the setup function
    above, but this is a simple demo, so we'll use the simple way.
    """
    app_info = list.get_model().get_item(position)

    # Prepare the context for launching the application and launch it. This
    # code is explained in detail in the documentation for GdkAppLaunchContext
    # and GAppInfo.
    context = list.get_display().get_app_launch_context()
    try:
        app_info.launch(None, context)
    except GLib.Error as error:
        # And because error handling is important, even a simple demo has it:
        # We display an error dialog that something went wrong.
        dialog = Gtk.AlertDialog(message=f"Could not launch {app_info.get_display_name()}")
        dialog.set_detail(error.message)
        dialog.show(list.get_root())


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        # Create a window and set a few defaults
        window = Gtk.Window()
        window.set_default_size(640, 320)
        window.set_display(do_widget.get_display())
        window.set_title("Application Launcher")
        window.close_request.connect(close_request)

        # The GtkListitemFactory is what is used to create GtkListItems
        # to display the data from the model. So it is absolutely necessary
        # to create one.
        # We will use a GtkSignalListItemFactory because it is the simplest
        # one to use. Different ones are available for different use cases.
        # The most powerful one is GtkBuilderListItemFactory which uses
        # GtkBuilder .ui files, so it requires little code.
        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_listitem_cb)
        factory.bind.connect(bind_listitem_cb)

        # And of course we need to set the data model. Here we call the function
        # we wrote above that gives us the list of applications. Then we set
        # it on the list widget.
        # The list will now take items from the model and use the factory
        # to create as many listitems as it needs to show itself to the user.
        model = create_application_list()

        # Create the list widget here.
        list = Gtk.ListView.new(Gtk.SingleSelection.new(model), factory)

        # We connect the activate signal here. It's the function we defined
        # above for launching the selected application.
        list.activate.connect(activate_cb)

        # List widgets should always be contained in a GtkScrolledWindow,
        # because otherwise they might get too large or they might not
        # be scrollable.
        sw = Gtk.ScrolledWindow()
        window.set_child(sw)
        sw.set_child(list)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
