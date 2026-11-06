"""Names of Unicode scripts, for the demos that list scripts."""

from PyLiite4 import GLib

GETTEXT_PACKAGE = "gtk40"


def hb_tag(tag: str) -> int:
    # HB_TAG(): four characters packed in an integer.
    return int.from_bytes(tag.encode("latin-1"), "big")


def hb_script_from_iso15924_tag(tag: int) -> int:
    # hb_script_from_iso15924_tag(), from HarfBuzz, which PyLiite4 doesn't expose: it normalizes the case of a script
    # tag, and maps the few tags that are aliases.
    if tag == 0:
        return 0  # HB_SCRIPT_INVALID

    # Lenient about case: it becomes one capital letter followed by three small letters.
    tag = (tag & 0xDFDFDFDF) | 0x00202020

    aliases = {
        hb_tag("Qaai"): hb_tag("Zinh"),
        hb_tag("Qaac"): hb_tag("Copt"),
        hb_tag("Geok"): hb_tag("Geor"),
        hb_tag("Syre"): hb_tag("Syrc"),
        hb_tag("Syrj"): hb_tag("Syrc"),
        hb_tag("Syrn"): hb_tag("Syrc"),
    }
    return aliases.get(tag, tag)


scripts = [
    (GLib.UnicodeScript.COMMON, hb_tag("Zyyy"), "No script"),
    (GLib.UnicodeScript.INHERITED, hb_tag("Zinh"), "No script"),
    (GLib.UnicodeScript.ARABIC, hb_tag("Arab"), "Arabic"),
    (GLib.UnicodeScript.ARMENIAN, hb_tag("Armn"), "Armenian"),
    (GLib.UnicodeScript.BENGALI, hb_tag("Beng"), "Bengali"),
    (GLib.UnicodeScript.BOPOMOFO, hb_tag("Bopo"), "Bopomofo"),
    (GLib.UnicodeScript.CHEROKEE, hb_tag("Cher"), "Cherokee"),
    (GLib.UnicodeScript.COPTIC, hb_tag("Copt"), "Coptic"),
    (GLib.UnicodeScript.CYRILLIC, hb_tag("Cyrl"), "Cyrillic"),
    (GLib.UnicodeScript.DESERET, hb_tag("Dsrt"), "Deseret"),
    (GLib.UnicodeScript.DEVANAGARI, hb_tag("Deva"), "Devanagari"),
    (GLib.UnicodeScript.ETHIOPIC, hb_tag("Ethi"), "Ethiopic"),
    (GLib.UnicodeScript.GEORGIAN, hb_tag("Geor"), "Georgian"),
    (GLib.UnicodeScript.GOTHIC, hb_tag("Goth"), "Gothic"),
    (GLib.UnicodeScript.GREEK, hb_tag("Grek"), "Greek"),
    (GLib.UnicodeScript.GUJARATI, hb_tag("Gujr"), "Gujarati"),
    (GLib.UnicodeScript.GURMUKHI, hb_tag("Guru"), "Gurmukhi"),
    (GLib.UnicodeScript.HAN, hb_tag("Hani"), "Han"),
    (GLib.UnicodeScript.HANGUL, hb_tag("Hang"), "Hangul"),
    (GLib.UnicodeScript.HEBREW, hb_tag("Hebr"), "Hebrew"),
    (GLib.UnicodeScript.HIRAGANA, hb_tag("Hira"), "Hiragana"),
    (GLib.UnicodeScript.KANNADA, hb_tag("Knda"), "Kannada"),
    (GLib.UnicodeScript.KATAKANA, hb_tag("Kana"), "Katakana"),
    (GLib.UnicodeScript.KHMER, hb_tag("Khmr"), "Khmer"),
    (GLib.UnicodeScript.LAO, hb_tag("Laoo"), "Lao"),
    (GLib.UnicodeScript.LATIN, hb_tag("Latn"), "Latin"),
    (GLib.UnicodeScript.MALAYALAM, hb_tag("Mlym"), "Malayalam"),
    (GLib.UnicodeScript.MONGOLIAN, hb_tag("Mong"), "Mongolian"),
    (GLib.UnicodeScript.MYANMAR, hb_tag("Mymr"), "Myanmar"),
    (GLib.UnicodeScript.OGHAM, hb_tag("Ogam"), "Ogham"),
    (GLib.UnicodeScript.OLD_ITALIC, hb_tag("Ital"), "Old Italic"),
    (GLib.UnicodeScript.ORIYA, hb_tag("Orya"), "Oriya"),
    (GLib.UnicodeScript.RUNIC, hb_tag("Runr"), "Runic"),
    (GLib.UnicodeScript.SINHALA, hb_tag("Sinh"), "Sinhala"),
    (GLib.UnicodeScript.SYRIAC, hb_tag("Syrc"), "Syriac"),
    (GLib.UnicodeScript.TAMIL, hb_tag("Taml"), "Tamil"),
    (GLib.UnicodeScript.TELUGU, hb_tag("Telu"), "Telugu"),
    (GLib.UnicodeScript.THAANA, hb_tag("Thaa"), "Thaana"),
    (GLib.UnicodeScript.THAI, hb_tag("Thai"), "Thai"),
    (GLib.UnicodeScript.TIBETAN, hb_tag("Tibt"), "Tibetan"),
    (GLib.UnicodeScript.CANADIAN_ABORIGINAL, hb_tag("Cans"), "Canadian Aboriginal"),
    (GLib.UnicodeScript.YI, hb_tag("Yiii"), "Yi"),
    (GLib.UnicodeScript.TAGALOG, hb_tag("Tglg"), "Tagalog"),
    (GLib.UnicodeScript.HANUNOO, hb_tag("Hano"), "Hanunoo"),
    (GLib.UnicodeScript.BUHID, hb_tag("Buhd"), "Buhid"),
    (GLib.UnicodeScript.TAGBANWA, hb_tag("Tagb"), "Tagbanwa"),
    (GLib.UnicodeScript.BRAILLE, hb_tag("Brai"), "Braille"),
    (GLib.UnicodeScript.CYPRIOT, hb_tag("Cprt"), "Cypriot"),
    (GLib.UnicodeScript.LIMBU, hb_tag("Limb"), "Limbu"),
    (GLib.UnicodeScript.OSMANYA, hb_tag("Osma"), "Osmanya"),
    (GLib.UnicodeScript.SHAVIAN, hb_tag("Shaw"), "Shavian"),
    (GLib.UnicodeScript.LINEAR_B, hb_tag("Linb"), "Linear B"),
    (GLib.UnicodeScript.TAI_LE, hb_tag("Tale"), "Tai Le"),
    (GLib.UnicodeScript.UGARITIC, hb_tag("Ugar"), "Ugaritic"),
    (GLib.UnicodeScript.NEW_TAI_LUE, hb_tag("Talu"), "New Tai Lue"),
    (GLib.UnicodeScript.BUGINESE, hb_tag("Bugi"), "Buginese"),
    (GLib.UnicodeScript.GLAGOLITIC, hb_tag("Glag"), "Glagolitic"),
    (GLib.UnicodeScript.TIFINAGH, hb_tag("Tfng"), "Tifinagh"),
    (GLib.UnicodeScript.SYLOTI_NAGRI, hb_tag("Sylo"), "Syloti Nagri"),
    (GLib.UnicodeScript.OLD_PERSIAN, hb_tag("Xpeo"), "Old Persian"),
    (GLib.UnicodeScript.KHAROSHTHI, hb_tag("Khar"), "Kharoshthi"),
    (GLib.UnicodeScript.UNKNOWN, hb_tag("Zzzz"), "Unknown"),
    (GLib.UnicodeScript.BALINESE, hb_tag("Bali"), "Balinese"),
    (GLib.UnicodeScript.CUNEIFORM, hb_tag("Xsux"), "Cuneiform"),
    (GLib.UnicodeScript.PHOENICIAN, hb_tag("Phnx"), "Phoenician"),
    (GLib.UnicodeScript.PHAGS_PA, hb_tag("Phag"), "Phags-pa"),
    (GLib.UnicodeScript.NKO, hb_tag("Nkoo"), "N'Ko"),
    (GLib.UnicodeScript.KAYAH_LI, hb_tag("Kali"), "Kayah Li"),
    (GLib.UnicodeScript.LEPCHA, hb_tag("Lepc"), "Lepcha"),
    (GLib.UnicodeScript.REJANG, hb_tag("Rjng"), "Rejang"),
    (GLib.UnicodeScript.SUNDANESE, hb_tag("Sund"), "Sundanese"),
    (GLib.UnicodeScript.SAURASHTRA, hb_tag("Saur"), "Saurashtra"),
    (GLib.UnicodeScript.CHAM, hb_tag("Cham"), "Cham"),
    (GLib.UnicodeScript.OL_CHIKI, hb_tag("Olck"), "Ol Chiki"),
    (GLib.UnicodeScript.VAI, hb_tag("Vaii"), "Vai"),
    (GLib.UnicodeScript.CARIAN, hb_tag("Cari"), "Carian"),
    (GLib.UnicodeScript.LYCIAN, hb_tag("Lyci"), "Lycian"),
    (GLib.UnicodeScript.LYDIAN, hb_tag("Lydi"), "Lydian"),
    (GLib.UnicodeScript.AVESTAN, hb_tag("Avst"), "Avestan"),
    (GLib.UnicodeScript.BAMUM, hb_tag("Bamu"), "Bamum"),
    (GLib.UnicodeScript.EGYPTIAN_HIEROGLYPHS, hb_tag("Egyp"), "Egyptian Hieroglyphs"),
    (GLib.UnicodeScript.IMPERIAL_ARAMAIC, hb_tag("Armi"), "Imperial Aramaic"),
    (GLib.UnicodeScript.INSCRIPTIONAL_PAHLAVI, hb_tag("Phli"), "Inscriptional Pahlavi"),
    (GLib.UnicodeScript.INSCRIPTIONAL_PARTHIAN, hb_tag("Prti"), "Inscriptional Parthian"),
    (GLib.UnicodeScript.JAVANESE, hb_tag("Java"), "Javanese"),
    (GLib.UnicodeScript.KAITHI, hb_tag("Kthi"), "Kaithi"),
    (GLib.UnicodeScript.LISU, hb_tag("Lisu"), "Lisu"),
    (GLib.UnicodeScript.MEETEI_MAYEK, hb_tag("Mtei"), "Meetei Mayek"),
    (GLib.UnicodeScript.OLD_SOUTH_ARABIAN, hb_tag("Sarb"), "Old South Arabian"),
    (GLib.UnicodeScript.OLD_TURKIC, hb_tag("Orkh"), "Old Turkic"),
    (GLib.UnicodeScript.SAMARITAN, hb_tag("Samr"), "Samaritan"),
    (GLib.UnicodeScript.TAI_THAM, hb_tag("Lana"), "Tai Tham"),
    (GLib.UnicodeScript.TAI_VIET, hb_tag("Tavt"), "Tai Viet"),
    (GLib.UnicodeScript.BATAK, hb_tag("Batk"), "Batak"),
    (GLib.UnicodeScript.BRAHMI, hb_tag("Brah"), "Brahmi"),
    (GLib.UnicodeScript.MANDAIC, hb_tag("Mand"), "Mandaic"),
    (GLib.UnicodeScript.CHAKMA, hb_tag("Cakm"), "Chakma"),
    (GLib.UnicodeScript.MEROITIC_CURSIVE, hb_tag("Merc"), "Meroitic Cursive"),
    (GLib.UnicodeScript.MEROITIC_HIEROGLYPHS, hb_tag("Mero"), "Meroitic Hieroglyphs"),
    (GLib.UnicodeScript.MIAO, hb_tag("Plrd"), "Miao"),
    (GLib.UnicodeScript.SHARADA, hb_tag("Shrd"), "Sharada"),
    (GLib.UnicodeScript.SORA_SOMPENG, hb_tag("Sora"), "Sora Sompeng"),
    (GLib.UnicodeScript.TAKRI, hb_tag("Takr"), "Takri"),
    (GLib.UnicodeScript.BASSA_VAH, hb_tag("Bass"), "Bassa"),
    (GLib.UnicodeScript.CAUCASIAN_ALBANIAN, hb_tag("Aghb"), "Caucasian Albanian"),
    (GLib.UnicodeScript.DUPLOYAN, hb_tag("Dupl"), "Duployan"),
    (GLib.UnicodeScript.ELBASAN, hb_tag("Elba"), "Elbasan"),
    (GLib.UnicodeScript.GRANTHA, hb_tag("Gran"), "Grantha"),
    (GLib.UnicodeScript.KHOJKI, hb_tag("Khoj"), "Khojki"),
    (GLib.UnicodeScript.KHUDAWADI, hb_tag("Sind"), "Khudawadi, Sindhi"),
    (GLib.UnicodeScript.LINEAR_A, hb_tag("Lina"), "Linear A"),
    (GLib.UnicodeScript.MAHAJANI, hb_tag("Mahj"), "Mahajani"),
    (GLib.UnicodeScript.MANICHAEAN, hb_tag("Mani"), "Manichaean"),
    (GLib.UnicodeScript.MENDE_KIKAKUI, hb_tag("Mend"), "Mende Kikakui"),
    (GLib.UnicodeScript.MODI, hb_tag("Modi"), "Modi"),
    (GLib.UnicodeScript.MRO, hb_tag("Mroo"), "Mro"),
    (GLib.UnicodeScript.NABATAEAN, hb_tag("Nbat"), "Nabataean"),
    (GLib.UnicodeScript.OLD_NORTH_ARABIAN, hb_tag("Narb"), "Old North Arabian"),
    (GLib.UnicodeScript.OLD_PERMIC, hb_tag("Perm"), "Old Permic"),
    (GLib.UnicodeScript.PAHAWH_HMONG, hb_tag("Hmng"), "Pahawh Hmong"),
    (GLib.UnicodeScript.PALMYRENE, hb_tag("Palm"), "Palmyrene"),
    (GLib.UnicodeScript.PAU_CIN_HAU, hb_tag("Pauc"), "Pau Cin Hau"),
    (GLib.UnicodeScript.PSALTER_PAHLAVI, hb_tag("Phlp"), "Psalter Pahlavi"),
    (GLib.UnicodeScript.SIDDHAM, hb_tag("Sidd"), "Siddham"),
    (GLib.UnicodeScript.TIRHUTA, hb_tag("Tirh"), "Tirhuta"),
    (GLib.UnicodeScript.WARANG_CITI, hb_tag("Wara"), "Warang Citi"),
    (GLib.UnicodeScript.AHOM, hb_tag("Ahom"), "Ahom"),
    (GLib.UnicodeScript.ANATOLIAN_HIEROGLYPHS, hb_tag("Hluw"), "Anatolian Hieroglyphs"),
    (GLib.UnicodeScript.HATRAN, hb_tag("Hatr"), "Hatran"),
    (GLib.UnicodeScript.MULTANI, hb_tag("Mult"), "Multani"),
    (GLib.UnicodeScript.OLD_HUNGARIAN, hb_tag("Hung"), "Old Hungarian"),
    (GLib.UnicodeScript.SIGNWRITING, hb_tag("Sgnw"), "Signwriting"),
    (GLib.UnicodeScript.ADLAM, hb_tag("Adlm"), "Adlam"),
    (GLib.UnicodeScript.BHAIKSUKI, hb_tag("Bhks"), "Bhaiksuki"),
    (GLib.UnicodeScript.MARCHEN, hb_tag("Marc"), "Marchen"),
    (GLib.UnicodeScript.NEWA, hb_tag("Newa"), "Newa"),
    (GLib.UnicodeScript.OSAGE, hb_tag("Osge"), "Osage"),
    (GLib.UnicodeScript.TANGUT, hb_tag("Tang"), "Tangut"),
    (GLib.UnicodeScript.MASARAM_GONDI, hb_tag("Gonm"), "Masaram Gondi"),
    (GLib.UnicodeScript.NUSHU, hb_tag("Nshu"), "Nushu"),
    (GLib.UnicodeScript.SOYOMBO, hb_tag("Soyo"), "Soyombo"),
    (GLib.UnicodeScript.ZANABAZAR_SQUARE, hb_tag("Zanb"), "Zanabazar Square"),
    (GLib.UnicodeScript.DOGRA, hb_tag("Dogr"), "Dogra"),
    (GLib.UnicodeScript.GUNJALA_GONDI, hb_tag("Gong"), "Gunjala Gondi"),
    (GLib.UnicodeScript.HANIFI_ROHINGYA, hb_tag("Rohg"), "Hanifi Rohingya"),
    (GLib.UnicodeScript.MAKASAR, hb_tag("Maka"), "Makasar"),
    (GLib.UnicodeScript.MEDEFAIDRIN, hb_tag("Medf"), "Medefaidrin"),
    (GLib.UnicodeScript.OLD_SOGDIAN, hb_tag("Sogo"), "Old Sogdian"),
    (GLib.UnicodeScript.SOGDIAN, hb_tag("Sogd"), "Sogdian"),
    (GLib.UnicodeScript.ELYMAIC, hb_tag("Elym"), "Elym"),
    (GLib.UnicodeScript.NANDINAGARI, hb_tag("Nand"), "Nand"),
    (GLib.UnicodeScript.NYIAKENG_PUACHUE_HMONG, hb_tag("Hmnp"), "Rohg"),
    (GLib.UnicodeScript.WANCHO, hb_tag("Wcho"), "Wcho"),
    (GLib.UnicodeScript.CHORASMIAN, hb_tag("Chrs"), "Chorasmian"),
    (GLib.UnicodeScript.DIVES_AKURU, hb_tag("Diak"), "Dives Akuru"),
    (GLib.UnicodeScript.KHITAN_SMALL_SCRIPT, hb_tag("Kits"), "Khitan small script"),
    (GLib.UnicodeScript.YEZIDI, hb_tag("Yezi"), "Yezidi"),
]


def get_script_name(script: GLib.UnicodeScript) -> str | None:
    for entry_script, _hb_script, name in scripts:
        if entry_script == script:
            if name:
                return GLib.dpgettext2(GETTEXT_PACKAGE, "Script", name)
            else:
                return ""

    return None


def get_script_name_for_tag(tag: int) -> str | None:
    for _script, hb_script, name in scripts:
        if hb_script == hb_script_from_iso15924_tag(tag):
            return GLib.dpgettext2(GETTEXT_PACKAGE, "Script", name)

    return None
