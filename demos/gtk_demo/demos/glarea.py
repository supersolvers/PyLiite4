"""OpenGL/OpenGL Area

GtkGLArea is a widget that allows custom drawing using OpenGL calls.
"""

import ctypes
import math

from PyLiite4 import Gdk, Gio, GLib, Gtk

# OpenGL, through the libepoxy that GTK uses: each epoxy_gl* symbol is a pointer to the function for the current
# context, as epoxy/gl.h's glFoo macros use it.
_epoxy = ctypes.CDLL("libepoxy.so.0")
GLuint = ctypes.c_uint
GLint = ctypes.c_int
GLenum = ctypes.c_uint


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

glGenVertexArrays = _gl("glGenVertexArrays", None, ctypes.c_int, ctypes.POINTER(GLuint))
glBindVertexArray = _gl("glBindVertexArray", None, GLuint)
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
glBindAttribLocation = _gl("glBindAttribLocation", None, GLuint, GLuint, ctypes.c_char_p)
glLinkProgram = _gl("glLinkProgram", None, GLuint)
glGetProgramiv = _gl("glGetProgramiv", None, GLuint, GLenum, ctypes.POINTER(GLint))
glGetProgramInfoLog = _gl("glGetProgramInfoLog", None, GLuint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p)
glDeleteProgram = _gl("glDeleteProgram", None, GLuint)
glGetUniformLocation = _gl("glGetUniformLocation", GLint, GLuint, ctypes.c_char_p)
glUseProgram = _gl("glUseProgram", None, GLuint)
glUniformMatrix4fv = _gl("glUniformMatrix4fv", None, GLint, ctypes.c_int, ctypes.c_ubyte,
                         ctypes.POINTER(ctypes.c_float))
glEnableVertexAttribArray = _gl("glEnableVertexAttribArray", None, GLuint)
glDisableVertexAttribArray = _gl("glDisableVertexAttribArray", None, GLuint)
glVertexAttribPointer = _gl("glVertexAttribPointer", None, GLuint, GLint, GLenum, ctypes.c_ubyte, ctypes.c_int,
                            ctypes.c_void_p)
glDrawArrays = _gl("glDrawArrays", None, GLenum, GLint, ctypes.c_int)
glClearColor = _gl("glClearColor", None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
glClear = _gl("glClear", None, ctypes.c_uint)
glFlush = _gl("glFlush", None)

demo_window: Gtk.Window | None = None

gl_area: Gtk.GLArea | None = None

X_AXIS, Y_AXIS, Z_AXIS, N_AXIS = range(4)

# The rotation angle on each axis.
rotation_angles = [0.0] * N_AXIS

# The triangle that is drawn: each vertex's coordinates, then its color.
vertex_data = (ctypes.c_float * 24)(
    # coord                  color
    0.0, 0.5, 0.0, 1.0,      1.0, 0.0, 0.0, 1.0,
    0.5, -0.366, 0.0, 1.0,   0.0, 1.0, 0.0, 1.0,
    -0.5, -0.366, 0.0, 1.0,  0.0, 0.0, 1.0, 1.0,
)


def init_buffers() -> tuple[int, int]:
    """Initialize the GL buffers"""
    vao = GLuint()
    buffer = GLuint()

    # Only one VAO is used, so it stays bound.
    glGenVertexArrays(1, ctypes.byref(vao))
    glBindVertexArray(vao)

    # The buffer that holds the vertices.
    glGenBuffers(1, ctypes.byref(buffer))
    glBindBuffer(GL_ARRAY_BUFFER, buffer)
    glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertex_data), vertex_data, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

    return vao.value, buffer.value


def create_shader(type: int, src: bytes) -> int:
    """Create and compile a shader"""
    shader = glCreateShader(type)
    glShaderSource(shader, 1, ctypes.byref(ctypes.c_char_p(src)), None)
    glCompileShader(shader)

    status = GLint()
    glGetShaderiv(shader, GL_COMPILE_STATUS, ctypes.byref(status))
    if status.value == GL_FALSE:
        log_len = GLint()
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(log_len))

        buffer = ctypes.create_string_buffer(log_len.value + 1)
        glGetShaderInfoLog(shader, log_len, None, buffer)

        GLib.log_default_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING, "Compile failure in %s shader:\n%s" % (
            "vertex" if type == GL_VERTEX_SHADER else "fragment", buffer.value.decode()))

        glDeleteShader(shader)

        return 0

    return shader


def init_shaders(vertex_path: str, fragment_path: str) -> tuple[int, int]:
    """Initialize the shaders and link them into a program"""
    program = 0
    mvp = 0
    status = GLint()

    source = Gio.resources_lookup_data(vertex_path, Gio.ResourceLookupFlags.NONE)
    vertex = create_shader(GL_VERTEX_SHADER, source.get_data())

    if vertex == 0:
        return 0, 0

    source = Gio.resources_lookup_data(fragment_path, Gio.ResourceLookupFlags.NONE)
    fragment = create_shader(GL_FRAGMENT_SHADER, source.get_data())

    if fragment == 0:
        glDeleteShader(vertex)
        return 0, 0

    program = glCreateProgram()
    glAttachShader(program, vertex)
    glAttachShader(program, fragment)

    glBindAttribLocation(program, 0, b"in_position")
    glBindAttribLocation(program, 1, b"in_color")

    glLinkProgram(program)

    glGetProgramiv(program, GL_LINK_STATUS, ctypes.byref(status))
    if status.value == GL_FALSE:
        log_len = GLint()
        glGetProgramiv(program, GL_INFO_LOG_LENGTH, ctypes.byref(log_len))

        buffer = ctypes.create_string_buffer(log_len.value + 1)
        glGetProgramInfoLog(program, log_len, None, buffer)

        GLib.log_default_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING,
                                 "Linking failure:\n%s" % buffer.value.decode())

        glDeleteProgram(program)
        program = 0
    else:
        mvp = glGetUniformLocation(program, b"mvp")

        glDetachShader(program, vertex)
        glDetachShader(program, fragment)

    glDeleteShader(vertex)
    glDeleteShader(fragment)

    return program, mvp


def compute_mvp(phi: float, theta: float, psi: float) -> list[float]:
    x = phi * (math.pi / 180)
    y = theta * (math.pi / 180)
    z = psi * (math.pi / 180)
    c1, s1 = math.cos(x), math.sin(x)
    c2, s2 = math.cos(y), math.sin(y)
    c3, s3 = math.cos(z), math.sin(z)
    c3c2 = c3 * c2
    s3c1 = s3 * c1
    c3s2s1 = c3 * s2 * s1
    s3s1 = s3 * s1
    c3s2c1 = c3 * s2 * c1
    s3c2 = s3 * c2
    c3c1 = c3 * c1
    s3s2s1 = s3 * s2 * s1
    c3s1 = c3 * s1
    s3s2c1 = s3 * s2 * c1
    c2s1 = c2 * s1
    c2c1 = c2 * c1

    res = [0.0] * 16

    # All three rotations are applied with these three matrices:
    #
    # ⎡  c3 s3 0 ⎤ ⎡ c2  0 -s2 ⎤ ⎡ 1   0  0 ⎤
    # ⎢ -s3 c3 0 ⎥ ⎢  0  1   0 ⎥ ⎢ 0  c1 s1 ⎥
    # ⎣   0  0 1 ⎦ ⎣ s2  0  c2 ⎦ ⎣ 0 -s1 c1 ⎦
    res[0] = c3c2;  res[4] = s3c1 + c3s2s1;  res[8] = s3s1 - c3s2c1; res[12] = 0.0  # noqa: E702
    res[1] = -s3c2; res[5] = c3c1 - s3s2s1;  res[9] = c3s1 + s3s2c1; res[13] = 0.0  # noqa: E702
    res[2] = s2;    res[6] = -c2s1;         res[10] = c2c1;          res[14] = 0.0  # noqa: E702
    res[3] = 0.0;   res[7] = 0.0;           res[11] = 0.0;           res[15] = 1.0  # noqa: E702

    return res


position_buffer = 0
program = 0
mvp_location = 0


def realize(widget: Gtk.GLArea) -> None:
    """We need to set up our state when we realize the GtkGLArea widget"""
    global position_buffer, program, mvp_location

    widget.make_current()

    if widget.get_error() is not None:
        return

    if widget.get_api() == Gdk.GLAPI.GLES:
        vertex_path = "/glarea/glarea-gles.vs.glsl"
        fragment_path = "/glarea/glarea-gles.fs.glsl"
    else:
        vertex_path = "/glarea/glarea-gl.vs.glsl"
        fragment_path = "/glarea/glarea-gl.fs.glsl"

    _, position_buffer = init_buffers()
    program, mvp_location = init_shaders(vertex_path, fragment_path)


def unrealize(widget: Gtk.GLArea) -> None:
    """We should tear down the state when unrealizing"""
    widget.make_current()

    if widget.get_error() is not None:
        return

    glDeleteBuffers(1, ctypes.byref(GLuint(position_buffer)))
    glDeleteProgram(program)


def draw_triangle() -> None:
    # The model view projection matrix comes from the rotation angles set with the GtkRange widgets.
    mvp = (ctypes.c_float * 16)(*compute_mvp(rotation_angles[X_AXIS],
                                             rotation_angles[Y_AXIS],
                                             rotation_angles[Z_AXIS]))

    glUseProgram(program)

    glUniformMatrix4fv(mvp_location, 1, GL_FALSE, mvp)

    # Each vertex is 32 bytes: four floats of coordinates, then four of color.
    glBindBuffer(GL_ARRAY_BUFFER, position_buffer)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 32, 0)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, 32, 16)

    glDrawArrays(GL_TRIANGLES, 0, 3)

    # Drawing is done, so the buffer and program are unbound.
    glDisableVertexAttribArray(0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glUseProgram(0)


def render(area: Gtk.GLArea, context: Gdk.GLContext) -> bool:
    if area.get_error() is not None:
        return False

    glClearColor(0.5, 0.5, 0.5, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)

    draw_triangle()

    glFlush()

    return True


def on_axis_value_change(adjustment: Gtk.Adjustment, axis: int) -> None:
    assert 0 <= axis < N_AXIS

    rotation_angles[axis] = adjustment.get_value()

    gl_area.queue_draw()


def create_axis_slider(axis: int) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

    if axis == X_AXIS:
        text = "X axis"
    elif axis == Y_AXIS:
        text = "Y axis"
    elif axis == Z_AXIS:
        text = "Z axis"
    else:
        raise AssertionError("not reached")

    label = Gtk.Label(label=text)
    box.append(label)

    adj = Gtk.Adjustment(value=0.0, lower=0.0, upper=360.0, step_increment=1.0, page_increment=12.0, page_size=0.0)
    adj.value_changed.connect(on_axis_value_change, axis)
    slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    box.append(slider)
    slider.set_hexpand(True)

    return box


def close_window(widget: Gtk.Widget) -> None:
    global demo_window, gl_area
    demo_window = None
    gl_area = None

    rotation_angles[X_AXIS] = 0.0
    rotation_angles[Y_AXIS] = 0.0
    rotation_angles[Z_AXIS] = 0.0


def close_request(window: Gtk.Window) -> bool:
    window.destroy()
    close_window(window)
    return True


def create_glarea_window(do_widget: Gtk.Widget) -> Gtk.Window:
    global gl_area

    window = Gtk.Window()
    window.set_display(do_widget.get_display())
    window.set_title("OpenGL Area")
    window.set_default_size(400, 600)
    # A Python reference keeps the window alive past gtk_window_destroy(), so "destroy" would come too late.
    window.close_request.connect(close_request)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_margin_start(12)
    box.set_margin_end(12)
    box.set_margin_top(12)
    box.set_margin_bottom(12)
    box.set_spacing(6)
    window.set_child(box)

    gl_area = Gtk.GLArea()
    gl_area.set_hexpand(True)
    gl_area.set_vexpand(True)
    gl_area.set_size_request(100, 200)
    box.append(gl_area)

    # GL resources are initialized and freed in the widget's realize and unrealize signals.
    gl_area.realize.connect(realize)
    gl_area.unrealize.connect(unrealize)

    # The "render" signal is GtkGLArea's main drawing call.
    gl_area.render.connect(render)

    controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.append(controls)
    controls.set_hexpand(True)

    for i in range(N_AXIS):
        controls.append(create_axis_slider(i))

    button = Gtk.Button.new_with_label("Quit")
    button.set_hexpand(True)
    box.append(button)
    button.clicked.connect(lambda button: close_request(window))

    return window


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global demo_window
    if demo_window is None:
        demo_window = create_glarea_window(do_widget)

    if not demo_window.get_visible():
        demo_window.set_visible(True)
    else:
        close_request(demo_window)

    return demo_window
