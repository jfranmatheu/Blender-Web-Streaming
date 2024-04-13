from math import hypot, dist, cos, sin, acos, sqrt
from collections import defaultdict
from dataclasses import dataclass
import numpy as np

from mathutils import Vector, Matrix, geometry
from bpy.types import Object
import bmesh
from bmesh.types import BMesh, BMFace

from .math import dotproduct, length, cross


# Constant integers for directions
RIGHT = 1
LEFT = -1
ZERO = 0


@dataclass
class FakeRectTransform:
    pos: Vector
    dimensions: Vector
    rotation: float = 0.0 # degrees.
    origin: Vector | None = None

    @property
    def center(self):
        return Vector((
            self.pos[0] + self.dimensions[0] * 0.5,
            self.pos[1] + self.dimensions[1] * 0.5
        ))

    @property
    def coords(self):
        x, y = self.pos
        w, h, = self.dimensions
        coords = [
            Vector((x, y + h)), # top-left corner,
            Vector((x, y)), # bottom-left corner,
            Vector((x + w, y)), # bottom-right corner
            Vector((x + w, y + h)), # top-right corner
        ]
        if self.rotation != 0.0:
            angle = self.rotation
            o = self.center if self.origin is None else self.origin
            return [rotate_point(v, o, angle) for v in coords]
        return coords


@dataclass
class Box:
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @property
    def pos(self) -> Vector:
        return Vector((self.x_min, self.y_min))

    @property
    def min(self) -> Vector:
        return Vector((self.x_min, self.y_min))

    @property
    def max(self) -> Vector:
        return Vector((self.x_max, self.y_max))

    @property
    def width(self) -> int:
        return self.x_max - self.x_min

    @property
    def height(self) -> int:
        return self.y_max - self.y_min

    @property
    def size(self) -> Vector:
        return Vector((self.width, self.height))

    @property
    def dimensions(self) -> Vector:
        return self.size

    @property
    def center_t(self) -> tuple[int, int]:
        return int(self.width / 2), int(self.height / 2)

    @property
    def center(self) -> Vector:
        return Vector(self.center_t)

    @property
    def top_left(self) -> Vector:
        return Vector((self.x_min, self.y_max))

    @property
    def bottom_left(self) -> Vector:
        return Vector((self.x_min, self.y_min))

    @property
    def bottom_right(self) -> Vector:
        return Vector((self.x_max, self.y_min))

    @property
    def top_right(self) -> Vector:
        return Vector((self.x_max, self.y_max))

    @property
    def coords(self) -> list[Vector]:
        ''' 'U' shape Order: Top-Left, Bot-Left, Bot-Right, Top-Right. '''
        return [self.top_left, self.bottom_left, self.bottom_right, self.top_right]

    def expanded(self, left: int, right: int, bottom: int, top: int) -> 'Box':
        ''' Returns a new Box but expanded. '''
        return Box(
            self.x_min + left,
            self.y_min + right,
            self.x_max + bottom,
            self.y_max + top
        )

    def expanded_uniform(self, offset: int) -> 'Box':
        ''' Returns a new Box but expanded uniformly in all sides. '''
        return Box(
            self.x_min - offset,
            self.y_min - offset,
            self.x_max + offset,
            self.y_max + offset
        )

    def copy(self) -> 'Box':
        return Box(self.x_min, self.y_min, self.x_max, self.y_max)

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (
            self.x_min, self.y_min, self.x_max, self.y_max
        )


def distance_between(_p1, _p2):
    return dist(_p1, _p2)
    return hypot(_p1[0] - _p2[0], _p1[1] - _p2[1])


def directionOfPoint(A: Vector, B: Vector, P: Vector):
    global RIGHT, LEFT, ZERO

    # Subtracting co-ordinates of
    # point A from B and P, to
    # make A as origin
    B.x -= A.x
    B.y -= A.y
    P.x -= A.x
    P.y -= A.y

    # Determining cross Product
    cross_product = B.x * P.y - B.y * P.x

    # Return RIGHT if cross product is positive
    if (cross_product > 0):
        return RIGHT

    # Return LEFT if cross product is negative
    if (cross_product < 0):
        return LEFT

    # Return ZERO if cross product is zero
    return ZERO

def point_inside_circle(point, c, radius):
    return distance_between(point, c) < radius


def get_point_in_rect_space(p: Vector, rect, invert: bool = False) -> Vector:
    if rect.rotation != 0:
        _p = p.copy()
        # rotate around rectangle center by -rectAngle
        s = sin(rect.rotation) if invert else sin(-rect.rotation)
        c = cos(rect.rotation) if invert else cos(-rect.rotation)
        rect_center: Vector = Vector(rect.origin)
        # set origin to rect center
        _p -= rect_center
        # rotate
        _p = Vector((p.x * c - p.y * s, p.x * s + p.y * c))
        # put origin back
        _p += rect_center
    else:
        _p = p.copy()

    return _p


def calculate_scale_to_fit_box_in_box(box1: list[float | int], box2: list[float | int]):
    ''' Calculate the scale to apply to box2 given dimensions so that it fits into box1.
        Supports boxes from any dimension but they should match dimensions! '''
    # Ensure that both boxes are represented as lists of dimensions
    if len(box1) != len(box2):
        raise ValueError("Both boxes must have the same number of dimensions")

    # Calculate the scale for each dimension
    scales = [box1_dim / box2_dim for box1_dim, box2_dim in zip(box1, box2)]

    # The overall scale factor is the minimum of the individual scales
    scale_factor = min(scales)

    # Apply the scale factor to the dimensions of the second box
    scaled_box2 = [box2_dim * scale_factor for box2_dim in box2]

    return scaled_box2, scale_factor


def distance_to_line_segment(A: Vector, B: Vector, P: Vector) -> float:
    x, y = P
    x1, y1 = A
    x2, y2 = B

    # Calculate the direction vector of the segment
    dx = x2 - x1
    dy = y2 - y1

    # Calculate the length of the direction vector
    segment_length = sqrt(dx * dx + dy * dy)

    # Avoid division by zero
    if segment_length == 0:
        return sqrt((x - x1) ** 2 + (y - y1) ** 2)

    # Calculate the normalized direction vector
    dx /= segment_length
    dy /= segment_length

    # Calculate the vector from the start point to the point
    vx = x - x1
    vy = y - y1

    # Calculate the dot product of the vector and the direction vector
    dot_product = vx * dx + vy * dy

    if dot_product <= 0:
        # The point is before the segment
        return sqrt((x - x1) ** 2 + (y - y1) ** 2)

    if dot_product >= segment_length:
        # The point is after the segment
        return sqrt((x - x2) ** 2 + (y - y2) ** 2)

    # The point is on the segment
    distance = sqrt((x - (x1 + dx * dot_product)) ** 2 + (y - (y1 + dy * dot_product)) ** 2)
    return distance


def rect_overlap(rect_A, rect_B) -> bool:
    R1 = (rect_A.x_min, rect_A.y_min, rect_A.x_max, rect_A.y_max)
    R2 = (rect_B.x_min, rect_B.y_min, rect_B.x_max, rect_B.y_max)
    if ((R1[0]>=R2[2]) or (R1[2]<=R2[0]) or (R1[3]<=R2[1]) or (R1[1]>=R2[3])):
        return False
    return True


# A utility function to calculate area
# of triangle formed by (x1, y1),
# (x2, y2) and (x3, y3)
def triangle_area(x1, y1, x2, y2, x3, y3):
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1)
                + x3 * (y1 - y2)) / 2.0)

# A function to check whether point P(x, y)
# lies inside the triangle formed by
# A(x1, y1), B(x2, y2) and C(x3, y3)
def is_inside_triangle(x1, y1, x2, y2, x3, y3, x, y):
    # Calculate area of triangle ABC
    A = triangle_area(x1, y1, x2, y2, x3, y3)
    # Calculate area of triangle PBC
    A1 = triangle_area(x, y, x2, y2, x3, y3)
    # Calculate area of triangle PAC
    A2 = triangle_area(x1, y1, x, y, x3, y3)
    # Calculate area of triangle PAB
    A3 = triangle_area(x1, y1, x2, y2, x, y)
    # Check if sum of A1, A2 and A3
    # is same as A
    if (A == A1 + A2 + A3):
        return True
    else:
        return False

def is_point_inside_triangle(p, p1, p2, p3):
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = sign(p, p1, p2)
    d2 = sign(p, p2, p3)
    d3 = sign(p, p3, p1)

    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

    return not (has_neg and has_pos)


def point_inside_rect(_p, _pos, _size, _angle=0, origin: Vector | None = None):
    ''' NOTE: '_angle' should be given in radians.
        '_p', '_pos' and '_size' should be Vector type.
        '_pos' should be the lower left corner of the rectangle.
    '''
    if _angle != 0:
        p = _p.copy()
        # rotate around rectangle center by -rectAngle
        s = sin(-_angle)
        c = cos(-_angle)
        if origin is not None:
            rect_center: Vector = origin
        else:
            rect_center: Vector = _pos + _size * 0.5
        # set origin to rect center
        p -= rect_center
        # rotate
        p = Vector((p.x * c - p.y * s, p.x * s + p.y * c))
        # put origin back
        p += rect_center
    else:
        p = _p

    return ((_pos[0] + _size[0]) > p[0] > _pos[0]) and ((_pos[1] + _size[1]) > p[1] > _pos[1])


def check_point_in_convex_hull(convex_hull: list[Vector], point: Vector) -> bool:
    def _is_inside() -> bool:
        for idx in range(1, len(convex_hull)):
            if cross(convex_hull[idx - 1], convex_hull[idx], point) < 0:
                return False
        return True

    # visualize results
    # draw_results(convex_hull, point, _is_inside())
    return _is_inside()


def get_center(pos: Vector, size: Vector) -> Vector:
    return pos + size * 0.5


def rotate_point(p: Vector, o: Vector, angle: float) -> Vector:
    if angle == 0:
        return p
    qx = o.x + cos(angle) * (p.x - o.x) - sin(angle) * (p.y - o.y)
    qy = o.y + sin(angle) * (p.x - o.x) + cos(angle) * (p.y - o.y)
    return Vector((qx, qy))


def angle_between(v1: Vector, v2: Vector) -> float:
    return acos(dotproduct(v1, v2) / (length(v1) * length(v2)))


def distance_between(_p1, _p2) -> float:
    return hypot(_p1[0] - _p2[0], _p1[1] - _p2[1])
    #return math.sqrt((_p1[1] - _p1[0])**2 + (_p2[1] - _p2[0])**2)

def direction_from_to(_p1: Vector, _p2: Vector, _norm=True) -> Vector:
    if _norm:
        return (_p1 - _p2).normalized()
    else:
        return _p1 - _p2


def unit_vector(vector):
    """ Returns the unit vector of the vector"""
    return vector / np.linalg.norm(vector)

def angle_signed(vector1, vector2):
    """ Returns the angle in radians between given vectors"""
    v1_u = unit_vector(vector1)
    v2_u = unit_vector(vector2)
    minor = np.linalg.det(
        np.stack((v1_u[-2:], v2_u[-2:]))
    )
    if minor == 0:
        return 0
        raise NotImplementedError('Too odd vectors =(')
    return np.sign(minor) * np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


@dataclass
class Circle:
    origin: Vector
    radius: float

    def point_inside(self, point: Vector) -> bool:
        return point_inside_circle(self.origin, self.radius, point)


def object_to_face(face_ob: Object, ob_to_align: Object):
    bm: BMesh = BMesh.from_object(face_ob)
    face: BMFace = bm.faces[0]

    n = face.normal
    t = face.calc_tangent_edge().normalized()
    bt = n.cross(t).normalized()
    mat = face_ob.matrix_world @ Matrix([t, bt, n]).transposed().to_4x4()

    ob_to_align.matrix_world = mat @ ob_to_align.matrix_world
    bm.free()


class Edge:
    def __init__(self, verts: tuple[int, int]):
        self.verts: tuple[int, int] = verts
        self.faces: list[int] = []
        self.linked_edges: set[Edge] = set()

    @property
    def is_boundary(self) -> bool:
        return len(self.faces) == 1


def find_edges(tri_indices: list[tuple[int, int, int]]) -> list[Edge]:
    edge_dict: dict[tuple, Edge] = {}

    # Function to add an edge to the dictionary
    def add_edge(vert_indices: tuple[int, int], tri_idx: int):
        edge_key = tuple(sorted(vert_indices))
        if edge_key not in edge_dict:
            edge_dict[edge_key] = Edge(vert_indices)
        edge_dict[edge_key].faces.append(tri_idx)

    # Iterate through faces (triangles) to find and store edges
    for tri_idx, tri in enumerate(tri_indices):
        for i in range(3):
            add_edge((tri[i], tri[(i + 1) % 3]), tri_idx)

    # Convert the dictionary values to a list
    edges: list[Edge] = list(edge_dict.values())

    # Second pass to establish linked_edges
    for edge in edges:
        for other_edge in edges:
            if other_edge != edge and any(v in other_edge.verts for v in edge.verts):
                edge.linked_edges.add(other_edge)

    return edges


def find_boundary_vertices_sorted__convex(vertices: list[tuple[float, float]], indices: list[tuple[int, int, int]]):
    '''
        # Example: indices of triangles in CCW order
        indices = [(0, 1, 2), (2, 1, 3)]

        # Example: vertices as a list of 2D vectors
        vertices = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    '''
    vertex_count: dict[int, int] = defaultdict(int)

    # Count occurrences of each vertex
    for tri in indices:
        for vert_index in tri:
            vertex_count[vert_index] += 1

    # Collect the boundary vertices
    boundary_vertices = [vertices[vert_index] for vert_index, count in vertex_count.items() if count < 3] # 1-2 faces per vertex to be a boundary.

    # Find the centroid of the vertices
    centroid = np.mean(vertices, axis=0)

    # Sort the boundary vertices based on the angle with respect to the centroid (CW)
    boundary_vertices.sort(key=lambda v_co: np.arctan2(v_co[1] - centroid[1], v_co[0] - centroid[0]))

    return boundary_vertices


def find_boundary_vertices_sorted__nonconvex(indices: list[tuple[int, int, int]], vertices: list[tuple[float, float]] | None = None):
    '''
        If no vertices are given, it will return a list of indices.

        # Example: indices of triangles in CCW order
        indices = [(0, 1, 4), (0, 4, 2), (4, 1, 3)]

        # Example: vertices as a list of 2D vectors
        vertices = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.5, 0.5)]
    '''
    def walk_border(start_edge: Edge) -> list[Edge]:
        walked: set[Edge] = set()
        boundary_path: list[Edge] = []

        def recursive_walk(edge: Edge):
            if edge in walked:
                return
            walked.add(edge)

            # Add the current edge to the boundary_path
            boundary_path.append(edge)

            for linked_edge in edge.linked_edges:
                if linked_edge.is_boundary:
                    recursive_walk(linked_edge)
                    if edge == start_edge:
                        break

        recursive_walk(start_edge)

        return boundary_path

    edges = find_edges(indices)

    # Get boundary edges
    boundary_edges = [e for e in edges if e.is_boundary]

    if len(boundary_edges) == 0:
        return []

    # Set a starting edge for walking
    start_edge = boundary_edges[0]

    # Walk the border and get the boundary path
    walked_path = walk_border(start_edge)

    # Turn the edge path into a vertices path.
    unique_vertices = set()
    result_vertices = []
    as_indices = vertices is None

    for edge in walked_path:
        for vertex_index in edge.verts:
            if as_indices:
                if vertex_index not in unique_vertices:
                    result_vertices.append(vertex_index)
                    unique_vertices.add(vertex_index)
            else:
                vertex_coords = vertices[vertex_index]
                if vertex_coords not in unique_vertices:
                    result_vertices.append(vertex_coords)
                    unique_vertices.add(vertex_coords)

    # Fix BAD sign.
    last_edge = walked_path[-1]
    if result_vertices[0] not in last_edge.verts and result_vertices[1] in last_edge.verts:
        result_vertices[0], result_vertices[1] = result_vertices[1], result_vertices[0]

    return result_vertices


def calculate_matrix_world(position, rotation, size, scale):
    # Create translation matrix
    T = np.array([
        [1, 0, position[0]],
        [0, 1, position[1]],
        [0, 0, 1]
    ])

    # Create rotation matrix (assuming rotation is in radians)
    R = np.array([
        [np.cos(rotation), -np.sin(rotation), 0],
        [np.sin(rotation), np.cos(rotation), 0],
        [0, 0, 1]
    ])

    # Create scale matrix
    S = np.array([
        [size[0] * scale[0], 0, 0],
        [0, size[1] * scale[1], 0],
        [0, 0, 1]
    ])

    # Combine transformations
    return Matrix(T @ R @ S)

def calculate_matrix_local(rotation, size, scale):
    # Since local matrix does not consider position, we can use the same function
    # but with position set to (0, 0)
    return calculate_matrix_world((0, 0), rotation, size, scale)
