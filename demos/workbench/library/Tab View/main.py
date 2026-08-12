from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

tab_view: Adw.TabView = workbench.builder.get_object("tab_view")
button_new_tab: Gtk.Button = workbench.builder.get_object("button_new_tab")
overview: Adw.TabOverview = workbench.builder.get_object("overview")
button_overview: Gtk.Button = workbench.builder.get_object("button_overview")
tab_count = 1

overview.create_tab.connect(lambda _: add_page())

button_overview.clicked.connect(lambda _: overview.set_open(True))

button_new_tab.clicked.connect(lambda _: add_page())


def add_page() -> Adw.TabPage:
    global tab_count
    title = f"Tab {tab_count}"
    page = create_page(title)
    tab_page = tab_view.append(page)
    tab_page.set_title(title)
    tab_page.set_live_thumbnail(True)

    tab_count += 1
    return tab_page


def create_page(title: str) -> Adw.StatusPage:
    page = Adw.StatusPage(
        title=title,
        vexpand=True,
    )
    return page
