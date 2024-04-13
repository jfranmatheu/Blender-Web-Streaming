from math import hypot, acos, sqrt, cos, pi, sin
from typing import Tuple
from mathutils import Vector


def rotate_vector(vector: list[float, float], angle: float) -> list[float, float]:
    x = vector[0] * cos(angle) - vector[1] * sin(angle)
    y = vector[0] * sin(angle) + vector[1] * cos(angle)
    return [x, y]

def cross(point_o: Vector, point_a: Vector, point_b: Vector) -> int:
    """ 2D cross product of OA and OB vectors,
    i.e. z-component of their 3D cross product
    :param point_o: point O
    :param point_a: point A
    :param point_b: point B
    :return cross product of vectors OA and OB (OA x OB),
    positive if OAB makes a counter-clockwise turn,
    negative for clockwise turn, and zero if the points are collinear
    """
    return (point_a[0] - point_o[0]) * (point_b[1] - point_o[1]) - (
            point_a[1] - point_o[1]) * (point_b[0] - point_o[0])

def clamp(value: float or int, min_value: float or int = 0.0, max_value: float or int = 1.0) -> float or int:
    return min(max(value, min_value), max_value)

def smoothstep(edge0, edge1, x):
    # Scale, bias and saturate x to 0..1 range
    x = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    # Evaluate polynomial
    return x * x * (3 - 2 * x)

def linear_interpol(x1: float, x2: float, y1: float, y2: float, x: float) -> float:
    """Perform linear interpolation for x between (x1,y1) and (x2,y2) """
    return ((y2 - y1) * x + x2 * y1 - x1 * y2) / (x2 - x1)

def lerp_point(t, times, points):
    dx = points[1][0] - points[0][0]
    dy = points[1][1] - points[0][1]
    dt = (t-times[0]) / (times[1]-times[0])
    return dt*dx + points[0][0], dt*dy + points[0][1]

# Precise method, which guarantees v = v1 when t = 1.
def lerp(v0: float, v1: float, t: float) -> float:
    return (1 - t) * v0 + t * v1

def ease_quadratic_out(t, start, change, duration):
    t /= duration
    return -change * t*(t-2) + start

def ease_sine_in(t, b, c, d=1.0):
    return -c * cos(t/d * (pi/2)) + c + b

def map_value(val: float, src: Tuple[float, float], dst: Tuple[float, float] = (0.0, 1.0)):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

def mix(x, y, a):
    return x*(1-a)+y*a

def dotproduct(v1, v2):
    return sum((a*b) for a, b in zip(v1, v2))

def length(v):
    return sqrt(dotproduct(v, v))
