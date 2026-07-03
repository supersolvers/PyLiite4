"""Perspective transforms between two sets of four points, used by demo2layout."""

from PyLiite4 import Graphene

from .singular_value_decomposition import singular_value_decomposition, singular_value_decomposition_solve


def unit_to(p1: Graphene.Point3D, p2: Graphene.Point3D, p3: Graphene.Point3D,
            p4: Graphene.Point3D) -> Graphene.Matrix:
    """Make a 4x4 matrix that maps
    e1        -> p1
    e2        -> p3
    e3        -> p3
    (1,1,1,0) -> p4
    """
    v = [0.0] * 16
    A = [0.0] * 16
    U = [0.0] * 16
    S = [0.0] * 4
    V = [0.0] * 16
    B = [0.0] * 4
    x = [0.0] * 4

    v1 = p1.to_vec3()
    v2 = p2.to_vec3()
    v3 = p3.to_vec3()
    v4 = p4.to_vec3()

    vv1 = Graphene.Vec4().init_from_vec3(v1, 1.)
    vv2 = Graphene.Vec4().init_from_vec3(v2, 1.)
    vv3 = Graphene.Vec4().init_from_vec3(v3, 1.)
    vv4 = Graphene.Vec4().init_from_vec3(v4, 1.)

    p = Graphene.Vec4().init(0., 0., 0., 1.)

    u = Graphene.Matrix().init_from_vec4(vv1, vv2, vv3, p)

    # solve x * u = vv4

    for i in range(4):
        for j in range(4):
            A[j * 4 + i] = u.get_value(i, j)

    B[0] = vv4.get_x()
    B[1] = vv4.get_y()
    B[2] = vv4.get_z()
    B[3] = vv4.get_w()

    singular_value_decomposition(A, 4, 4, U, S, V)
    singular_value_decomposition_solve(U, S, V, 4, 4, B, x)

    v[0] = x[0]
    v[5] = x[1]
    v[10] = x[2]
    v[15] = 1

    s = Graphene.Matrix().init_from_float(v)
    return s.multiply(u)


def perspective_3d(p1: Graphene.Point3D, p2: Graphene.Point3D, p3: Graphene.Point3D, p4: Graphene.Point3D,
                   q1: Graphene.Point3D, q2: Graphene.Point3D, q3: Graphene.Point3D,
                   q4: Graphene.Point3D) -> Graphene.Matrix:
    """Compute a 4x4 matrix m that maps
    p1 -> q1
    p2 -> q2
    p3 -> q3
    p4 -> q4

    This is not in general possible, because projective
    transforms preserve coplanarity. But in the cases we
    care about here, both sets of points are always coplanar.
    """
    a = unit_to(p1, p2, p3, p4)
    b = unit_to(q1, q2, q3, q4)

    _, a_inv = a.inverse()
    return a_inv.multiply(b)
