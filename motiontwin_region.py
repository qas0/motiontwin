from dataclasses import dataclass, field
from hashlib import sha256
from itertools import product

import numpy as np
from scipy.spatial import cKDTree


def _points(values):
    raw = np.asarray(values)
    if raw.ndim < 1 or raw.shape[-1] != 3 or raw.dtype.kind not in "iuf" or not np.isfinite(raw).all():
        raise ValueError("Region queries require finite physical xyz points.")
    return raw.astype(float)


def _immutable(values, dtype):
    array = np.asarray(values, dtype=dtype, order="C")
    return np.frombuffer(array.tobytes(), dtype=dtype).reshape(array.shape)


def _snap_faces(indices, tolerance):
    shifted = indices + .5
    return np.where(np.abs(shifted - np.rint(shifted)) <= tolerance, np.rint(shifted) - .5, indices)


@dataclass(frozen=True, eq=False)
class VoxelRegion:
    mask: np.ndarray = field(repr=False)
    spacing: tuple
    origin: tuple
    direction: np.ndarray = field(repr=False)
    _affine: np.ndarray = field(init=False, repr=False)
    _inverse: np.ndarray = field(init=False, repr=False)
    _tree: object = field(init=False, repr=False)
    _blocks: np.ndarray = field(init=False, repr=False)
    _block_size: int = field(init=False, repr=False)
    centroid_lps_mm: tuple = field(init=False)
    aim_point_lps_mm: tuple = field(init=False)
    volume_mm3: float = field(init=False)
    fingerprint: str = field(init=False, repr=False)

    def __post_init__(self):
        mask = np.asarray(self.mask)
        spacing, origin, direction = np.asarray(self.spacing), np.asarray(self.origin), np.asarray(self.direction)
        if (mask.dtype != bool or mask.ndim != 3 or min(mask.shape, default=0) < 1
                or mask.size > 512 * 1024 ** 2 or spacing.shape != (3,) or origin.shape != (3,)
                or direction.shape != (3, 3) or any(a.dtype.kind not in "iuf" for a in (spacing, origin, direction))
                or not all(np.isfinite(a).all() for a in (spacing, origin, direction)) or np.any(spacing <= 0)
                or not np.allclose(direction.T @ direction, np.eye(3), rtol=0, atol=1e-8)):
            raise ValueError("A voxel region requires a boolean 3D mask and finite orthogonal CT geometry.")
        spacing, origin, direction = spacing.astype(float), origin.astype(float), direction.astype(float)
        lower, upper, total, count = np.array(mask.shape[::-1]), np.zeros(3, int), np.zeros(3), 0
        for z, section in enumerate(mask):
            y, x = np.nonzero(section)
            if len(x):
                lower = np.minimum(lower, (x.min(), y.min(), z))
                upper = np.maximum(upper, (x.max(), y.max(), z))
                total += (x.sum(dtype=float), y.sum(dtype=float), z * len(x))
                count += len(x)
        if not count:
            raise ValueError("A planning region must contain at least one foreground voxel.")
        centroid_index = total / count - lower
        cropped = mask[tuple(slice(int(a), int(b) + 1) for a, b in zip(lower[::-1], upper[::-1]))]
        origin = origin + direction @ (lower * spacing)
        mask = _immutable(cropped, np.bool_)
        affine = np.eye(4)
        affine[:3, :3], affine[:3, 3] = direction @ np.diag(spacing), origin
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "spacing", tuple(spacing))
        object.__setattr__(self, "origin", tuple(origin))
        object.__setattr__(self, "direction", _immutable(direction, np.float64))
        object.__setattr__(self, "_affine", _immutable(affine, np.float64))
        object.__setattr__(self, "_inverse", _immutable(np.linalg.inv(affine), np.float64))
        object.__setattr__(self, "centroid_lps_mm", tuple(self.index_to_world(centroid_index)))
        object.__setattr__(self, "volume_mm3", float(count * abs(np.linalg.det(affine[:3, :3]))))
        digest = sha256(np.asarray((*mask.shape, *spacing, *origin, *direction.ravel()), dtype="<f8").tobytes())
        digest.update(memoryview(mask).cast("B"))
        object.__setattr__(self, "fingerprint", digest.hexdigest())
        # scan source slices so selecting a real interior voxel does not allocate a 3D coordinate grid.
        best, aim = np.inf, None
        for z, section in enumerate(mask):
            y, x = np.nonzero(section)
            if len(x):
                squared = ((x - centroid_index[0]) * spacing[0]) ** 2 + ((y - centroid_index[1]) * spacing[1]) ** 2
                squared += ((z - centroid_index[2]) * spacing[2]) ** 2
                index = int(np.argmin(squared))
                if squared[index] < best:
                    best, aim = squared[index], (x[index], y[index], z)
        object.__setattr__(self, "aim_point_lps_mm", tuple(self.index_to_world(aim)))
        self._build_tree(count)

    @classmethod
    def from_mask(cls, mask, spacing, origin, direction):
        return cls(mask, spacing, origin, direction)

    def __eq__(self, other):
        return isinstance(other, VoxelRegion) and self.fingerprint == other.fingerprint

    def __hash__(self):
        return hash(self.fingerprint)

    @property
    def shape(self):
        return self.mask.shape

    @property
    def affine(self):
        return self._affine

    def index_to_world(self, indices):
        indices = _points(indices)
        return indices @ self._affine[:3, :3].T + self._affine[:3, 3]

    def world_to_index(self, points):
        points = _points(points)
        return (points - np.asarray(self.origin)) @ self._inverse[:3, :3].T

    def _index_tolerance(self, points, indices):
        # subtracting a CT origin can lose more precision than the small resulting voxel coordinate suggests.
        scale = (np.abs(points) + np.abs(self.origin)) @ np.abs(self._inverse[:3, :3].T)
        return 64 * np.finfo(float).eps * np.maximum(1., np.maximum(np.abs(indices), scale))

    def contains(self, points):
        indices = self.world_to_index(points)
        nearest = np.floor(_snap_faces(indices, self._index_tolerance(points, indices)) + .5)
        inside = np.all((nearest >= 0) & (nearest < np.asarray(self.shape[::-1])), axis=-1)
        selected = np.zeros(inside.shape, bool)
        if np.any(inside):
            xyz = nearest[inside].astype(np.intp)
            selected[inside] = self.mask[xyz[..., 2], xyz[..., 1], xyz[..., 0]]
        return selected

    def _closed_contains(self, indices, tolerance):
        indices = np.asarray(indices, dtype=float)
        floor = np.floor(indices + .5)
        on_face = np.abs(indices + .5 - np.rint(indices + .5)) <= tolerance
        floor = np.where(on_face, np.rint(indices + .5), floor)
        result = np.zeros(indices.shape[:-1], bool)
        choices = [(0, 1) if np.any(on_face[..., axis]) else (0,) for axis in range(3)]
        for offset in product(*choices):
            candidate = floor - on_face * np.asarray(offset)
            valid = np.all((candidate >= 0) & (candidate < np.asarray(self.shape[::-1])), axis=-1)
            if np.any(valid):
                xyz = candidate[valid].astype(np.intp)
                result[valid] |= self.mask[xyz[..., 2], xyz[..., 1], xyz[..., 0]]
        return result

    def segment_intervals(self, start, end):
        a, b = self.world_to_index(start), self.world_to_index(end)
        if a.shape != (3,) or b.shape != (3,):
            raise ValueError("Region intersection intervals require one finite segment.")
        # physical oblique transforms can perturb an exactly face-aligned endpoint by a few ulps.
        tolerance = np.maximum(self._index_tolerance(start, a), self._index_tolerance(end, b))
        start, end = _snap_faces(a, tolerance), _snap_faces(b, tolerance)
        delta = end - start
        if not np.isfinite(delta).all():
            raise ValueError("The segment cannot be represented in source coordinates.")
        if not np.any(delta):
            return ((0., 1.),) if bool(self._closed_contains(start, tolerance)) else ()
        lower, upper = 0., 1.
        for axis, size in enumerate(self.shape[::-1]):
            if delta[axis] == 0:
                if start[axis] < -.5 - tolerance[axis] or start[axis] > size - .5 + tolerance[axis]:
                    return ()
            else:
                bounds = sorted(((-.5 - start[axis]) / delta[axis], (size - .5 - start[axis]) / delta[axis]))
                lower, upper = max(lower, bounds[0]), min(upper, bounds[1])
        if lower > upper:
            contact = float(np.clip((lower + upper) / 2, 0., 1.))
            return ((contact, contact),) if bool(self._closed_contains(start + contact * delta, tolerance)) else ()
        lower, upper = float(np.clip(lower, 0., 1.)), float(np.clip(upper, 0., 1.))
        knots = [np.array((lower, upper))]
        # crossings of source cell faces divide the path into intervals with constant voxel ownership.
        for axis, size in enumerate(self.shape[::-1]):
            if delta[axis] != 0:
                crossings = (np.arange(size + 1, dtype=float) - .5 - start[axis]) / delta[axis]
                knots.append(crossings[(crossings > lower) & (crossings < upper)])
        knots = np.unique(np.concatenate(knots))
        intervals = []
        if len(knots) > 1:
            inside = self._closed_contains(start + ((knots[:-1] + knots[1:]) / 2)[:, None] * delta, tolerance)
            intervals.extend(zip(knots[:-1][inside], knots[1:][inside]))
        contact = self._closed_contains(start + knots[:, None] * delta, tolerance)
        intervals.extend((value, value) for value in knots[contact])
        merged = []
        for a, b in sorted(intervals):
            if merged and a <= merged[-1][1] + 64 * np.finfo(float).eps:
                merged[-1] = (merged[-1][0], max(merged[-1][1], float(b)))
            else:
                merged.append((float(a), float(b)))
        return tuple(merged)

    def segment_contact(self, start, end):
        start, end = np.broadcast_arrays(_points(start), _points(end))
        if start.ndim == 1:
            return bool(self.segment_intervals(start, end))
        return np.array([bool(self.segment_intervals(a, b)) for a, b in zip(start.reshape(-1, 3), end.reshape(-1, 3))]).reshape(start.shape[:-1])

    segment_intersects = segment_contact

    def _build_tree(self, count):
        block = 1
        if count > 262144:
            block = max(2, int(np.ceil((self.mask.size / 262144) ** (1 / 3))))
            while np.prod((np.asarray(self.shape) + block - 1) // block) > 262144:
                block += 1
        groups = []
        for z in range(0, self.shape[0], block):
            section = self.mask[z] if block == 1 else self.mask[z:z + block].any(axis=0)
            if block > 1:
                section = np.logical_or.reduceat(section, np.arange(0, self.shape[1], block), axis=0)
                section = np.logical_or.reduceat(section, np.arange(0, self.shape[2], block), axis=1)
            y, x = np.nonzero(section)
            if len(x):
                groups.append(np.column_stack((x * block, y * block, np.full_like(x, z))))
        blocks = np.concatenate(groups).astype(np.int32)
        centers = (blocks + (block - 1) / 2) * np.asarray(self.spacing)
        object.__setattr__(self, "_blocks", _immutable(blocks, np.int32))
        object.__setattr__(self, "_block_size", block)
        object.__setattr__(self, "_tree", cKDTree(centers, copy_data=True))

    def _block_distance(self, point, candidates):
        block, spacing = self._block_size, np.asarray(self.spacing)
        origins = self._blocks[np.asarray(candidates, dtype=np.intp)]
        if block == 1:
            distances = np.maximum(np.abs(point - origins * spacing) - spacing / 2, 0.)
            return float(np.linalg.norm(distances, axis=-1).min())
        best = np.inf
        for x, y, z in origins:
            patch = self.mask[z:z + block, y:y + block, x:x + block]
            if patch.all():
                lower = (np.array((x, y, z)) - .5) * spacing
                upper = (np.array((x, y, z)) + np.asarray(patch.shape[::-1]) - .5) * spacing
                best = min(best, float(np.linalg.norm(np.maximum(np.maximum(lower - point, point - upper), 0.))))
            else:
                for offset, section in enumerate(patch):
                    yy, xx = np.nonzero(section)
                    if len(xx):
                        centers = np.column_stack((xx + x, yy + y, np.full_like(xx, z + offset))) * spacing
                        best = min(best, float(np.linalg.norm(np.maximum(np.abs(point - centers) - spacing / 2, 0.), axis=-1).min()))
        return best

    def distance_mm(self, points):
        points = _points(points)
        local = (points.reshape(-1, 3) - np.asarray(self.origin)) @ self.direction
        result = np.zeros(len(local))
        inside = self.contains(points).reshape(-1)
        half_diagonal = float(np.linalg.norm(np.asarray(self.spacing) * self._block_size / 2))
        for index in np.flatnonzero(~inside):
            point = local[index]
            _, nearest = self._tree.query(point)
            best = self._block_distance(point, [nearest])
            candidates = self._tree.query_ball_point(point, np.nextafter(best + half_diagonal, np.inf))
            result[index] = min(best, self._block_distance(point, candidates)) if candidates else best
        return result.reshape(points.shape[:-1])

    distance = distance_mm
