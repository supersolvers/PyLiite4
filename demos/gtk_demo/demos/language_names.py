"""Names of languages, from the ISO codes, for the Font Explorer demo."""

import ctypes
import gettext
import io
import sys
import xml.etree.ElementTree as ET

from PyLiite4 import Pango

ISO_CODES_PREFIX = "/usr"
ISO_CODES_DATADIR = ISO_CODES_PREFIX + "/share/xml/iso-codes"
ISO_CODES_LOCALESDIR = ISO_CODES_PREFIX + "/share/locale"

# PyLiite4 doesn't expose HarfBuzz, so its two functions used here are called through ctypes, in the copy of HarfBuzz
# that Pango has loaded already.
_harfbuzz = ctypes.CDLL("libharfbuzz.so.0")
_harfbuzz.hb_ot_tag_to_language.restype = ctypes.c_void_p
_harfbuzz.hb_ot_tag_to_language.argtypes = [ctypes.c_uint32]
_harfbuzz.hb_language_to_string.restype = ctypes.c_char_p
_harfbuzz.hb_language_to_string.argtypes = [ctypes.c_void_p]


def hb_ot_tag_to_language(tag: int) -> int | None:
    return _harfbuzz.hb_ot_tag_to_language(tag)


def hb_language_to_string(language: int | None) -> str | None:
    s = _harfbuzz.hb_language_to_string(language)
    return s.decode() if s is not None else None


# PangoLanguages are interned, so the C code keys its table by them; here they're keyed by their string.
language_map: dict[str, str] | None = None


def get_first_item_in_semicolon_list(list: str) -> str:
    return list.split("; ", 1)[0]


def capitalize_utf8_string(s: str | None) -> str | None:
    if not s:
        return s

    return s[0].title() + s[1:]


def get_display_name(language: str) -> str:
    translated = gettext.dgettext("iso_639", language)

    tmp = get_first_item_in_semicolon_list(translated)
    name = capitalize_utf8_string(tmp)

    return name


def languages_parse_start_tag(element_name: str, attrs: dict[str, str]) -> None:
    if not (element_name == "iso_639_entry" or element_name == "iso_639_3_entry") or not attrs:
        return

    ccode = None
    ccode_longB = None
    ccode_longT = None
    ccode_id = None
    lang_name = None

    for attr_name, attr_value in attrs.items():
        if attr_name == "iso_639_1_code":
            if attr_value:
                if len(attr_value) != 2:
                    return
                ccode = attr_value
        elif attr_name == "iso_639_2B_code":
            if attr_value:
                if len(attr_value) != 3:
                    return
                ccode_longB = attr_value
        elif attr_name == "iso_639_2T_code":
            if attr_value:
                if len(attr_value) != 3:
                    return
                ccode_longT = attr_value
        elif attr_name == "id":
            if attr_value:
                if len(attr_value) != 2 and len(attr_value) != 3:
                    return
                ccode_id = attr_value
        elif attr_name == "name":
            lang_name = attr_value

    if lang_name is None:
        return

    display_name = get_display_name(lang_name)

    for code in (ccode, ccode_longB, ccode_longT, ccode_id):
        if code is not None:
            language_map[Pango.Language.from_string(code).to_string()] = display_name


def warning(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def languages_variant_init(variant: str) -> None:
    gettext.bindtextdomain(variant, ISO_CODES_LOCALESDIR)

    filename = ISO_CODES_DATADIR + "/" + variant + ".xml"
    try:
        with open(filename, "rb") as file:
            buf = file.read()
    except OSError as error:
        warning(f"Failed to load '{filename}': {error.strerror}")
        return

    try:
        for _event, element in ET.iterparse(io.BytesIO(buf), events=("start",)):
            languages_parse_start_tag(element.tag, element.attrib)
    except ET.ParseError as error:
        warning(f"Failed to parse '{filename}': {error}")


def languages_init() -> None:
    global language_map
    if language_map is not None:
        return

    language_map = {}

    languages_variant_init("iso_639")
    languages_variant_init("iso_639_3")


def get_language_name(language: Pango.Language) -> str | None:
    languages_init()

    return language_map.get(language.to_string())


def get_language_name_for_tag(tag: int) -> str | None:
    lang = hb_ot_tag_to_language(tag)
    s = hb_language_to_string(lang)

    if s == "und-fonipa":
        return "International Phonetic Alphabet"
    elif s == "und-fonnapa":
        return "North-American Phonetic Alphabet"
    elif s == "ro-md":
        return "Moldavian"

    return get_language_name(Pango.Language.from_string(s))

