from PyLiite4 import Gtk

from demos.workbench import workbench

# Workbench's main.blp for this demo is the template itself, handed to the code as workbench.template. GtkBuilder
# can't build a <template> on its own, so it's here, converted to XML, and main.ui holds the preview instead: the
# FlowBox that the original creates in code and shows with workbench.preview().
template = """\
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <requires lib="gtk" version="4.0"/>
  <template class="AwesomeButton" parent="GtkButton">
    <signal name="clicked" handler="onclicked"/>
    <child>
      <object class="GtkImage">
        <property name="halign">center</property>
        <property name="icon-name">emoji-people-symbolic</property>
      </object>
    </child>
  </template>
</interface>
"""


@Gtk.Template(string=template)
class AwesomeButton(Gtk.Button):
    __gtype_name__ = "AwesomeButton"

    @Gtk.Template.Callback()
    def onclicked(self, _button: Gtk.Button) -> None:
        print("Clicked")


container: Gtk.FlowBox = workbench.builder.get_object("container")

for i in range(100):
    widget = AwesomeButton()
    container.append(widget)
