from PyLiite4 import Gtk, Manette

from demos.workbench import workbench

stack: Gtk.Stack = workbench.builder.get_object("stack")
button_rumble: Gtk.Button = workbench.builder.get_object("button_rumble")

devices: set[Manette.Device] = set()

stack.set_visible_child_name("connect")


def on_rumble_button_clicked(*_: object) -> None:
    for device in devices:
        if device.has_rumble():
            device.rumble(1000, 1500, 200)


button_rumble.clicked.connect(on_rumble_button_clicked)


def on_button_press_event(device: Manette.Device, event: Manette.Event) -> None:
    success, button = event.get_button()
    print(
        f"{device.get_name()}: press {button if success else event.get_hardware_code()}"
    )


def on_button_release_event(device: Manette.Device, event: Manette.Event) -> None:
    success, button = event.get_button()
    print(
        f"{device.get_name()}: release {button if success else event.get_hardware_code()}"
    )


def on_hat_axis_event(device: Manette.Device, event: Manette.Event) -> None:
    _, hat_axis, hat_value = event.get_hat()
    print(f"{device.get_name()}: moved axis {hat_axis} to {hat_value}")


def on_absolute_axis_event(device: Manette.Device, event: Manette.Event) -> None:
    _, axis, value = event.get_absolute()
    if abs(value) > 0.2:
        print(f"{device.get_name()}: moved axis {axis} to {value}")


def on_device(_: Manette.Monitor | None, device: Manette.Device) -> None:
    print("Device connected:", device.get_name())

    # Face and shoulder buttons
    device.button_press_event.connect(on_button_press_event)

    device.button_release_event.connect(on_button_release_event)

    # D-pads
    device.hat_axis_event.connect(on_hat_axis_event)

    # Analog axes: triggers and joysticks
    device.absolute_axis_event.connect(on_absolute_axis_event)

    devices.add(device)
    stack.set_visible_child_name("watch")


def on_device_disconnected(_: Manette.Monitor, device: Manette.Device) -> None:
    print(f"Device Disconnected: {device.get_name()}")

    devices.remove(device)
    stack.set_visible_child_name("connect" if len(devices) < 1 else "watch")


monitor = Manette.Monitor()
monitor_iter = monitor.iterate()

while True:
    has_next, device = monitor_iter.next()
    if device:
        on_device(None, device)
    if not has_next:
        break

monitor.device_connected.connect(on_device)
monitor.device_disconnected.connect(on_device_disconnected)
