"""A paintable that draws a texture through filters, used by image_filtering."""

import math

from PyLiite4 import Gdk, GObject, Graphene, Gsk

R = 0.2126
G = 0.7152
B = 0.0722


def component_transfer_equal(transfer: Gsk.ComponentTransfer, identity: Gsk.ComponentTransfer) -> bool:
    # gsk_component_transfer_equal() takes gconstpointer arguments, which PyGObject can't pass a boxed for. A
    # component transfer node serializes only the transfers that aren't the identity, so that tells the same.
    node = Gsk.ComponentTransferNode.new(Gsk.ColorNode.new(Gdk.RGBA(), Graphene.Rect().init(0, 0, 1, 1)),
                                         transfer, identity, identity, identity)
    return "red:" not in node.serialize().get_data().decode()


class GtkFilterPaintable(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkFilterPaintable"

    def __init__(self, **properties: object) -> None:
        self._texture = Gdk.Texture.new_from_resource("/image_filtering/portland-rose.jpg")
        self._brightness = 1.0
        self._contrast = 1.0
        self._saturation = 1.0
        self._sepia = 0.0
        self._invert = 0.0
        self._rotate = 0.0
        self._blur = 0.0

        self._red_transfer = Gsk.ComponentTransfer.new_identity()
        self._green_transfer = Gsk.ComponentTransfer.new_identity()
        self._blue_transfer = Gsk.ComponentTransfer.new_identity()
        self._alpha_transfer = Gsk.ComponentTransfer.new_identity()
        super().__init__(**properties)

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        identity = Gsk.ComponentTransfer.new_identity()

        if self._brightness != 1:
            matrix = Graphene.Matrix().init_scale(self._brightness, self._brightness, self._brightness)
            snapshot.push_color_matrix(matrix, Graphene.Vec4.zero())

        if self._contrast != 1:
            matrix = Graphene.Matrix().init_scale(self._contrast, self._contrast, self._contrast)

            offset = Graphene.Vec4().init(0.5 - 0.5 * self._contrast, 0.5 - 0.5 * self._contrast,
                                          0.5 - 0.5 * self._contrast, 0.0)

            snapshot.push_color_matrix(matrix, offset)

        if self._saturation != 1:
            value = self._saturation

            matrix = Graphene.Matrix().init_from_float([
                R + (1.0 - R) * value, R - R * value, R - R * value, 0.0,
                G - G * value, G + (1.0 - G) * value, G - G * value, 0.0,
                B - B * value, B - B * value, B + (1.0 - B) * value, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ])
            snapshot.push_color_matrix(matrix, Graphene.Vec4.zero())

        if self._sepia != 0:
            value = self._sepia

            matrix = Graphene.Matrix().init_from_float([
                1.0 - 0.607 * value, 0.349 * value, 0.272 * value, 0.0,
                0.769 * value, 1.0 - 0.314 * value, 0.534 * value, 0.0,
                0.189 * value, 0.168 * value, 1.0 - 0.869 * value, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ])
            snapshot.push_color_matrix(matrix, Graphene.Vec4.zero())

        if self._invert != 0:
            matrix = Graphene.Matrix().init_scale(1 - 2 * self._invert, 1 - 2 * self._invert, 1 - 2 * self._invert)

            offset = Graphene.Vec4().init(self._invert, self._invert, self._invert, 0)

            snapshot.push_color_matrix(matrix, offset)

        if self._rotate != 0:
            c = math.cos(self._rotate * math.pi / 180)
            s = math.sin(self._rotate * math.pi / 180)

            matrix = Graphene.Matrix().init_from_float([
                0.213 + 0.787 * c - 0.213 * s,
                0.213 - 0.213 * c + 0.143 * s,
                0.213 - 0.213 * c - 0.787 * s,
                0,
                0.715 - 0.715 * c - 0.715 * s,
                0.715 + 0.285 * c + 0.140 * s,
                0.715 - 0.715 * c + 0.715 * s,
                0,
                0.072 - 0.072 * c + 0.928 * s,
                0.072 - 0.072 * c - 0.283 * s,
                0.072 + 0.928 * c + 0.072 * s,
                0,
                0, 0, 0, 1,
            ])

            snapshot.push_color_matrix(matrix, Graphene.Vec4.zero())

        transfer = (not component_transfer_equal(self._red_transfer, identity)
                    or not component_transfer_equal(self._green_transfer, identity)
                    or not component_transfer_equal(self._blue_transfer, identity)
                    or not component_transfer_equal(self._alpha_transfer, identity))
        if transfer:
            snapshot.push_component_transfer(self._red_transfer, self._green_transfer, self._blue_transfer,
                                             self._alpha_transfer)

        if self._blur != 0:
            snapshot.push_blur(self._blur)

        snapshot.append_texture(self._texture, Graphene.Rect().init(0, 0, self._texture.get_width(),
                                                                    self._texture.get_height()))

        if self._blur != 0:
            snapshot.pop()

        if transfer:
            snapshot.pop()

        if self._saturation != 1:
            snapshot.pop()

        if self._sepia != 0:
            snapshot.pop()

        if self._contrast != 1:
            snapshot.pop()

        if self._brightness != 1:
            snapshot.pop()

        if self._invert != 0:
            snapshot.pop()

        if self._rotate != 0:
            snapshot.pop()

    def do_get_intrinsic_width(self) -> int:
        return self._texture.get_width()

    def do_get_intrinsic_height(self) -> int:
        return self._texture.get_height()

    def _set(self, name: str, value: object) -> None:
        setattr(self, name, value)
        self.invalidate_contents()

    @GObject.Property(type=Gdk.Texture)
    def texture(self) -> Gdk.Texture:
        return self._texture

    @texture.setter
    def texture(self, value: Gdk.Texture) -> None:
        self._set("_texture", value)

    @GObject.Property(type=float, minimum=0, maximum=2, default=1)
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, value: float) -> None:
        self._set("_brightness", value)

    @GObject.Property(type=float, minimum=0, maximum=2, default=1)
    def contrast(self) -> float:
        return self._contrast

    @contrast.setter
    def contrast(self, value: float) -> None:
        self._set("_contrast", value)

    @GObject.Property(type=float, minimum=0, maximum=2, default=1)
    def saturation(self) -> float:
        return self._saturation

    @saturation.setter
    def saturation(self, value: float) -> None:
        self._set("_saturation", value)

    @GObject.Property(type=float, minimum=0, maximum=1, default=1)
    def sepia(self) -> float:
        return self._sepia

    @sepia.setter
    def sepia(self, value: float) -> None:
        self._set("_sepia", value)

    @GObject.Property(type=float, minimum=0, maximum=1, default=0)
    def invert(self) -> float:
        return self._invert

    @invert.setter
    def invert(self, value: float) -> None:
        self._set("_invert", value)

    @GObject.Property(type=float, minimum=0, maximum=360, default=0)
    def rotate(self) -> float:
        return self._rotate

    @rotate.setter
    def rotate(self, value: float) -> None:
        self._set("_rotate", value)

    @GObject.Property(type=float, minimum=0, maximum=50, default=0)
    def blur(self) -> float:
        return self._blur

    @blur.setter
    def blur(self, value: float) -> None:
        self._set("_blur", value)

    @GObject.Property(type=Gsk.ComponentTransfer)
    def red_transfer(self) -> Gsk.ComponentTransfer:
        return self._red_transfer

    @red_transfer.setter
    def red_transfer(self, value: Gsk.ComponentTransfer) -> None:
        self._set("_red_transfer", value.copy())

    @GObject.Property(type=Gsk.ComponentTransfer)
    def green_transfer(self) -> Gsk.ComponentTransfer:
        return self._green_transfer

    @green_transfer.setter
    def green_transfer(self, value: Gsk.ComponentTransfer) -> None:
        self._set("_green_transfer", value.copy())

    @GObject.Property(type=Gsk.ComponentTransfer)
    def blue_transfer(self) -> Gsk.ComponentTransfer:
        return self._blue_transfer

    @blue_transfer.setter
    def blue_transfer(self, value: Gsk.ComponentTransfer) -> None:
        self._set("_blue_transfer", value.copy())

    @GObject.Property(type=Gsk.ComponentTransfer)
    def alpha_transfer(self) -> Gsk.ComponentTransfer:
        return self._alpha_transfer

    @alpha_transfer.setter
    def alpha_transfer(self, value: Gsk.ComponentTransfer) -> None:
        self._set("_alpha_transfer", value.copy())
