"""Conversions between GdkRGBA and the HSLA colour model, used by the Masking demo's Demo4Widget.

Ported from GTK Demo's hsla.c and hsla.h.
"""

from dataclasses import dataclass

from PyLiite4 import Gdk


@dataclass
class GdkHSLA:
    hue: float = 0.0
    saturation: float = 0.0
    lightness: float = 0.0
    alpha: float = 0.0


def _gdk_hsla_init_from_rgba(hsla: GdkHSLA, rgba: Gdk.RGBA) -> None:
    red = rgba.red
    green = rgba.green
    blue = rgba.blue

    if red > green:
        if red > blue:
            max = red
        else:
            max = blue

        if green < blue:
            min = green
        else:
            min = blue
    else:
        if green > blue:
            max = green
        else:
            max = blue

        if red < blue:
            min = red
        else:
            min = blue

    hsla.lightness = (max + min) / 2
    hsla.saturation = 0
    hsla.hue = 0
    hsla.alpha = rgba.alpha

    if max != min:
        if hsla.lightness <= 0.5:
            hsla.saturation = (max - min) / (max + min)
        else:
            hsla.saturation = (max - min) / (2 - max - min)

        delta = max - min
        if red == max:
            hsla.hue = (green - blue) / delta
        elif green == max:
            hsla.hue = 2 + (blue - red) / delta
        elif blue == max:
            hsla.hue = 4 + (red - green) / delta

        hsla.hue *= 60
        if hsla.hue < 0.0:
            hsla.hue += 360


def _channel(m1: float, m2: float, hue: float) -> float:
    while hue > 360:
        hue -= 360
    while hue < 0:
        hue += 360

    if hue < 60:
        return m1 + (m2 - m1) * hue / 60
    elif hue < 180:
        return m2
    elif hue < 240:
        return m1 + (m2 - m1) * (240 - hue) / 60
    else:
        return m1


def _gdk_rgba_init_from_hsla(rgba: Gdk.RGBA, hsla: GdkHSLA) -> None:
    lightness = hsla.lightness
    saturation = hsla.saturation

    if lightness <= 0.5:
        m2 = lightness * (1 + saturation)
    else:
        m2 = lightness + saturation - lightness * saturation
    m1 = 2 * lightness - m2

    rgba.alpha = hsla.alpha

    if saturation == 0:
        rgba.red = lightness
        rgba.green = lightness
        rgba.blue = lightness
    else:
        rgba.red = _channel(m1, m2, hsla.hue + 120)
        rgba.green = _channel(m1, m2, hsla.hue)
        rgba.blue = _channel(m1, m2, hsla.hue - 120)
