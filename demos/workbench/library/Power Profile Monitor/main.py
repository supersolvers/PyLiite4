from PyLiite4 import Adw, Gio, GObject

from demos.workbench import workbench

power_profile_monitor = Gio.PowerProfileMonitor.dup_default()
overlay: Adw.ToastOverlay = workbench.builder.get_object("overlay")


def on_power_saver_enabled(monitor: Gio.PowerProfileMonitor, _paramspec: GObject.ParamSpec) -> None:
    toast = Adw.Toast(
        priority=Adw.ToastPriority.HIGH,
    )

    if monitor.get_power_saver_enabled():
        toast.set_title("Power Saver Enabled")
    else:
        toast.set_title("Power Saver Disabled")

    overlay.add_toast(toast)


power_profile_monitor.notify["power-saver-enabled"].connect(on_power_saver_enabled)
