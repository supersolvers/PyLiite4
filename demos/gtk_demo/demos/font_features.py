"""Pango/Font Explorer

This example demonstrates support for OpenType font features with
Pango attributes. The attributes can be used manually or via Pango
markup.

It can also be used to explore available features in OpenType fonts
and their effect.

If the selected font supports OpenType font variations, then the
axes are also offered for customization.
"""

import ctypes
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk, Pango

from .fontplane import gtk_font_plane_new
from .language_names import get_language_name_for_tag


def _(text: str) -> str:
    return GLib.dgettext(None, text)


def NC_(context: str, text: str) -> str:
    return text


# {{{ HarfBuzz

# PyLiite4 doesn't expose HarfBuzz, though GTK's Pango uses it and the bundle has its typelib. The few HarfBuzz
# functions this demo needs are called through ctypes, in the copy of HarfBuzz that Pango has loaded, on the hb_font_t
# of a PangoFont.

class hb_ot_var_axis_info_t(ctypes.Structure):
    _fields_ = [
        ("axis_index", ctypes.c_uint),
        ("tag", ctypes.c_uint32),
        ("name_id", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("min_value", ctypes.c_float),
        ("default_value", ctypes.c_float),
        ("max_value", ctypes.c_float),
        ("reserved", ctypes.c_uint),
    ]


_hb = ctypes.CDLL("libharfbuzz.so.0")
_pango = ctypes.CDLL("libpango-1.0.so.0")

_p = ctypes.c_void_p
_u = ctypes.c_uint
_pu = ctypes.POINTER(ctypes.c_uint)
for _name, _restype, _argtypes in [
    ("hb_font_get_face", _p, [_p]),
    ("hb_font_get_var_coords_normalized", ctypes.POINTER(ctypes.c_int), [_p, _pu]),
    ("hb_language_from_string", _p, [ctypes.c_char_p, ctypes.c_int]),
    ("hb_language_to_string", ctypes.c_char_p, [_p]),
    ("hb_ot_tag_from_language", ctypes.c_uint32, [_p]),
    ("hb_ot_tag_to_language", _p, [ctypes.c_uint32]),
    ("hb_ot_layout_table_get_script_tags", _u, [_p, ctypes.c_uint32, _u, _pu, ctypes.POINTER(ctypes.c_uint32)]),
    ("hb_ot_layout_script_get_language_tags", _u,
     [_p, ctypes.c_uint32, _u, _u, _pu, ctypes.POINTER(ctypes.c_uint32)]),
    ("hb_ot_layout_language_get_feature_tags", _u,
     [_p, ctypes.c_uint32, _u, _u, _u, _pu, ctypes.POINTER(ctypes.c_uint32)]),
    ("hb_ot_layout_language_find_feature", ctypes.c_int, [_p, ctypes.c_uint32, _u, _u, ctypes.c_uint32, _pu]),
    ("hb_ot_layout_feature_get_name_ids", ctypes.c_int, [_p, ctypes.c_uint32, _u, _pu, _pu, _pu, _pu, _pu]),
    ("hb_ot_name_get_utf8", _u, [_p, _u, _p, _pu, ctypes.c_char_p]),
    ("hb_ot_var_get_axis_infos", _u, [_p, _u, _pu, ctypes.POINTER(hb_ot_var_axis_info_t)]),
    ("hb_ot_var_get_named_instance_count", _u, [_p]),
    ("hb_ot_var_named_instance_get_subfamily_name_id", _u, [_p, _u]),
    ("hb_ot_var_named_instance_get_design_coords", _u, [_p, _u, _pu, ctypes.POINTER(ctypes.c_float)]),
]:
    getattr(_hb, _name).restype = _restype
    getattr(_hb, _name).argtypes = _argtypes
    globals()[_name] = getattr(_hb, _name)

_pango.pango_font_get_hb_font.restype = _p
_pango.pango_font_get_hb_font.argtypes = [_p]

_capsule_get_pointer = ctypes.pythonapi.PyCapsule_GetPointer
_capsule_get_pointer.restype = _p
_capsule_get_pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]


def pango_font_get_hb_font(font: Pango.Font) -> int | None:
    return _pango.pango_font_get_hb_font(_capsule_get_pointer(font.__gpointer__, None))


def MAKE_TAG(tag: str) -> int:
    return int.from_bytes(tag.encode("latin-1"), "big")


def hb_tag_from_string(s: str) -> int:
    # hb_tag_from_string(): pad with spaces to four characters
    return MAKE_TAG((s + "    ")[:4])


def hb_tag_to_string(tag: int) -> str:
    return tag.to_bytes(4, "big").decode("latin-1")


HB_OT_TAG_GSUB = MAKE_TAG("GSUB")
HB_OT_TAG_GPOS = MAKE_TAG("GPOS")
HB_OT_TAG_DEFAULT_LANGUAGE = MAKE_TAG("dflt")
HB_OT_NAME_ID_INVALID = 0xFFFF
HB_LANGUAGE_INVALID = None

# }}}

# {{{ open-type-layout.h

# Registered OpenType layout tags, see
# https://www.microsoft.com/typography/otspec/featuretags.htm

# These don't include ss01 - ss19 and cv01 - cv99
open_type_layout_features = [
    (MAKE_TAG("aalt"), "Access All Alternates"),
    (MAKE_TAG("abvf"), "Above-base Forms"),
    (MAKE_TAG("abvm"), "Above-base Mark Positioning"),
    (MAKE_TAG("abvs"), "Above-base Substitutions"),
    (MAKE_TAG("afrc"), "Alternative Fractions"),
    (MAKE_TAG("akhn"), "Akhands"),
    (MAKE_TAG("blwf"), "Below-base Forms"),
    (MAKE_TAG("blwm"), "Below-base Mark Positioning"),
    (MAKE_TAG("blws"), "Below-base Substitutions"),
    (MAKE_TAG("calt"), "Contextual Alternates"),
    (MAKE_TAG("case"), "Case-Sensitive Forms"),
    (MAKE_TAG("ccmp"), "Glyph Composition / Decomposition"),
    (MAKE_TAG("cfar"), "Conjunct Form After Ro"),
    (MAKE_TAG("cjct"), "Conjunct Forms"),
    (MAKE_TAG("clig"), "Contextual Ligatures"),
    (MAKE_TAG("cpct"), "Centered CJK Punctuation"),
    (MAKE_TAG("cpsp"), "Capital Spacing"),
    (MAKE_TAG("cswh"), "Contextual Swash"),
    (MAKE_TAG("curs"), "Cursive Positioning"),
    (MAKE_TAG("c2pc"), "Petite Capitals From Capitals"),
    (MAKE_TAG("c2sc"), "Small Capitals From Capitals"),
    (MAKE_TAG("dist"), "Distances"),
    (MAKE_TAG("dlig"), "Discretionary Ligatures"),
    (MAKE_TAG("dnom"), "Denominators"),
    (MAKE_TAG("dtls"), "Dotless Forms"),
    (MAKE_TAG("expt"), "Expert Forms"),
    (MAKE_TAG("falt"), "Final Glyph on Line Alternates"),
    (MAKE_TAG("fin2"), "Terminal Forms #2"),
    (MAKE_TAG("fin3"), "Terminal Forms #3"),
    (MAKE_TAG("fina"), "Terminal Forms"),
    (MAKE_TAG("flac"), "Flattened accent forms"),
    (MAKE_TAG("frac"), "Fractions"),
    (MAKE_TAG("fwid"), "Full Widths"),
    (MAKE_TAG("half"), "Half Forms"),
    (MAKE_TAG("haln"), "Halant Forms"),
    (MAKE_TAG("halt"), "Alternate Half Widths"),
    (MAKE_TAG("hist"), "Historical Forms"),
    (MAKE_TAG("hkna"), "Horizontal Kana Alternates"),
    (MAKE_TAG("hlig"), "Historical Ligatures"),
    (MAKE_TAG("hngl"), "Hangul"),
    (MAKE_TAG("hojo"), "Hojo Kanji Forms"),
    (MAKE_TAG("hwid"), "Half Widths"),
    (MAKE_TAG("init"), "Initial Forms"),
    (MAKE_TAG("isol"), "Isolated Forms"),
    (MAKE_TAG("ital"), "Italics"),
    (MAKE_TAG("jalt"), "Justification Alternates"),
    (MAKE_TAG("jp78"), "JIS78 Forms"),
    (MAKE_TAG("jp83"), "JIS83 Forms"),
    (MAKE_TAG("jp90"), "JIS90 Forms"),
    (MAKE_TAG("jp04"), "JIS2004 Forms"),
    (MAKE_TAG("kern"), "Kerning"),
    (MAKE_TAG("lfbd"), "Left Bounds"),
    (MAKE_TAG("liga"), "Standard Ligatures"),
    (MAKE_TAG("ljmo"), "Leading Jamo Forms"),
    (MAKE_TAG("lnum"), "Lining Figures"),
    (MAKE_TAG("locl"), "Localized Forms"),
    (MAKE_TAG("ltra"), "Left-to-right alternates"),
    (MAKE_TAG("ltrm"), "Left-to-right mirrored forms"),
    (MAKE_TAG("mark"), "Mark Positioning"),
    (MAKE_TAG("med2"), "Medial Forms #2"),
    (MAKE_TAG("medi"), "Medial Forms"),
    (MAKE_TAG("mgrk"), "Mathematical Greek"),
    (MAKE_TAG("mkmk"), "Mark to Mark Positioning"),
    (MAKE_TAG("mset"), "Mark Positioning via Substitution"),
    (MAKE_TAG("nalt"), "Alternate Annotation Forms"),
    (MAKE_TAG("nlck"), "NLC Kanji Forms"),
    (MAKE_TAG("nukt"), "Nukta Forms"),
    (MAKE_TAG("numr"), "Numerators"),
    (MAKE_TAG("onum"), "Oldstyle Figures"),
    (MAKE_TAG("opbd"), "Optical Bounds"),
    (MAKE_TAG("ordn"), "Ordinals"),
    (MAKE_TAG("ornm"), "Ornaments"),
    (MAKE_TAG("palt"), "Proportional Alternate Widths"),
    (MAKE_TAG("pcap"), "Petite Capitals"),
    (MAKE_TAG("pkna"), "Proportional Kana"),
    (MAKE_TAG("pnum"), "Proportional Figures"),
    (MAKE_TAG("pref"), "Pre-Base Forms"),
    (MAKE_TAG("pres"), "Pre-base Substitutions"),
    (MAKE_TAG("pstf"), "Post-base Forms"),
    (MAKE_TAG("psts"), "Post-base Substitutions"),
    (MAKE_TAG("pwid"), "Proportional Widths"),
    (MAKE_TAG("qwid"), "Quarter Widths"),
    (MAKE_TAG("rand"), "Randomize"),
    (MAKE_TAG("rclt"), "Required Contextual Alternates"),
    (MAKE_TAG("rkrf"), "Rakar Forms"),
    (MAKE_TAG("rlig"), "Required Ligatures"),
    (MAKE_TAG("rphf"), "Reph Forms"),
    (MAKE_TAG("rtbd"), "Right Bounds"),
    (MAKE_TAG("rtla"), "Right-to-left alternates"),
    (MAKE_TAG("rtlm"), "Right-to-left mirrored forms"),
    (MAKE_TAG("ruby"), "Ruby Notation Forms"),
    (MAKE_TAG("rvrn"), "Required Variation Alternates"),
    (MAKE_TAG("salt"), "Stylistic Alternates"),
    (MAKE_TAG("sinf"), "Scientific Inferiors"),
    (MAKE_TAG("size"), "Optical size"),
    (MAKE_TAG("smcp"), "Small Capitals"),
    (MAKE_TAG("smpl"), "Simplified Forms"),
    (MAKE_TAG("ssty"), "Math script style alternates"),
    (MAKE_TAG("stch"), "Stretching Glyph Decomposition"),
    (MAKE_TAG("subs"), "Subscript"),
    (MAKE_TAG("sups"), "Superscript"),
    (MAKE_TAG("swsh"), "Swash"),
    (MAKE_TAG("titl"), "Titling"),
    (MAKE_TAG("tjmo"), "Trailing Jamo Forms"),
    (MAKE_TAG("tnam"), "Traditional Name Forms"),
    (MAKE_TAG("tnum"), "Tabular Figures"),
    (MAKE_TAG("trad"), "Traditional Forms"),
    (MAKE_TAG("twid"), "Third Widths"),
    (MAKE_TAG("unic"), "Unicase"),
    (MAKE_TAG("valt"), "Alternate Vertical Metrics"),
    (MAKE_TAG("vatu"), "Vattu Variants"),
    (MAKE_TAG("vert"), "Vertical Writing"),
    (MAKE_TAG("vhal"), "Alternate Vertical Half Metrics"),
    (MAKE_TAG("vjmo"), "Vowel Jamo Forms"),
    (MAKE_TAG("vkna"), "Vertical Kana Alternates"),
    (MAKE_TAG("vkrn"), "Vertical Kerning"),
    (MAKE_TAG("vpal"), "Proportional Alternate Vertical Metrics"),
    (MAKE_TAG("vrt2"), "Vertical Alternates and Rotation"),
    (MAKE_TAG("vrtr"), "Vertical Alternates for Rotation"),
    (MAKE_TAG("zero"), "Slashed Zero"),
]

# }}}

# {{{ ScriptLang object


class ScriptLang(GObject.Object):
    __gtype_name__ = "ScriptLang"

    def __init__(self) -> None:
        super().__init__()
        self.langname = ""
        self.script_index = 0
        self.lang_index = 0
        self.lang_tag = 0


def script_lang_new(langname: str, script_index: int, lang_index: int, lang_tag: int) -> ScriptLang:
    self = ScriptLang()

    self.langname = langname
    self.script_index = script_index
    self.lang_index = lang_index
    self.lang_tag = lang_tag

    return self


def script_lang_get_langname(self: ScriptLang) -> str:
    return self.langname

# }}}


@dataclass
class FeatureItem:
    tag: int
    name: str
    icon: Gtk.Widget | None
    dflt: Gtk.Widget | None
    feat: Gtk.CheckButton


@dataclass
class Range:
    start: int
    end: int
    desc: Pango.FontDescription | None = None
    features: str | None = None
    language: Pango.Language | None = None


@dataclass
class Axis:
    tag: int
    adjustment: Gtk.Adjustment
    default_value: float
    tick_cb: int = 0
    start_time: int = 0
    increasing: bool = False
    button: Gtk.Button | None = None
    unset_instance_handler: int = 0


@dataclass
class Instance:
    name: str
    index: int


@dataclass
class FontFeaturesDemo:
    the_label: Gtk.Label = None
    settings: Gtk.Label = None
    description: Gtk.Label = None
    font: Gtk.FontDialogButton = None
    script_lang: Gtk.DropDown = None
    feature_list: Gtk.Box = None
    variations_grid: Gtk.Grid = None
    instance_combo: Gtk.DropDown | None = None
    stack: Gtk.Stack = None
    entry: Gtk.TextView = None
    plain_toggle: Gtk.ToggleButton = None
    waterfall_toggle: Gtk.ToggleButton = None
    edit_toggle: Gtk.ToggleButton = None
    size_adjustment: Gtk.Adjustment = None
    letterspacing_adjustment: Gtk.Adjustment = None
    line_height_adjustment: Gtk.Adjustment = None
    foreground: Gtk.ColorDialogButton = None
    background: Gtk.ColorDialogButton = None
    size_scale: Gtk.Scale = None
    size_entry: Gtk.Entry = None
    letterspacing_entry: Gtk.Entry = None
    line_height_entry: Gtk.Entry = None
    feature_items: list[FeatureItem] = field(default_factory=list)
    ranges: list[Range] = field(default_factory=list)
    instances: dict[str, Instance] | None = None
    axes: dict[int, Axis] | None = None
    text: str | None = None
    swin: Gtk.ScrolledWindow = None
    provider: Gtk.CssProvider = None
    sample: int = 0


def demo_free(data: FontFeaturesDemo) -> None:
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), data.provider)


demo: FontFeaturesDemo


def font_features_toggle_plain(*args: object) -> None:
    if demo.plain_toggle.get_active() or demo.waterfall_toggle.get_active():
        demo.stack.set_visible_child_name("label")
        update_display()


def font_features_notify_waterfall(*args: object) -> None:
    can_change_size = not demo.waterfall_toggle.get_active()
    demo.size_scale.set_sensitive(can_change_size)
    demo.size_entry.set_sensitive(can_change_size)


def update_in_idle(bd: tuple[Gtk.Adjustment, Gtk.Entry]) -> bool:
    adjustment, entry = bd

    entry.set_text(f"{adjustment.get_value():g}")

    update_display()

    return GLib.SOURCE_REMOVE


def basic_value_changed(adjustment: Gtk.Adjustment, data: Gtk.Entry) -> None:
    bd = (adjustment, data)

    GLib.idle_add(update_in_idle, bd)


def strtod(text: str) -> float:
    # g_strtod(): the longest prefix that is a number, or 0
    match = re.match(r"\s*[-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+([eE][-+]?\d+)?|inf(inity)?|nan)", text, re.IGNORECASE)
    return float(match.group(0)) if match else 0.0


def basic_entry_activated(entry: Gtk.Entry, adjustment: Gtk.Adjustment) -> None:
    # g_strtod() always sets its end pointer, so the C version always sets the value.
    value = strtod(entry.get_text())
    adjustment.set_value(value)


def color_set_cb(*args: object) -> None:
    update_display()


def swap_colors(*args: object) -> None:
    fg = demo.foreground.get_rgba()
    bg = demo.background.get_rgba()
    demo.foreground.set_rgba(bg)
    demo.background.set_rgba(fg)


def font_features_reset_basic(*args: object) -> None:
    demo.size_adjustment.set_value(20)
    demo.letterspacing_adjustment.set_value(0)
    demo.line_height_adjustment.set_value(1)
    demo.foreground.set_rgba(Gdk.RGBA(red=0., green=0., blue=0., alpha=1.))
    demo.background.set_rgba(Gdk.RGBA(red=1., green=1., blue=1., alpha=1.))


def update_basic() -> None:
    desc = demo.font.get_font_desc()

    demo.size_adjustment.set_value(desc.get_size() / Pango.SCALE)


def compare_range(ra: Range, rb: Range) -> int:
    if ra.start < rb.start:
        return -1
    elif ra.start > rb.start:
        return 1
    elif ra.end < rb.end:
        return 1
    elif ra.end > rb.end:
        return -1

    return 0


def ensure_range(start: int, end: int, desc: Pango.FontDescription | None, features: str,
                 language: Pango.Language | None) -> None:
    for r in demo.ranges:
        if r.start == start and r.end == end:
            range = r
            break
    else:
        range = Range(start, end)

        # g_list_insert_sorted()
        position = 0
        while position < len(demo.ranges) and compare_range(range, demo.ranges[position]) > 0:
            position += 1
        demo.ranges.insert(position, range)

    if desc:
        range.desc = desc.copy()
    else:
        range.desc = None
    range.features = features
    range.language = language


def get_feature_display_name(tag: int) -> str:
    if tag == MAKE_TAG("xxxx"):
        return _("Default")

    buf = hb_tag_to_string(tag)
    if buf.startswith("ss") and buf[2].isdigit() and buf[3].isdigit():
        num = int(buf[2:4])
        return GLib.dpgettext2(None, "OpenType layout", "Stylistic Set %d") % num
    elif buf.startswith("cv") and buf[2].isdigit() and buf[3].isdigit():
        num = int(buf[2:4])
        return GLib.dpgettext2(None, "OpenType layout", "Character Variant %d") % num

    for feature_tag, name in open_type_layout_features:
        if tag == feature_tag:
            return GLib.dpgettext2(None, "OpenType layout", name)

    print(f"WARNING: unknown OpenType layout feature tag: {buf}", file=sys.stderr)

    return buf


def set_inconsistent(button: Gtk.CheckButton, inconsistent: bool) -> None:
    button.set_inconsistent(inconsistent)
    button.get_first_child().set_opacity(0.0 if inconsistent else 1.0)


def feat_pressed(gesture: Gtk.GestureClick, n_press: int, x: float, y: float, feat: Gtk.CheckButton) -> None:
    button = gesture.get_current_button()

    if button == Gdk.BUTTON_PRIMARY:
        # The C version blocks feat_pressed on the check button here, which isn't connected to it.
        if feat.get_inconsistent():
            set_inconsistent(feat, False)
            feat.set_active(True)
    elif button == Gdk.BUTTON_SECONDARY:
        inconsistent = feat.get_inconsistent()
        set_inconsistent(feat, not inconsistent)


def feat_toggled_cb(check_button: Gtk.CheckButton) -> None:
    set_inconsistent(check_button, False)


def get_default(feat: Gtk.Widget) -> Gtk.CheckButton | None:
    # g_object_get_data (feat, "default")
    return getattr(feat, "default_button", None)


def add_check_group(box: Gtk.Box, title: str, tags: list[str]) -> None:
    group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    group.set_halign(Gtk.Align.START)

    label = Gtk.Label(label=title)
    label.set_xalign(0.0)
    label.set_halign(Gtk.Align.START)
    label.set_properties(margin_top=10, margin_bottom=10)
    label.add_css_class("heading")
    group.append(label)

    for name in tags:
        tag = hb_tag_from_string(name)

        feat = Gtk.CheckButton.new_with_label(get_feature_display_name(tag))
        set_inconsistent(feat, True)

        feat.notify["active"].connect(update_display)
        feat.notify["inconsistent"].connect(update_display)
        feat.toggled.connect(feat_toggled_cb)

        gesture = Gtk.GestureClick()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.pressed.connect(feat_pressed, feat)
        feat.add_controller(gesture)

        group.append(feat)

        item = FeatureItem(name=name, tag=tag, icon=None, dflt=None, feat=feat)

        demo.feature_items.insert(0, item)

    box.append(group)


def add_radio_group(box: Gtk.Box, title: str, tags: list[str]) -> None:
    group_button = None

    group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    group.set_halign(Gtk.Align.START)

    label = Gtk.Label(label=title)
    label.set_xalign(0.0)
    label.set_halign(Gtk.Align.START)
    label.set_properties(margin_top=10, margin_bottom=10)
    label.add_css_class("heading")
    group.append(label)

    for name in tags:
        tag = hb_tag_from_string(name)
        display_name = get_feature_display_name(tag)
        feat = Gtk.CheckButton.new_with_label(display_name if display_name else _("Default"))
        if group_button is None:
            group_button = feat
        else:
            feat.set_group(group_button)

        feat.notify["active"].connect(update_display)
        feat.default_button = group_button

        group.append(feat)

        item = FeatureItem(name=name, tag=tag, icon=None, dflt=None, feat=feat)

        demo.feature_items.insert(0, item)

    box.append(group)


PANGO_ATTR_INDEX_FROM_TEXT_BEGINNING = 0
PANGO_ATTR_INDEX_TO_TEXT_END = GLib.MAXUINT


def update_display(*args: object) -> None:
    buffer = demo.entry.get_buffer()
    start_iter, end_iter = buffer.get_bounds()
    text = buffer.get_text(start_iter, end_iter, False)
    text_len = len(text.encode())

    do_waterfall = demo.waterfall_toggle.get_active()

    demo.the_label.set_wrap(not do_waterfall)

    selection = demo.the_label.get_selection_bounds()
    if do_waterfall:
        start = PANGO_ATTR_INDEX_FROM_TEXT_BEGINNING
        end = PANGO_ATTR_INDEX_TO_TEXT_END
    elif selection[0]:
        _ok, ins, bound = selection
        start = len(text[:ins].encode())
        end = len(text[:bound].encode())
    else:
        start = PANGO_ATTR_INDEX_FROM_TEXT_BEGINNING
        end = PANGO_ATTR_INDEX_TO_TEXT_END

    desc = demo.font.get_font_desc()

    value = demo.size_adjustment.get_value()
    desc.set_size(int(value * Pango.SCALE))

    s = add_font_variations()
    if len(s) > 0:
        desc.set_variations(s)

    font_desc = desc.to_string()

    s = ""

    has_feature = False
    for item in demo.feature_items:
        if not item.feat.is_sensitive():
            continue

        if isinstance(item.feat, Gtk.CheckButton):
            if get_default(item.feat):
                if item.feat.get_active() and item.name != "xxxx":
                    if has_feature:
                        s += ", "
                    s += item.name
                    s += " 1"
                    has_feature = True
            else:
                if item.feat.get_inconsistent():
                    continue

                if has_feature:
                    s += ", "
                s += item.name
                if item.feat.get_active():
                    s += " 1"
                else:
                    s += " 0"
                has_feature = True

    features = s

    if demo.script_lang.get_selected() != 0:
        selected = demo.script_lang.get_selected_item()

        lang = Pango.Language.from_string(hb_language_to_string(hb_ot_tag_to_language(selected.lang_tag)).decode())
    else:
        lang = None

    attrs = Pango.AttrList()

    if demo.letterspacing_adjustment.get_value() != 0.:
        attr = Pango.attr_letter_spacing_new(int(demo.letterspacing_adjustment.get_value()))
        attr.start_index = start
        attr.end_index = end
        attrs.insert(attr)

    if demo.line_height_adjustment.get_value() != 1.:
        attr = Pango.attr_line_height_new(demo.line_height_adjustment.get_value())
        attr.start_index = start
        attr.end_index = end
        attrs.insert(attr)

    rgba = demo.foreground.get_rgba()
    attr = Pango.attr_foreground_new(int(65535 * rgba.red),
                                     int(65535 * rgba.green),
                                     int(65535 * rgba.blue))
    attr.start_index = start
    attr.end_index = end
    attrs.insert(attr)
    attr = Pango.attr_foreground_alpha_new(int(65535 * rgba.alpha))
    attr.start_index = start
    attr.end_index = end
    attrs.insert(attr)

    fg = rgba.to_string()
    rgba = demo.background.get_rgba()
    bg = rgba.to_string()
    css = f".font_features_background {{ caret-color: {fg}; background-color: {bg}; }}"
    demo.provider.load_from_data(css, -1)

    if do_waterfall:
        attr = Pango.attr_font_desc_new(desc)
        attrs.insert(attr)
        attr = Pango.attr_font_features_new(features)
        attrs.insert(attr)
        if lang is not None:
            # pango_attr_language_new (NULL) sets no language, but PyGObject doesn't accept NULL here.
            attr = Pango.attr_language_new(lang)
            attrs.insert(attr)
    else:
        ensure_range(start, end, desc, features, lang)

        for range in demo.ranges:
            attr = Pango.attr_font_desc_new(range.desc)
            attr.start_index = range.start
            attr.end_index = range.end
            attrs.insert(attr)

            attr = Pango.attr_font_features_new(range.features)
            attr.start_index = range.start
            attr.end_index = range.end
            attrs.insert(attr)

            if range.language:
                attr = Pango.attr_language_new(range.language)
                attr.start_index = range.start
                attr.end_index = range.end
                attrs.insert(attr)

    demo.description.set_text(font_desc)
    demo.settings.set_text(features)

    if do_waterfall:
        waterfall = ""
        sizes = [7, 8, 9, 10, 12, 14, 16, 20, 24, 30, 40, 50, 60, 70, 90]
        start = 0
        for size in sizes:
            waterfall += text
            waterfall += "\n"

            attr = Pango.attr_size_new(size * Pango.SCALE)
            attr.start_index = start
            attr.end_index = start + text_len
            attrs.insert(attr)

            start += text_len + 1
        demo.the_label.set_text(waterfall)
    else:
        demo.the_label.set_text(text)

    demo.the_label.set_attributes(attrs)


def get_pango_font() -> Pango.Font:
    desc = demo.font.get_font_desc()
    context = demo.font.get_pango_context()

    return context.load_font(desc)


def script_sort(item1: ScriptLang, item2: ScriptLang, data: object) -> int:
    a = item1.langname
    b = item2.langname

    # strcmp()
    a_bytes, b_bytes = a.encode(), b.encode()
    return (a_bytes > b_bytes) - (a_bytes < b_bytes)


def update_script_combo() -> None:
    language = demo.font.get_language()
    lang = language.to_string() if language else None

    active = hb_ot_tag_from_language(hb_language_from_string(lang.encode() if lang else None, -1))

    store = Gio.ListStore(item_type=ScriptLang)

    pango_font = get_pango_font()
    hb_font = pango_font_get_hb_font(pango_font)

    # TagPairs, keyed by script tag and language tag: (script_tag, lang_tag, script_index, lang_index)
    tags: dict[tuple[int, int], tuple[int, int, int, int]] = {}

    tags[(0, 0)] = (0, 0, 0, 0)

    if hb_font:
        tables = [HB_OT_TAG_GSUB, HB_OT_TAG_GPOS]

        hb_face = hb_font_get_face(hb_font)

        for i in range(2):
            scripts = (ctypes.c_uint32 * 80)()
            script_count = ctypes.c_uint(len(scripts))

            hb_ot_layout_table_get_script_tags(hb_face, tables[i], 0, ctypes.byref(script_count), scripts)
            for j in range(script_count.value):
                languages = (ctypes.c_uint32 * 80)()
                language_count = ctypes.c_uint(len(languages))

                hb_ot_layout_script_get_language_tags(hb_face, tables[i], j, 0, ctypes.byref(language_count),
                                                      languages)
                for k in range(language_count.value):
                    tags[(scripts[j], languages[k])] = (scripts[j], languages[k], j, k)

    for script_tag, lang_tag, script_index, lang_index in tags.values():
        if lang_tag == 0 and script_tag == 0:
            langname = NC_("Language", "None")
        elif lang_tag == HB_OT_TAG_DEFAULT_LANGUAGE:
            langname = NC_("Language", "Default")
        else:
            langname = get_language_name_for_tag(lang_tag)
            if not langname:
                langname = hb_tag_to_string(lang_tag)

        store.append(script_lang_new(langname, script_index, lang_index, lang_tag))

    sortmodel = Gtk.SortListModel.new(store, Gtk.CustomSorter.new(script_sort, None))
    demo.script_lang.set_model(sortmodel)

    for i in range(sortmodel.get_n_items()):
        item = sortmodel.get_item(i)

        if item.lang_tag == active:
            demo.script_lang.set_selected(i)
            break


def get_name(hbface: int, id: int) -> str | None:
    if id == HB_OT_NAME_ID_INVALID:
        return None

    length = hb_ot_name_get_utf8(hbface, id, HB_LANGUAGE_INVALID, None, None)
    length += 1
    text = ctypes.create_string_buffer(length)
    size = ctypes.c_uint(length)
    hb_ot_name_get_utf8(hbface, id, HB_LANGUAGE_INVALID, ctypes.byref(size), text)

    return text.value.decode()


def update_features() -> None:
    # set feature presence checks from the font features

    selected = demo.script_lang.get_selected_item()

    if selected.lang_tag == 0:  # None is selected
        for item in demo.feature_items:
            item.feat.set_visible(True)
            item.feat.get_parent().set_visible(True)
            if item.name == "xxxx":
                item.feat.set_active(True)

        return

    for item in demo.feature_items:
        item.feat.set_visible(False)
        item.feat.get_parent().set_visible(False)
        if item.name == "xxxx":
            item.feat.set_active(True)

    pango_font = get_pango_font()
    hb_font = pango_font_get_hb_font(pango_font)

    if hb_font:
        tables = [HB_OT_TAG_GSUB, HB_OT_TAG_GPOS]

        hb_face = hb_font_get_face(hb_font)

        for i in range(2):
            features = (ctypes.c_uint32 * 80)()
            count = ctypes.c_uint(len(features))

            hb_ot_layout_language_get_feature_tags(hb_face,
                                                   tables[i],
                                                   selected.script_index,
                                                   selected.lang_index,
                                                   0,
                                                   ctypes.byref(count),
                                                   features)

            for j in range(count.value):
                buf = hb_tag_to_string(features[j])

                if buf.startswith("ss") or buf.startswith("cv"):
                    feature_index = ctypes.c_uint()
                    label_id, tooltip_id, sample_id, first_param_id = (ctypes.c_uint() for _ in range(4))
                    num_params = ctypes.c_uint()

                    hb_ot_layout_language_find_feature(hb_face,
                                                       tables[i],
                                                       selected.script_index,
                                                       selected.lang_index,
                                                       features[j],
                                                       ctypes.byref(feature_index))

                    if hb_ot_layout_feature_get_name_ids(hb_face,
                                                         tables[i],
                                                         feature_index.value,
                                                         ctypes.byref(label_id),
                                                         ctypes.byref(tooltip_id),
                                                         ctypes.byref(sample_id),
                                                         ctypes.byref(num_params),
                                                         ctypes.byref(first_param_id)):
                        label = get_name(hb_face, label_id.value)

                        if label:
                            for item in demo.feature_items:
                                if item.tag == features[j]:
                                    item.feat.set_label(label)
                                    break

                for item in demo.feature_items:
                    if item.tag == features[j]:
                        item.feat.set_visible(True)
                        item.feat.get_parent().set_visible(True)
                        if isinstance(item.feat, Gtk.CheckButton):
                            default = get_default(item.feat)
                            if default:
                                default.set_visible(True)
                                default.get_parent().set_visible(True)
                                default.set_active(True)
                            else:
                                set_inconsistent(item.feat, True)

        feat = demo.font.get_font_features()
        if feat:
            for item in demo.feature_items:
                buf = hb_tag_to_string(item.tag)

                p = feat.find(buf)
                if p >= 0:
                    if isinstance(item.feat, Gtk.CheckButton) and get_default(item.feat):
                        item.feat.set_active(feat[p + 6:p + 7] == "1")
                    elif isinstance(item.feat, Gtk.CheckButton):
                        set_inconsistent(item.feat, False)
                        item.feat.set_active(feat[p + 6:p + 7] == "1")


def adjustment_changed(adjustment: Gtk.Adjustment, entry: Gtk.Entry) -> None:
    entry.set_text(f"{adjustment.get_value():g}")

    update_display()


def entry_activated(entry: Gtk.Entry, adjustment: Gtk.Adjustment) -> None:
    value = strtod(entry.get_text())
    adjustment.set_value(value)


def font_features_reset_variations(*args: object) -> None:
    for axis in demo.axes.values():
        if axis.tick_cb:
            start_or_stop_axis_animation(axis.button, axis)
        axis.adjustment.set_value(axis.default_value)


def add_font_variations() -> str:
    s = ""
    sep = ""

    for axis in demo.axes.values():
        tag = hb_tag_to_string(axis.tag)
        value = axis.adjustment.get_value()

        # g_ascii_dtostr()
        s += f"{sep}{tag}={value:.17g}"
        sep = ","

    return s


def ease_out_cubic(t: float) -> float:
    p = t - 1

    return p * p * p + 1


def animate_axis(widget: Gtk.Widget, frame_clock: Gdk.FrameClock, axis: Axis) -> bool:
    now = GLib.get_monotonic_time()

    if now >= axis.start_time + GLib.TIME_SPAN_SECOND:
        axis.start_time += GLib.TIME_SPAN_SECOND
        axis.increasing = not axis.increasing

    value = (now - axis.start_time) / GLib.TIME_SPAN_SECOND

    value = ease_out_cubic(value)

    lower = axis.adjustment.get_lower()
    upper = axis.adjustment.get_upper()

    if axis.increasing:
        axis.adjustment.set_value(lower + (upper - lower) * value)
    else:
        axis.adjustment.set_value(upper - (upper - lower) * value)

    return GLib.SOURCE_CONTINUE


def start_or_stop_axis_animation(button: Gtk.Button, axis: Axis) -> None:
    if axis.tick_cb:
        button.remove_tick_callback(axis.tick_cb)
        axis.tick_cb = 0
        button.set_icon_name("media-playback-start")
    else:
        button.set_icon_name("media-playback-stop")
        axis.tick_cb = button.add_tick_callback(animate_axis, axis)
        value = axis.adjustment.get_value()
        lower = axis.adjustment.get_lower()
        upper = axis.adjustment.get_upper()
        value = value / (upper - lower)
        axis.start_time = int(GLib.get_monotonic_time() - value * GLib.TIME_SPAN_SECOND)
        axis.increasing = True


def name_get_utf8(hb_face: int, name_id: int, size: int) -> str:
    # hb_ot_name_get_utf8() into a char[size]
    name = ctypes.create_string_buffer(size)
    name_len = ctypes.c_uint(size)
    hb_ot_name_get_utf8(hb_face, name_id, HB_LANGUAGE_INVALID, ctypes.byref(name_len), name)
    return name.value.decode("utf-8", "replace")


def add_axis(hb_face: int, ax: hb_ot_var_axis_info_t, value: float, i: int) -> None:
    name = name_get_utf8(hb_face, ax.name_id, 20)

    axis_label = Gtk.Label(label=name)
    axis_label.set_halign(Gtk.Align.START)
    axis_label.set_valign(Gtk.Align.BASELINE_FILL)
    demo.variations_grid.attach(axis_label, 0, i, 1, 1)
    adjustment = Gtk.Adjustment.new(value, ax.min_value, ax.max_value, 1.0, 10.0, 0.0)
    axis_scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adjustment)
    axis_scale.add_mark(ax.default_value, Gtk.PositionType.TOP, None)
    axis_scale.set_valign(Gtk.Align.BASELINE_FILL)
    axis_scale.set_hexpand(True)
    axis_scale.set_size_request(100, -1)
    demo.variations_grid.attach(axis_scale, 1, i, 1, 1)
    axis_entry = Gtk.Entry()
    axis_entry.set_valign(Gtk.Align.BASELINE_FILL)
    axis_entry.set_width_chars(4)
    axis_entry.set_max_width_chars(4)
    axis_entry.set_hexpand(False)
    demo.variations_grid.attach(axis_entry, 2, i, 1, 1)

    axis = Axis(tag=ax.tag, adjustment=adjustment, default_value=ax.default_value)
    demo.axes[axis.tag] = axis

    axis.button = Gtk.Button.new_from_icon_name("media-playback-start")
    axis.button.add_css_class("circular")
    axis.button.set_valign(Gtk.Align.CENTER)
    axis.button.clicked.connect(start_or_stop_axis_animation, axis)
    demo.variations_grid.attach(axis.button, 3, i, 1, 1)

    adjustment_changed(adjustment, axis_entry)

    adjustment.value_changed.connect(adjustment_changed, axis_entry)
    axis.unset_instance_handler = adjustment.value_changed.connect(unset_instance)
    axis_entry.activate.connect(entry_activated, adjustment)


def add_instance(face: int, index: int, strings: Gtk.StringList) -> None:
    name_id = hb_ot_var_named_instance_get_subfamily_name_id(face, index)
    name = name_get_utf8(face, name_id, 20)

    instance = Instance(name=name, index=index)

    demo.instances[instance.name] = instance
    strings.append(instance.name)


def unset_instance(adjustment: Gtk.Adjustment) -> None:
    if demo.instance_combo:
        demo.instance_combo.set_selected(0)


def axis_infos(hb_face: int) -> list[hb_ot_var_axis_info_t]:
    n_axes = ctypes.c_uint(hb_ot_var_get_axis_infos(hb_face, 0, None, None))
    ai = (hb_ot_var_axis_info_t * n_axes.value)()
    hb_ot_var_get_axis_infos(hb_face, 0, ctypes.byref(n_axes), ai)
    return list(ai)


def named_instance_design_coords(hb_face: int, index: int, n_axes: int) -> list[float]:
    coords = (ctypes.c_float * n_axes)()
    coords_length = ctypes.c_uint(n_axes)
    hb_ot_var_named_instance_get_design_coords(hb_face, index, ctypes.byref(coords_length), coords)
    return list(coords)


def instance_changed(combo: Gtk.DropDown, pspec: GObject.ParamSpec) -> None:
    text = combo.get_model().get_string(combo.get_selected())
    if text == "":
        return

    instance = demo.instances.get(text)
    if not instance:
        return

    pango_font = get_pango_font()
    hb_font = pango_font_get_hb_font(pango_font)
    hb_face = hb_font_get_face(hb_font)

    ai = axis_infos(hb_face)
    n_axes = len(ai)

    coords = named_instance_design_coords(hb_face, instance.index, n_axes)

    for i in range(n_axes):
        value = coords[ai[i].axis_index]

        axis = demo.axes.get(ai[i].tag)
        if axis:
            # g_signal_handlers_block_by_func (axis->adjustment, unset_instance, NULL)
            with axis.adjustment.value_changed.blocked(axis.unset_instance_handler):
                axis.adjustment.set_value(value)


def matches_instance(hb_face: int, index: int, n_axes: int, coords: list[float]) -> bool:
    instance_coords = named_instance_design_coords(hb_face, index, n_axes)

    for i in range(n_axes):
        if instance_coords[i] != coords[i]:
            return False

    return True


def add_font_plane(i: int) -> None:
    weight_axis = demo.axes.get(MAKE_TAG("wght"))
    width_axis = demo.axes.get(MAKE_TAG("wdth"))

    if weight_axis and width_axis:
        plane = gtk_font_plane_new(weight_axis.adjustment, width_axis.adjustment)

        plane.set_size_request(300, 300)
        plane.set_halign(Gtk.Align.CENTER)
        demo.variations_grid.attach(plane, 0, i, 3, 1)


# FIXME: This doesn't work if the font has an avar table
def denorm_coord(axis: hb_ot_var_axis_info_t, coord: int) -> float:
    r = coord / 16384.0

    if coord < 0:
        return axis.default_value + r * (axis.default_value - axis.min_value)
    else:
        return axis.default_value + r * (axis.max_value - axis.default_value)


def update_font_variations() -> None:
    while (child := demo.variations_grid.get_first_child()):
        demo.variations_grid.remove(child)

    demo.instance_combo = None

    demo.axes.clear()
    demo.instances.clear()

    pango_font = get_pango_font()
    hb_font = pango_font_get_hb_font(pango_font)
    hb_face = hb_font_get_face(hb_font)

    ai = axis_infos(hb_face)
    n_axes = len(ai)
    if n_axes == 0:
        return

    design_coords = [0.0] * n_axes

    length = ctypes.c_uint()
    coords = hb_font_get_var_coords_normalized(hb_font, ctypes.byref(length))
    for i in range(length.value):
        design_coords[i] = ctypes.c_float(denorm_coord(ai[i], coords[i])).value

    if hb_ot_var_get_named_instance_count(hb_face) > 0:
        label = Gtk.Label(label="Instance")
        label.set_xalign(0)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.BASELINE_FILL)
        demo.variations_grid.attach(label, 0, -1, 1, 1)

        strings = Gtk.StringList.new(None)
        combo = Gtk.DropDown.new(strings, None)

        combo.set_halign(Gtk.Align.START)
        combo.set_valign(Gtk.Align.BASELINE_FILL)

        strings.append("")

        for i in range(hb_ot_var_get_named_instance_count(hb_face)):
            add_instance(hb_face, i, strings)

        for i in range(hb_ot_var_get_named_instance_count(hb_face)):
            if matches_instance(hb_face, i, n_axes, design_coords):
                combo.set_selected(i + 1)
                break

        demo.variations_grid.attach(combo, 1, -1, 3, 1)
        combo.notify["selected"].connect(instance_changed)
        demo.instance_combo = combo

    for i in range(n_axes):
        add_axis(hb_face, ai[i], design_coords[i], i)

    add_font_plane(n_axes)


def font_features_font_changed(*args: object) -> None:
    update_basic()
    update_script_combo()
    update_features()
    update_font_variations()


def font_features_script_changed(*args: object) -> None:
    update_features()
    update_display()


def font_features_reset_features(*args: object) -> None:
    demo.the_label.select_region(0, 0)

    demo.ranges = []

    for item in demo.feature_items:
        if isinstance(item.feat, Gtk.CheckButton):
            if item.name == "xxxx":
                item.feat.set_active(True)
            else:
                item.feat.set_active(False)
                set_inconsistent(item.feat, True)


def font_features_toggle_edit(*args: object) -> None:
    if demo.stack.get_visible_child_name() != "entry":
        buffer = demo.entry.get_buffer()
        start, end = buffer.get_bounds()
        demo.text = buffer.get_text(start, end, False)
        demo.stack.set_visible_child_name("entry")
        demo.entry.grab_focus()
        demo.swin.get_vadjustment().set_value(0)
    else:
        demo.text = None
        demo.plain_toggle.set_active(True)
        update_display()


def font_features_stop_edit(*args: object) -> None:
    demo.edit_toggle.clicked.emit()


def entry_key_press(controller: Gtk.EventControllerKey, keyval: int, keycode: int, modifiers: Gdk.ModifierType,
                    entry: Gtk.TextView) -> bool:
    if keyval == Gdk.KEY_Escape:
        entry.get_buffer().set_text(demo.text, -1)
        return Gdk.EVENT_STOP

    return Gdk.EVENT_PROPAGATE


paragraphs = [
    "Grumpy wizards make toxic brew for the evil Queen and Jack. A quick movement of the enemy will jeopardize six "
    "gunboats. The job of waxing linoleum frequently peeves chintzy kids. My girl wove six dozen plaid jackets before "
    "she quit. Twelve ziggurats quickly jumped a finch box.",
    "Разъяренный чтец эгоистично бьёт пятью жердями шустрого фехтовальщика. Наш банк вчера же выплатил Ф.Я. "
    "Эйхгольду комиссию за ценные вещи. Эх, чужак, общий съём цен шляп (юфть) – вдрызг! В чащах юга жил бы цитрус? "
    "Да, но фальшивый экземпляр!",
    "Τάχιστη αλώπηξ βαφής ψημένη γη, δρασκελίζει υπέρ νωθρού κυνός",
]

alphabets = [
    "abcdefghijklmnopqrstuvwxzy",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "0123456789",
    "!@#$%^&*/?;",
]


def set_text_alphabet(*args: object) -> None:
    demo.sample += 1
    demo.entry.get_buffer().set_text(alphabets[demo.sample % len(alphabets)], -1)
    update_display()


def set_text_paragraph(*args: object) -> None:
    demo.sample += 1
    demo.entry.get_buffer().set_text(paragraphs[demo.sample % len(paragraphs)], -1)
    update_display()


class BuilderCScope(GObject.Object, Gtk.BuilderScope):
    """GtkBuilderCScope, for Python callbacks.

    PyGObject's own builder scope calls a handler whose signal names an object with just that object, rather than with
    the signal's arguments followed by the object.
    """

    def __init__(self) -> None:
        super().__init__()
        self.callbacks: dict[str, object] = {}

    def add_callback(self, callback: object) -> None:
        self.callbacks[callback.__name__] = callback

    def do_create_closure(self, builder: Gtk.Builder, function_name: str, flags: Gtk.BuilderClosureFlags,
                          object: GObject.Object | None) -> object:
        callback = self.callbacks[function_name]
        if object is not None:
            return lambda *args: callback(*args, object)
        return callback


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref, demo

    window = window_ref()
    if window is None:
        builder = Gtk.Builder()

        scope = BuilderCScope()
        scope.add_callback(basic_value_changed)
        scope.add_callback(basic_entry_activated)
        scope.add_callback(color_set_cb)
        scope.add_callback(swap_colors)
        scope.add_callback(font_features_reset_basic)
        scope.add_callback(font_features_reset_features)
        scope.add_callback(font_features_reset_variations)
        scope.add_callback(font_features_toggle_plain)
        scope.add_callback(font_features_toggle_edit)
        scope.add_callback(font_features_stop_edit)
        scope.add_callback(font_features_font_changed)
        scope.add_callback(font_features_script_changed)
        scope.add_callback(font_features_notify_waterfall)
        scope.add_callback(set_text_alphabet)
        scope.add_callback(set_text_paragraph)
        builder.set_scope(scope)

        demo = FontFeaturesDemo()

        builder.add_from_resource("/font_features/font_features.ui")

        window = builder.get_object("window")

        demo.the_label = builder.get_object("label")
        demo.settings = builder.get_object("settings")
        demo.description = builder.get_object("description")
        demo.font = builder.get_object("font")
        demo.script_lang = builder.get_object("script_lang")
        assert isinstance(demo.script_lang, Gtk.DropDown)
        expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, script_lang_get_langname, None)
        demo.script_lang.set_expression(expression)
        demo.feature_list = builder.get_object("feature_list")
        demo.stack = builder.get_object("stack")
        demo.entry = builder.get_object("entry")
        demo.plain_toggle = builder.get_object("plain_toggle")
        demo.waterfall_toggle = builder.get_object("waterfall_toggle")
        demo.edit_toggle = builder.get_object("edit_toggle")
        demo.size_scale = builder.get_object("size_scale")
        demo.size_entry = builder.get_object("size_entry")
        demo.size_adjustment = builder.get_object("size_adjustment")
        demo.letterspacing_entry = builder.get_object("letterspacing_entry")
        demo.letterspacing_adjustment = builder.get_object("letterspacing_adjustment")
        demo.line_height_entry = builder.get_object("line_height_entry")
        demo.line_height_adjustment = builder.get_object("line_height_adjustment")
        demo.foreground = builder.get_object("foreground")
        demo.background = builder.get_object("background")
        demo.swin = builder.get_object("swin")

        demo.provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), demo.provider, 800)

        basic_value_changed(demo.size_adjustment, demo.size_entry)
        basic_value_changed(demo.letterspacing_adjustment, demo.letterspacing_entry)
        basic_value_changed(demo.line_height_adjustment, demo.line_height_entry)

        controller = Gtk.EventControllerKey()
        controller.key_pressed.connect(entry_key_press, demo.entry)
        demo.entry.add_controller(controller)

        add_check_group(demo.feature_list, _("Kerning"),
                        ["kern"])
        add_check_group(demo.feature_list, _("Ligatures"),
                        ["liga", "dlig", "hlig", "clig", "rlig"])
        add_check_group(demo.feature_list, _("Letter Case"),
                        ["smcp", "c2sc", "pcap", "c2pc", "unic", "cpsp",
                         "case"])
        add_radio_group(demo.feature_list, _("Number Case"),
                        ["xxxx", "lnum", "onum"])
        add_radio_group(demo.feature_list, _("Number Spacing"),
                        ["xxxx", "pnum", "tnum"])
        add_radio_group(demo.feature_list, _("Fractions"),
                        ["xxxx", "frac", "afrc"])
        add_check_group(demo.feature_list, _("Numeric Extras"),
                        ["zero", "nalt", "sinf"])
        add_check_group(demo.feature_list, _("Character Alternatives"),
                        ["swsh", "cswh", "locl", "calt", "falt", "hist",
                         "salt", "jalt", "titl", "rand", "subs", "sups",
                         "ordn", "ltra", "ltrm", "rtla", "rtlm", "rclt"])
        add_check_group(demo.feature_list, _("Positional Alternatives"),
                        ["init", "medi", "med2", "fina", "fin2", "fin3",
                         "isol"])
        add_check_group(demo.feature_list, _("Width Variants"),
                        ["fwid", "hwid", "halt", "pwid", "palt", "twid",
                         "qwid"])
        add_check_group(demo.feature_list, _("Alternative Stylistic Sets"),
                        ["ss01", "ss02", "ss03", "ss04", "ss05", "ss06",
                         "ss07", "ss08", "ss09", "ss10", "ss11", "ss12",
                         "ss13", "ss14", "ss15", "ss16", "ss17", "ss18",
                         "ss19", "ss20"])
        add_check_group(demo.feature_list, _("Character Variants"),
                        ["cv01", "cv02", "cv03", "cv04", "cv05", "cv06",
                         "cv07", "cv08", "cv09", "cv10", "cv11", "cv12",
                         "cv13", "cv14", "cv15", "cv16", "cv17", "cv18",
                         "cv19", "cv20"])
        add_check_group(demo.feature_list, _("Mathematical"),
                        ["dtls", "flac", "mgrk", "ssty"])
        add_check_group(demo.feature_list, _("Optical Bounds"),
                        ["opbd", "lfbd", "rtbd"])
        demo.feature_items.reverse()

        demo.variations_grid = builder.get_object("variations_grid")
        if demo.instances is None:
            demo.instances = {}
        else:
            demo.instances.clear()

        if demo.axes is None:
            demo.axes = {}
        else:
            demo.axes.clear()

        font_features_font_changed()

        window_ref = window.weak_ref()
        # g_object_set_data_full() with demo_free() as the destroy notify
        window.weak_ref(demo_free, demo)

        update_display()

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
