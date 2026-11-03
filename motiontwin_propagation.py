from dataclasses import asdict, dataclass, field
from hashlib import sha256
from itertools import product
import json
from types import MappingProxyType

import numpy as np
from scipy.ndimage import map_coordinates

from motiontwin import Volume
from motiontwin_registration import RegistrationResult
from motiontwin_region import _snap_faces


MAX_MASK_VOXELS = 128 * 1024 ** 2
MAX_CANDIDATE_VOXELS = 8_000_000
INVERSE_TOLERANCE_MM = 1e-4
CONTRACTION_LIMIT = .95
SAMPLING_TIE_TOLERANCE_VOX = 1e-7


def _mask(mask):
    mask = np.asarray(mask)
    if (mask.dtype != bool or mask.ndim != 3 or not 0 < mask.size <= MAX_MASK_VOXELS
            or not np.any(mask)):
        raise ValueError("Propagation requires a nonempty bounded boolean annotation mask.")
    return mask


def mask_digest(mask):
    mask = _mask(mask)
    digest = sha256(np.asarray(mask.shape, dtype='<i8').tobytes())
    digest.update(np.packbits(mask).tobytes())
    return digest.hexdigest()


def registration_digest(registration):
    if not isinstance(registration, RegistrationResult):
        raise ValueError("Annotation propagation requires a completed registration mapping.")
    description = dict(settings=asdict(registration.settings), reference_id=registration.reference_id,
        moving_id=registration.moving_id, reference_index=registration.reference_index,
        moving_index=registration.moving_index)
    for name in ('reference_grid', 'moving_grid', 'work_grid'):
        grid = getattr(registration, name)
        description[name] = dict(shape=grid.shape, spacing=grid.spacing, origin=grid.origin,
                                 direction=grid.direction.tolist())
    digest = sha256(json.dumps(description, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    digest.update(np.asarray(registration.rigid_matrix, dtype='<f8').tobytes())
    if registration.field_mm is not None:
        digest.update(np.asarray(registration.field_mm, dtype='<f4').tobytes())
    return digest.hexdigest()


def validate_provenance(metadata, phase, mask):
    if type(metadata) is not dict:
        raise ValueError("Applied annotation provenance must be a dictionary.")
    if metadata == {'kind': 'manual'}:
        mask = np.asarray(mask)
        if mask.dtype != bool or mask.ndim != 3 or not mask.size or not mask.any():
            raise ValueError("Applied annotations require a nonempty boolean source-grid mask.")
        return {'kind': 'manual'}
    mask = _mask(mask)
    names = {'kind', 'source_phase', 'target_phase', 'reference_id', 'moving_id', 'registration_id',
        'source_mask_sha256', 'initial_mask_sha256', 'source_voxels', 'initial_voxels',
        'inverse_tolerance_mm', 'max_roundtrip_error_mm', 'contraction_bound', 'corrected'}
    if set(metadata) != names or metadata['kind'] != 'propagated':
        raise ValueError("The annotation transfer provenance is incomplete or unsupported.")
    for name in ('source_phase', 'target_phase'):
        if type(metadata[name]) is not int or not 0 <= metadata[name] < 1000:
            raise ValueError("Annotation transfer provenance requires valid source and destination phases.")
    if metadata['target_phase'] != phase or metadata['source_phase'] == phase:
        raise ValueError("The transferred annotation belongs to a different destination phase.")
    for name in ('reference_id', 'moving_id', 'registration_id', 'source_mask_sha256', 'initial_mask_sha256'):
        value = metadata[name]
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError("Annotation transfer provenance requires complete source and mapping fingerprints.")
    for name in ('source_voxels', 'initial_voxels'):
        if type(metadata[name]) is not int or not 1 <= metadata[name] <= MAX_MASK_VOXELS:
            raise ValueError("The annotation transfer voxel counts are invalid.")
    if type(metadata['corrected']) is not bool:
        raise ValueError("The transferred annotation correction flag is invalid.")
    for name in ('inverse_tolerance_mm', 'max_roundtrip_error_mm', 'contraction_bound'):
        value = metadata[name]
        if type(value) not in (int, float) or not np.isfinite(value):
            raise ValueError("Annotation inverse diagnostics must be finite numeric values.")
    if (not 0 < metadata['inverse_tolerance_mm'] <= .05
            or not 0 <= metadata['max_roundtrip_error_mm'] <= metadata['inverse_tolerance_mm']
            or not 0 <= metadata['contraction_bound'] < CONTRACTION_LIMIT):
        raise ValueError("The annotation inverse diagnostics exceed their accepted numerical bounds.")
    changed = metadata['initial_mask_sha256'] != mask_digest(mask)
    if metadata['corrected'] != changed or not changed and metadata['initial_voxels'] != int(np.count_nonzero(mask)):
        raise ValueError("The transferred annotation correction flag or initial voxel count disagrees with its mask.")
    return dict(metadata)


@dataclass(frozen=True)
class PropagationResult:
    mask: np.ndarray = field(repr=False)
    _metadata: dict = field(repr=False)

    def __post_init__(self):
        mask = _mask(self.mask)
        if type(self._metadata) is not dict or self._metadata.get('kind') != 'propagated' or self._metadata.get('corrected') is not False:
            raise ValueError("A new propagation result requires its uncorrected transfer provenance.")
        metadata = validate_provenance(self._metadata, self._metadata.get('target_phase'), mask)
        object.__setattr__(self, 'mask', np.frombuffer(mask.tobytes(), dtype=bool).reshape(mask.shape))
        object.__setattr__(self, '_metadata', MappingProxyType(metadata))

    @property
    def provenance(self):
        return dict(self._metadata)


def _bounds(mask):
    lower, upper = np.asarray(mask.shape[::-1]), np.zeros(3, int)
    for z, section in enumerate(mask):
        y, x = np.nonzero(section)
        if len(x):
            lower = np.minimum(lower, (x.min(), y.min(), z))
            upper = np.maximum(upper, (x.max(), y.max(), z))
    return lower - .5, upper + .5


def _corners(lower, upper):
    return np.asarray(list(product(*zip(lower, upper))))


def _domain(registration, lower, upper, check):
    work, reference = registration.work_grid, registration.reference_grid
    if np.any(lower < 0) or np.any(upper > np.asarray(reference.shape[::-1]) - 1):
        raise ValueError("Deformable propagation cannot verify source voxel cells touching the CT boundary. Annotate that phase manually.")
    first = np.maximum(0, np.floor(lower * reference.spacing / work.spacing).astype(int) - 1)
    last = np.minimum(np.asarray(work.shape[::-1]) - 1,
                      np.ceil(upper * reference.spacing / work.spacing).astype(int) + 1)
    inverse_direction = np.linalg.inv(reference.direction)
    derivative = np.zeros((3, 3))
    projected_min, projected_max = np.full(3, np.inf), np.full(3, -np.inf)
    destination_inverse = np.linalg.inv(registration.moving_grid.direction @ np.diag(registration.moving_grid.spacing))
    project = (destination_inverse @ registration.rigid_matrix[:3, :3]).T
    for z in range(int(first[2]), int(last[2]), 8):
        check()
        patch = registration.field_mm[z:min(z + 8, last[2]) + 1,
            first[1]:last[1] + 1, first[0]:last[0] + 1]
        physical = np.asarray(patch, dtype=float) @ inverse_direction.T
        for axis in range(3):
            edges = np.diff(physical, axis=2 - axis) / work.spacing[axis]
            derivative[:, axis] = np.maximum(derivative[:, axis], np.abs(edges).reshape(-1, 3).max(axis=0))
        projected = np.asarray(patch, dtype=float).reshape(-1, 3) @ project
        projected_min = np.minimum(projected_min, projected.min(axis=0))
        projected_max = np.maximum(projected_max, projected.max(axis=0))
    contraction = float(derivative.sum(axis=1).max())
    if contraction >= CONTRACTION_LIMIT:
        raise ValueError("The local deformation cannot be uniquely inverted by the bounded propagation method. Use another registration or annotate the destination phase manually.")
    lower_u = np.maximum(first * work.spacing, 0.)
    upper_u = np.minimum(last * work.spacing, (np.asarray(reference.shape[::-1]) - 1) * reference.spacing)
    return lower_u, upper_u, contraction, projected_min, projected_max


def _inverse(registration, points, domain, check):
    rotation, translation = registration.rigid_matrix[:3, :3], registration.rigid_matrix[:3, 3]
    rigid_inverse = (points - translation) @ np.linalg.inv(rotation).T
    if registration.field_mm is None:
        residual = float(np.linalg.norm(rigid_inverse @ rotation.T + translation - points, axis=1).max())
        return rigid_inverse, np.ones(len(points), bool), residual
    lower, upper, contraction, _, _ = domain
    grid = registration.work_grid
    inverse_direction = np.linalg.inv(grid.direction)
    query = (rigid_inverse - grid.origin) @ inverse_direction.T
    estimate = query.copy()
    sampling_error = min(registration.reference_grid.spacing) * SAMPLING_TIE_TOLERANCE_VOX / 8
    for iteration in range(1024):
        if iteration % 8 == 0:
            check()
        indices = np.clip(estimate, lower, upper) / grid.spacing
        displacement = np.column_stack([map_coordinates(registration.field_mm[..., axis], indices[:, ::-1].T,
            output=np.float64, order=1, mode='nearest', prefilter=False) for axis in range(3)]) @ inverse_direction.T
        updated = query - displacement
        step = float(np.max(np.abs(updated - estimate)))
        estimate = updated
        # projection is nonexpansive; a derivative norm below one makes this inverse iteration a contraction.
        if np.sqrt(3.) * np.linalg.norm(grid.direction, ord=2) * contraction * step / max(1 - contraction, 1e-12) <= sampling_error:
            break
    else:
        raise ValueError("Annotation propagation did not converge within its bounded inverse iteration budget.")
    inside = np.all((estimate >= lower - 1e-8) & (estimate <= upper + 1e-8), axis=1)
    physical = estimate @ grid.direction.T + grid.origin
    residual = 0.
    if np.any(inside):
        mapped, supported = registration.map_points(physical[inside], return_support=True)
        if not np.all(supported):
            raise ValueError("The annotation inverse left the supported reference CT domain.")
        residual = float(np.linalg.norm(mapped - points[inside], axis=1).max())
        if residual > INVERSE_TOLERANCE_MM:
            raise ValueError("The annotation inverse failed its physical round-trip residual check.")
    return physical, inside, residual


def propagate_annotation(registration, reference, moving, source_mask, *, progress=None, cancelled=None):
    if not isinstance(registration, RegistrationResult) or not isinstance(reference, Volume) or not isinstance(moving, Volume):
        raise ValueError("Annotation propagation requires a completed registration and its original source CT pair.")
    source_mask = _mask(source_mask)
    if source_mask.shape != reference.shape or moving.data.size > MAX_MASK_VOXELS:
        raise ValueError("The annotation must match the reference CT and fit the bounded destination mask budget.")
    def check():
        if cancelled is not None and cancelled():
            raise InterruptedError("Annotation propagation cancelled; no partial region was published.")
    def report(message):
        check()
        if progress is not None:
            progress(message)
    report('Verifying annotation sources and local inverse support…')
    registration.validate_sources(reference, moving)
    lower, upper = _bounds(source_mask)
    domain = _domain(registration, lower, upper, check) if registration.field_mm is not None else None
    points = reference.index_to_world(_corners(lower, upper))
    mapped = points @ registration.rigid_matrix[:3, :3].T + registration.rigid_matrix[:3, 3]
    destination = moving.world_to_index(mapped)
    minimum, maximum = destination.min(axis=0), destination.max(axis=0)
    if domain is not None:
        minimum, maximum = minimum + domain[3], maximum + domain[4]
    if np.any(minimum < -.5 - 1e-6) or np.any(maximum > np.asarray(moving.shape[::-1]) - .5 + 1e-6):
        raise ValueError("The complete mapped annotation cannot be bounded inside the destination CT. No clipped transfer was produced.")
    first = np.maximum(0, np.ceil(minimum - 1e-7).astype(int))
    last = np.minimum(np.asarray(moving.shape[::-1]) - 1, np.floor(maximum + 1e-7).astype(int))
    size = last - first + 1
    count = int(np.prod(size))
    if min(size) < 1 or count > MAX_CANDIDATE_VOXELS:
        raise ValueError("The mapped annotation is empty or exceeds the bounded native-grid propagation budget.")
    output = np.zeros(moving.shape, bool)
    largest_residual = 0.
    source_inverse = np.linalg.inv(reference.affine[:3, :3])
    for start in range(0, count, 32768):
        report(f"Pulling annotation onto destination CT · {start * 100 // count}%")
        flat = np.arange(start, min(start + 32768, count))
        index = np.column_stack((flat % size[0], (flat // size[0]) % size[1], flat // (size[0] * size[1]))) + first
        source, supported, residual = _inverse(registration, moving.index_to_world(index), domain, check)
        largest_residual = max(largest_residual, residual)
        source_index = reference.world_to_index(source)
        scale = (np.abs(source) + np.abs(reference.origin)) @ np.abs(source_inverse.T)
        # half-voxel ties use a fixed tiny voxel tolerance, wider than the certified inverse error.
        tolerance = np.maximum(SAMPLING_TIE_TOLERANCE_VOX,
            64 * np.finfo(float).eps * np.maximum(1., np.maximum(np.abs(source_index), scale)))
        nearest = np.floor(_snap_faces(source_index, tolerance) + .5).astype(int)
        valid = supported & np.all((nearest >= 0) & (nearest < np.asarray(reference.shape[::-1])), axis=1)
        selected = np.zeros(len(index), bool)
        if np.any(valid):
            xyz = nearest[valid]
            selected[valid] = source_mask[xyz[:, 2], xyz[:, 1], xyz[:, 0]]
        output[index[:, 2], index[:, 1], index[:, 0]] = selected
    if not output.any():
        raise ValueError("The region has no foreground samples on the destination CT grid. No empty annotation was produced.")
    check()
    metadata = dict(kind='propagated', source_phase=registration.reference_index, target_phase=registration.moving_index,
        reference_id=registration.reference_id, moving_id=registration.moving_id,
        registration_id=registration_digest(registration), source_mask_sha256=mask_digest(source_mask),
        initial_mask_sha256=mask_digest(output), source_voxels=int(np.count_nonzero(source_mask)),
        initial_voxels=int(np.count_nonzero(output)), inverse_tolerance_mm=INVERSE_TOLERANCE_MM,
        max_roundtrip_error_mm=largest_residual, contraction_bound=domain[2] if domain is not None else 0., corrected=False)
    report('Annotation transfer ready for inspection and manual correction.')
    return PropagationResult(output, metadata)
