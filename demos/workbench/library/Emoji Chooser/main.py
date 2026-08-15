from PyLiite4 import Gtk

from demos.workbench import workbench

emoji_chooser: Gtk.EmojiChooser = workbench.builder.get_object("emoji_chooser")
button: Gtk.Button = workbench.builder.get_object("button")

emoji_chooser.emoji_picked.connect(lambda _chooser, emoji: button.set_label(emoji))
