import os

from PyLiite4 import Adw, Gdk, GLib, Gtk

# The demo's version control tag; the C build takes it from git with meson's vcs_tag().
ADW_DEMO_VCS_TAG = "PyLiite4"


def get_gtk_info() -> tuple[str, str]:
    """Copied and adapted from gtk/inspector/general.c"""
    display = Gdk.Display.get_default()
    display_type = display.__gtype__.name

    backend = {"GdkX11Display": "X11",
               "GdkWaylandDisplay": "Wayland",
               "GdkBroadwayDisplay": "Broadway",
               "GdkWin32Display": "Windows",
               "GdkMacosDisplay": "macOS"}.get(display_type, display_type)

    # C makes a surface with gdk_surface_new_toplevel() and a renderer for it. From Python, Gdk.Surface.destroy()
    # drops a reference that it doesn't own (it's annotated transfer none), so the surface's wrapper crashes when it
    # goes. A realized window has a surface and a renderer made the same way.
    window = Gtk.Window()
    window.realize()
    gsk_renderer = window.get_renderer()
    renderer_type = gsk_renderer.__gtype__.name
    renderer = {"GskVulkanRenderer": "Vulkan",
                "GskNglRenderer": "NGL",
                "GskGLRenderer": "GL",
                "GskCairoRenderer": "Cairo"}.get(renderer_type, renderer_type)

    window.destroy()

    return backend, renderer


def get_flatpak_info(group: str, key: str) -> str | None:
    keyfile = GLib.KeyFile()

    try:
        keyfile.load_from_file("/.flatpak-info", GLib.KeyFileFlags.NONE)
        return keyfile.get_string(group, key)
    except GLib.Error:
        return None


def adw_demo_generate_debug_info() -> str:
    string = []
    flatpak = os.name != "nt" and GLib.file_test("/.flatpak-info", GLib.FileTest.EXISTS)

    string.append(f"Libadwaita demo: {Adw.VERSION_S} ({ADW_DEMO_VCS_TAG})\n")
    string.append("\n")

    # The versions the typelibs, and so these bindings, were built against.
    string.append("Compiled against:\n")
    string.append(f"- GLib: {GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}\n")
    string.append(f"- GTK: {Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}\n")
    string.append("\n")

    string.append("Running against:\n")
    string.append("- GLib: {}.{}.{}\n".format(*GLib.glib_version))
    string.append(f"- GTK: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}\n")
    string.append("\n")

    os_name = GLib.get_os_info("NAME")
    os_version = GLib.get_os_info("VERSION")

    string.append("System:\n")
    string.append(f"- Name: {os_name}\n")
    string.append(f"- Version: {os_version}\n")
    string.append("\n")

    backend, renderer = get_gtk_info()

    string.append("GTK:\n")
    string.append(f"- GDK backend: {backend}\n")
    string.append(f"- GSK renderer: {renderer}\n")
    string.append("\n")

    if flatpak:
        runtime = get_flatpak_info("Application", "runtime")
        runtime_commit = get_flatpak_info("Instance", "runtime-commit")
        arch = get_flatpak_info("Instance", "arch")
        flatpak_version = get_flatpak_info("Instance", "flatpak-version")
        devel = get_flatpak_info("Instance", "devel")

        string.append("Flatpak:\n")
        string.append(f"- Runtime: {runtime}\n")
        string.append(f"- Runtime commit: {runtime_commit}\n")
        string.append(f"- Arch: {arch}\n")
        string.append(f"- Flatpak version: {flatpak_version}\n")
        string.append(f"- Devel: {'yes' if devel else 'no'}\n")
        string.append("\n")

    desktop = GLib.getenv("XDG_CURRENT_DESKTOP")
    session_desktop = GLib.getenv("XDG_SESSION_DESKTOP")
    session_type = GLib.getenv("XDG_SESSION_TYPE")
    lang = GLib.getenv("LANG")
    builder = GLib.getenv("INSIDE_GNOME_BUILDER")
    gtk_debug = GLib.getenv("GTK_DEBUG")
    gtk_theme = GLib.getenv("GTK_THEME")
    adw_debug_color_scheme = GLib.getenv("ADW_DEBUG_COLOR_SCHEME")
    adw_debug_accent_color = GLib.getenv("ADW_DEBUG_ACCENT_COLOR")
    adw_debug_high_contrast = GLib.getenv("ADW_DEBUG_HIGH_CONTRAST")
    adw_disable_portal = GLib.getenv("ADW_DISABLE_PORTAL")

    string.append("Environment:\n")
    string.append(f"- Desktop: {desktop}\n")
    string.append(f"- Session: {session_desktop} ({session_type})\n")
    string.append(f"- Language: {lang}\n")
    string.append(f"- Running inside Builder: {'yes' if builder else 'no'}\n")

    if gtk_debug:
        string.append(f"- GTK_DEBUG: {gtk_debug}\n")
    if gtk_theme:
        string.append(f"- GTK_THEME: {gtk_theme}\n")
    if adw_debug_color_scheme:
        string.append(f"- ADW_DEBUG_COLOR_SCHEME: {adw_debug_color_scheme}\n")
    if adw_debug_accent_color:
        string.append(f"- ADW_DEBUG_ACCENT_COLOR: {adw_debug_accent_color}\n")
    if adw_debug_high_contrast:
        string.append(f"- ADW_DEBUG_HIGH_CONTRAST: {adw_debug_high_contrast}\n")
    if adw_disable_portal:
        string.append(f"- ADW_DISABLE_PORTAL: {adw_disable_portal}\n")

    return "".join(string)
