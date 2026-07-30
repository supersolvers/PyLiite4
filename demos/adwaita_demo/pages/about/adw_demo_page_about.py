from gettext import gettext as _

from PyLiite4 import Adw, Gtk

from .adw_demo_page_about_ui import AdwDemoPageAboutChildren, template


@template
class AdwDemoPageAbout(AdwDemoPageAboutChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageAbout"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        developers = [
            "Angela Avery <angela@example.org>",
        ]

        artists = [
            "GNOME Design Team",
        ]

        special_thanks = [
            "My cat",
        ]

        release_notes = """\
<p>\
  This release adds the following features:\
</p>\
<ul>\
  <li>Added a way to export fonts.</li>\
  <li>Better support for <code>monospace</code> fonts.</li>\
  <li>Added a way to preview <em>italic</em> text.</li>\
  <li>Bug fixes and performance improvements.</li>\
  <li>Translation updates.</li>\
</ul>\
  """

        about = Adw.AboutDialog(
            application_icon="org.example.Typeset",
            application_name=_("Typeset"),
            developer_name=_("Angela Avery"),
            version="1.2.3",
            release_notes_version="1.2.0",
            release_notes=release_notes,
            comments=_("Typeset is an app that doesn’t exist and is used as an example content for this about dialog."),
            website="https://example.org",
            issue_url="https://example.org",
            support_url="https://example.org",
            copyright="© 2022 Angela Avery",
            license_type=Gtk.License.LGPL_2_1,
            developers=developers,
            artists=artists,
            translator_credits=_("translator-credits"),
        )

        about.add_link(_("_Documentation"),
                       "https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.AboutDialog.html")

        about.add_legal_section(_("Fonts"),
                                None,
                                Gtk.License.CUSTOM,
                                "This application uses font data from <a href='https://example.org'>somewhere</a>.")

        about.add_acknowledgement_section(_("Special thanks to"),
                                          special_thanks)

        about.add_other_app("org.gnome.Adwaita1.Demo",
                            _("Adwaita Demo"),
                            _("Tour of the features in Libadwaita"))

        about.present(self)


AdwDemoPageAbout.install_action("demo.run", None, AdwDemoPageAbout.demo_run_cb)
