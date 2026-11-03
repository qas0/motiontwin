from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json

import numpy as np
from scipy.ndimage import map_coordinates

from motiontwin import CTSequence, Volume, _CTHeader, _to_sitk, load_volume, target_study_id


MAX_WORK_VOXELS = 2_000_000


def _number(value, low, high, name):
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating))
            or not np.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{name} must be between {low:g} and {high:g}.")
    return float(value)


def _frozen(array, dtype):
    array = np.asarray(array, dtype=dtype, order="C")
    return np.frombuffer(array.tobytes(), dtype=dtype).reshape(array.shape)


@dataclass(frozen=True)
class RegistrationSettings:
    method: str = "Rigid + deformable"
    spacing_mm: float = 3.
    rigid_iterations: int = 100
    deformable_iterations: int = 40
    smoothing_mm: float = 4.

    def __post_init__(self):
        if self.method not in ("Rigid", "Rigid + deformable"):
            raise ValueError("Choose Rigid or Rigid + deformable registration.")
        for name, low, high in (("spacing_mm", 1., 8.), ("smoothing_mm", 1., 8.)):
            object.__setattr__(self, name, _number(getattr(self, name), low, high, name.replace('_', ' ')))
        for name in ("rigid_iterations", "deformable_iterations"):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 200:
                raise ValueError("Registration iterations must be integers between 1 and 200.")


@dataclass(frozen=True, eq=False)
class RegistrationGrid:
    shape: tuple
    spacing: tuple
    origin: tuple
    direction: np.ndarray = field(repr=False)

    def __post_init__(self):
        shape = tuple(self.shape)
        spacing, origin, direction = np.asarray(self.spacing), np.asarray(self.origin), np.asarray(self.direction)
        if (len(shape) != 3 or any(type(n) is not int or not 1 <= n <= 65536 for n in shape)
                or spacing.shape != (3,) or origin.shape != (3,) or direction.shape != (3, 3)
                or any(a.dtype.kind not in 'iuf' or not np.isfinite(a).all() for a in (spacing, origin, direction))
                or np.any(spacing <= 0) or not np.allclose(direction.T @ direction, np.eye(3), rtol=0, atol=1e-5)):
            raise ValueError("Registration requires finite orthogonal physical image geometry.")
        object.__setattr__(self, 'shape', shape)
        object.__setattr__(self, 'spacing', tuple(float(v) for v in spacing))
        object.__setattr__(self, 'origin', tuple(float(v) for v in origin))
        object.__setattr__(self, 'direction', _frozen(direction, np.float64))

    @classmethod
    def from_volume(cls, volume):
        return cls(tuple(volume.shape), volume.spacing, volume.origin, volume.direction)

    def matches(self, volume):
        return (tuple(volume.shape) == self.shape and all(np.allclose(getattr(self, name), getattr(volume, name),
                rtol=0, atol=1e-6) for name in ('spacing', 'origin', 'direction')))

    def world_to_index(self, points):
        return (np.asarray(points) - self.origin) @ np.linalg.inv(self.direction @ np.diag(self.spacing)).T

    def index_to_world(self, indices):
        return np.asarray(indices) @ (self.direction @ np.diag(self.spacing)).T + self.origin

    def contains(self, points):
        index = self.world_to_index(points)
        return np.all((index >= -1e-6) & (index <= np.asarray(self.shape[::-1]) - 1 + 1e-6), axis=-1)


@dataclass(frozen=True)
class RegistrationQuality:
    comparison_voxels: int
    overlap_before: float
    overlap_after: float
    rmse_before_hu: float
    rmse_after_hu: float
    jacobian_min: float
    jacobian_max: float
    max_displacement_mm: float

    def __post_init__(self):
        if type(self.comparison_voxels) is not int or not 32 <= self.comparison_voxels <= MAX_WORK_VOXELS:
            raise ValueError("Registration comparison requires a bounded common supported voxel population.")
        for name in ('overlap_before', 'overlap_after'):
            object.__setattr__(self, name, _number(getattr(self, name), 0., 1., name))
        for name in ('rmse_before_hu', 'rmse_after_hu', 'max_displacement_mm'):
            object.__setattr__(self, name, _number(getattr(self, name), 0., 5000., name))
        for name in ('jacobian_min', 'jacobian_max'):
            object.__setattr__(self, name, _number(getattr(self, name), 1e-6, 1000., name))
        if self.jacobian_min > self.jacobian_max:
            raise ValueError("The registration Jacobian range is inconsistent.")


def _jacobian_range(displacement, grid):
    if displacement is None:
        return 1., 1.
    low, high = np.inf, -np.inf
    inverse_direction = np.linalg.inv(grid.direction)
    # slabs bound temporary derivative storage; vector components are physical LPS, not voxel axes.
    for first in range(0, grid.shape[0], 8):
        last = min(first + 8, grid.shape[0])
        start, end = max(0, first - 1), min(grid.shape[0], last + 1)
        block = np.asarray(displacement[start:end], dtype=float)
        derivative = np.stack([np.stack(np.gradient(block[..., component], *grid.spacing[::-1], edge_order=1)[::-1],
            axis=-1) for component in range(3)], axis=-2)
        derivative = derivative[first - start:last - start] @ inverse_direction
        values = np.linalg.det(derivative + np.eye(3))
        low, high = min(low, float(values.min())), max(high, float(values.max()))
    return low, high


def _mapped(points, work_grid, rigid_matrix, displacement):
    values = np.asarray(points, dtype=float)
    if displacement is not None:
        indices = work_grid.world_to_index(values).reshape(-1, 3)
        residual = np.stack([map_coordinates(displacement[..., component], indices[:, ::-1].T,
            output=np.float64, order=1, mode='nearest', prefilter=False) for component in range(3)], axis=-1).reshape(values.shape)
        values = values + residual
    return values @ rigid_matrix[:3, :3].T + rigid_matrix[:3, 3]


def _maximum_displacement(reference_grid, work_grid, matrix, displacement):
    maximum = 0.
    y, x = np.indices(work_grid.shape[1:])
    for z in range(work_grid.shape[0]):
        points = work_grid.index_to_world(np.stack((x, y, np.full_like(x, z)), axis=-1))
        supported = reference_grid.contains(points)
        if np.any(supported):
            selected = points[supported]
            maximum = max(maximum, float(np.linalg.norm(_mapped(selected, work_grid, matrix, displacement) - selected, axis=-1).max()))
    return maximum


@dataclass(frozen=True, eq=False)
class RegistrationResult:
    settings: RegistrationSettings
    reference_id: str
    moving_id: str
    reference_index: int
    moving_index: int
    reference_grid: RegistrationGrid
    moving_grid: RegistrationGrid
    work_grid: RegistrationGrid
    rigid_matrix: np.ndarray = field(repr=False)
    field_mm: np.ndarray | None = field(repr=False)
    quality: RegistrationQuality
    stop_reason: str

    def __post_init__(self):
        if (not isinstance(self.settings, RegistrationSettings) or not isinstance(self.quality, RegistrationQuality)
                or any(not isinstance(getattr(self, name), RegistrationGrid) for name in ('reference_grid', 'moving_grid', 'work_grid'))
                or any(not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value)
                       for value in (self.reference_id, self.moving_id))
                or any(type(value) is not int or not 0 <= value < 1000 for value in (self.reference_index, self.moving_index))
                or self.reference_index == self.moving_index or not isinstance(self.stop_reason, str)
                or not self.stop_reason or len(self.stop_reason) > 2000):
            raise ValueError("A registration result requires a defined source pair, method and quality assessment.")
        matrix = np.asarray(self.rigid_matrix)
        if (matrix.shape != (4, 4) or matrix.dtype.kind not in 'iuf' or not np.isfinite(matrix).all()
                or not np.allclose(matrix[3], (0, 0, 0, 1), rtol=0, atol=1e-8)
                or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), rtol=0, atol=1e-6)
                or not np.isclose(np.linalg.det(matrix[:3, :3]), 1., rtol=0, atol=1e-6)
                or np.linalg.norm(matrix[:3, 3]) > 1000 or np.prod(self.work_grid.shape) > MAX_WORK_VOXELS
                or min(self.work_grid.shape) < 4 or self.quality.comparison_voxels > np.prod(self.work_grid.shape)
                or min(self.quality.overlap_before, self.quality.overlap_after) < .25):
            raise ValueError("The registration mapping has invalid or excessive physical geometry.")
        reference_extent = (np.asarray(self.reference_grid.shape[::-1]) - 1) * self.reference_grid.spacing
        work_extent = (np.asarray(self.work_grid.shape[::-1]) - 1) * self.work_grid.spacing
        if (not np.allclose(self.reference_grid.origin, self.work_grid.origin, rtol=0, atol=1e-6)
                or not np.allclose(self.reference_grid.direction, self.work_grid.direction, rtol=0, atol=1e-6)
                or np.any(work_extent < reference_extent - 1e-6)
                or np.any(work_extent - reference_extent > np.asarray(self.work_grid.spacing) + 1e-6)):
            raise ValueError("The registration working grid must cover and align with the reference CT.")
        object.__setattr__(self, 'rigid_matrix', _frozen(matrix, np.float64))
        field_values = self.field_mm
        if self.settings.method == 'Rigid':
            if field_values is not None:
                raise ValueError("A rigid registration cannot contain a deformable field.")
        else:
            field_values = np.asarray(field_values)
            if (field_values.shape != (*self.work_grid.shape, 3) or field_values.dtype.kind != 'f'
                    or not np.isfinite(field_values).all() or np.linalg.norm(field_values, axis=-1).max() > 100.):
                raise ValueError("The registration displacement field is invalid or exceeds 100 mm.")
            object.__setattr__(self, 'field_mm', _frozen(field_values, np.float32))
        low, high = _jacobian_range(self.field_mm, self.work_grid)
        if low <= 0 or not np.allclose((low, high), (self.quality.jacobian_min, self.quality.jacobian_max), rtol=1e-5, atol=1e-5):
            raise ValueError("The sampled registration field folds or disagrees with its stored Jacobian assessment.")
        maximum = _maximum_displacement(self.reference_grid, self.work_grid, self.rigid_matrix, self.field_mm)
        if not np.isclose(maximum, self.quality.max_displacement_mm, rtol=1e-5, atol=1e-4):
            raise ValueError("The registration displacement disagrees with its stored physical assessment.")

    @property
    def pair_id(self):
        return sha256(json.dumps((self.reference_id, self.moving_id, self.reference_index, self.moving_index)).encode()).hexdigest()

    @property
    def metrics(self):
        return asdict(self.quality)

    def validate_sources(self, reference, moving):
        if (not self.reference_grid.matches(reference) or not self.moving_grid.matches(moving)
                or self.reference_id != target_study_id(reference) or self.moving_id != target_study_id(moving)):
            raise ValueError("The registration belongs to a different acquired CT source pair.")
        return self

    def map_points(self, points, *, return_support=False):
        points = np.asarray(points)
        if points.shape[-1:] != (3,) or points.dtype.kind not in 'iuf' or not np.isfinite(points).all():
            raise ValueError("Registration points must be finite physical LPS coordinates.")
        values = points.astype(float)
        support = self.reference_grid.contains(values) & self.work_grid.contains(values)
        if not return_support and not np.all(support):
            raise ValueError("The requested point is outside the verified reference registration domain.")
        mapped = _mapped(values, self.work_grid, self.rigid_matrix, self.field_mm)
        return (mapped, support) if return_support else mapped

    def landmark_errors(self, reference_point, moving_point):
        reference, moving = np.asarray(reference_point, dtype=float), np.asarray(moving_point, dtype=float)
        if reference.shape != (3,) or moving.shape != (3,) or not np.isfinite(moving).all() or not self.moving_grid.contains(moving):
            raise ValueError("Landmark verification requires a supported point in each source CT.")
        predicted = self.map_points(reference)
        return dict(before_mm=float(np.linalg.norm(reference - moving)), after_mm=float(np.linalg.norm(predicted - moving)),
                    predicted_lps_mm=tuple(predicted))


def _working_grid(volume, spacing):
    extent = (np.asarray(volume.shape[::-1]) - 1) * volume.spacing
    spacing = min(spacing, float(extent.min() / 7))
    while True:
        size = np.ceil(extent / spacing).astype(int) + 1
        if np.prod(size) <= MAX_WORK_VOXELS and size.max() <= 256:
            break
        spacing *= 1.05
    if size.min() < 4:
        raise ValueError("The acquired CT is too thin for bounded 3D registration.")
    return RegistrationGrid(tuple(int(v) for v in size[::-1]), (spacing,) * 3, volume.origin, volume.direction)


def _image(array, grid):
    return _to_sitk(Volume(array, grid.spacing, grid.origin, grid.direction))


def _finite_volume(volume):
    low, high = np.inf, -np.inf
    for section in volume.data:
        if volume.data.dtype.kind == 'f' and not np.isfinite(section).all():
            raise ValueError("Acquired CT intensities must be finite before registration.")
        low, high = min(low, float(section.min())), max(high, float(section.max()))
    if min(400., high) - max(-1000., low) < 1.:
        raise ValueError("The acquired CT has insufficient image structure in the registration intensity window.")


def _transform_matrix(transform):
    origin = np.asarray(transform.TransformPoint((0., 0., 0.)))
    matrix = np.eye(4)
    matrix[:3, :3] = np.column_stack([np.asarray(transform.TransformPoint(tuple(axis))) - origin for axis in np.eye(3)])
    matrix[:3, 3] = origin
    return matrix


def load_pair(sequence, reference_index, moving_index, *, cancelled=None):
    if (not isinstance(sequence, CTSequence) or any(type(index) is not int or not 0 <= index < len(sequence.phases)
            for index in (reference_index, moving_index)) or reference_index == moving_index):
        raise ValueError("Choose two distinct phases from the acquired CT sequence.")
    volumes = []
    for index in (reference_index, moving_index):
        if cancelled is not None and cancelled():
            raise InterruptedError("Registration cancelled; no partial mapping was published.")
        sequence._check_sources(index)
        volume = load_volume(sequence.phases[index].image)
        _finite_volume(volume)
        expected = sequence._sources[index][0].header
        actual = _CTHeader(volume.shape, volume.spacing, volume.origin, tuple(volume.direction.ravel()))
        if not expected.matches(actual):
            raise ValueError("An acquired phase's geometry changed since its checked source header.")
        volumes.append(volume)
    for index in (reference_index, moving_index):
        sequence._check_sources(index)
    if cancelled is not None and cancelled():
        raise InterruptedError("Registration cancelled; no partial mapping was published.")
    return tuple(volumes)


def register_pair(reference, moving, settings=None, *, reference_index=0, moving_index=1, progress=None, cancelled=None):
    import SimpleITK as sitk
    settings = RegistrationSettings() if settings is None else settings
    if (not isinstance(reference, Volume) or not isinstance(moving, Volume) or not isinstance(settings, RegistrationSettings)
            or min(*reference.shape, *moving.shape) < 8
            or any(type(index) is not int or not 0 <= index < 1000 for index in (reference_index, moving_index))
            or reference_index == moving_index):
        raise ValueError("Registration requires two acquired 3D CT volumes with at least eight voxels on each axis.")
    def check():
        if cancelled is not None and cancelled():
            raise InterruptedError("Registration cancelled; no partial mapping was published.")
    def report(message):
        check()
        if progress is not None:
            progress(message)
    report('Preparing bounded physical registration grids…')
    _finite_volume(reference); _finite_volume(moving)
    reference_grid, moving_grid = RegistrationGrid.from_volume(reference), RegistrationGrid.from_volume(moving)
    work = _working_grid(reference, settings.spacing_mm)
    def normalized(volume, grid):
        target = sitk.Image(list(grid.shape[::-1]), sitk.sitkFloat32)
        target.SetSpacing(grid.spacing); target.SetOrigin(grid.origin); target.SetDirection(tuple(grid.direction.ravel()))
        sampled = sitk.Resample(_to_sitk(volume), target, sitk.Transform(), sitk.sitkLinear, -1000., sitk.sitkFloat32)
        clipped = sitk.GetArrayFromImage(sampled)
        np.clip(clipped, -1000., 400., out=clipped)
        clipped += 1000.; clipped /= 1400.
        return _image(clipped, grid)
    fixed = normalized(reference, work)
    moving_source = normalized(moving, _working_grid(moving, settings.spacing_mm))
    moving_work = sitk.Resample(moving_source, fixed, sitk.Transform(), sitk.sitkLinear, 0.)
    if np.std(sitk.GetArrayViewFromImage(fixed)) < 1e-4 or np.std(sitk.GetArrayViewFromImage(moving_work)) < 1e-4:
        raise ValueError("The acquired phase pair has insufficient image structure or physical overlap for registration.")
    rigid = sitk.CenteredTransformInitializer(fixed, moving_source, sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY)
    registration = sitk.ImageRegistrationMethod()
    registration.SetNumberOfThreads(1)
    registration.SetMetricAsMattesMutualInformation(32)
    registration.SetMetricSamplingStrategy(registration.REGULAR)
    registration.SetMetricSamplingPercentage(.3, 1979)
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsRegularStepGradientDescent(2., .005, settings.rigid_iterations, gradientMagnitudeTolerance=1e-6)
    registration.SetOptimizerScalesFromPhysicalShift()
    registration.SetShrinkFactorsPerLevel((2, 1)); registration.SetSmoothingSigmasPerLevel((2., 0.))
    registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    registration.SetInitialTransform(rigid, inPlace=True)
    def rigid_update():
        if cancelled is not None and cancelled():
            registration.StopRegistration()
        elif progress is not None:
            progress(f"Rigid alignment · level {registration.GetCurrentLevel() + 1}/2 · iteration {registration.GetOptimizerIteration() + 1}")
    registration.AddCommand(sitk.sitkIterationEvent, rigid_update)
    report('Estimating rigid reference-to-moving alignment…')
    try:
        registration.Execute(fixed, moving_source)
    except RuntimeError as error:
        check()
        raise ValueError('Rigid registration failed. Inspect phase coverage and image structure. ' + str(error)[-400:]) from error
    check()
    matrix = _transform_matrix(rigid)
    displacement = None
    reason = registration.GetOptimizerStopConditionDescription()
    if settings.method == 'Rigid + deformable':
        aligned = sitk.Resample(moving_source, fixed, rigid, sitk.sitkLinear, 0.)
        for factor in (2, 1):
            report(f"Deformable alignment · {'coarse' if factor == 2 else 'fine'} grid…")
            coarse = sitk.Shrink(fixed, (factor,) * 3) if factor > 1 else fixed
            phase = sitk.Shrink(aligned, (factor,) * 3) if factor > 1 else aligned
            if displacement is not None:
                displacement = sitk.Resample(displacement, coarse, sitk.Transform(), sitk.sitkLinear)
            demons = sitk.FastSymmetricForcesDemonsRegistrationFilter()
            demons.SetNumberOfThreads(2)
            demons.SetNumberOfIterations(settings.deformable_iterations)
            demons.SetSmoothDisplacementField(True)
            demons.SetStandardDeviations(settings.smoothing_mm / coarse.GetSpacing()[0])
            demons.SetMaximumUpdateStepLength(1.)
            demons.SetMaximumRMSError(1e-4)
            def demons_update():
                if cancelled is not None and cancelled():
                    demons.StopRegistration()
                elif progress is not None:
                    progress(f"Deformable alignment · {'coarse' if factor == 2 else 'fine'} grid · iteration {demons.GetElapsedIterations()}")
            demons.AddCommand(sitk.sitkIterationEvent, demons_update)
            displacement = demons.Execute(coarse, phase, displacement) if displacement is not None else demons.Execute(coarse, phase)
            check()
        displacement = sitk.GetArrayFromImage(displacement).astype(np.float32)
        reason += f"; regularized Demons {demons.GetElapsedIterations()} final-level iterations, RMS update {demons.GetRMSChange():.6g} mm"
    report('Checking support, shared-population image agreement and deformation Jacobians…')
    low, high = _jacobian_range(displacement, work)
    if low <= 0:
        raise ValueError('The estimated deformation folds on the working grid. Inspect the rigid result or increase smoothing.')
    totals = np.zeros(5)
    common_count, maximum_displacement = 0, 0.
    y, x = np.indices(work.shape[1:])
    for z in range(work.shape[0]):
        check()
        points = work.index_to_world(np.stack((x, y, np.full_like(x, z)), axis=-1))
        warped = _mapped(points, work, matrix, displacement)
        domain = reference_grid.contains(points) & work.contains(points)
        if np.any(domain):
            maximum_displacement = max(maximum_displacement, float(np.linalg.norm(warped[domain] - points[domain], axis=-1).max()))
        before, after = moving_grid.contains(points) & domain, moving_grid.contains(warped) & domain
        common = before & after
        totals[:3] += (np.count_nonzero(domain), np.count_nonzero(before), np.count_nonzero(after))
        if np.any(common):
            fixed_values = np.clip(reference.sample_world(points[common]), -1000., 400.)
            totals[3] += np.sum((fixed_values - np.clip(moving.sample_world(points[common]), -1000., 400.)) ** 2)
            totals[4] += np.sum((fixed_values - np.clip(moving.sample_world(warped[common]), -1000., 400.)) ** 2)
        common_count += int(np.count_nonzero(common))
    if common_count < 32 or min(totals[1:3]) < .25 * totals[0]:
        raise ValueError('Registration has insufficient shared source coverage for a comparable alignment check.')
    quality = RegistrationQuality(common_count, totals[1] / totals[0], totals[2] / totals[0],
        float(np.sqrt(totals[3] / common_count)), float(np.sqrt(totals[4] / common_count)), low, high,
        maximum_displacement)
    check()
    return RegistrationResult(settings, target_study_id(reference), target_study_id(moving), reference_index, moving_index,
        reference_grid, moving_grid, work, matrix, displacement, quality, reason)
