from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

video: Gtk.Video = workbench.builder.get_object("video")
video.set_file(Gio.File.new_for_uri(workbench.resolve("./workbench-video.mp4")))


def on_pressed(*_: object) -> None:
    media_stream = video.get_media_stream()
    if media_stream.get_playing():
        media_stream.pause()
    else:
        media_stream.play()


click_gesture = Gtk.GestureClick()
click_gesture.pressed.connect(on_pressed)

video.add_controller(click_gesture)
