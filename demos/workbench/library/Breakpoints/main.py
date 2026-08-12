from PyLiite4 import Adw

from demos.workbench import workbench

breakpoint: Adw.Breakpoint = workbench.builder.get_object("breakpoint")

breakpoint.apply.connect(lambda _widget: print("Breakpoint Applied"))
breakpoint.unapply.connect(lambda _widget: print("Breakpoint Unapplied"))
