import re

from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

button: Gtk.ToggleButton = workbench.builder.get_object("button_search")
searchbar: Gtk.SearchBar = workbench.builder.get_object("searchbar")
searchentry: Gtk.SearchEntry = workbench.builder.get_object("searchentry")
stack: Gtk.Stack = workbench.builder.get_object("stack")
main_page: Adw.StatusPage = workbench.builder.get_object("main_page")
search_page: Gtk.ScrolledWindow = workbench.builder.get_object("search_page")
status_page: Adw.StatusPage = workbench.builder.get_object("status_page")
listbox: Gtk.ListBox = workbench.builder.get_object("listbox")

button.clicked.connect(lambda *_: searchbar.set_search_mode(not searchbar.get_search_mode()))

searchbar.notify["search-mode-enabled"].connect(
    lambda *_: stack.set_visible_child(search_page if searchbar.get_search_mode() else main_page)
)

fruits = [
    "Apple 🍎️",
    "Orange 🍊️",
    "Pear 🍐️",
    "Watermelon 🍉️",
    "Melon 🍈️",
    "Pineapple 🍍️",
    "Grape 🍇️",
    "Kiwi 🥝️",
    "Banana 🍌️",
    "Peach 🍑️",
    "Cherry 🍒️",
    "Strawberry 🍓️",
    "Blueberry 🫐️",
    "Mango 🥭️",
    "Bell Pepper 🫑️",
]
results_count = 0

for name in fruits:
    row = Adw.ActionRow(title=name)
    listbox.append(row)


def filter(row: Adw.ActionRow) -> bool:
    global results_count
    try:
        match = re.search(searchentry.get_text(), row.get_title(), re.IGNORECASE) is not None
    except re.error:
        match = False
    if match:
        results_count += 1
    return match


listbox.set_filter_func(filter)


def on_search_changed(_search_widget: Gtk.SearchEntry) -> None:
    global results_count
    results_count = -1
    listbox.invalidate_filter()
    if results_count == -1:
        stack.set_visible_child(status_page)
    elif searchbar.get_search_mode():
        stack.set_visible_child(search_page)


searchentry.search_changed.connect(on_search_changed)
