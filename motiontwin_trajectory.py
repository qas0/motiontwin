from dataclasses import dataclass, field

import numpy as np

from motiontwin import NeedlePlan, SlicePlane, Volume


TRAJECTORY_PLANES = ("longitudinal_1", "longitudinal_2", "cross_section")
MAX_TRAJECTORY_PIXELS = 384


def _number(value, label, lower, upper, *, integer=False):
    if (isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))
            or not np.isfinite(value) or not lower <= value <= upper
            or integer and int(value) != value):
        raise ValueError(f"{label} must be {'an integer' if integer else 'finite'} between {lower:g} and {upper:g}.")
    return int(value) if integer else float(value)


def _point(value, label):
    try:
        raw = np.asarray(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"{label} must contain three finite physical LPS coordinates.") from error
    if raw.dtype.kind not in "iuf" or raw.shape != (3,) or not np.isfinite(raw).all():
        raise ValueError(f"{label} must contain three finite physical LPS coordinates.")
    return raw.astype(float)


def _readonly(value, dtype=None):
    array = np.ascontiguousarray(value, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


def _source_matrix(value):
    if value is None:
        return np.eye(4)
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf" or raw.shape != (4, 4) or not np.isfinite(raw).all():
        raise ValueError("The inspection mapping must be a finite 4-by-4 physical affine matrix.")
    matrix = raw.astype(float)
    if not np.allclose(matrix[3], [0., 0., 0., 1.], rtol=0., atol=1e-12):
        raise ValueError("The inspection mapping must be affine, with final row 0, 0, 0, 1.")
    singular = np.linalg.svd(matrix[:3, :3], compute_uv=False)
    if singular[-1] < 1e-8 or singular[0] > 1e6 or singular[0] / singular[-1] > 1e8:
        raise ValueError("The inspection mapping must have a supported invertible physical transform.")
    return matrix


@dataclass(frozen=True)
class TrajectoryFrame:
    entry_lps_mm: tuple
    endpoint_lps_mm: tuple
    length_mm: float = field(init=False)
    _direction: tuple = field(init=False, repr=False)
    _u: tuple = field(init=False, repr=False)
    _v: tuple = field(init=False, repr=False)

    def __post_init__(self):
        entry = _point(self.entry_lps_mm, "Trajectory entry")
        endpoint = _point(self.endpoint_lps_mm, "Trajectory endpoint")
        length = float(np.linalg.norm(endpoint - entry))
        if not np.isfinite(length) or not 1e-6 < length <= 1000.:
            raise ValueError("The inspected trajectory must have distinct endpoints and be at most 1000 mm long.")
        direction = (endpoint - entry) / length
        # the least-aligned physical axis avoids an unstable cross product near any cardinal direction.
        u = np.cross(np.eye(3)[int(np.argmin(np.abs(direction)))], direction)
        u /= np.linalg.norm(u)
        v = np.cross(direction, u)
        for name, value in (("entry_lps_mm", entry), ("endpoint_lps_mm", endpoint),
                ("_direction", direction), ("_u", u), ("_v", v)):
            object.__setattr__(self, name, tuple(float(item) for item in value))
        object.__setattr__(self, "length_mm", length)

    @classmethod
    def from_plan(cls, plan):
        if not isinstance(plan, NeedlePlan):
            raise ValueError("Inspect a current frozen needle plan.")
        return cls(plan.entry_lps_mm, plan.endpoint_lps_mm)

    @property
    def direction(self):
        return _readonly(self._direction, float)

    @property
    def u(self):
        return _readonly(self._u, float)

    @property
    def v(self):
        return _readonly(self._v, float)

    def point_at(self, station_mm):
        station = _number(station_mm, "Inspection distance", 0., self.length_mm)
        return np.asarray(self.entry_lps_mm) + station * self.direction

    def station_of(self, world, *, clamp=True):
        if type(clamp) is not bool:
            raise ValueError("Trajectory projection clamping must be true or false.")
        station = float((_point(world, "Inspection point") - self.entry_lps_mm) @ self.direction)
        if not np.isfinite(station):
            raise ValueError("The inspection point has an unsupported physical projection.")
        return float(np.clip(station, 0., self.length_mm)) if clamp else station

    def grid(self, kind, station_mm=0., *, width_mm=80., margin_mm=12., spacing_mm=1., max_pixels=256):
        if not isinstance(kind, str) or kind not in TRAJECTORY_PLANES:
            raise ValueError("Choose a longitudinal trajectory plane or its cross-section.")
        station = _number(station_mm, "Inspection distance", 0., self.length_mm)
        width = _number(width_mm, "Inspection field width", 2., 300.)
        margin = _number(margin_mm, "Trajectory end margin", 0., 100.)
        requested_spacing = _number(spacing_mm, "Inspection sampling spacing", 1e-4, 1000.)
        limit = _number(max_pixels, "Inspection pixel bound", 2, MAX_TRAJECTORY_PIXELS, integer=True)
        entry, direction = np.asarray(self.entry_lps_mm), self.direction
        if kind == "cross_section":
            u, v = self.u, self.v
            centre = self.point_at(station)
            span_u, span_v = width, width
            origin = centre - width / 2. * (u + v)
        else:
            u, v = direction, self.u if kind == "longitudinal_1" else self.v
            span_u, span_v = self.length_mm + 2. * margin, width
            origin = entry - margin * direction - width / 2. * v
        spacing = max(requested_spacing, span_u / (limit - 1), span_v / (limit - 1))
        columns = min(limit, max(2, int(np.ceil(span_u / spacing)) + 1))
        rows = min(limit, max(2, int(np.ceil(span_v / spacing)) + 1))
        # centre any subpixel padding, using one physical step along both displayed axes.
        origin = origin - .5 * ((columns - 1) * spacing - span_u) * u
        origin = origin - .5 * ((rows - 1) * spacing - span_v) * v
        normal = np.cross(u, v)
        return SlicePlane(_readonly(np.zeros((rows, columns), dtype=np.float32)), _readonly(origin),
            _readonly(u), _readonly(v), (spacing, spacing), kind, _readonly(normal), float(origin @ normal))


@dataclass(frozen=True)
class TrajectorySlice:
    frame: TrajectoryFrame
    kind: str
    station_mm: float
    plane: SlicePlane
    coverage: np.ndarray = field(repr=False)
    source_matrix: np.ndarray = field(repr=False)
    _overlays: tuple = field(default=(), repr=False)

    def __post_init__(self):
        if (not isinstance(self.frame, TrajectoryFrame) or self.kind not in TRAJECTORY_PLANES
                or not isinstance(self.plane, SlicePlane)):
            raise ValueError("A trajectory slice requires its frame and a supported physical plane.")
        _number(self.station_mm, "Inspection distance", 0., self.frame.length_mm)
        if (self.coverage.dtype != bool or self.coverage.shape != self.plane.shape
                or self.plane.image.dtype.kind not in "iuf" or not np.isfinite(self.plane.image).all()
                or max(self.plane.shape) > MAX_TRAJECTORY_PIXELS):
            raise ValueError("A trajectory slice needs finite bounded pixels and matching source coverage.")
        object.__setattr__(self, "coverage", _readonly(self.coverage, bool))
        object.__setattr__(self, "source_matrix", _readonly(_source_matrix(self.source_matrix)))
        overlays = []
        names = set()
        for name, overlay in self._overlays:
            if (not isinstance(name, str) or not name or name in names
                    or overlay.dtype != bool or overlay.shape != self.plane.shape):
                raise ValueError("Trajectory overlays must have distinct names and match the sampled plane.")
            names.add(name)
            overlays.append((name, _readonly(overlay, bool)))
        object.__setattr__(self, "_overlays", tuple(overlays))

    @property
    def image(self):
        return self.plane.image

    @property
    def valid_mask(self):
        return self.coverage

    @property
    def overlays(self):
        return dict(self._overlays)


def sample_trajectory_slice(volume, frame, kind, station_mm=0., *, masks=None, world_to_reference=None,
                            width_mm=80., margin_mm=12., max_pixels=256):
    if not isinstance(volume, Volume) or not isinstance(frame, TrajectoryFrame):
        raise ValueError("Trajectory inspection requires its original CT volume and a finite trajectory frame.")
    matrix = _source_matrix(world_to_reference)
    if masks is not None and not isinstance(masks, dict):
        raise ValueError("Trajectory overlays must be named boolean masks on the original CT grid.")
    masks = {} if masks is None else masks
    if len(masks) > 128:
        raise ValueError("Inspect at most 128 named segmentation layers together.")
    for name, mask in masks.items():
        if (not isinstance(name, str) or not name or not isinstance(mask, np.ndarray)
                or mask.dtype != bool or mask.shape != volume.shape):
            raise ValueError("Every trajectory overlay must be a named boolean mask aligned with the source CT.")
    grid = frame.grid(kind, station_mm, width_mm=width_mm, margin_mm=margin_mm,
        spacing_mm=min(volume.spacing), max_pixels=max_pixels)
    world = grid.world_grid()
    source = world @ matrix[:3, :3].T + matrix[:3, 3]
    if not np.isfinite(source).all():
        raise ValueError("The inspection transform produced non-finite source coordinates.")
    indices = volume.world_to_index(source)
    nearest = np.rint(indices)
    indices = np.where(np.abs(indices - nearest) < 1e-7, nearest, indices)
    limits = np.asarray(volume.shape[::-1]) - 1
    coverage = np.all((indices >= 0.) & (indices <= limits), axis=-1)
    image = volume.sample_world(source, interpolation=1, cval=-1000.)
    overlays = []
    if masks:
        selected = np.floor(np.clip(indices, 0., limits) + .5).astype(np.int64)
        for name, mask in masks.items():
            overlay = mask[selected[..., 2], selected[..., 1], selected[..., 0]] & coverage
            overlays.append((name, overlay))
    plane = SlicePlane(_readonly(image), grid.origin, grid.u, grid.v, grid.spacing,
        grid.name, grid.normal, grid.position)
    return TrajectorySlice(frame, kind, float(station_mm), plane, coverage, matrix, tuple(overlays))
