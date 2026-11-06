"""GtkGears, the classic OpenGL gears in a GtkGLArea, used by the Gears and Fishbowl demos.

The rendering code in here is taken from es2gears, which has the
following copyright notice:

Copyright (C) 1999-2001  Brian Paul   All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
BRIAN PAUL BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Ported to GLES2.
Kristian Høgsberg <krh@bitplanet.net>
May 3, 2010

Improve GLES2 port:
  * Refactor gear drawing.
  * Use correct normals for surfaces.
  * Improve shader.
  * Use perspective projection transformation.
  * Add FPS count.
  * Add comments.
Alexandros Frantzis <alexandros.frantzis@linaro.org>
Jul 13, 2010
"""

import ctypes
import logging
import math
from dataclasses import dataclass, field

from PyLiite4 import Gdk, GLib, Gtk

# OpenGL, through the libepoxy that GTK uses: each epoxy_gl* symbol is a pointer to the function for the current
# context, as epoxy/gl.h's glFoo macros use it.
_epoxy = ctypes.CDLL("libepoxy.so.0")
GLuint = ctypes.c_uint
GLint = ctypes.c_int
GLenum = ctypes.c_uint
GLfloat = ctypes.c_float
GLboolean = ctypes.c_ubyte


def _gl(name: str, restype, *argtypes):
    pointer = ctypes.c_void_p.in_dll(_epoxy, f"epoxy_{name}")
    prototype = ctypes.CFUNCTYPE(restype, *argtypes)
    functions = {}

    def call(*args):
        # epoxy points the symbol at a resolver first, then at the function it resolved.
        function = functions.get(pointer.value)
        if function is None:
            function = functions[pointer.value] = prototype(pointer.value)
        return function(*args)
    return call


GL_FALSE = 0
GL_FLOAT = 0x1406
GL_TRIANGLE_STRIP = 0x0005
GL_CULL_FACE = 0x0B44
GL_DEPTH_TEST = 0x0B71
GL_ARRAY_BUFFER = 0x8892
GL_STATIC_DRAW = 0x88E4
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_FRAGMENT_SHADER = 0x8B30
GL_VERTEX_SHADER = 0x8B31

glEnable = _gl("glEnable", None, GLenum)
glViewport = _gl("glViewport", None, GLint, GLint, ctypes.c_int, ctypes.c_int)
glGenVertexArrays = _gl("glGenVertexArrays", None, ctypes.c_int, ctypes.POINTER(GLuint))
glBindVertexArray = _gl("glBindVertexArray", None, GLuint)
glDeleteVertexArrays = _gl("glDeleteVertexArrays", None, ctypes.c_int, ctypes.POINTER(GLuint))
glGenBuffers = _gl("glGenBuffers", None, ctypes.c_int, ctypes.POINTER(GLuint))
glBindBuffer = _gl("glBindBuffer", None, GLenum, GLuint)
glBufferData = _gl("glBufferData", None, GLenum, ctypes.c_ssize_t, ctypes.c_void_p, GLenum)
glDeleteBuffers = _gl("glDeleteBuffers", None, ctypes.c_int, ctypes.POINTER(GLuint))
glCreateShader = _gl("glCreateShader", GLuint, GLenum)
glShaderSource = _gl("glShaderSource", None, GLuint, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p),
                     ctypes.c_void_p)
glCompileShader = _gl("glCompileShader", None, GLuint)
glGetShaderInfoLog = _gl("glGetShaderInfoLog", None, GLuint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
glDeleteShader = _gl("glDeleteShader", None, GLuint)
glCreateProgram = _gl("glCreateProgram", GLuint)
glAttachShader = _gl("glAttachShader", None, GLuint, GLuint)
glDetachShader = _gl("glDetachShader", None, GLuint, GLuint)
glBindAttribLocation = _gl("glBindAttribLocation", None, GLuint, GLuint, ctypes.c_char_p)
glLinkProgram = _gl("glLinkProgram", None, GLuint)
glGetProgramInfoLog = _gl("glGetProgramInfoLog", None, GLuint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
glDeleteProgram = _gl("glDeleteProgram", None, GLuint)
glUseProgram = _gl("glUseProgram", None, GLuint)
glGetUniformLocation = _gl("glGetUniformLocation", GLint, GLuint, ctypes.c_char_p)
glUniform4fv = _gl("glUniform4fv", None, GLint, ctypes.c_int, ctypes.POINTER(GLfloat))
glUniformMatrix4fv = _gl("glUniformMatrix4fv", None, GLint, ctypes.c_int, GLboolean, ctypes.POINTER(GLfloat))
glEnableVertexAttribArray = _gl("glEnableVertexAttribArray", None, GLuint)
glDisableVertexAttribArray = _gl("glDisableVertexAttribArray", None, GLuint)
glVertexAttribPointer = _gl("glVertexAttribPointer", None, GLuint, GLint, GLenum, GLboolean, ctypes.c_int,
                            ctypes.c_void_p)
glDrawArrays = _gl("glDrawArrays", None, GLenum, GLint, ctypes.c_int)
glClearColor = _gl("glClearColor", None, GLfloat, GLfloat, GLfloat, GLfloat)
glClear = _gl("glClear", None, ctypes.c_uint)


def floats(values: list[float]) -> ctypes.Array:
    return (GLfloat * len(values))(*values)


GTK_GEARS_X_AXIS, GTK_GEARS_Y_AXIS, GTK_GEARS_Z_AXIS, GTK_GEARS_N_AXIS = range(4)

STRIPS_PER_TOOTH = 7
VERTICES_PER_TOOTH = 34
GEAR_VERTEX_STRIDE = 6

log = logging.getLogger(__name__)


@dataclass
class VertexStrip:
    """Struct describing the vertices in triangle strip"""
    # The first vertex in the strip.
    first: int = 0
    # The number of consecutive vertices in the strip after the first.
    count: int = 0


@dataclass
class Gear:
    """Struct representing a gear."""
    # The vertices comprising the gear, GEAR_VERTEX_STRIDE floats each.
    vertices: list[float] = field(default_factory=list)
    # The number of vertices comprising the gear.
    nvertices: int = 0
    # The triangle strips comprising the gear.
    strips: list[VertexStrip] = field(default_factory=list)
    # The number of triangle strips comprising the gear.
    nstrips: int = 0


def create_gear(inner_radius: float, outer_radius: float, width: float, teeth: int, tooth_depth: float) -> Gear:
    """Create a gear wheel.

    inner_radius: radius of hole at center
    outer_radius: radius at center of teeth
    width: width of gear
    teeth: number of teeth
    tooth_depth: depth of tooth
    """
    gear = Gear()

    # The radii used in the gear
    r0 = inner_radius
    r1 = outer_radius - tooth_depth / 2.0
    r2 = outer_radius + tooth_depth / 2.0

    da = 2.0 * math.pi / teeth / 4.0

    # The triangle strip information
    gear.nstrips = STRIPS_PER_TOOTH * teeth
    gear.strips = [VertexStrip() for _ in range(gear.nstrips)]

    v = gear.vertices
    cur_strip = 0
    normal = [0.0, 0.0, 0.0]

    for i in range(teeth):
        # Helpers that make creating the gears easier, as the C macros do.
        def set_normal(x: float, y: float, z: float) -> None:
            normal[:] = [x, y, z]

        def gear_vert(point: int, sign: int) -> None:
            v.extend([p[point][0], p[point][1], sign * width * 0.5, *normal])

        def start_strip() -> None:
            gear.strips[cur_strip].first = len(v) // GEAR_VERTEX_STRIDE

        def end_strip() -> None:
            nonlocal cur_strip
            gear.strips[cur_strip].count = len(v) // GEAR_VERTEX_STRIDE - gear.strips[cur_strip].first
            cur_strip += 1

        def quad_with_normal(p1: int, p2: int) -> None:
            set_normal(p[p1][1] - p[p2][1], -(p[p1][0] - p[p2][0]), 0)
            gear_vert(p1, -1)
            gear_vert(p1, 1)
            gear_vert(p2, -1)
            gear_vert(p2, 1)

        # The sines and cosines of the angles a tooth needs.
        s = [math.sin(i * 2.0 * math.pi / teeth + da * k) for k in range(5)]
        c = [math.cos(i * 2.0 * math.pi / teeth + da * k) for k in range(5)]

        def gear_point(r: float, da: int) -> tuple[float, float]:
            return r * c[da], r * s[da]

        # The 7 points, x and y only, that a tooth is drawn with.
        p = [
            gear_point(r2, 1),
            gear_point(r2, 2),
            gear_point(r1, 0),
            gear_point(r1, 3),
            gear_point(r0, 0),
            gear_point(r1, 4),
            gear_point(r0, 4),
        ]

        # Front face
        start_strip()
        set_normal(0, 0, 1.0)
        for point in range(7):
            gear_vert(point, +1)
        end_strip()

        # Inner face
        start_strip()
        quad_with_normal(4, 6)
        end_strip()

        # Back face
        start_strip()
        set_normal(0, 0, -1.0)
        for point in reversed(range(7)):
            gear_vert(point, -1)
        end_strip()

        # Outer face
        start_strip()
        quad_with_normal(0, 2)
        end_strip()

        start_strip()
        quad_with_normal(1, 0)
        end_strip()

        start_strip()
        quad_with_normal(3, 1)
        end_strip()

        start_strip()
        quad_with_normal(5, 3)
        end_strip()

    gear.nvertices = len(v) // GEAR_VERTEX_STRIDE

    return gear


def multiply(m: list[float], n: list[float]) -> None:
    """Multiplies two 4x4 matrices. The result is stored in matrix m."""
    tmp = [0.0] * 16

    for i in range(16):
        quot, rem = divmod(i, 4)
        for j in range(4):
            tmp[i] += n[quot * 4 + j] * m[rem + j * 4]
    m[:] = tmp


def rotate(m: list[float], angle: float, x: float, y: float, z: float) -> None:
    """Rotates a 4x4 matrix by angle, around the direction x, y, z."""
    s = math.sin(angle)
    c = math.cos(angle)

    r = [
        x * x * (1 - c) + c,     y * x * (1 - c) + z * s, x * z * (1 - c) - y * s, 0,
        x * y * (1 - c) - z * s, y * y * (1 - c) + c,     y * z * (1 - c) + x * s, 0,
        x * z * (1 - c) + y * s, y * z * (1 - c) - x * s, z * z * (1 - c) + c,     0,
        0, 0, 0, 1,
    ]

    multiply(m, r)


def translate(m: list[float], x: float, y: float, z: float) -> None:
    """Translates a 4x4 matrix by x, y, z."""
    t = [1, 0, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0,  x, y, z, 1]

    multiply(m, t)


def identity(m: list[float]) -> None:
    """Makes m an identity 4x4 matrix."""
    m[:] = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def transpose(m: list[float]) -> None:
    """Transposes a 4x4 matrix."""
    m[:] = [
        m[0], m[4], m[8],  m[12],
        m[1], m[5], m[9],  m[13],
        m[2], m[6], m[10], m[14],
        m[3], m[7], m[11], m[15]]


def invert(m: list[float]) -> None:
    """Inverts a 4x4 matrix.

    This function can currently handle only pure translation-rotation matrices.
    Read http://www.gamedev.net/community/forums/topic.asp?topic_id=425118
    for an explanation.
    """
    t = [0.0] * 16
    identity(t)

    # The translation part, t, inverted: negating a translation's coordinates inverts it.
    t[12] = -m[12]
    t[13] = -m[13]
    t[14] = -m[14]

    # The rotation part, r, inverted: a rotation matrix's inverse is its transpose.
    m[12] = m[13] = m[14] = 0
    transpose(m)

    # inv(m) = inv(r) * inv(t)
    multiply(m, t)


def perspective(m: list[float], fovy: float, aspect: float, zNear: float, zFar: float) -> None:
    """Calculate a perspective projection transformation into m."""
    tmp = [0.0] * 16
    radians = fovy / 2 * math.pi / 180
    identity(tmp)

    deltaZ = zFar - zNear
    sine = math.sin(radians)
    cosine = math.cos(radians)

    if deltaZ == 0 or sine == 0 or aspect == 0:
        return

    cotangent = cosine / sine

    tmp[0] = cotangent / aspect
    tmp[5] = cotangent
    tmp[10] = -(zFar + zNear) / deltaZ
    tmp[11] = -1
    tmp[14] = -2 * zNear * zFar / deltaZ
    tmp[15] = 0

    m[:] = tmp


vertex_shader_gl = """#version 150

in vec3 position;
in vec3 normal;

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 NormalMatrix;
uniform vec4 LightSourcePosition;
uniform vec4 MaterialColor;

smooth out vec4 Color;

void main(void)
{
    // Transform the normal to eye coordinates
    vec3 N = normalize(vec3(NormalMatrix * vec4(normal, 1.0)));

    // The LightSourcePosition is actually its direction for directional light
    vec3 L = normalize(LightSourcePosition.xyz);

    // Multiply the diffuse value by the vertex color (which is fixed in this case)
    // to get the actual color that we will use to draw this vertex with
    float diffuse = (dot(N, L) + 1.0) * 0.5;
    Color = vec4(diffuse * MaterialColor.rgb, 1.0);

    // Transform the position to clip coordinates
    gl_Position = ModelViewProjectionMatrix * vec4(position, 1.0);
}"""

fragment_shader_gl = """#version 150

smooth in vec4 Color;

void main(void)
{
    gl_FragColor = Color;
}"""

vertex_shader_gles = """attribute vec3 position;
attribute vec3 normal;

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 NormalMatrix;
uniform vec4 LightSourcePosition;
uniform vec4 MaterialColor;

varying vec4 Color;

void main(void)
{
    // Transform the normal to eye coordinates
    vec3 N = normalize(vec3(NormalMatrix * vec4(normal, 1.0)));

    // The LightSourcePosition is actually its direction for directional light
    vec3 L = normalize(LightSourcePosition.xyz);

    // Multiply the diffuse value by the vertex color (which is fixed in this case)
    // to get the actual color that we will use to draw this vertex with
    float diffuse = (dot(N, L) + 1.0) * 0.5;
    Color = vec4(diffuse * MaterialColor.rgb, 1.0);

    // Transform the position to clip coordinates
    gl_Position = ModelViewProjectionMatrix * vec4(position, 1.0);
}"""

fragment_shader_gles = """precision mediump float;
varying vec4 Color;

void main(void)
{
    gl_FragColor = Color;
}"""


class GtkGears(Gtk.GLArea):
    __gtype_name__ = "GtkGears"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        # The view rotation, [x, y, z].
        self.view_rot = [0.0] * GTK_GEARS_N_AXIS
        self.view_rot[GTK_GEARS_X_AXIS] = 20.0
        self.view_rot[GTK_GEARS_Y_AXIS] = 30.0
        self.view_rot[GTK_GEARS_Z_AXIS] = 20.0

        # The Vertex Array Object.
        self.vao = 0
        # The shader program.
        self.program = 0

        self.gear1: Gear | None = None
        self.gear2: Gear | None = None
        self.gear3: Gear | None = None

        # The Vertex Buffer Objects holding the vertices in the graphics card.
        self.gear_vbo = [0, 0, 0]

        # The locations of the shader uniforms.
        self.ModelViewProjectionMatrix_location = 0
        self.NormalMatrix_location = 0
        self.LightSourcePosition_location = 0
        self.MaterialColor_location = 0

        # The current gear rotation angle, in degrees.
        self.angle = 0.0

        self.ProjectionMatrix = [0.0] * 16

        # The direction of the directional light for the scene.
        self.LightSourcePosition = [5.0, 5.0, 10.0, 1.0]

        self.first_frame_time = 0
        self.fps_label: Gtk.Label | None = None

        self.tick = self.add_tick_callback(self.gtk_gears_tick)

    def draw_gear(self, gear: Gear, gear_vbo: int, transform: list[float], x: float, y: float, angle: float,
                  color: list[float]) -> None:
        """Draws a gear at x, y, rotated by angle, in color, with the current transformation matrix."""
        model_view = list(transform)
        translate(model_view, x, y, 0)
        rotate(model_view, 2 * math.pi * angle / 360.0, 0, 0, 1)

        model_view_projection = list(self.ProjectionMatrix)
        multiply(model_view_projection, model_view)

        glUniformMatrix4fv(self.ModelViewProjectionMatrix_location, 1, GL_FALSE, floats(model_view_projection))

        # The NormalMatrix is the inverse transpose of the ModelView matrix.
        normal_matrix = list(model_view)
        invert(normal_matrix)
        transpose(normal_matrix)
        glUniformMatrix4fv(self.NormalMatrix_location, 1, GL_FALSE, floats(normal_matrix))

        glUniform4fv(self.MaterialColor_location, 1, floats(color))

        glBindBuffer(GL_ARRAY_BUFFER, gear_vbo)

        # Each vertex is 6 floats: its position, then its normal.
        size = ctypes.sizeof(GLfloat)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * size, 0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * size, 3 * size)

        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)

        for strip in gear.strips:
            glDrawArrays(GL_TRIANGLE_STRIP, strip.first, strip.count)

        glDisableVertexAttribArray(1)
        glDisableVertexAttribArray(0)

    # Called for a new window size or exposure.
    def do_resize(self, width: int, height: int) -> None:
        perspective(self.ProjectionMatrix, 60.0, width / height, 1.0, 1024.0)

        glViewport(0, 0, width, height)

    def do_render(self, context: Gdk.GLContext) -> bool:
        red = [0.8, 0.1, 0.0, 1.0]
        green = [0.0, 0.8, 0.2, 1.0]
        blue = [0.2, 0.2, 1.0, 1.0]

        transform = [0.0] * 16
        identity(transform)

        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        translate(transform, 0, 0, -20)
        rotate(transform, 2 * math.pi * self.view_rot[0] / 360.0, 1, 0, 0)
        rotate(transform, 2 * math.pi * self.view_rot[1] / 360.0, 0, 1, 0)
        rotate(transform, 2 * math.pi * self.view_rot[2] / 360.0, 0, 0, 1)

        self.draw_gear(self.gear1, self.gear_vbo[0], transform, -3.0, -2.0, self.angle, red)
        self.draw_gear(self.gear2, self.gear_vbo[1], transform, 3.1, -2.0, -2 * self.angle - 9.0, green)
        self.draw_gear(self.gear3, self.gear_vbo[2], transform, -3.1, 4.2, -2 * self.angle - 25.0, blue)

        return True

    def do_realize(self) -> None:
        msg = ctypes.create_string_buffer(512)

        Gtk.GLArea.do_realize(self)

        self.make_current()
        if self.get_error() is not None:
            return

        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)

        # The VAO
        vao = GLuint()
        glGenVertexArrays(1, ctypes.byref(vao))
        glBindVertexArray(vao)
        self.vao = vao.value

        # The vertex shader
        if self.get_api() == Gdk.GLAPI.GLES:
            p = vertex_shader_gles
        else:
            p = vertex_shader_gl
        v = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(v, 1, ctypes.byref(ctypes.c_char_p(p.encode())), None)
        glCompileShader(v)
        glGetShaderInfoLog(v, ctypes.sizeof(msg), None, msg)
        log.debug("vertex shader info: %s", msg.value.decode())

        # The fragment shader
        if self.get_api() == Gdk.GLAPI.GLES:
            p = fragment_shader_gles
        else:
            p = fragment_shader_gl
        f = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(f, 1, ctypes.byref(ctypes.c_char_p(p.encode())), None)
        glCompileShader(f)
        glGetShaderInfoLog(f, ctypes.sizeof(msg), None, msg)
        log.debug("fragment shader info: %s", msg.value.decode())

        # The shader program
        program = glCreateProgram()
        glAttachShader(program, v)
        glAttachShader(program, f)
        glBindAttribLocation(program, 0, b"position")
        glBindAttribLocation(program, 1, b"normal")

        glLinkProgram(program)
        glGetProgramInfoLog(program, ctypes.sizeof(msg), None, msg)
        log.debug("program info: %s", msg.value.decode())
        glDetachShader(program, v)
        glDetachShader(program, f)
        glDeleteShader(v)
        glDeleteShader(f)

        glUseProgram(program)
        self.program = program

        self.ModelViewProjectionMatrix_location = glGetUniformLocation(program, b"ModelViewProjectionMatrix")
        self.NormalMatrix_location = glGetUniformLocation(program, b"NormalMatrix")
        self.LightSourcePosition_location = glGetUniformLocation(program, b"LightSourcePosition")
        self.MaterialColor_location = glGetUniformLocation(program, b"MaterialColor")

        # The LightSourcePosition uniform is constant throughout the program, so it's set once.
        glUniform4fv(self.LightSourcePosition_location, 1, floats(self.LightSourcePosition))

        # The gears, each with its vertices in a vertex buffer object (VBO)
        self.gear1 = create_gear(1.0, 4.0, 1.0, 20, 0.7)
        self.gear2 = create_gear(0.5, 2.0, 2.0, 10, 0.7)
        self.gear3 = create_gear(1.3, 2.0, 0.5, 10, 0.7)

        for i, gear in enumerate((self.gear1, self.gear2, self.gear3)):
            vbo = GLuint()
            glGenBuffers(1, ctypes.byref(vbo))
            self.gear_vbo[i] = vbo.value
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            vertices = floats(gear.vertices)
            glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertices), vertices, GL_STATIC_DRAW)

    def do_unrealize(self) -> None:
        self.make_current()
        if self.get_error() is None:
            for vbo in self.gear_vbo:
                if vbo != 0:
                    glDeleteBuffers(1, ctypes.byref(GLuint(vbo)))

            if self.vao != 0:
                glDeleteVertexArrays(1, ctypes.byref(GLuint(self.vao)))

            if self.program != 0:
                glDeleteProgram(self.program)

        self.ModelViewProjectionMatrix_location = 0
        self.NormalMatrix_location = 0
        self.LightSourcePosition_location = 0
        self.MaterialColor_location = 0

        Gtk.GLArea.do_unrealize(self)

    def gtk_gears_tick(self, widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        frame = frame_clock.get_frame_counter()
        frame_time = frame_clock.get_frame_time()

        if self.first_frame_time == 0:
            # Nothing changes on the first frame.
            self.first_frame_time = frame_time
            if self.fps_label:
                self.fps_label.set_label("FPS: ---")
            return GLib.SOURCE_CONTINUE

        # glxgears advances 70 degrees per second, so do the same

        self.angle = math.fmod((frame_time - self.first_frame_time) / GLib.USEC_PER_SEC * 70.0, 360.0)

        widget.queue_draw()

        history_start = frame_clock.get_history_start()

        if self.fps_label and frame % 60 == 0:
            history_len = frame - history_start
            if history_len > 0:
                previous_timings = frame_clock.get_timings(frame - history_len)
                previous_frame_time = previous_timings.get_frame_time()

                s = "FPS: %-4.1f" % ((GLib.USEC_PER_SEC * history_len) / (frame_time - previous_frame_time))
                self.fps_label.set_label(s)

        return GLib.SOURCE_CONTINUE

    def set_axis(self, axis: int, value: float) -> None:
        if axis < 0 or axis >= GTK_GEARS_N_AXIS:
            return

        self.view_rot[axis] = value

        self.queue_draw()

    def get_axis(self, axis: int) -> float:
        if axis < 0 or axis >= GTK_GEARS_N_AXIS:
            return 0.0

        return self.view_rot[axis]

    def set_fps_label(self, label: Gtk.Label | None) -> None:
        self.fps_label = label


def gtk_gears_new() -> Gtk.Widget:
    return GtkGears(has_depth_buffer=True)
