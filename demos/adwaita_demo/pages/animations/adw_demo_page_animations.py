from gettext import gettext as _

from PyLiite4 import Adw, GObject, Graphene, Gsk, Gtk

from .adw_demo_page_animations_ui import AdwDemoPageAnimationsChildren, template

EASING_NAMES = {
    Adw.Easing.LINEAR: _("Linear"),
    Adw.Easing.EASE_IN_QUAD: _("Ease-in (Quadratic)"),
    Adw.Easing.EASE_OUT_QUAD: _("Ease-out (Quadratic)"),
    Adw.Easing.EASE_IN_OUT_QUAD: _("Ease-in-out (Quadratic)"),
    Adw.Easing.EASE_IN_CUBIC: _("Ease-in (Cubic)"),
    Adw.Easing.EASE_OUT_CUBIC: _("Ease-out (Cubic)"),
    Adw.Easing.EASE_IN_OUT_CUBIC: _("Ease-in-out (Cubic)"),
    Adw.Easing.EASE_IN_QUART: _("Ease-in (Quartic)"),
    Adw.Easing.EASE_OUT_QUART: _("Ease-out (Quartic)"),
    Adw.Easing.EASE_IN_OUT_QUART: _("Ease-in-out (Quartic)"),
    Adw.Easing.EASE_IN_QUINT: _("Ease-in (Quintic)"),
    Adw.Easing.EASE_OUT_QUINT: _("Ease-out (Quintic)"),
    Adw.Easing.EASE_IN_OUT_QUINT: _("Ease-in-out (Quintic)"),
    Adw.Easing.EASE_IN_SINE: _("Ease-in (Sine)"),
    Adw.Easing.EASE_OUT_SINE: _("Ease-out (Sine)"),
    Adw.Easing.EASE_IN_OUT_SINE: _("Ease-in-out (Sine)"),
    Adw.Easing.EASE_IN_EXPO: _("Ease-in (Exponential)"),
    Adw.Easing.EASE_OUT_EXPO: _("Ease-out (Exponential)"),
    Adw.Easing.EASE_IN_OUT_EXPO: _("Ease-in-out (Exponential)"),
    Adw.Easing.EASE_IN_CIRC: _("Ease-in (Circular)"),
    Adw.Easing.EASE_OUT_CIRC: _("Ease-out (Circular)"),
    Adw.Easing.EASE_IN_OUT_CIRC: _("Ease-in-out (Circular)"),
    Adw.Easing.EASE_IN_ELASTIC: _("Ease-in (Elastic)"),
    Adw.Easing.EASE_OUT_ELASTIC: _("Ease-out (Elastic)"),
    Adw.Easing.EASE_IN_OUT_ELASTIC: _("Ease-in-out (Elastic)"),
    Adw.Easing.EASE_IN_BACK: _("Ease-in (Back)"),
    Adw.Easing.EASE_OUT_BACK: _("Ease-out (Back)"),
    Adw.Easing.EASE_IN_OUT_BACK: _("Ease-in-out (Back)"),
    Adw.Easing.EASE_IN_BOUNCE: _("Ease-in (Bounce)"),
    Adw.Easing.EASE_OUT_BOUNCE: _("Ease-out (Bounce)"),
    Adw.Easing.EASE_IN_OUT_BOUNCE: _("Ease-in-out (Bounce)"),
    Adw.Easing.EASE: _("Ease"),
    Adw.Easing.EASE_IN: _("Ease-in"),
    Adw.Easing.EASE_OUT: _("Ease-out"),
    Adw.Easing.EASE_IN_OUT: _("Ease-in-out"),
}


def timed_animation_measure(widget: Gtk.Widget, orientation: Gtk.Orientation,
                            for_size: int) -> tuple[int, int, int, int]:
    child = widget.get_first_child()

    if not child:
        return 0, 0, -1, -1

    return child.measure(orientation, for_size)


def timed_animation_allocate(widget: Gtk.Widget, width: int, height: int, baseline: int) -> None:
    self = widget.get_ancestor(AdwDemoPageAnimations)
    child = widget.get_first_child()

    if not child:
        return

    assert isinstance(self, AdwDemoPageAnimations)
    animation = self.get_current_animation()

    progress = animation.get_value()

    child_width, _natural, _minimum_baseline, _natural_baseline = child.measure(Gtk.Orientation.HORIZONTAL, -1)

    offset = int((width - child_width) * (progress - 0.5))

    child.allocate(width, height, baseline,
                   Gsk.Transform().translate(Graphene.Point().init(offset, 0)))


class TimedAnimationLayout(Gtk.LayoutManager):
    """gtk_custom_layout_new (NULL, timed_animation_measure, timed_animation_allocate).

    Gtk.CustomLayout can't be used from Python: its callbacks are scope="call", so PyGObject frees them as soon as
    gtk_custom_layout_new() returns, and the first measure crashes.
    """

    __gtype_name__ = "AdwDemoTimedAnimationLayout"

    def do_measure(self, widget: Gtk.Widget, orientation: Gtk.Orientation,
                   for_size: int) -> tuple[int, int, int, int]:
        return timed_animation_measure(widget, orientation, for_size)

    def do_allocate(self, widget: Gtk.Widget, width: int, height: int, baseline: int) -> None:
        timed_animation_allocate(widget, width, height, baseline)


@template
class AdwDemoPageAnimations(AdwDemoPageAnimationsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageAnimations"

    timed_animation = GObject.Property(type=Adw.Animation, nick="timed-animation")
    spring_animation = GObject.Property(type=Adw.Animation, nick="spring-animation")

    def __init__(self) -> None:
        super().__init__()

        sample = self.timed_animation_sample
        target = Adw.CallbackAnimationTarget.new(lambda value: sample.queue_allocate())

        # Setting the properties notifies them, as g_object_notify_by_pspec() does in C.
        self.timed_animation = Adw.TimedAnimation.new(self.timed_animation_sample,
                                                      0, 1, 100, target)

        self.spring_animation = Adw.SpringAnimation.new(self.timed_animation_sample, 0, 1,
                                                        Adw.SpringParams.new_full(10, 1, 100),
                                                        target)

        self.notify_spring_params_change()

        flags = GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL
        self.timed_animation_repeat_count.bind_property("value", self.timed_animation, "repeat-count", flags)
        self.timed_animation_reverse.bind_property("active", self.timed_animation, "reverse", flags)
        self.timed_animation_alternate.bind_property("active", self.timed_animation, "alternate", flags)
        self.timed_animation_duration.bind_property("value", self.timed_animation, "duration", flags)
        self.timed_animation_easing.bind_property("selected", self.timed_animation, "easing", flags)

        self.spring_animation_velocity.bind_property("value", self.spring_animation, "initial_velocity", flags)
        self.spring_animation_epsilon.bind_property("value", self.spring_animation, "epsilon", flags)
        self.spring_animation_clamp_switch.bind_property("active", self.spring_animation, "clamp", flags)

        self.timed_animation.set_easing(Adw.Easing.EASE_IN_OUT_CUBIC)

        self.timed_animation.set_follow_enable_animations_setting(False)
        self.spring_animation.set_follow_enable_animations_setting(False)

        manager = TimedAnimationLayout()

        self.timed_animation_sample.set_layout_manager(manager)

        self.timed_animation_button_box.set_direction(Gtk.TextDirection.LTR)

    def get_current_animation(self) -> Adw.Animation:
        current_animation = self.animation_preferences_stack.get_visible_child_name()

        if current_animation == "Timed":
            return self.timed_animation
        elif current_animation == "Spring":
            return self.spring_animation
        else:
            raise AssertionError("not reached")

    # Expression closures, which pyliite4-ui doesn't bind: it only looks at <signal> handlers.
    @Gtk.Template.Callback()
    def animations_easing_name(self, value: Adw.EnumListItem) -> str | None:
        return EASING_NAMES.get(Adw.Easing(value.get_value()))

    def timed_animation_reset(self, *_args: object) -> None:
        self.timed_animation.reset()
        self.spring_animation.reset()

    def timed_animation_play_pause(self, _button: Gtk.Button) -> None:
        animation = self.get_current_animation()

        match animation.get_state():
            case Adw.AnimationState.IDLE | Adw.AnimationState.FINISHED:
                animation.play()
            case Adw.AnimationState.PAUSED:
                animation.resume()
            case Adw.AnimationState.PLAYING:
                animation.pause()
            case _:
                raise AssertionError("not reached")

    def timed_animation_skip(self, _button: Gtk.Button) -> None:
        self.timed_animation.skip()
        self.spring_animation.skip()

    @Gtk.Template.Callback()
    def get_play_pause_icon_name(self, _this: GObject.Object, timed_state: Adw.AnimationState,
                                 spring_state: Adw.AnimationState) -> str:
        playing = (timed_state == Adw.AnimationState.PLAYING or
                   spring_state == Adw.AnimationState.PLAYING)

        return "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"

    @Gtk.Template.Callback()
    def timed_animation_can_reset(self, _this: GObject.Object, timed_state: Adw.AnimationState,
                                  spring_state: Adw.AnimationState) -> bool:
        return (timed_state != Adw.AnimationState.IDLE or
                spring_state != Adw.AnimationState.IDLE)

    @Gtk.Template.Callback()
    def timed_animation_can_skip(self, _this: GObject.Object, timed_state: Adw.AnimationState,
                                 spring_state: Adw.AnimationState) -> bool:
        return (timed_state != Adw.AnimationState.FINISHED and
                spring_state != Adw.AnimationState.FINISHED)

    def notify_spring_params_change(self, *_args: object) -> None:
        spring_params = Adw.SpringParams.new_full(self.spring_animation_damping.get_value(),
                                                  self.spring_animation_mass.get_value(),
                                                  self.spring_animation_stiffness.get_value())

        self.spring_animation.set_spring_params(spring_params)
