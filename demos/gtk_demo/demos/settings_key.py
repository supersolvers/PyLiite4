"""SettingsKey: a GObject wrapping a GSettingsSchemaKey, used by the Lists/Settings demos.

Ported from GTK Demo's settings-key.c and settings-key.h.
"""

from PyLiite4 import Gio, GObject

_READABLE = GObject.ParamFlags.READABLE


class SettingsKey(GObject.Object):
    """An object that wraps GSettingsSchemaKey because that's a boxed type."""

    __gtype_name__ = "SettingsKey"

    def __init__(self) -> None:
        super().__init__()
        self._settings: Gio.Settings | None = None
        self.key: Gio.SettingsSchemaKey | None = None

    @GObject.Property(type=str, flags=_READABLE)
    def description(self) -> str | None:
        return self.key.get_description()

    @GObject.Property(type=str, flags=_READABLE)
    def name(self) -> str:
        return self.key.get_name()

    @GObject.Property(type=Gio.Settings, flags=_READABLE)
    def settings(self) -> Gio.Settings:
        return self._settings

    @GObject.Property(type=str, flags=_READABLE)
    def summary(self) -> str | None:
        return self.key.get_summary()

    @GObject.Property(type=str, flags=_READABLE)
    def value(self) -> str:
        variant = self._settings.get_value(self.key.get_name())
        return variant.print_(False)

    @GObject.Property(type=str, flags=_READABLE)
    def type(self) -> str:
        type = self.key.get_value_type()
        return type.dup_string()

    @GObject.Property(type=str, flags=_READABLE)
    def default_value(self) -> str:
        variant = self.key.get_default_value()
        return variant.print_(False)

    def get_key(self) -> Gio.SettingsSchemaKey:
        return self.key

    def get_settings(self) -> Gio.Settings:
        return self._settings

    def get_search_string(self) -> str:
        schema = self._settings.get_property("schema-id")

        return " ".join([self.key.get_name(), self.key.get_summary() or "", schema])


def settings_key_new(settings: Gio.Settings, key: Gio.SettingsSchemaKey) -> SettingsKey:
    result = SettingsKey()

    result._settings = settings
    result.key = key

    return result


def settings_key_get_search_string(self: SettingsKey, *_user_data: object) -> str:
    return self.get_search_string()
