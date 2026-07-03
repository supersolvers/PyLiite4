"""Singular value decomposition, used by four_point_transform.

See Golub and Reinsch,
"Handbook for Automatic Computation vol II - Linear Algebra",
Springer, 1971

Matrices are flat lists of rows, and C's pointers into them are offsets.
"""

import math
import sys

MAX_ITERATION_COUNT = 30
DBL_EPSILON = sys.float_info.epsilon


def householder_reduction(A: list[float], nrows: int, ncols: int, U: list[float], V: list[float],
                          diagonal: list[float], superdiagonal: list[float]) -> None:
    """Perform Householder reduction to bidiagonal form

    Input: Matrix A of size nrows x ncols

    Output: Matrices and vectors such that
    A = U*Bidiag(diagonal, superdiagonal)*Vt

    All matrices are allocated by the caller

    Sizes:
     A, U: nrows x ncols
     diagonal, superdiagonal: ncols
     V: ncols x ncols
    """
    assert nrows >= 2
    assert ncols >= 2

    U[:nrows * ncols] = A[:nrows * ncols]

    diagonal[0] = 0.0
    s = 0.0
    scale = 0.0
    pui = 0
    ip1 = 1
    for i in range(ncols):
        superdiagonal[i] = scale * s

        scale = 0.0
        pu = pui
        for j in range(i, nrows):
            scale += abs(U[pu + i])
            pu += ncols

        if scale > 0.0:
            s2 = 0.0
            pu = pui
            for j in range(i, nrows):
                U[pu + i] /= scale
                s2 += U[pu + i] * U[pu + i]
                pu += ncols
            s = math.sqrt(s2) if U[pui + i] < 0.0 else -math.sqrt(s2)
            half_norm_squared = U[pui + i] * s - s2
            U[pui + i] -= s

            for j in range(ip1, ncols):
                si = 0.0
                pu = pui
                for k in range(i, nrows):
                    si += U[pu + i] * U[pu + j]
                    pu += ncols
                si /= half_norm_squared
                pu = pui
                for k in range(i, nrows):
                    U[pu + j] += si * U[pu + i]
                    pu += ncols
        pu = pui
        for j in range(i, nrows):
            U[pu + i] *= scale
            pu += ncols
        diagonal[i] = s * scale
        s = 0.0
        scale = 0.0
        if not (i >= nrows or i == ncols - 1):
            for j in range(ip1, ncols):
                scale += abs(U[pui + j])
            if scale > 0.0:
                s2 = 0.0
                for j in range(ip1, ncols):
                    U[pui + j] /= scale
                    s2 += U[pui + j] * U[pui + j]
                s = math.sqrt(s2) if U[pui + ip1] < 0.0 else -math.sqrt(s2)
                half_norm_squared = U[pui + ip1] * s - s2
                U[pui + ip1] -= s
                for k in range(ip1, ncols):
                    superdiagonal[k] = U[pui + k] / half_norm_squared
                if i < nrows - 1:
                    pu = pui + ncols
                    for j in range(ip1, nrows):
                        si = 0.0
                        for k in range(ip1, ncols):
                            si += U[pui + k] * U[pu + k]
                        for k in range(ip1, ncols):
                            U[pu + k] += si * superdiagonal[k]
                        pu += ncols
                for k in range(ip1, ncols):
                    U[pui + k] *= scale
        pui += ncols
        ip1 += 1

    pui = ncols * (ncols - 2)
    pvi = ncols * (ncols - 1)
    V[pvi + ncols - 1] = 1.0
    s = superdiagonal[ncols - 1]
    pvi -= ncols
    ip1 = ncols - 1
    for i in range(ncols - 2, -1, -1):
        if s != 0.0:
            pv = pvi + ncols
            for j in range(ip1, ncols):
                V[pv + i] = (U[pui + j] / U[pui + ip1]) / s
                pv += ncols
            for j in range(ip1, ncols):
                si = 0.0
                pv = pvi + ncols
                for k in range(ip1, ncols):
                    si += U[pui + k] * V[pv + j]
                    pv += ncols
                pv = pvi + ncols
                for k in range(ip1, ncols):
                    V[pv + j] += si * V[pv + i]
                    pv += ncols
        pv = pvi + ncols
        for j in range(ip1, ncols):
            V[pvi + j] = 0.0
            V[pv + i] = 0.0
            pv += ncols
        V[pvi + i] = 1.0
        s = superdiagonal[i]
        pui -= ncols
        pvi -= ncols
        ip1 -= 1

    pui = ncols * (ncols - 1)
    ip1 = ncols
    for i in range(ncols - 1, -1, -1):
        s = diagonal[i]
        for j in range(ip1, ncols):
            U[pui + j] = 0.0
        if s != 0.0:
            for j in range(ip1, ncols):
                si = 0.0
                pu = pui + ncols
                for k in range(ip1, nrows):
                    si += U[pu + i] * U[pu + j]
                    pu += ncols
                si = (si / U[pui + i]) / s
                pu = pui
                for k in range(i, nrows):
                    U[pu + j] += si * U[pu + i]
                    pu += ncols
            pu = pui
            for j in range(i, nrows):
                U[pu + i] /= s
                pu += ncols
        else:
            pu = pui
            for j in range(i, nrows):
                U[pu + i] = 0.0
                pu += ncols
        U[pui + i] += 1.0
        ip1 = i
        pui -= ncols


def givens_reduction(nrows: int, ncols: int, U: list[float], V: list[float], diagonal: list[float],
                     superdiagonal: list[float]) -> int:
    """Perform Givens reduction

    Input: Matrices such that
    A = U*Bidiag(diagonal,superdiagonal)*Vt

    Output: The same, with superdiagonal = 0

    All matrices are allocated by the caller

    Sizes:
     U: nrows x ncols
     diagonal, superdiagonal: ncols
     V: ncols x ncols
    """
    assert nrows >= 2
    assert ncols >= 2

    x = 0.0
    for i in range(ncols):
        y = abs(diagonal[i]) + abs(superdiagonal[i])
        if x < y:
            x = y
    epsilon = x * DBL_EPSILON
    for k in range(ncols - 1, -1, -1):
        iteration_count = 0
        while True:
            rotation_test = True
            m = k
            while m >= 0:
                if abs(superdiagonal[m]) <= epsilon:
                    rotation_test = False
                    break
                if abs(diagonal[m - 1]) <= epsilon:
                    break
                m -= 1
            if rotation_test:
                c = 0.0
                s = 1.0
                for i in range(m, k + 1):
                    f = s * superdiagonal[i]
                    superdiagonal[i] *= c
                    if abs(f) <= epsilon:
                        break
                    g = diagonal[i]
                    h = math.sqrt(f * f + g * g)
                    diagonal[i] = h
                    c = g / h
                    s = -f / h
                    pu = 0
                    for j in range(nrows):
                        y = U[pu + m - 1]
                        z = U[pu + i]
                        U[pu + m - 1] = y * c + z * s
                        U[pu + i] = -y * s + z * c
                        pu += ncols
            z = diagonal[k]
            if m == k:
                if z < 0.0:
                    diagonal[k] = -z
                    pv = 0
                    for j in range(ncols):
                        V[pv + k] = -V[pv + k]
                        pv += ncols
                break
            else:
                if iteration_count >= MAX_ITERATION_COUNT:
                    return -1
                iteration_count += 1
                x = diagonal[m]
                y = diagonal[k - 1]
                g = superdiagonal[k - 1]
                h = superdiagonal[k]
                f = ((y - z) * (y + z) + (g - h) * (g + h)) / (2.0 * h * y)
                g = math.sqrt(f * f + 1.0)
                if f < 0.0:
                    g = -g
                f = ((x - z) * (x + z) + h * (y / (f + g) - h)) / x
                c = 1.0
                s = 1.0
                for i in range(m + 1, k + 1):
                    g = superdiagonal[i]
                    y = diagonal[i]
                    h = s * g
                    g *= c
                    z = math.sqrt(f * f + h * h)
                    superdiagonal[i - 1] = z
                    c = f / z
                    s = h / z
                    f = x * c + g * s
                    g = -x * s + g * c
                    h = y * s
                    y *= c
                    pv = 0
                    for j in range(ncols):
                        x = V[pv + i - 1]
                        z = V[pv + i]
                        V[pv + i - 1] = x * c + z * s
                        V[pv + i] = -x * s + z * c
                        pv += ncols
                    z = math.sqrt(f * f + h * h)
                    diagonal[i - 1] = z
                    if z != 0.0:
                        c = f / z
                        s = h / z
                    f = c * g + s * y
                    x = -s * g + c * y
                    pu = 0
                    for j in range(nrows):
                        y = U[pu + i - 1]
                        z = U[pu + i]
                        U[pu + i - 1] = c * y + s * z
                        U[pu + i] = -s * y + c * z
                        pu += ncols
                superdiagonal[m] = 0.0
                superdiagonal[k] = f
                diagonal[k] = x
    return 0


def sort_singular_values(nrows: int, ncols: int, S: list[float], U: list[float], V: list[float]) -> None:
    """Given a singular value decomposition
    of an nrows x ncols matrix A = U*Diag(S)*Vt,
    sort the values of S by decreasing value,
    permuting V to match.
    """
    assert nrows >= 2
    assert ncols >= 2

    for i in range(ncols - 1):
        max_index = i
        for j in range(i + 1, ncols):
            if S[j] > S[max_index]:
                max_index = j
        if max_index == i:
            continue
        S[i], S[max_index] = S[max_index], S[i]
        p1 = max_index
        p2 = i
        for j in range(nrows):
            U[p1], U[p2] = U[p2], U[p1]
            p1 += ncols
            p2 += ncols
        p1 = max_index
        p2 = i
        for j in range(ncols):
            V[p1], V[p2] = V[p2], V[p1]
            p1 += ncols
            p2 += ncols


def singular_value_decomposition(A: list[float], nrows: int, ncols: int, U: list[float], S: list[float],
                                 V: list[float]) -> int:
    """Compute a singular value decomposition of A,
    A = U*Diag(S)*Vt

    All matrices are allocated by the caller

    Sizes:
     A, U: nrows x ncols
     S: ncols
     V: ncols x ncols
    """
    superdiagonal = [0.0] * ncols

    if nrows < ncols:
        return -1

    householder_reduction(A, nrows, ncols, U, V, S, superdiagonal)

    if givens_reduction(nrows, ncols, U, V, S, superdiagonal) < 0:
        return -1

    sort_singular_values(nrows, ncols, S, U, V)

    return 0


def singular_value_decomposition_solve(U: list[float], S: list[float], V: list[float], nrows: int, ncols: int,
                                       B: list[float], x: list[float]) -> None:
    """Given a singular value decomposition of A = U*Diag(S)*Vt,
    compute the best approximation x to A*x = B.

    All matrices are allocated by the caller

    Sizes:
     U: nrows x ncols
     S: ncols
     V: ncols x ncols
     B, x: ncols
    """
    assert nrows >= 2
    assert ncols >= 2

    tolerance = DBL_EPSILON * S[0] * ncols

    pv = 0
    for i in range(ncols):
        x[i] = 0.0
        for j in range(ncols):
            if S[j] > tolerance:
                d = 0.0
                pu = 0
                for k in range(nrows):
                    d += U[pu + j] * B[k]
                    pu += ncols
                x[i] += d * V[pv + j] / S[j]
        pv += ncols
