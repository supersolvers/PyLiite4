"""GtkShadertoy, a GtkGLArea that renders a Shadertoy-style image shader. Used by the Shadertoy demo."""

import ctypes

from PyLiite4 import Gdk, GLib, Gtk

# OpenGL, through the libepoxy that GTK uses: each epoxy_gl* symbol is a pointer to the function for the current
# context, as epoxy/gl.h's glFoo macros use it.
_epoxy = ctypes.CDLL("libepoxy.so.0")
GLuint = ctypes.c_uint
GLint = ctypes.c_int
GLenum = ctypes.c_uint
GLfloat = ctypes.c_float


def _gl(name: str, restype, *argtypes):
    pointer = ctypes.c_void_p.in_dll(_epoxy, f"epoxy_{name}")

    def call(*args):
        return ctypes.CFUNCTYPE(restype, *argtypes)(pointer.value)(*args)
    return call


GL_FALSE = 0
GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_ARRAY_BUFFER = 0x8892
GL_STATIC_DRAW = 0x88E4
GL_COLOR_BUFFER_BIT = 0x4000
GL_FRAGMENT_SHADER = 0x8B30
GL_VERTEX_SHADER = 0x8B31
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_INFO_LOG_LENGTH = 0x8B84

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
glGetShaderiv = _gl("glGetShaderiv", None, GLuint, GLenum, ctypes.POINTER(GLint))
glGetShaderInfoLog = _gl("glGetShaderInfoLog", None, GLuint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
glDeleteShader = _gl("glDeleteShader", None, GLuint)
glCreateProgram = _gl("glCreateProgram", GLuint)
glAttachShader = _gl("glAttachShader", None, GLuint, GLuint)
glDetachShader = _gl("glDetachShader", None, GLuint, GLuint)
glLinkProgram = _gl("glLinkProgram", None, GLuint)
glGetProgramiv = _gl("glGetProgramiv", None, GLuint, GLenum, ctypes.POINTER(GLint))
glGetProgramInfoLog = _gl("glGetProgramInfoLog", None, GLuint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
glDeleteProgram = _gl("glDeleteProgram", None, GLuint)
glGetUniformLocation = _gl("glGetUniformLocation", GLint, GLuint, ctypes.c_char_p)
glUseProgram = _gl("glUseProgram", None, GLuint)
glUniform1f = _gl("glUniform1f", None, GLint, GLfloat)
glUniform1i = _gl("glUniform1i", None, GLint, GLint)
glUniform3fv = _gl("glUniform3fv", None, GLint, ctypes.c_int, ctypes.POINTER(GLfloat))
glUniform4fv = _gl("glUniform4fv", None, GLint, ctypes.c_int, ctypes.POINTER(GLfloat))
glEnableVertexAttribArray = _gl("glEnableVertexAttribArray", None, GLuint)
glDisableVertexAttribArray = _gl("glDisableVertexAttribArray", None, GLuint)
glVertexAttribPointer = _gl("glVertexAttribPointer", None, GLuint, GLint, GLenum, ctypes.c_ubyte, ctypes.c_int,
                            ctypes.c_void_p)
glDrawArrays = _gl("glDrawArrays", None, GLenum, GLint, ctypes.c_int)
glClearColor = _gl("glClearColor", None, GLfloat, GLfloat, GLfloat, GLfloat)
glClear = _gl("glClear", None, ctypes.c_uint)
glFlush = _gl("glFlush", None)

default_image_shader = (
    "void mainImage(out vec4 fragColor, in vec2 fragCoord) {\n"
    "    // Normalized pixel coordinates (from 0 to 1)\n"
    "    vec2 uv = fragCoord/iResolution.xy;\n"
    "\n"
    "   // Time varying pixel color\n"
    "    vec3 col = 0.5 + 0.5*cos(iTime+uv.xyx+vec3(0,2,4));\n"
    "\n"
    "    if (distance(iMouse.xy, fragCoord.xy) <= 10.0) {\n"
    "        col = vec3(0.0);\n"
    "    }\n"
    "\n"
    "    // Output to screen\n"
    "    fragColor = vec4(col,1.0);\n"
    "}\n")

shadertoy_shader_prefix = {
    Gdk.GLAPI.GL:
        "#version 150 core\n"
        "\n",
    Gdk.GLAPI.GLES:
        "#version 300 es\n"
        "precision highp float;\n"
        "\n",
}

shadertoy_vertex_shader = (
    "uniform vec3 iResolution;\n"
    "\n"
    "in vec2 position;\n"
    "out vec2 fragCoord;\n"
    "\n"
    "void main() {\n"
    "    gl_Position = vec4(position, 0.0, 1.0);\n"
    "\n"
    "    // Convert from OpenGL coordinate system (with origin in center\n"
    "    // of screen) to Shadertoy/texture coordinate system (with origin\n"
    "    // in lower left corner)\n"
    "    fragCoord = (gl_Position.xy + vec2(1.0)) / vec2(2.0) * iResolution.xy;\n"
    "}\n")

fragment_prefix = (
    "uniform vec3      iResolution;           // viewport resolution (in pixels)\n"
    "uniform float     iTime;                 // shader playback time (in seconds)\n"
    "uniform float     iTimeDelta;            // render time (in seconds)\n"
    "uniform int       iFrame;                // shader playback frame\n"
    "uniform float     iChannelTime[4];       // channel playback time (in seconds)\n"
    "uniform vec3      iChannelResolution[4]; // channel resolution (in pixels)\n"
    "uniform vec4      iMouse;                // mouse pixel coords. xy: current (if MLB down), zw: click\n"
    "uniform sampler2D iChannel0;\n"
    "uniform sampler2D iChannel1;\n"
    "uniform sampler2D iChannel2;\n"
    "uniform sampler2D iChannel3;\n"
    "uniform vec4      iDate;                 // (year, month, day, time in seconds)\n"
    "uniform float     iSampleRate;           // sound sample rate (i.e., 44100)\n"
    "\n"
    "in vec2 fragCoord;\n"
    "out vec4 vFragColor;\n")

# Fragment shader suffix
fragment_suffix = (
    "    void main() {\n"
    "        vec4 c;\n"
    "        mainImage(c, fragCoord);\n"
    "         vFragColor = c;\n"
    "    }\n")


class GtkShadertoy(Gtk.GLArea):
    __gtype_name__ = "GtkShadertoy"

    def __init__(self, **properties) -> None:
        super().__init__(**properties)

        self.image_shader = default_image_shader
        self.image_shader_dirty = False

        self.error_set = False

        # Vertex buffers
        self.vao = 0
        self.buffer = 0

        # Active program
        self.program = 0

        # Location of uniforms for program
        self.resolution_location = -1
        self.time_location = -1
        self.timedelta_location = -1
        self.frame_location = -1
        self.mouse_location = -1

        # Current uniform values
        self.resolution = (GLfloat * 3)()
        self.time = 0.0
        self.timedelta = 0.0
        self.mouse = (GLfloat * 4)()
        self.frame = 0

        # Animation data
        self.first_frame_time = 0
        self.first_frame = 0
        # An unbound function, so the callback doesn't keep the widget alive.
        self.tick = self.add_tick_callback(GtkShadertoy.gtk_shadertoy_tick)

        drag = Gtk.GestureDrag()
        self.add_controller(drag)
        drag.drag_begin.connect(self.drag_begin_cb)
        drag.drag_update.connect(self.drag_update_cb)
        drag.drag_end.connect(self.drag_end_cb)

    def drag_begin_cb(self, drag: Gtk.GestureDrag, x: float, y: float) -> None:
        height = self.get_height()
        scale = self.get_scale_factor()

        self.mouse[0] = x * scale
        self.mouse[1] = (height - y) * scale
        self.mouse[2] = self.mouse[0]
        self.mouse[3] = self.mouse[1]

    def drag_update_cb(self, drag: Gtk.GestureDrag, dx: float, dy: float) -> None:
        width = self.get_width()
        height = self.get_height()
        scale = self.get_scale_factor()

        _, x, y = drag.get_start_point()
        x += dx
        y += dy

        if 0 <= x < width and 0 <= y < height:
            self.mouse[0] = x * scale
            self.mouse[1] = (height - y) * scale

    def drag_end_cb(self, drag: Gtk.GestureDrag, dx: float, dy: float) -> None:
        self.mouse[2] = -self.mouse[2]
        self.mouse[3] = -self.mouse[3]

    # Called for a new window size or exposure.
    def do_resize(self, width: int, height: int) -> None:
        self.resolution[0] = width
        self.resolution[1] = height
        self.resolution[2] = 1.0  # The pixel aspect ratio, which Shadertoy keeps in iResolution.z.

        glViewport(0, 0, width, height)

    def init_shaders(self, vertex_source: str, fragment_source: str) -> None:
        """Compile and link the program; raises GLib.Error on failure."""
        vertex = create_shader(GL_VERTEX_SHADER, vertex_source)

        try:
            fragment = create_shader(GL_FRAGMENT_SHADER, fragment_source)
        except GLib.Error:
            glDeleteShader(vertex)
            raise

        program = glCreateProgram()
        glAttachShader(program, vertex)
        glAttachShader(program, fragment)

        glLinkProgram(program)

        status = GLint()
        glGetProgramiv(program, GL_LINK_STATUS, ctypes.byref(status))
        try:
            if status.value == GL_FALSE:
                log_len = GLint()
                glGetProgramiv(program, GL_INFO_LOG_LENGTH, ctypes.byref(log_len))

                buffer = ctypes.create_string_buffer(log_len.value + 1)
                glGetProgramInfoLog(program, log_len, None, buffer)

                glDeleteProgram(program)

                raise GLib.Error.new_literal(Gdk.GLError.quark(), f"Linking failure:\n{buffer.value.decode()}",
                                             Gdk.GLError.LINK_FAILED)

            if self.program != 0:
                glDeleteProgram(self.program)

            self.program = program
            self.resolution_location = glGetUniformLocation(program, b"iResolution")
            self.time_location = glGetUniformLocation(program, b"iTime")
            self.timedelta_location = glGetUniformLocation(program, b"iTimeDelta")
            self.frame_location = glGetUniformLocation(program, b"iFrame")
            self.mouse_location = glGetUniformLocation(program, b"iMouse")

            glDetachShader(program, vertex)
            glDetachShader(program, fragment)
        finally:
            # The program owns these now, so they can be deleted.
            glDeleteShader(vertex)
            glDeleteShader(fragment)

    def realize_shader(self) -> None:
        api = self.get_api()
        prefix = shadertoy_shader_prefix[api]

        vertex_shader = prefix + shadertoy_vertex_shader
        fragment_shader = prefix + fragment_prefix + self.image_shader + fragment_suffix
        try:
            self.init_shaders(vertex_shader, fragment_shader)
        except GLib.Error as error:
            self.error_set = True
            self.set_error(error)

        # A new shader starts at time zero.
        self.first_frame_time = 0
        self.first_frame = 0

        self.image_shader_dirty = False

    def do_render(self, context: Gdk.GLContext) -> bool:
        if self.get_error() is not None:
            return False

        if self.image_shader_dirty:
            self.realize_shader()

        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.program)

        if self.resolution_location != -1:
            glUniform3fv(self.resolution_location, 1, self.resolution)
        if self.time_location != -1:
            glUniform1f(self.time_location, self.time)
        if self.timedelta_location != -1:
            glUniform1f(self.timedelta_location, self.timedelta)
        if self.frame_location != -1:
            glUniform1i(self.frame_location, self.frame)
        if self.mouse_location != -1:
            glUniform4fv(self.mouse_location, 1, self.mouse)

        glBindBuffer(GL_ARRAY_BUFFER, self.buffer)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)

        glDrawArrays(GL_TRIANGLES, 0, 6)

        # Drawing is done, so the buffer and program are unbound.
        glDisableVertexAttribArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glUseProgram(0)

        glFlush()

        return True

    def get_image_shader(self) -> str:
        return self.image_shader

    def set_image_shader(self, shader: str) -> None:
        self.image_shader = shader

        # Only an error that this widget set is cleared, not one set by someone else.
        if self.error_set:
            self.set_error(None)
            self.error_set = False
        self.image_shader_dirty = True

    def do_realize(self) -> None:
        # Two triangles that cover the whole screen.
        vertex_data = (GLfloat * 24)(
            -1.0, -1.0, 0.0, 1.0,
            -1.0, 1.0, 0.0, 1.0,
            1.0, 1.0, 0.0, 1.0,

            -1.0, -1.0, 0.0, 1.0,
            1.0, 1.0, 0.0, 1.0,
            1.0, -1.0, 0.0, 1.0,
        )

        Gtk.GLArea.do_realize(self)

        self.make_current()
        if self.get_error() is not None:
            return

        vao = GLuint()
        glGenVertexArrays(1, ctypes.byref(vao))
        glBindVertexArray(vao)
        self.vao = vao.value

        buffer = GLuint()
        glGenBuffers(1, ctypes.byref(buffer))
        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertex_data), vertex_data, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.buffer = buffer.value

        self.realize_shader()

    def do_unrealize(self) -> None:
        self.make_current()
        if self.get_error() is None:
            if self.buffer != 0:
                glDeleteBuffers(1, ctypes.byref(GLuint(self.buffer)))

            if self.vao != 0:
                glDeleteVertexArrays(1, ctypes.byref(GLuint(self.vao)))

            if self.program != 0:
                glDeleteProgram(self.program)

        Gtk.GLArea.do_unrealize(self)

    def gtk_shadertoy_tick(self, frame_clock: Gdk.FrameClock) -> bool:
        frame = frame_clock.get_frame_counter()
        frame_time = frame_clock.get_frame_time()

        if self.first_frame_time == 0:
            self.first_frame_time = frame_time
            self.first_frame = frame
            previous_time = 0.0
        else:
            previous_time = self.time

        self.time = (frame_time - self.first_frame_time) / 1000000.0
        self.frame = frame - self.first_frame
        self.timedelta = self.time - previous_time

        self.queue_draw()

        return GLib.SOURCE_CONTINUE


def create_shader(type: int, src: str) -> int:
    shader = glCreateShader(type)
    glShaderSource(shader, 1, ctypes.byref(ctypes.c_char_p(src.encode())), None)
    glCompileShader(shader)

    status = GLint()
    glGetShaderiv(shader, GL_COMPILE_STATUS, ctypes.byref(status))
    if status.value == GL_FALSE:
        log_len = GLint()
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(log_len))

        buffer = ctypes.create_string_buffer(log_len.value + 1)
        glGetShaderInfoLog(shader, log_len, None, buffer)

        glDeleteShader(shader)

        raise GLib.Error.new_literal(Gdk.GLError.quark(), "Compile failure in %s shader:\n%s" % (
            "vertex" if type == GL_VERTEX_SHADER else "fragment", buffer.value.decode()),
            Gdk.GLError.COMPILATION_FAILED)

    return shader


def gtk_shadertoy_new() -> GtkShadertoy:
    return GtkShadertoy(allowed_apis=Gdk.GLAPI.GL | Gdk.GLAPI.GLES)
