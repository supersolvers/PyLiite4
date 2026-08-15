from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

controls: Gtk.MediaControls = workbench.builder.get_object("controls")

audio_files = {
    "sound": "./Dog.ogg",
    "music": "./Chopin-nocturne-op-9-no-2.ogg",
}


def on_button_clicked(_button: Gtk.Button, file: Gio.File) -> None:
    if controls.get_media_stream():
        controls.get_media_stream().set_playing(False)

    controls.set_media_stream(Gtk.MediaFile.new_for_file(file))
    controls.get_media_stream().play()


for button_name, file_name in audio_files.items():
    button: Gtk.Button = workbench.builder.get_object(f"button_{button_name}")
    file = Gio.File.new_for_uri(workbench.resolve(file_name))
    button.clicked.connect(on_button_clicked, file)
