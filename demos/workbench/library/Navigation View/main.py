from PyLiite4 import Adw, GObject, Gtk

from demos.workbench import workbench

nav_view: Adw.NavigationView = workbench.builder.get_object("nav_view")
nav_pageone: Adw.NavigationPage = workbench.builder.get_object("nav_pageone")
next_button: Gtk.Button = workbench.builder.get_object("next_button")
previous_button: Gtk.Button = workbench.builder.get_object("previous_button")
nav_pagetwo: Adw.NavigationPage = workbench.builder.get_object("nav_pagetwo")
nav_pagethree: Adw.NavigationPage = workbench.builder.get_object("nav_pagethree")
nav_pagefour: Adw.NavigationPage = workbench.builder.get_object("nav_pagefour")
title: Gtk.Label = workbench.builder.get_object("title")


def on_next_button_clicked(_button: Gtk.Button) -> None:
    page = nav_view.get_visible_page()
    if page == nav_pageone:
        nav_view.push(nav_pagetwo)
    elif page == nav_pagetwo:
        nav_view.push(nav_pagethree)
    elif page == nav_pagethree:
        nav_view.push(nav_pagefour)


def on_page_changed(_view: Adw.NavigationView, _visible_page: GObject.ParamSpec) -> None:
    previous_button.set_sensitive(nav_view.get_visible_page() != nav_pageone)
    next_button.set_sensitive(nav_view.get_visible_page() != nav_pagefour)
    title.set_label(nav_view.get_visible_page().get_title())


next_button.clicked.connect(on_next_button_clicked)

previous_button.clicked.connect(lambda _: nav_view.pop())

nav_view.notify["visible-page"].connect(on_page_changed)
