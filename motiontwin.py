"""MotionTwin scientific core: imaging, respiratory simulation, planning and AI.

Sections retain the existing mathematical and imaging implementations. The
desktop interface and executable launcher are in run.py. Public CT data,
trained models and generated results are stored locally and are not source.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from functools import lru_cache
import yaml

__version__ = "0.1.0"

DEFAULT_APPLICATION_CONFIG = {'simulation': {'seed': 17,
                'amplitude': 12.0,
                'frequency': 0.25,
                'irregularity': 0.1,
                'target_radius': 6.0,
                'noise': 0.5,
                'delay': 1.0,
                'insertion_speed': 60.0},
 'training': {'seed': 431,
              'patients': 48,
              'samples_per_patient': 90,
              'history_points': 24,
              'history_seconds': 8.0,
              'horizons': [0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0],
              'epochs': 70,
              'patience': 12,
              'batch_size': 128,
              'hidden_units': [64, 64],
              'device': 'cpu',
              'output_dir': 'outputs/model'}}

DEFAULT_EXPERIMENT_CONFIG = {'seed': 104729,
 'patients': 4,
 'repetitions': 1,
 'bootstrap_samples': 200,
 'confidence': 0.95,
 'experiments': ['A', 'B', 'C', 'D', 'E', 'F'],
 'methods': ['static', 'sinusoidal', 'learned'],
 'amplitudes': [0, 6, 12, 20],
 'forecast_delays': [0.25, 1.0, 2.0],
 'delays': [0.25, 1.0, 2.0],
 'irregularities': [0.0, 0.2, 0.5],
 'risk_tolerances': [0.01, 0.1, 0.25],
 'time_steps': [0.1, 0.05, 0.025],
 'spatial_resolutions': [4.0, 2.0, 1.0],
 'integration_steps': [0.04, 0.02, 0.01],
 'episode': {'risk_tolerance': 0.1,
             'dt': 0.05,
             'history_duration': 8.0,
             'history_step': 0.1,
             'spatial_resolution': 2.0,
             'integration_step': 0.02,
             'delay_aware': True,
             'uncertainty': True}}

def load_config(path="builtin:default"):
    """Read optional external YAML, or return an independent built-in default."""
    defaults={"builtin:default":DEFAULT_APPLICATION_CONFIG,
              "builtin:experiments":DEFAULT_EXPERIMENT_CONFIG,
              "configs/default.yaml":DEFAULT_APPLICATION_CONFIG,
              "configs/experiments.yaml":DEFAULT_EXPERIMENT_CONFIG}
    key=str(path).replace("\\","/")
    if key in defaults and not Path(path).is_file():
        return deepcopy(defaults[key])
    with Path(path).open(encoding="utf-8") as stream:
        result=yaml.safe_load(stream) or {}
    if not isinstance(result,dict):
        raise ValueError("Configuration must be a YAML mapping")
    return result


@lru_cache(maxsize=1)
def _motion_mlp_class():
    """Create the existing model only when training/learned prediction needs it."""
    from torch import nn

    class MotionMLP(nn.Module):
        def __init__(self,input_features:int,hidden_units=64):
            super().__init__()
            first,second=(hidden_units,hidden_units) if isinstance(hidden_units,int) else hidden_units
            self.network=nn.Sequential(nn.Linear(input_features,first),nn.ReLU(),
                nn.Linear(first,second),nn.ReLU(),nn.Linear(second,3))

        def forward(self,features):
            return self.network(features)

    return MotionMLP


def __getattr__(name):
    if name=="MotionMLP":
        return _motion_mlp_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ============================================================================
# imaging / coordinates
# ============================================================================

"""Vectorised conversion between voxel xyz indices and LPS physical millimetres."""



import numpy as np


def index_to_world(indices, spacing, origin, direction):
    indices = np.asarray(indices, dtype=float)
    return (indices * np.asarray(spacing)) @ np.asarray(direction).T + np.asarray(origin)


def world_to_index(points, spacing, origin, direction):
    points = np.asarray(points, dtype=float)
    return ((points - np.asarray(origin)) @ np.linalg.inv(np.asarray(direction)).T) / np.asarray(spacing)


def lps_to_ras(points):
    return np.asarray(points, dtype=float) * np.array([-1.0, -1.0, 1.0])


def ras_to_lps(points):
    return lps_to_ras(points)


def affine_matrix(spacing, origin, direction):
    matrix = np.eye(4)
    matrix[:3, :3] = np.asarray(direction) @ np.diag(spacing)
    matrix[:3, 3] = origin
    return matrix


# ============================================================================
# imaging / volumes
# ============================================================================

"""Volume IO and physical, anatomically aligned multiplanar reslicing."""



from dataclasses import dataclass, field
from pathlib import Path
from itertools import product

import numpy as np
from scipy.ndimage import map_coordinates




@dataclass
class SlicePlane:
    """Rows increase along v, columns along u; coordinates are pixel centres.

    Axial: u=L, v=P. Coronal: u=L, v=S. Sagittal: u=P, v=S.
    Display clients may reverse rows for radiological presentation, provided
    the same reversal is applied to pixel coordinates and orientation labels.
    """

    image: np.ndarray
    origin: np.ndarray
    u: np.ndarray
    v: np.ndarray
    spacing: tuple[float, float]
    name: str
    normal: np.ndarray
    position: float

    @property
    def shape(self):
        return self.image.shape

    @property
    def extent(self):
        return (0.0, (self.image.shape[1] - 1) * self.spacing[0],
                0.0, (self.image.shape[0] - 1) * self.spacing[1])

    def world_to_pixel(self, points):
        relative = np.asarray(points, dtype=float) - self.origin
        return np.stack((relative @ self.u / self.spacing[0],
                         relative @ self.v / self.spacing[1]), axis=-1)

    def pixel_to_world(self, pixels):
        pixels = np.asarray(pixels, dtype=float)
        return (self.origin + pixels[..., 0, None] * self.spacing[0] * self.u
                + pixels[..., 1, None] * self.spacing[1] * self.v)

    def distance_to_plane(self, points):
        return (np.asarray(points, dtype=float) - self.origin) @ self.normal

    def world_grid(self):
        """Physical pixel centres, shared by intensity and mask resampling."""
        rows, columns = np.indices(self.shape, dtype=float)
        return self.pixel_to_world(np.stack((columns, rows), axis=-1))


@dataclass
class Volume:
    """A scalar medical image. Array indexing is z,y,x; metadata is x,y,z."""

    data: np.ndarray
    spacing: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: np.ndarray = field(default_factory=lambda: np.eye(3))
    name: str = "Synthetic CT"

    def __post_init__(self):
        self.data = np.asarray(self.data)
        self.spacing = tuple(float(value) for value in self.spacing)
        self.origin = tuple(float(value) for value in self.origin)
        self.direction = np.asarray(self.direction, dtype=float).reshape(3, 3)
        if self.data.ndim != 3 or 0 in self.data.shape:
            raise ValueError("A volume must contain a non-empty 3D scalar z,y,x array.")
        if (len(self.spacing) != 3 or len(self.origin) != 3
                or not np.all(np.isfinite(self.spacing)) or min(self.spacing) <= 0
                or not np.all(np.isfinite(self.origin))
                or not np.all(np.isfinite(self.direction))):
            raise ValueError("Image spacing, origin and direction must be finite; spacing must be positive.")
        if not np.allclose(self.direction.T @ self.direction, np.eye(3), atol=1e-4):
            raise ValueError("Image direction must be an orthonormal 3-by-3 direction matrix.")

    @property
    def shape(self):
        return self.data.shape

    @property
    def affine(self):
        return affine_matrix(self.spacing, self.origin, self.direction)

    @property
    def bounds(self):
        corners = np.array(list(product(*[(0, size - 1) for size in self.shape[::-1]])), dtype=float)
        world = self.index_to_world(corners)
        return np.stack((world.min(axis=0), world.max(axis=0)))

    @property
    def center(self):
        return self.index_to_world((np.asarray(self.shape[::-1]) - 1) / 2)

    def index_to_world(self, indices):
        return index_to_world(indices, self.spacing, self.origin, self.direction)

    def world_to_index(self, points):
        return world_to_index(points, self.spacing, self.origin, self.direction)

    def same_geometry(self, other, atol=1e-4):
        return (self.shape == other.shape
                and np.allclose(self.spacing, other.spacing, atol=atol)
                and np.allclose(self.origin, other.origin, atol=atol)
                and np.allclose(self.direction, other.direction, atol=atol))

    def sample_world(self, points, *, interpolation=1, cval=-1000.0):
        """Sample just the requested LPS positions without copying the volume.

        Floating-point output preserves sub-voxel HU values even when the
        source CT is stored as integers. SciPy samples that integer source
        directly, so navigating a large scan does not allocate a float 3D copy.
        """
        points = np.asarray(points, dtype=float)
        if points.shape[-1:] != (3,) or not np.all(np.isfinite(points)):
            raise ValueError("Sample positions must be finite physical xyz coordinates.")
        if interpolation not in (0, 1):
            raise ValueError("Use nearest-neighbour (0) or linear (1) interpolation.")
        output_shape = points.shape[:-1]
        indices = self.world_to_index(points.reshape(-1, 3))
        nearest = np.rint(indices)
        indices = np.where(np.abs(indices - nearest) < 1e-7, nearest, indices)
        values = map_coordinates(self.data,
                               [indices[..., 2], indices[..., 1], indices[..., 0]],
                               output=np.float32, order=interpolation,
                               mode="constant", cval=float(cval), prefilter=False)
        return values.reshape(output_shape)

    def reslice_like(self, plane, *, interpolation=1, coordinate_mapper=None,
                     cval=-1000.0):
        """Sample on another SlicePlane's exact physical grid.

        A mapper converts output-world positions into source-world positions;
        it can apply an inverse deformation without constructing a 3D frame.
        """
        points = plane.world_grid()
        if coordinate_mapper is not None:
            mapped = np.asarray(coordinate_mapper(points), dtype=float)
            if mapped.shape != points.shape:
                raise ValueError("A coordinate mapper must preserve the slice grid shape.")
            points = mapped
        image = self.sample_world(points, interpolation=interpolation, cval=cval)
        return SlicePlane(image, plane.origin.copy(), plane.u.copy(), plane.v.copy(),
                          plane.spacing, plane.name, plane.normal.copy(), plane.position)

    def slice_plane(self, plane, crosshair, *, interpolation=1, max_pixels=1024,
                    coordinate_mapper=None, cval=-1000.0):
        """Resample an LPS anatomical plane, including from oblique source data.

        Returns a SlicePlane, whose world_to_pixel/pixel_to_world functions
        should also be used for crosshairs, targets and trajectory overlays.
        """
        section = self.slice_grid(plane, crosshair, max_pixels=max_pixels)
        return self.reslice_like(section, interpolation=interpolation,
                                 coordinate_mapper=coordinate_mapper, cval=cval)

    def slice_grid(self, plane, crosshair, *, max_pixels=1024):
        """Build the physical plane grid without reading image intensities."""
        names = {"axial": (0, 1, 2), "coronal": (0, 2, 1), "sagittal": (1, 2, 0)}
        if plane.lower() not in names:
            raise ValueError("Plane must be axial, coronal or sagittal.")
        crosshair = np.asarray(crosshair, dtype=float)
        if crosshair.shape != (3,) or not np.all(np.isfinite(crosshair)):
            raise ValueError("Crosshair must be a finite physical xyz position.")
        if isinstance(max_pixels, bool) or int(max_pixels) != max_pixels or max_pixels < 2:
            raise ValueError("max_pixels must be an integer of at least 2.")
        max_pixels = int(max_pixels)
        u_axis, v_axis, normal_axis = names[plane.lower()]
        basis = np.eye(3)
        bounds = self.bounds
        resolution = min(self.spacing)
        counts = np.ceil((bounds[1] - bounds[0]) / resolution).astype(int) + 1
        nu, nv = min(max_pixels, counts[u_axis]), min(max_pixels, counts[v_axis])
        su = (bounds[1, u_axis] - bounds[0, u_axis]) / max(1, nu - 1)
        sv = (bounds[1, v_axis] - bounds[0, v_axis]) / max(1, nv - 1)
        su, sv = max(su, resolution), max(sv, resolution)
        origin = bounds[0].copy()
        origin[normal_axis] = crosshair[normal_axis]
        return SlicePlane(np.empty((nv, nu), dtype=np.float32), origin,
                          basis[u_axis], basis[v_axis], (su, sv), plane.lower(),
                          basis[normal_axis], float(crosshair[normal_axis]))


def _to_sitk(volume):
    import SimpleITK as sitk
    image = sitk.GetImageFromArray(volume.data)
    image.SetSpacing(volume.spacing)
    image.SetOrigin(volume.origin)
    image.SetDirection(tuple(volume.direction.ravel()))
    return image


def _from_sitk(image, name):
    import SimpleITK as sitk
    if image.GetDimension() != 3 or image.GetNumberOfComponentsPerPixel() != 1:
        raise ValueError("Select a 3D scalar image; use a phase manifest for 4D data.")
    return Volume(sitk.GetArrayFromImage(image), image.GetSpacing(), image.GetOrigin(),
                  np.array(image.GetDirection()).reshape(3, 3), name)


def load_volume(path):
    """Read NIfTI, MetaImage or a DICOM series directory using SimpleITK LPS."""
    import SimpleITK as sitk
    path = Path(path)
    if path.is_dir():
        series = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(path))
        if not series:
            raise ValueError("No readable DICOM series found in the selected directory.")
        if len(series) != 1:
            raise ValueError("The directory contains multiple DICOM series; select a single-series directory.")
        reader = sitk.ImageSeriesReader()
        reader.SetFileNames(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(path), series[0]))
        image = reader.Execute()
    else:
        if not path.is_file():
            raise FileNotFoundError(path)
        image = sitk.ReadImage(str(path))
    return _from_sitk(image, path.name)


def save_volume(volume, path):
    import SimpleITK as sitk
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(_to_sitk(volume), str(path), True)


# ============================================================================
# imaging / segmentation
# ============================================================================

"""Physical-coordinate segmentation loading and VTK surface extraction."""



import numpy as np




def load_mask(path, reference: Volume, *, label=None, resample=False):
    """Load a matching label image, or explicitly nearest-neighbour resample it."""
    mask = load_volume(path)
    if not mask.same_geometry(reference):
        if not resample:
            raise ValueError("Segmentation geometry does not match its CT. Supply an aligned mask or explicitly resample it.")
        import SimpleITK as sitk
        image = sitk.Resample(_to_sitk(mask), _to_sitk(reference), sitk.Transform(),
                              sitk.sitkNearestNeighbor, 0, sitk.sitkUInt16)
        mask = _from_sitk(image, mask.name)
    return np.asarray(mask.data == label if label is not None else mask.data > 0, dtype=bool)


def mesh_from_mask(mask, volume: Volume, *, smooth_iterations=8):
    """Extract a surface in LPS millimetres; no generated anatomy is substituted."""
    import pyvista as pv
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != volume.shape:
        raise ValueError("Mask array must match the reference volume's z,y,x shape.")
    if not np.any(mask):
        return pv.PolyData()
    # Padding closes structures touching an image boundary.
    padded = np.pad(mask, 1)
    grid = pv.ImageData(dimensions=padded.shape[::-1], spacing=volume.spacing,
                        origin=-np.asarray(volume.spacing))
    grid.point_data["structure"] = padded.astype(np.uint8).ravel(order="C")
    mesh = grid.contour([0.5], scalars="structure").triangulate()
    if smooth_iterations:
        mesh = mesh.smooth(n_iter=int(smooth_iterations), relaxation_factor=0.08)
    mesh.points = mesh.points @ volume.direction.T + np.asarray(volume.origin)
    return mesh


# ============================================================================
# simulation / virtual_patient
# ============================================================================

from dataclasses import dataclass
from numbers import Integral

import numpy as np


@dataclass(frozen=True)
class VirtualPatient:
    seed: int = 0
    amplitude: float = 12.0
    frequency: float = 0.25
    irregularity: float = 0.1
    target_radius: float = 6.0
    noise: float = 0.5
    delay: float = 1.0
    insertion_speed: float = 60.0

    def __post_init__(self):
        if not isinstance(self.seed, Integral) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("Patient seed must be a nonnegative integer")
        values = [self.amplitude, self.frequency, self.irregularity, self.target_radius,
                  self.noise, self.delay, self.insertion_speed]
        if not np.all(np.isfinite(values)):
            raise ValueError("Virtual-patient parameters must be finite")
        if self.amplitude < 0 or self.noise < 0 or self.delay < 0:
            raise ValueError("Amplitude, measurement noise and delay must be nonnegative")
        if self.frequency <= 0 or self.target_radius <= 0 or self.insertion_speed <= 0:
            raise ValueError("Frequency, target radius and insertion speed must be positive")
        if not 0 <= self.irregularity <= 1:
            raise ValueError("Irregularity must be between zero and one")


# ============================================================================
# simulation / respiratory
# ============================================================================

"""Seeded respiratory motion with immutable history and smooth parameter edits."""
from dataclasses import dataclass

import numpy as np


def _times(values):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("Simulation times must be finite and nonnegative")
    return values


def _blend(time, start, duration):
    u = np.clip((time - start) / duration, 0., 1.)
    weight = u**3 * (10 - 15*u + 6*u**2)
    derivative = 30*u**2 * (1-u)**2 / duration
    return weight, derivative


class _Profile:
    """One fixed parameter set; its closed-form trace never changes."""
    def __init__(self, patient):
        self.patient = patient
        rng = np.random.default_rng(patient.seed)
        self.phase0 = rng.uniform(0, 2*np.pi)
        self.modulation_phase = rng.uniform(0, 2*np.pi)
        self.random_phases = rng.uniform(0, 2*np.pi, 3)
        self.random_coefficients = rng.normal(0, .025, 3)
        self.random_frequencies = np.array([.19, .61, 1.07])

    @staticmethod
    def _step_integral(time, center, width):
        logcosh = lambda x: np.logaddexp(x, -x) - np.log(2.)
        return .5*(time + width*(logcosh((time-center)/width)-logcosh(-center/width)))

    def frequency_integral(self, time):
        p = self.patient
        modulation = p.irregularity * .32
        integral = time + modulation*(np.cos(self.modulation_phase)-np.cos(.35*time+self.modulation_phase))/.35
        for coefficient, frequency, offset in zip(self.random_coefficients, self.random_frequencies, self.random_phases):
            integral += p.irregularity*coefficient*(np.cos(offset)-np.cos(frequency*time+offset))/frequency
        if p.irregularity >= .95:
            integral += .35*self._step_integral(time, 14., .35)-.20*self._step_integral(time, 22., .4)
        return p.frequency*integral

    def frequency(self, time):
        p = self.patient
        factor = 1+p.irregularity*.32*np.sin(.35*time+self.modulation_phase)
        for coefficient, frequency, offset in zip(self.random_coefficients, self.random_frequencies, self.random_phases):
            factor += p.irregularity*coefficient*np.sin(frequency*time+offset)
        if p.irregularity >= .95:
            factor += .35*.5*(1+np.tanh((time-14)/.35))-.20*.5*(1+np.tanh((time-22)/.4))
        return p.frequency*factor

    def amplitude(self, time):
        p = self.patient
        factor = 1+p.irregularity*.22*np.sin(.21*time)
        factor += p.irregularity*.08*np.sin(.51*time+self.random_phases[0])
        if p.irregularity >= .95:
            factor += .3*.5*(1+np.tanh((time-16)/.4))
        return p.amplitude*factor

    def amplitude_derivative(self, time):
        p = self.patient
        result = p.amplitude*p.irregularity*.22*.21*np.cos(.21*time)
        result += p.amplitude*p.irregularity*.08*.51*np.cos(.51*time+self.random_phases[0])
        if p.irregularity >= .95:
            result += p.amplitude*.3*.5/.4*(1-np.tanh((time-16)/.4)**2)
        return result


@dataclass(frozen=True)
class _Change:
    time: float
    duration: float
    profile: _Profile
    phase_at_start: float


class RespiratoryModel:
    def __init__(self, patient, integration_step=None):
        if integration_step is not None and (not np.isfinite(integration_step) or integration_step <= 0):
            raise ValueError("Integration step must be finite and positive")
        self.patient = patient
        self.integration_step = integration_step
        self._initial = _Profile(patient)
        self.phase0 = self._initial.phase0
        self.direction = np.array([.18, .30, 1.])
        self._changes = []
        self._integration_cache = {}
        self._nodes, self._weights = np.polynomial.legendre.leggauss(32)

    @property
    def last_change_time(self):
        return self._changes[-1].time if self._changes else 0.

    def _frequency(self, time, count):
        result = self._initial.frequency(time)
        for change in self._changes[:count]:
            weight, _ = _blend(time, change.time, change.duration)
            result = (1-weight)*result + weight*change.profile.frequency(time)
        return result

    def frequency(self, time):
        return self._frequency(_times(time), len(self._changes))

    def _integral(self, start, ends, function, key):
        if ends.size == 0:
            return np.empty_like(ends)
        if self.integration_step is None:
            # Integrate only the short transition numerically; unchanged
            # intervals retain the original closed-form frequency integral.
            half = (ends-start)/2
            samples = start+half[..., None]*(self._nodes+1)
            return half*np.sum(function(samples)*self._weights, axis=-1)
        step = self.integration_step
        end = float(np.max(ends))
        cached = self._integration_cache.get(key)
        if cached is None or cached[0][-1] < end:
            count = max(1, int(np.ceil((end-start)/step)))
            grid = start+np.arange(count+1)*step
            frequency = function(grid)
            values = np.r_[0., np.cumsum((frequency[:-1]+frequency[1:])*.5*step)]
            cached = self._integration_cache[key] = (grid, values)
        return np.interp(ends, *cached)

    def _profile_integral(self, profile, start, ends, key):
        if self.integration_step is None:
            return profile.frequency_integral(ends)-profile.frequency_integral(np.asarray(start))
        return self._integral(start, ends, profile.frequency, key)

    def phase(self, time):
        t = _times(time)
        result = self.phase0+2*np.pi*self._profile_integral(self._initial, 0., t, ("initial",))
        for index, change in enumerate(self._changes):
            end = change.time+change.duration
            transition_time = np.clip(t, change.time, end)
            transition = self._integral(change.time, transition_time,
                lambda samples, count=index+1: self._frequency(samples, count), ("transition", index))
            tail_time = np.maximum(t, end)
            tail = self._profile_integral(change.profile, end, tail_time, ("tail", index))
            updated = change.phase_at_start+2*np.pi*(transition+tail)
            result = np.where(t >= change.time, updated, result)
        return result

    def _amplitude_and_derivative(self, time):
        value = self._initial.amplitude(time)
        derivative = self._initial.amplitude_derivative(time)
        for change in self._changes:
            weight, weight_derivative = _blend(time, change.time, change.duration)
            target = change.profile.amplitude(time)
            derivative = ((1-weight)*derivative + weight*change.profile.amplitude_derivative(time)
                          + weight_derivative*(target-value))
            value = (1-weight)*value+weight*target
        return value, derivative

    def amplitude(self, time):
        return self._amplitude_and_derivative(_times(time))[0]

    def _irregularity_and_derivative(self, time):
        value = np.full_like(time, self._initial.patient.irregularity)
        derivative = np.zeros_like(time)
        for change in self._changes:
            weight, weight_derivative = _blend(time, change.time, change.duration)
            target = change.profile.patient.irregularity
            derivative = (1-weight)*derivative+weight_derivative*(target-value)
            value = (1-weight)*value+weight*target
        return value, derivative

    def displacement(self, time):
        t = _times(time)
        phase = self.phase(t)
        irregularity, _ = self._irregularity_and_derivative(t)
        amount = self.amplitude(t)*(np.sin(phase)+.12*irregularity*np.sin(2*phase))
        return amount[..., None]*self.direction

    def velocity(self, time):
        t = _times(time)
        phase = self.phase(t)
        amplitude, amplitude_derivative = self._amplitude_and_derivative(t)
        irregularity, irregularity_derivative = self._irregularity_and_derivative(t)
        shape = np.sin(phase)+.12*irregularity*np.sin(2*phase)
        derivative = amplitude_derivative*shape+amplitude*(
            2*np.pi*self.frequency(t)*(np.cos(phase)+.24*irregularity*np.cos(2*phase))
            +.12*irregularity_derivative*np.sin(2*phase))
        return derivative[..., None]*self.direction

    def acceleration(self, time, step=1e-3):
        t = _times(time)
        if not np.isfinite(step) or step <= 0:
            raise ValueError("Derivative step must be finite and positive")
        lower = np.maximum(0., t-step)
        return (self.velocity(t+step)-self.velocity(lower))/(t+step-lower)[..., None]

    def change_patient(self, patient, time, transition_duration=1.):
        instant = float(_times(time))
        duration = float(transition_duration)
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError("Transition duration must be finite and positive")
        if self._changes and instant < self.last_change_time:
            raise ValueError("Past parameter changes cannot be rewritten; reset the scenario to edit earlier times")
        phase = float(self.phase(instant))
        self._changes.append(_Change(instant, duration, _Profile(patient), phase))
        self.patient = patient

    def observe(self, times, origin):
        times = _times(times)
        origin = np.asarray(origin, dtype=float)
        if times.ndim != 1 or origin.shape != (3,) or not np.all(np.isfinite(origin)):
            raise ValueError("Observations require a 1D time array and a finite xyz origin")
        patients = [self._initial.patient]*len(times)
        for change in self._changes:
            for index in np.flatnonzero(times > change.time):
                patients[index] = change.profile.patient
        noise = np.array([np.random.default_rng(np.random.SeedSequence(
            [patient.seed, int(round(t*1e6))])).normal(0, patient.noise, 3)
            for t, patient in zip(times, patients)]).reshape(-1, 3)
        return origin+self.displacement(times)+noise


# ============================================================================
# planning / geometry
# ============================================================================

"""Geometry uses finite segments and millimetres throughout."""
import numpy as np


def _xyz(values, name="Points"):
    values = np.asarray(values, dtype=float)
    if values.shape[-1:] != (3,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain finite xyz coordinates")
    return values


def _vector(values, name="Position"):
    values = _xyz(values, name)
    if values.shape != (3,):
        raise ValueError(f"{name} must be one xyz vector")
    return values


def _radius(value, name="Radius"):
    value = float(value)
    if not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def unit(vector):
    vector = _vector(vector, "Direction")
    length = np.linalg.norm(vector)
    if length < 1e-12:
        raise ValueError("Cannot normalise a zero vector")
    return vector / length


def project_segment(point, start, end):
    point, start, end = map(_vector, (point, start, end))
    delta = end - start
    denominator = np.dot(delta, delta)
    fraction = 0.0 if denominator < 1e-12 else np.clip(np.dot(point - start, delta) / denominator, 0, 1)
    return start + fraction * delta, float(fraction)


def point_segment_distance(point, start, end):
    closest, _ = project_segment(point, start, end)
    return float(np.linalg.norm(np.asarray(point) - closest))


def segment_sphere_intersection(start, end, center, radius):
    radius = _radius(radius)
    return point_segment_distance(center, start, end) <= radius


def segment_distance(p0, p1, q0, q1):
    """Closest distance between closed 3D segments, including parallel cases."""
    return float(segment_distances(p0, p1, q0, q1))


def point_segment_distances(points, starts, ends):
    """Broadcastable distances from xyz points to closed xyz segments."""
    points, starts, ends = np.broadcast_arrays(*[_xyz(item)
                                                for item in (points, starts, ends)])
    delta = ends - starts
    squared_length = np.sum(delta * delta, axis=-1)
    fraction = np.clip(np.sum((points - starts) * delta, axis=-1)
                       / np.where(squared_length > 0, squared_length, 1), 0, 1)
    return np.linalg.norm(points - starts - fraction[..., None] * delta, axis=-1)


def segment_distances(p0, p1, q0, q1):
    """Broadcastable exact finite-segment distances, including zero lengths.

    A constrained minimum occurs at one of the four endpoint projections or
    at the interior stationary point. Cross products avoid cancellation of
    a*c-b*b for almost parallel segments.
    """
    p0, p1, q0, q1 = np.broadcast_arrays(*[_xyz(item)
                                         for item in (p0, p1, q0, q1)])
    u, v, w = p1 - p0, q1 - q0, q0 - p0
    best = np.minimum.reduce([point_segment_distances(p0, q0, q1),
                              point_segment_distances(p1, q0, q1),
                              point_segment_distances(q0, p0, p1),
                              point_segment_distances(q1, p0, p1)])
    cross = np.cross(u, v)
    denominator = np.sum(cross * cross, axis=-1)
    safe = np.where(denominator > np.finfo(float).tiny, denominator, 1)
    s = np.sum(np.cross(w, v) * cross, axis=-1) / safe
    t = np.sum(np.cross(w, u) * cross, axis=-1) / safe
    interior = (denominator > np.finfo(float).tiny) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
    distance = np.linalg.norm(-w + s[..., None] * u - t[..., None] * v, axis=-1)
    return np.minimum(best, np.where(interior, distance, np.inf))


def capsule_clearance(start, end, segments, radii, needle_radius=0.8):
    return float(capsule_clearances(start, end, segments, radii, needle_radius))


def capsule_clearances(starts, ends, segments, radii, needle_radius=0.8, chunk_size=48):
    """Minimum capsule clearance for broadcastable candidate paths.

    Chunking bounds temporary arrays when there are many entry candidates.
    Obstacle centre lines remain finite segments, not infinite lines.
    """
    starts, ends = np.broadcast_arrays(_xyz(starts), _xyz(ends))
    segments, radii = np.asarray(segments, dtype=float), np.asarray(radii, dtype=float)
    needle_radius = _radius(needle_radius, "Needle radius")
    if segments.size == 0:
        segments = segments.reshape(0, 2, 3)
    if (radii.ndim != 1 or segments.shape != (len(radii), 2, 3)
            or not np.all(np.isfinite(segments))
            or not np.all(np.isfinite(radii)) or np.any(radii < 0)):
        raise ValueError("Obstacles require matching finite (n,2,3) segments and nonnegative radii")
    shape = starts.shape[:-1]
    if len(segments) == 0:
        return np.full(shape, np.inf)
    first, last = starts.reshape(-1, 3), ends.reshape(-1, 3)
    clearances = np.empty(len(first))
    midpoints = segments.mean(axis=1)
    half_lengths = np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1) / 2
    for offset in range(0, len(first), max(1, int(chunk_size))):
        stop = offset + max(1, int(chunk_size))
        begin, finish = first[offset:stop], last[offset:stop]
        midpoint_distances = point_segment_distances(midpoints[None], begin[:, None], finish[:, None])
        upper_bound = np.min(midpoint_distances - radii[None] - needle_radius, axis=1)
        lower_bounds = midpoint_distances - half_lengths[None] - radii[None] - needle_radius
        # Triangle-inequality bounds discard distant rib tubes without changing
        # the exact minimum. Midpoints supply a valid feasible upper bound.
        row, obstacle = np.nonzero(lower_bounds <= upper_bound[:, None] + 1e-10)
        distances = segment_distances(begin[row], finish[row], segments[obstacle, 0], segments[obstacle, 1])
        np.minimum.at(upper_bound, row, distances - radii[obstacle] - needle_radius)
        clearances[offset:stop] = upper_bound
    return clearances.reshape(shape)


def sampled_capsule_clearance(points, segments, radii, needle_radius=0.8):
    """Sampled point-to-capsule clearance, for spatial-convergence diagnostics."""
    points = _xyz(points)
    if points.ndim != 2 or not len(points):
        raise ValueError("Clearance sampling requires a nonempty n-by-3 array")
    segments, radii = np.asarray(segments, dtype=float), np.asarray(radii, dtype=float)
    needle_radius = _radius(needle_radius, "Needle radius")
    if segments.size == 0:
        segments = segments.reshape(0, 2, 3)
    if (radii.ndim != 1 or segments.shape != (len(radii), 2, 3)
            or not np.all(np.isfinite(segments)) or not np.all(np.isfinite(radii))
            or np.any(radii < 0)):
        raise ValueError("Obstacles require matching finite (n,2,3) segments and nonnegative radii")
    if len(segments) == 0:
        return float("inf")
    distances = point_segment_distances(points[:, None], segments[None, :, 0], segments[None, :, 1])
    return float(np.min(distances - np.asarray(radii)[None] - needle_radius))


def ellipsoid_surface(point, center, radii, tolerance=0.08):
    point, center, radii = map(_vector, (point, center, radii))
    if np.any(radii <= 0) or not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Ellipsoid radii must be positive and tolerance nonnegative")
    return abs(float(np.sum(((point - center) / radii) ** 2)) - 1) <= tolerance


def segment_ellipsoid_intersections(start, end, center, radii):
    """Ordered physical boundary hits on a finite axis-aligned ellipsoid segment."""
    start, end, center, radii = map(_vector, (start, end, center, radii))
    if np.any(radii <= 0):
        raise ValueError("Ellipsoid radii must be positive")
    offset, direction = (start - center) / radii, (end - start) / radii
    a = float(direction @ direction)
    if a == 0:
        return start[None].copy() if ellipsoid_surface(start, center, radii, 1e-12) else np.empty((0, 3))
    b, c = float(2 * offset @ direction), float(offset @ offset - 1)
    discriminant = b * b - 4 * a * c
    tolerance = 1e-12 * max(1.0, b * b, abs(4 * a * c))
    if discriminant < -tolerance:
        return np.empty((0, 3))
    root = np.sqrt(max(0.0, discriminant))
    # Avoid cancellation when one boundary hit lies close to the segment start.
    q = -.5 * (b + np.copysign(root, b))
    fractions = np.array([-b / (2 * a)]) if q == 0 else np.array([q / a, c / q])
    fractions = fractions[(fractions >= -1e-12) & (fractions <= 1 + 1e-12)]
    fractions = np.unique(np.clip(fractions, 0, 1))
    return start + fractions[:, None] * (end - start)


def rotation_matrix(axis, angle):
    angle = float(angle)
    if not np.isfinite(angle):
        raise ValueError("Rotation angle must be finite")
    x, y, z = unit(axis)
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew


def transform_points(points, matrix):
    points = _xyz(points)
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("A homogeneous transform must be a finite 4-by-4 matrix")
    homogeneous = np.concatenate([points, np.ones((*points.shape[:-1], 1))], axis=-1)
    transformed = homogeneous @ matrix.T
    if np.any(np.abs(transformed[..., 3]) < 1e-12):
        raise ValueError("Transform maps a point to infinity")
    return transformed[..., :3] / transformed[..., 3:4]


# ============================================================================
# simulation / anatomy
# ============================================================================

"""Reproducible synthetic thorax built from one physical-coordinate model.

The intensity image, segmentation surfaces and planning obstacles share the
same rasterised tubes and organ masks. This is anatomical inspiration rather
than patient-derived physiology.
"""



from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates




def _depth_factor(z):
    t = np.clip((155.0 - np.asarray(z)) / 300.0, 0.0, 1.0)
    return 0.3 + 0.7 * t * t * (3.0 - 2.0 * t)


@dataclass
class Anatomy:
    volume: Volume
    masks: dict[str, np.ndarray]
    target: np.ndarray
    target_radius: float
    entry_candidates: np.ndarray
    obstacle_segments: np.ndarray
    obstacle_radii: np.ndarray
    body_center: np.ndarray
    body_radii: np.ndarray
    obstacle_labels: np.ndarray
    segment_groups: dict[str, np.ndarray]
    seed: int = 0
    _fixed_ct: np.ndarray = field(repr=False, default=None)
    _cache_key: tuple | None = field(repr=False, default=None)
    _cache_coordinates: list | None = field(repr=False, default=None)
    _cache_volume: Volume | None = field(repr=False, default=None)
    _cache_masks: dict | None = field(repr=False, default=None)

    def deform_points(self, points, displacement_xyz):
        """Depth-dependent deformation, normalised at the reference target.

        displacement_xyz is the target's physical displacement in millimetres.
        Body/rib points should be retained unchanged by the caller.
        """
        points = np.asarray(points, dtype=float)
        if points.shape[-1:] != (3,) or not np.all(np.isfinite(points)):
            raise ValueError("Deformation points must be finite xyz positions.")
        displacement = self._displacement(displacement_xyz)
        factor = _depth_factor(points[..., 2]) / _depth_factor(self.target[2])
        return points + factor[..., None] * displacement

    def obstacles_at(self, displacement_xyz):
        segments = self.obstacle_segments.copy()
        moving = self.obstacle_labels != "ribs"
        segments[moving] = self.deform_points(segments[moving], displacement_xyz)
        return segments, self.obstacle_radii.copy()

    @staticmethod
    def _displacement(displacement_xyz):
        displacement = np.asarray(displacement_xyz, dtype=float)
        if displacement.shape != (3,) or not np.all(np.isfinite(displacement)):
            raise ValueError("Displacement must be a finite xyz vector.")
        if np.linalg.norm(displacement) > 80:
            raise ValueError("Synthetic target displacement is limited to 80 mm.")
        return displacement

    def _inverse_coordinates(self, displacement_xyz):
        # The forward field must remain monotone for inverse image resampling.
        displacement = self._displacement(displacement_xyz)
        key = tuple(displacement)
        if key == self._cache_key:
            return self._cache_coordinates
        self._cache_key = key
        self._cache_volume = None
        self._cache_masks = None
        zz = np.arange(self.volume.shape[0], dtype=np.float32)[:, None, None]
        yy = np.arange(self.volume.shape[1], dtype=np.float32)[None, :, None]
        xx = np.arange(self.volume.shape[2], dtype=np.float32)[None, None, :]
        sx, sy, sz = self.volume.spacing
        ox, oy, oz = self.volume.origin
        world_z = zz * sz + oz
        source_z = world_z.copy()
        normalisation = float(_depth_factor(self.target[2]))
        for _ in range(4):
            t = np.clip((155 - source_z) / 300, 0, 1)
            factor = _depth_factor(source_z) / normalisation
            derivative = -0.7 * 6 * t * (1 - t) / (300 * normalisation)
            source_z -= (source_z + displacement[2] * factor - world_z) / (1 + displacement[2] * derivative)
        factor = _depth_factor(source_z) / normalisation
        self._cache_coordinates = list(np.broadcast_arrays(
            ((source_z - oz) / sz).astype(np.float32),
            (yy - displacement[1] * factor / sy).astype(np.float32),
            (xx - displacement[0] * factor / sx).astype(np.float32)))
        return self._cache_coordinates

    def masks_at(self, displacement_xyz):
        coordinates = self._inverse_coordinates(displacement_xyz)
        if self._cache_masks is None:
            self._cache_masks = {
                name: (mask if name in ("body", "ribs") else
                       map_coordinates(mask.astype(np.uint8), coordinates, order=0,
                                       mode="constant", cval=0, prefilter=False).astype(bool))
                for name, mask in self.masks.items()
            }
        return self._cache_masks

    def volume_at(self, displacement_xyz):
        coordinates = self._inverse_coordinates(displacement_xyz)
        if self._cache_volume is None:
            source_moving = np.logical_or.reduce([mask for name, mask in self.masks.items()
                                                 if name not in ("body", "ribs")])
            moving = map_coordinates(source_moving.astype(np.uint8), coordinates, order=0,
                                     mode="constant", cval=0, prefilter=False).astype(bool)
            warped = map_coordinates(self.volume.data, coordinates, order=1,
                                     mode="constant", cval=-1000.0, prefilter=False)
            data = self._fixed_ct.copy()
            data[moving] = warped[moving]
            # The chest wall and ribs belong to the fixed reference frame.
            data[self.masks["ribs"]] = self.volume.data[self.masks["ribs"]]
            self._cache_volume = Volume(data, self.volume.spacing, self.volume.origin,
                                        self.volume.direction, "Synthetic CT — respiratory deformation")
        return self._cache_volume


def _tube_mask(segments, radii, shape, spacing, origin):
    mask = np.zeros(shape, dtype=bool)
    spacing = np.asarray(spacing, dtype=float)
    origin = np.asarray(origin, dtype=float)
    size = np.asarray(shape[::-1])
    for (start, end), radius in zip(segments, radii):
        lower = np.maximum(0, np.floor((np.minimum(start, end) - radius - origin) / spacing).astype(int))
        upper = np.minimum(size - 1, np.ceil((np.maximum(start, end) + radius - origin) / spacing).astype(int))
        if np.any(lower > upper):
            continue
        zz, yy, xx = np.meshgrid(np.arange(lower[2], upper[2] + 1),
                                 np.arange(lower[1], upper[1] + 1),
                                 np.arange(lower[0], upper[0] + 1), indexing="ij")
        points = np.stack((xx, yy, zz), axis=-1) * spacing + origin
        delta = end - start
        fraction = np.clip(np.sum((points - start) * delta, axis=-1) / max(delta @ delta, 1e-12), 0, 1)
        distance2 = np.sum((points - start - fraction[..., None] * delta) ** 2, axis=-1)
        region = (slice(lower[2], upper[2] + 1), slice(lower[1], upper[1] + 1), slice(lower[0], upper[0] + 1))
        mask[region] |= distance2 <= radius ** 2
    return mask


def _airway_tree(rng):
    segments = []
    radii = []

    def add(start, end, radius):
        segments.append([start, end])
        radii.append(radius)

    add([0, -8, 150], [0, -8, 68], 7.2)
    for side in (-1, 1):
        carina = np.array([0, -8, 68], dtype=float)
        root = np.array([side * 36, -2, 48], dtype=float)
        add(carina, root, 5.6)
        lobes = [(side * 59, 0, 100), (side * 66, 8, 23), (side * 57, 10, -54)]
        for lobe_index, lobe in enumerate(lobes):
            lobe = np.asarray(lobe, dtype=float)
            add(root, lobe, 4.0)
            for branch in (-1, 1):
                tip = lobe + [side * 14, branch * 27, (-20 if lobe_index == 2 else -13)]
                tip += rng.normal(0, 2, 3)
                add(lobe, tip, 3.1)
                for twig in (-1, 1):
                    end = tip + [side * 8, twig * 14, -22 if lobe_index == 2 else 11]
                    add(tip, end, 2.6)
    return np.asarray(segments, dtype=float), np.asarray(radii)


def _ribs(body_radii):
    segments, radii = [], []
    for z in np.linspace(-112, 120, 11):
        scale = np.sqrt(max(0.28, 1 - (z / (body_radii[2] * 1.12)) ** 2))
        for side in (-1, 1):
            angles = np.linspace(0.10, np.pi - 0.26, 32)
            curve = np.stack((side * (body_radii[0] - 12) * scale * np.sin(angles),
                              (body_radii[1] - 11) * scale * np.cos(angles),
                              z - 12 * np.sin(angles)), axis=-1)
            segments.extend(np.stack((curve[:-1], curve[1:]), axis=1))
            radii.extend(np.full(len(curve) - 1, 3.8))
    # A bony posterior spinal column is included in the same obstacle group.
    for z in np.linspace(-140, 135, 18):
        segments.append([[0, 70, z - 5], [0, 70, z + 5]])
        radii.append(8.0)
    return np.asarray(segments), np.asarray(radii)


def _segment_clearance(point, segments, radii):
    delta = segments[:, 1] - segments[:, 0]
    t = np.clip(np.sum((point - segments[:, 0]) * delta, axis=1)
                / np.maximum(np.sum(delta * delta, axis=1), 1e-12), 0, 1)
    return np.min(np.linalg.norm(point - segments[:, 0] - t[:, None] * delta, axis=1) - radii)


def generate_anatomy(seed=0, target_radius=6.0, spacing=4.0, *, reference_target=None):
    """Generate one reproducible synthetic patient, with spacing in millimetres.

    ``reference_target`` keeps an existing scenario's physical lesion centre
    when rendering a finer source CT. The usual seeded target choice is still
    computed first, preserving the default generation sequence. It does not
    alter airway, rib, vessel or body primitives. This remains a newly sampled
    synthetic image, rather than an upsampled or patient-derived scan.
    """
    if not 2.0 <= float(spacing) <= 8.0:
        raise ValueError("Synthetic image spacing must be between 2 and 8 mm.")
    if not 2.0 <= float(target_radius) <= 20.0:
        raise ValueError("Synthetic target radius must be between 2 and 20 mm.")
    if reference_target is not None:
        reference_target = np.asarray(reference_target, dtype=float)
        if reference_target.shape != (3,) or not np.all(np.isfinite(reference_target)):
            raise ValueError("Reference target must be a finite xyz centre in millimetres.")
        reference_target = reference_target.copy()
    rng = np.random.default_rng(seed)
    spacing = float(spacing)
    target_radius = float(target_radius)
    body_radii = np.array([155.0, 108.0, 177.0]) * rng.uniform(0.97, 1.03, 3)
    origin = tuple(-np.ceil((body_radii + 12) / spacing) * spacing)
    dimensions = (2 * np.ceil((body_radii + 12) / spacing).astype(int) + 1)
    shape = tuple(dimensions[::-1])
    zz, yy, xx = np.indices(shape, dtype=np.float32)
    x, y, z = xx * spacing + origin[0], yy * spacing + origin[1], zz * spacing + origin[2]
    body = (x / body_radii[0]) ** 2 + (y / body_radii[1]) ** 2 + (z / body_radii[2]) ** 2 <= 1
    lungs = {}
    for name, side in (("right_lung", -1), ("left_lung", 1)):
        cx, cy, cz = side * 64.0, -3.0, 12.0
        radii = np.array([54.0, 75.0, 128.0]) * rng.uniform(0.97, 1.025, 3)
        q = ((x - cx) / radii[0]) ** 2 + ((y - cy) / radii[1]) ** 2 + ((z - cz) / radii[2]) ** 2
        perturbation = 0.035 * np.sin(z / 21) * np.cos(y / 24) + 0.02 * np.sin(x / 17 + y / 13)
        mask = (q <= 1 + perturbation) & body
        if side == 1:
            cardiac_notch = ((x - 23) / 39) ** 2 + ((y + 38) / 43) ** 2 + ((z + 32) / 55) ** 2 < 1
            mask &= ~cardiac_notch
        lungs[name] = mask
    airway_segments, airway_radii = _airway_tree(rng)
    vessel_segments = airway_segments[1:].copy()
    vessel_segments[:, :, 1] += 12.0
    vessel_segments[:, :, 0] += np.sign(vessel_segments[:, :, 0]) * 3.0
    vessel_radii = np.maximum(2.7, airway_radii[1:] * 0.78)
    rib_segments, rib_radii = _ribs(body_radii)
    obstacle_segments = np.concatenate((rib_segments, airway_segments, vessel_segments))
    obstacle_radii = np.concatenate((rib_radii, airway_radii + 1.8, vessel_radii))
    obstacle_labels = np.array(["ribs"] * len(rib_segments) + ["airways"] * len(airway_segments)
                               + ["vessels"] * len(vessel_segments))
    masks = {"body": body, **lungs,
             "ribs": _tube_mask(rib_segments, rib_radii, shape, (spacing,) * 3, origin) & body,
             "airways": _tube_mask(airway_segments, airway_radii + 1.8, shape, (spacing,) * 3, origin) & body,
             "vessels": _tube_mask(vessel_segments, vessel_radii, shape, (spacing,) * 3, origin) & body}
    # Locate the lesion inside peripheral lung and clear of the known obstacles.
    lung_depth = distance_transform_edt(lungs["right_lung"], sampling=(spacing,) * 3)
    interior = lung_depth > target_radius + spacing
    preferred = interior & (z > -80) & (z < -15) & (y > -45) & (y < 5) & (x < -55)
    candidate_voxels = np.argwhere(preferred if np.any(preferred) else interior)
    if not len(candidate_voxels):
        raise ValueError("The chosen target radius does not fit inside this synthetic lung.")
    selected = rng.choice(len(candidate_voxels), min(180, len(candidate_voxels)), replace=False)
    candidate_targets = candidate_voxels[selected, ::-1] * spacing + np.asarray(origin)
    clearance = np.array([_segment_clearance(point, obstacle_segments, obstacle_radii)
                          for point in candidate_targets])
    target = candidate_targets[np.argmax(clearance)]
    if reference_target is not None:
        target_index = (reference_target - np.asarray(origin)) / spacing
        centre_depth = float(map_coordinates(
            lung_depth, target_index[::-1, None], order=1,
            mode="constant", cval=0., prefilter=False)[0])
        # The distance transform measures voxel centres. Half a voxel is the
        # uncertainty of the binary boundary; an additional sphere/mask check
        # below prevents a represented lesion crossing the actual raster mask.
        if centre_depth < target_radius - spacing * .5:
            raise ValueError("Reference target sphere must fit inside the right lung.")
        target = reference_target
    masks["target"] = (x - target[0]) ** 2 + (y - target[1]) ** 2 + (z - target[2]) ** 2 <= target_radius ** 2
    if reference_target is not None and (not np.any(masks["target"])
                                         or np.any(masks["target"] & ~lungs["right_lung"])):
        raise ValueError("Reference target sphere must fit inside the right lung segmentation.")
    # HU-only appearance detail is generated after all masks, obstacles and
    # target selection. It cannot move the target or add an unmodelled vessel.
    # Texture describes unresolved tissue density, not patient-derived detail.
    noise = rng.normal(0, 1, shape).astype(np.float32)
    texture = gaussian_filter(noise, sigma=max(.35, 1.4 / spacing))
    texture /= max(float(np.std(texture[body])), 1e-6)
    coarse_texture = gaussian_filter(noise, sigma=max(.8, 7. / spacing))
    coarse_texture /= max(float(np.std(coarse_texture[body])), 1e-6)
    body_depth = distance_transform_edt(body, sampling=(spacing,) * 3)
    fixed_ct = np.full(shape, -1000.0, dtype=np.float32)
    fixed_ct[body] = 32 + 11 * texture[body] + 8 * coarse_texture[body]
    # Skin, subcutaneous fat and muscle have recognisable CT densities. These
    # intensity bands keep the exact pre-existing body and lung boundaries.
    subcutaneous_fat = body & (body_depth > 5.5) & (body_depth < 16.)
    chest_muscle = body & (body_depth >= 16.) & (body_depth < 34.)
    skin = body & (body_depth <= 5.5)
    fixed_ct[subcutaneous_fat] = -96 + 9 * texture[subcutaneous_fat]
    fixed_ct[chest_muscle] = 48 + 9 * texture[chest_muscle]
    fixed_ct[skin] = 38 + 8 * texture[skin]
    heart = ((x - 16) / 42) ** 2 + ((y + 31) / 44) ** 2 + ((z + 26) / 58) ** 2 <= 1
    fixed_ct[heart & body] = 52 + 6 * texture[heart & body] + 4 * coarse_texture[heart & body]
    fixed_ct[masks["ribs"]] = 870 + 75 * texture[masks["ribs"]]
    data = fixed_ct.copy()
    lung_mask = masks["left_lung"] | masks["right_lung"]
    dependent_density = 26 * np.clip((y + 25) / 95, 0, 1)
    lung_density = (-851 + 24 * texture + 14 * coarse_texture
                    + 17 * np.sin(z / 31) + dependent_density)
    data[lung_mask] = np.clip(lung_density[lung_mask], -965, -670)
    airway_lumen = _tube_mask(airway_segments, airway_radii, shape, (spacing,) * 3, origin)
    data[masks["airways"]] = 30
    data[airway_lumen & body] = -970
    data[masks["vessels"]] = 135 + 12 * texture[masks["vessels"]]
    data[masks["target"]] = 68 + 8 * texture[masks["target"]]
    data[masks["ribs"]] = fixed_ct[masks["ribs"]]
    angles = np.linspace(-np.pi, np.pi, 64, endpoint=False)
    entries = []
    for entry_z in target[2] + np.array([-32, -16, 0, 16, 32]):
        scale = np.sqrt(1 - (entry_z / body_radii[2]) ** 2)
        entries.extend(np.stack((body_radii[0] * scale * np.cos(angles),
                                 body_radii[1] * scale * np.sin(angles),
                                 np.full_like(angles, entry_z)), axis=-1))
    return Anatomy(Volume(data, (spacing,) * 3, origin, name="Synthetic CT — procedural thorax"),
                   masks, target, float(target_radius), np.asarray(entries), obstacle_segments,
                   obstacle_radii, np.zeros(3), body_radii, obstacle_labels,
                   {"ribs": rib_segments, "airways": airway_segments, "vessels": vessel_segments},
                   int(seed), fixed_ct)


# ============================================================================
# imaging / synthetic_slices
# ============================================================================

"""Sample displayed synthetic CT planes without materialising a warped volume."""

from dataclasses import replace
from itertools import product

import numpy as np
from scipy.ndimage import map_coordinates




class SyntheticSliceSource:
    """Evaluate the existing voxel deformation only at each plane's neighbours.

    Interpolation happens after the same moving-tissue/fixed-wall composition
    as Anatomy.volume_at, so display speed does not change the CT model.
    """

    def __init__(self, anatomy):
        self.anatomy = anatomy
        self.volume = anatomy.volume
        self.moving = np.logical_or.reduce([
            mask for name, mask in anatomy.masks.items() if name not in ("body", "ribs")])
        self._depth_key = None
        self._axis_aligned = np.array_equal(self.volume.direction, np.eye(3))

    def _depth_coordinates(self, displacement):
        key = tuple(displacement)
        if key != self._depth_key:
            spacing, origin = self.volume.spacing[2], self.volume.origin[2]
            world_z = np.arange(self.volume.shape[0], dtype=np.float32)*spacing+origin
            source_z = world_z.copy()
            normalisation = float(_depth_factor(self.anatomy.target[2]))
            for _ in range(4):
                t = np.clip((155-source_z)/300, 0, 1)
                factor = _depth_factor(source_z)/normalisation
                derivative = -.7*6*t*(1-t)/(300*normalisation)
                source_z -= (source_z+displacement[2]*factor-world_z)/(1+displacement[2]*derivative)
            self._inverse_z = (source_z-origin)/spacing
            self._depth_factors = _depth_factor(source_z)/normalisation
            self._depth_key = key
        return self._inverse_z, self._depth_factors

    def _source_indices(self, nodes, displacement):
        if self._axis_aligned:
            inverse_z, factors = self._depth_coordinates(displacement)
            factor = factors[nodes[..., 2]]
            indices = np.empty(nodes.shape, dtype=np.float32)
            indices[..., 0] = nodes[..., 0]-displacement[0]*factor/self.volume.spacing[0]
            indices[..., 1] = nodes[..., 1]-displacement[1]*factor/self.volume.spacing[1]
            indices[..., 2] = inverse_z[nodes[..., 2]]
            return indices
        world = self.volume.index_to_world(nodes).astype(np.float32)
        source_z = world[..., 2].copy()
        normalisation = float(_depth_factor(self.anatomy.target[2]))
        for _ in range(4):
            t = np.clip((155-source_z)/300, 0, 1)
            factor = _depth_factor(source_z)/normalisation
            derivative = -.7*6*t*(1-t)/(300*normalisation)
            source_z -= (source_z+displacement[2]*factor-world[..., 2])/(1+displacement[2]*derivative)
        factor = _depth_factor(source_z)/normalisation
        source = world.copy()
        source[..., :2] -= factor[..., None]*displacement[:2]
        source[..., 2] = source_z
        return self.volume.world_to_index(source)

    @staticmethod
    def _sample(array, indices, order, cval):
        return map_coordinates(array, [indices[..., 2], indices[..., 1], indices[..., 0]],
                               order=order, output=np.float32, mode="constant",
                               cval=cval, prefilter=False)

    def _ct_nodes(self, nodes, displacement):
        address = tuple(nodes[..., ::-1].T)
        if not np.any(displacement):
            return self.volume.data[address]
        source = self._source_indices(nodes, displacement)
        moving = self._sample(self.moving, source, 0, 0) > 0
        data = self.anatomy._fixed_ct[address].copy()
        if np.any(moving):
            data[moving] = self._sample(self.volume.data, source[moving], 1, -1000.)
        ribs = self.anatomy.masks["ribs"][address]
        data[ribs] = self.volume.data[address][ribs]
        return data

    def slice_plane(self, name, crosshair, displacement, *, max_pixels=384, overlays=False):
        displacement = self.anatomy._displacement(displacement)
        # This also supplies the standard physical grid and coordinate helpers.
        plane = self.volume.slice_grid(name, crosshair, max_pixels=max_pixels)
        rows, cols = plane.shape
        world = plane.world_grid()
        indices = self.volume.world_to_index(world).reshape(-1, 3)
        rounded = np.rint(indices)
        indices = np.where(np.abs(indices-rounded) < 1e-7, rounded, indices)
        size = np.asarray(self.volume.shape[::-1])
        valid = np.all((indices >= 0) & (indices <= size-1), axis=1)
        lower = np.floor(indices).astype(int)
        fraction = indices-lower
        image = np.zeros(len(indices), dtype=np.float64)
        # Native synthetic planes usually need only two corners per pixel.
        choices = [(0, 1) if np.any(fraction[:, axis] > 0) else (0,) for axis in range(3)]
        for offset in product(*choices):
            offset = np.asarray(offset)
            weight = np.prod(np.where(offset, fraction, 1-fraction), axis=1)
            selected = valid & (weight > 0)
            nodes = np.clip(lower[selected]+offset, 0, size-1)
            image[selected] += weight[selected]*self._ct_nodes(nodes, displacement)
        image[~valid] = -1000.
        plane = replace(plane, image=image.reshape(rows, cols).astype(np.float32))
        mask_planes = {}
        if overlays:
            nodes = np.clip(np.floor(indices+.5).astype(int), 0, size-1)
            address = tuple(nodes[..., ::-1].T)
            source = self._source_indices(nodes, displacement)
            for role, mask in self.anatomy.masks.items():
                if role == "body":
                    continue
                data = mask[address] if role == "ribs" else self._sample(mask, source, 0, 0) > 0
                data = np.asarray(data & valid, dtype=np.uint8).reshape(rows, cols)
                mask_planes[role] = replace(plane, image=data)
        return plane, mask_planes


# ============================================================================
# imaging / anatomy_display
# ============================================================================

"""CT-linked display surfaces; this module never changes planning anatomy.

The reference mask is the source of each organ boundary. Synthetic airway
lumens may use the exact centreline/radius that generated their CT, avoiding
the voxel-staircase and the 1.8 mm airway wall used for collision avoidance.
No extra vessels, fissures, target offsets or anatomical detail are invented.
"""



import numpy as np




def _bounded_surface(mesh, max_cells):
    if mesh.n_cells > max_cells:
        mesh = mesh.decimate(1.0 - max_cells / mesh.n_cells)
    return mesh


def attach_ct_scalars(mesh, volume, *, inset_mm=0.0):
    """Attach actual source HU and a subdued CT palette to an LPS surface.

    A small inward sampling offset can show parenchyma rather than mixing
    exterior air/chest wall at a segmented pleural boundary. Mesh positions
    stay unchanged, and the offset is recorded with the sampling metadata.
    """
    if not np.isfinite(inset_mm) or inset_mm < 0:
        raise ValueError("Surface CT sampling inset must be finite and nonnegative.")
    result = mesh.copy()
    if not result.n_points:
        return result
    points = result.points
    if inset_mm:
        result = result.compute_normals(point_normals=True, cell_normals=False,
                                        consistent_normals=True, auto_orient_normals=True)
        points = result.points - float(inset_mm) * result.point_data["Normals"]
    values = volume.sample_world(points)
    result.point_data["CT_HU"] = values.astype(np.float32)
    anchors = np.array([-1000., -900., -800., -600., -150., 100., 700.])
    palette = np.array([[14, 22, 23], [48, 72, 74], [94, 145, 149],
                        [141, 175, 171], [168, 187, 179], [195, 204, 191],
                        [234, 233, 215]], dtype=float)
    result.point_data["CT_RGB"] = np.column_stack([
        np.interp(values, anchors, palette[:, channel]) for channel in range(3)
    ]).astype(np.uint8)
    result.field_data["CT_sampling_inset_mm"] = np.array([inset_mm], dtype=float)
    result.field_data["source"] = np.array(["reference CT in physical LPS millimetres"])
    return result


def airway_lumen_mesh(anatomy, *, radial_resolution=14, max_cells=40000):
    """Smooth physical lumen tubes from the same primitives as the synthetic CT.

    The collision capsule includes the airway wall; the lumen radius removes
    exactly that wall. Imported CT has no such primitive model and should use
    its aligned segmentation instead.
    """
    import pyvista as pv

    if int(radial_resolution) != radial_resolution or not 6 <= radial_resolution <= 64:
        raise ValueError("Airway radial resolution must be an integer from 6 to 64.")
    selected = np.asarray(anatomy.obstacle_labels) == "airways"
    segments = np.asarray(anatomy.obstacle_segments)[selected]
    radii = np.asarray(anatomy.obstacle_radii)[selected] - 1.8
    if not len(segments):
        return pv.PolyData()
    if np.any(radii <= 0) or not np.all(np.isfinite(radii)):
        raise ValueError("Synthetic airway lumens must have positive finite radii.")
    parts = [pv.Line(start, end).tube(radius=float(radius),
                                    n_sides=int(radial_resolution), capping=True)
             for (start, end), radius in zip(segments, radii)]
    mesh = pv.merge(parts, merge_points=False).triangulate()
    mesh = _bounded_surface(mesh, max_cells)
    mesh.field_data["source"] = np.array(["exact synthetic CT lumen primitives"])
    return mesh


def prepare_display_meshes(volume, masks, *, anatomy=None, max_cells=40000):
    """Prepare bounded CT-linked surfaces without modifying volume or masks.

    Taubin smoothing removes voxel steps with limited volume shrinkage.
    It cannot turn a coarse synthetic segmentation into a patient-derived
    scan, and intentionally adds no unmodelled branches or fissures.
    """
    if isinstance(max_cells, bool) or int(max_cells) != max_cells or max_cells < 100:
        raise ValueError("Display surface cell limit must be an integer of at least 100.")
    result = {}
    for name, mask in masks.items():
        if name == "airways" and anatomy is not None:
            mesh = airway_lumen_mesh(anatomy, max_cells=max_cells)
        else:
            mesh = mesh_from_mask(mask, volume, smooth_iterations=0)
            if mesh.n_points and ("lung" in name or name == "body"):
                mesh = mesh.smooth_taubin(n_iter=24, pass_band=.08)
            elif mesh.n_points:
                mesh = mesh.smooth_taubin(n_iter=12, pass_band=.15)
            mesh = _bounded_surface(mesh, max_cells)
        if mesh.n_points:
            inset = min(volume.spacing) * .65 if "lung" in name else 0.
            result[name] = attach_ct_scalars(mesh, volume, inset_mm=inset)
    return result


def ct_cutface_mesh(volume, mask, origin, normal=(0., 1., 0.), *,
                    resolution_mm=2., max_cells=45000):
    """A textured physical cut face clipped to an aligned source segmentation.

    Samples source CT in an arbitrary LPS plane. The reference pose can be
    deformed with the same anatomy field as other display meshes. Cell
    selection samples the segmentation at each cell centre; there is no
    bounding-box fill outside the selected anatomy.
    """
    import pyvista as pv

    mask = np.asarray(mask, dtype=bool)
    origin, normal = np.asarray(origin, dtype=float), np.asarray(normal, dtype=float)
    if mask.shape != volume.shape:
        raise ValueError("Cut face mask must match the source volume.")
    if (origin.shape != (3,) or normal.shape != (3,)
            or not np.all(np.isfinite(origin)) or not np.all(np.isfinite(normal))
            or np.linalg.norm(normal) < 1e-12):
        raise ValueError("Cut face requires a finite physical origin and nonzero normal.")
    if not np.isfinite(resolution_mm) or resolution_mm <= 0:
        raise ValueError("Cut face resolution must be finite and positive.")
    if isinstance(max_cells, bool) or int(max_cells) != max_cells or max_cells < 4:
        raise ValueError("Cut face cell limit must be an integer of at least four.")
    normal = normal / np.linalg.norm(normal)
    axis = np.eye(3)[np.argmin(np.abs(normal))]
    u = np.cross(normal, axis)
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    corners = volume.index_to_world(np.array([
        [x, y, z] for x in (0, volume.shape[2] - 1)
        for y in (0, volume.shape[1] - 1) for z in (0, volume.shape[0] - 1)
    ]))
    projected = np.column_stack(((corners - origin) @ u, (corners - origin) @ v))
    lower, upper = projected.min(axis=0), projected.max(axis=0)
    counts = np.maximum(1, np.ceil((upper - lower) / resolution_mm).astype(int))
    if np.prod(counts) > max_cells:
        counts = np.maximum(1, np.floor(counts * np.sqrt(max_cells / np.prod(counts))).astype(int))
    nx, ny = map(int, counts)
    uu, vv = np.meshgrid(np.linspace(lower[0], upper[0], nx + 1),
                          np.linspace(lower[1], upper[1], ny + 1))
    points = origin + uu.ravel()[:, None] * u + vv.ravel()[:, None] * v
    row, col = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    a = (row * (nx + 1) + col).ravel()
    cells = np.column_stack((a, a + 1, a + nx + 2, a + nx + 1))
    centres = points[cells].mean(axis=1)
    indices = np.rint(volume.world_to_index(centres)).astype(int)
    inside = np.all((indices >= 0) & (indices < np.asarray(volume.shape[::-1])), axis=1)
    selected = np.zeros(len(cells), dtype=bool)
    valid = indices[inside]
    selected[inside] = mask[valid[:, 2], valid[:, 1], valid[:, 0]]
    if not np.any(selected):
        return pv.PolyData()
    cells = cells[selected]
    faces = np.column_stack((np.full(len(cells), 4), cells)).ravel()
    mesh = pv.PolyData(points, faces).clean()
    result = attach_ct_scalars(mesh, volume)
    result.field_data["source"] = np.array(["aligned source segmentation and CT cut plane"])
    return result


# ============================================================================
# imaging / phases
# ============================================================================

"""Ordered, on-demand respiratory phase loading with bounded caches."""



from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
import json

import numpy as np






@dataclass
class PhaseFrame:
    identifier: str
    volume: Volume
    masks: dict[str, np.ndarray] = field(default_factory=dict)
    target: np.ndarray | None = None
    landmarks: np.ndarray | None = None
    displacement_field: np.ndarray | None = None
    registered: bool = False

    def displace_points(self, points):
        """Apply a supplied reference-to-phase LPS displacement field.

        The field is sampled in physical coordinates. Points outside its grid
        are rejected, rather than silently assigned zero displacement.
        """
        if self.displacement_field is None:
            raise ValueError("This phase has no supplied deformation field.")
        from scipy.ndimage import map_coordinates
        points = np.asarray(points, dtype=float)
        indices = self.volume.world_to_index(points)
        limits = np.array(self.volume.shape[::-1]) - 1
        if np.any(indices < -1e-6) or np.any(indices > limits + 1e-6):
            raise ValueError("Point lies outside the supplied displacement-field grid.")
        indices = np.clip(indices, 0, limits)
        flat = indices.reshape(-1, 3)
        displacement = np.stack([map_coordinates(self.displacement_field[..., axis], flat[:, ::-1].T,
                                                order=1, mode="nearest", prefilter=False)
                                 for axis in range(3)], axis=-1).reshape(points.shape)
        return points + displacement


class PhaseSequence:
    """Manifest order is preserved, and frames are not assumed registered.

    JSON/YAML schema: {"coordinate_system":"LPS", "registered":false,
    "phases":[{"id":"0%", "volume":"ct0.mha", "masks":{"lungs":"lungs0.mha"},
    "target":[-60,0,-30], "landmarks":[[1,2,3]]}]}.
    Masks may be {"path":"labels.mha", "label":2}; target_mask is supported.
    An optional displacement_field is a 3D SimpleITK vector image of LPS mm,
    specifying reference-to-phase displacement. Backward fields require explicit
    conversion before import; no registration is estimated by this reader.
    Its grid must match that phase, and mapping is explicitly marked as supplied.
    """

    def __init__(self, phases, *, base_dir=".", cache_size=2, registered=False,
                 coordinate_system="LPS"):
        if not phases:
            raise ValueError("A phase sequence must contain at least one phase.")
        self.phases = [dict(phase) for phase in phases]
        self.base_dir = Path(base_dir)
        self.cache_size = max(1, int(cache_size))
        self.registered = bool(registered)
        self.coordinate_system = coordinate_system.upper()
        if self.coordinate_system not in ("LPS", "RAS"):
            raise ValueError("Manifest coordinates must explicitly be LPS or RAS.")
        self._cache = OrderedDict()
        self._mesh_cache = OrderedDict()
        identifiers = self.identifiers
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Phase identifiers must be unique.")
        for phase in self.phases:
            if "volume" not in phase:
                raise ValueError("Every phase requires a volume path.")

    @classmethod
    def from_manifest(cls, path, *, cache_size=2):
        path = Path(path)
        with path.open(encoding="utf-8") as stream:
            if path.suffix.lower() in (".yaml", ".yml"):
                import yaml
                manifest = yaml.safe_load(stream)
            else:
                manifest = json.load(stream)
        return cls(manifest["phases"], base_dir=path.parent, cache_size=cache_size,
                   registered=manifest.get("registered", False),
                   coordinate_system=manifest.get("coordinate_system", "LPS"))

    @property
    def phase_count(self):
        return len(self.phases)

    def __len__(self):
        return self.phase_count

    @property
    def identifiers(self):
        return [str(phase.get("id", index)) for index, phase in enumerate(self.phases)]

    def _path(self, path):
        return self.base_dir / Path(path)

    def _mask(self, specification, volume):
        if isinstance(specification, str):
            return load_mask(self._path(specification), volume)
        return load_mask(self._path(specification["path"]), volume,
                         label=specification.get("label"), resample=specification.get("resample", False))

    def get(self, index):
        index = int(index)
        if index < 0 or index >= len(self):
            raise IndexError("Respiratory phase index is outside the sequence.")
        if index in self._cache:
            self._cache.move_to_end(index)
            return self._cache[index]
        specification = self.phases[index]
        volume = load_volume(self._path(specification["volume"]))
        masks = {name: self._mask(mask, volume) for name, mask in specification.get("masks", {}).items()}
        target = specification.get("target")
        if target is not None:
            target = np.asarray(target, dtype=float)
            if target.shape != (3,) or not np.all(np.isfinite(target)):
                raise ValueError("Phase target must contain three finite physical coordinates.")
            if self.coordinate_system == "RAS":
                target = ras_to_lps(target)
        if "target_mask" in specification:
            masks["target"] = self._mask(specification["target_mask"], volume)
        if target is None and np.any(masks.get("target", False)):
            target = volume.index_to_world(np.argwhere(masks["target"]).mean(axis=0)[::-1])
        landmarks = specification.get("landmarks")
        if landmarks is not None:
            landmarks = np.asarray(landmarks, dtype=float)
            if landmarks.ndim != 2 or landmarks.shape[1] != 3 or not np.all(np.isfinite(landmarks)):
                raise ValueError("Landmarks must be a finite N-by-3 array of physical coordinates.")
            if self.coordinate_system == "RAS":
                landmarks = ras_to_lps(landmarks)
        if target is None and "target_landmark" in specification:
            if landmarks is None:
                raise ValueError("A target_landmark requires phase landmark annotations.")
            landmark_index = int(specification["target_landmark"])
            if not 0 <= landmark_index < len(landmarks):
                raise ValueError("target_landmark is outside the supplied landmark array.")
            target = landmarks[landmark_index].copy()
        field_data = None
        if "displacement_field" in specification:
            import SimpleITK as sitk
            image = sitk.ReadImage(str(self._path(specification["displacement_field"])))
            if specification.get("field_mapping", "reference_to_phase") != "reference_to_phase":
                raise ValueError("Only explicitly reference-to-phase displacement fields are supported.")
            if image.GetDimension() != 3 or image.GetNumberOfComponentsPerPixel() != 3:
                raise ValueError("A displacement field must be a 3D image with three physical components.")
            if (tuple(image.GetSize()) != volume.shape[::-1]
                    or not np.allclose(image.GetSpacing(), volume.spacing)
                    or not np.allclose(image.GetOrigin(), volume.origin)
                    or not np.allclose(np.array(image.GetDirection()).reshape(3, 3), volume.direction)):
                raise ValueError("Supplied displacement field must match the phase's physical image grid.")
            field_data = sitk.GetArrayFromImage(image)
        frame = PhaseFrame(self.identifiers[index], volume, masks, target, landmarks,
                           field_data, bool(specification.get("registered", self.registered)))
        self._cache[index] = frame
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        return frame

    def meshes(self, index):
        if index in self._mesh_cache:
            self._mesh_cache.move_to_end(index)
            return self._mesh_cache[index]
        frame = self.get(index)
        meshes = {name: mesh_from_mask(mask, frame.volume) for name, mask in frame.masks.items()}
        self._mesh_cache[index] = meshes
        while len(self._mesh_cache) > self.cache_size:
            self._mesh_cache.popitem(last=False)
        return meshes

    def target_at(self, index, *, reference_index=0):
        frame = self.get(index)
        if frame.target is not None:
            return frame.target.copy()
        reference = self.get(reference_index)
        if reference.target is not None and frame.displacement_field is not None:
            return frame.displace_points(reference.target)
        return None

    def motion_vectors(self, index, *, reference_index=0, max_vectors=300):
        """Return (reference xyz, displacement xyz), using supplied evidence only."""
        frame = self.get(index)
        reference = self.get(reference_index)
        if frame.landmarks is not None and reference.landmarks is not None:
            if frame.landmarks.shape != reference.landmarks.shape:
                raise ValueError("Corresponding landmark arrays must have matching shapes and order.")
            return reference.landmarks.copy(), frame.landmarks - reference.landmarks
        if frame.displacement_field is not None:
            step = max(1, int(np.ceil((np.prod(frame.volume.shape) / max(1, max_vectors)) ** (1 / 3))))
            indices = np.stack(np.meshgrid(*[np.arange(0, n, step) for n in frame.volume.shape[::-1]],
                                          indexing="ij"), axis=-1).reshape(-1, 3)[:max_vectors]
            points = frame.volume.index_to_world(indices)
            return points, frame.displace_points(points) - points
        return np.empty((0, 3)), np.empty((0, 3))

    def clear_cache(self):
        self._cache.clear()
        self._mesh_cache.clear()


# ============================================================================
# imaging / phase_analysis
# ============================================================================

"""Phase annotation summaries; no motion or registration is inferred from CT alone."""
from pathlib import Path
import csv
import json

import numpy as np


def analyse_phases(sequence, output_dir):
    destination=Path(output_dir)
    destination.mkdir(parents=True,exist_ok=True)
    rows=[]
    targets=[]
    registered=[]
    for index in range(len(sequence)):
        frame=sequence.get(index)
        target=sequence.target_at(index)
        targets.append(target)
        registered.append(frame.registered)
        rows.append(dict(phase=frame.identifier,target_source="annotation or supplied displacement field" if target is not None else "unavailable",
                         x_mm=None if target is None else float(target[0]),
                         y_mm=None if target is None else float(target[1]),
                         z_mm=None if target is None else float(target[2]),
                         registered=frame.registered))
    valid=[target for target in targets if target is not None]
    aligned=all(registered)
    summary=dict(phases=len(sequence),annotated_targets=len(valid),
                 coordinate_system="LPS millimetres",registered_by_manifest=aligned,
                 target_excursion_mm=None,peak_to_peak_xyz_mm=None,
                 csv=str((destination/"phase_targets.csv").resolve()),
                 limitation="Discrete supplied phases. No continuous deformation or respiratory timing is estimated. Registration declarations are supplied by the user and have not been independently validated.")
    if len(valid)>=2 and aligned:
        points=np.asarray(valid)
        summary["peak_to_peak_xyz_mm"]=(points.max(axis=0)-points.min(axis=0)).tolist()
        summary["target_excursion_mm"]=float(np.max(np.linalg.norm(points[:,None,:]-points[None,:,:],axis=-1)))
    elif len(valid)>=2:
        summary["limitation"]+=" Displacement metrics are withheld because the phases are not declared spatially registered."
    with (destination/"phase_targets.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (destination/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary


# ============================================================================
# imaging / public_sample
# ============================================================================

"""Optional static public CT example, with explicitly derived display masks."""



from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4

import numpy as np
from scipy import ndimage




SAMPLE_SHA256 = "4507b664690840abb6cb9af2d919377ffc4ef75b167cb6fd0f747befdb12e38e"
SAMPLE_URL = ("https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/"
              + SAMPLE_SHA256)
LICENSE_URL = "https://raw.githubusercontent.com/Slicer/Slicer/main/License.txt"
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 25
TOTAL_TIMEOUT_SECONDS = 180
DISPLAY_MASK_VERSION = "ct-threshold-display-v2"
LUNG_DETAIL_THRESHOLD_HU = -450
LUNG_DETAIL_LABEL = "High-density lung detail (derived)"


def _digest(path):
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cached_public_sample_available(cache_dir="data/public-example"):
    """Validate the optional local CT without downloading or creating files."""
    source = Path(cache_dir) / "CT-chest.nrrd"
    try:
        return (source.is_file() and 0 < source.stat().st_size <= MAX_DOWNLOAD_BYTES
                and _digest(source) == SAMPLE_SHA256)
    except OSError:
        return False


def _download_verified(url, destination, expected_digest, *, max_bytes=MAX_DOWNLOAD_BYTES,
                       socket_timeout=SOCKET_TIMEOUT_SECONDS,
                       total_timeout=TOTAL_TIMEOUT_SECONDS):
    """Stream a bounded HTTPS file and replace the destination only after hashing."""
    if not url.lower().startswith("https://"):
        raise ValueError("Public example downloads require HTTPS.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.{uuid4().hex}.part")
    started, received = monotonic(), 0
    digest = sha256()
    try:
        request = Request(url, headers={"User-Agent": "MotionTwin-public-CT-example/1.0"})
        with urlopen(request, timeout=socket_timeout) as response:
            if not response.geturl().lower().startswith("https://"):
                raise ValueError("Public example redirected outside HTTPS.")
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    declared = int(length)
                except ValueError as error:
                    raise ValueError("The public example server returned an invalid file size.") from error
                if declared < 0 or declared > max_bytes:
                    raise ValueError("The public example exceeds the download size limit.")
            with partial.open("xb") as target:
                while True:
                    if monotonic() - started > total_timeout:
                        raise TimeoutError("Public example download exceeded its time limit.")
                    chunk = response.read(min(1024 * 1024, max_bytes - received + 1))
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > max_bytes:
                        raise ValueError("The public example exceeds the download size limit.")
                    target.write(chunk)
                    digest.update(chunk)
            if length is not None and received != declared:
                raise ValueError("The public example download was incomplete.")
        if digest.hexdigest() != expected_digest:
            raise ValueError("Public example SHA-256 verification failed; the file was not installed.")
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return received


def _ellipsoid(radius_mm, spacing_zyx):
    """A small physical-radius morphology kernel on the unchanged source grid."""
    spacing = np.asarray(spacing_zyx, dtype=float)
    half = np.ceil(radius_mm / spacing).astype(int)
    coordinates = np.ogrid[tuple(slice(-extent, extent + 1) for extent in half)]
    distance = sum((coordinate * step) ** 2 for coordinate, step in zip(coordinates, spacing))
    return distance <= radius_mm ** 2 + 1e-8


def _largest_component(mask):
    labels, count = ndimage.label(mask)
    if not count:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def derive_display_masks(volume: Volume):
    """Lung envelopes and "High-density lung detail (derived)" on the CT grid.

    These are display structures, not expert annotations, automatic diagnoses,
    a validated vessel segmentation or obstacles for needle planning.
    """
    internal = np.zeros(volume.shape, dtype=bool)
    body_centres = []
    slice_structure = _ellipsoid(2., volume.spacing[1::-1])
    for index, section in enumerate(volume.data):
        if not np.all(np.isfinite(section)):
            raise ValueError("The public CT must contain finite intensities.")
        air = section < -450
        labels, count = ndimage.label(air)
        if count:
            border = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
            keep = np.ones(count + 1, dtype=bool)
            keep[border] = False
            keep[0] = False
            enclosed = keep[labels]
            enclosed = ndimage.binary_closing(enclosed, structure=slice_structure)
            internal[index] = ndimage.binary_fill_holes(enclosed)
        tissue_labels, tissue_count = ndimage.label(section > -350)
        if tissue_count:
            sizes = np.bincount(tissue_labels.ravel())
            sizes[0] = 0
            largest = int(np.argmax(sizes))
            if sizes[largest] > 100:
                row, column = ndimage.center_of_mass(section > -350, tissue_labels, largest)
                body_centres.append(volume.index_to_world([column, row, index])[0])
    if not body_centres or not np.any(internal):
        raise ValueError("No internal lung-like air was found in the public CT.")

    # Physical opening suppresses the narrow trachea and detached bowel gas.
    opened = ndimage.binary_opening(internal, structure=_ellipsoid(3.5, volume.spacing[::-1]))
    midline = float(np.median(body_centres))
    zz = np.arange(volume.shape[0], dtype=float)[:, None, None]
    yy = np.arange(volume.shape[1], dtype=float)[None, :, None]
    xx = np.arange(volume.shape[2], dtype=float)[None, None, :]
    physical_left = (volume.origin[0] + volume.direction[0, 0] * volume.spacing[0] * xx
                     + volume.direction[0, 1] * volume.spacing[1] * yy
                     + volume.direction[0, 2] * volume.spacing[2] * zz) >= midline
    masks = {}
    for name, side in (("left_lung", physical_left), ("right_lung", ~physical_left)):
        lung = _largest_component(opened & side)
        if not np.any(lung):
            raise ValueError("The public CT did not yield two lung-like display regions.")
        for index in range(len(lung)):
            lung[index] = ndimage.binary_fill_holes(lung[index])
        masks[name] = lung
    interior = ndimage.binary_erosion(masks["left_lung"] | masks["right_lung"],
                                     structure=_ellipsoid(2., volume.spacing[::-1]))
    masks["vascular_display"] = interior & (volume.data > LUNG_DETAIL_THRESHOLD_HU)
    return masks


def load_public_sample(cache_dir="data/public-example"):
    """Return ``(Volume, display_masks, provenance)`` for one static public CT.

    The optional first download is about 40 MB. A checksum-verified local copy
    works offline. Voxel values and physical geometry are retained; masks are
    derived on that exact grid. No lesion or measured respiratory field exists.
    """
    cache_dir = Path(cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    source_path = cache_dir / "CT-chest.nrrd"
    if not cached_public_sample_available(cache_dir):
        try:
            _download_verified(SAMPLE_URL, source_path, SAMPLE_SHA256)
        except (OSError, ValueError) as error:
            raise RuntimeError("The optional public CT could not be downloaded and verified. "
                               "Check the connection or continue with the synthetic study.") from error
    volume = load_volume(source_path)
    volume.name = "Slicer CTChest — public static CT example"
    if np.issubdtype(volume.data.dtype, np.integer):
        # The public source can use int32 storage for ordinary CT HU values.
        # Lossless int16 storage avoids retaining twice the required RAM.
        if np.min(volume.data) >= -32768 and np.max(volume.data) <= 32767:
            volume.data = volume.data.astype(np.int16, copy=False)
    masks = derive_display_masks(volume)
    bundled_license = Path(__file__).resolve().with_name("THIRD_PARTY_LICENSES.txt")
    license_path = cache_dir / "Slicer-CTChest-LICENSE.txt"
    if bundled_license.is_file():
        shutil.copyfile(bundled_license, license_path)
    provenance = {
        "id": "slicer-ctchest-public-example",
        "name": "Slicer CTChest public example",
        "source": "public CT",
        "provider": "3D Slicer project / The Brigham and Women's Hospital, Inc.",
        "source_url": SAMPLE_URL,
        "source_path": str(source_path),
        "sha256": SAMPLE_SHA256,
        "bytes": source_path.stat().st_size,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "registration_source": "https://github.com/Slicer/Slicer/blob/main/Modules/Scripted/SampleData/SampleData.py",
        "license": "3D Slicer Contribution and Software License Agreement, Version 1.0",
        "license_url": LICENSE_URL,
        "license_path": str(license_path) if license_path.is_file() else None,
        "attribution": ("All or portions of this licensed product (such portions are the \"Software\") "
                        "have been obtained under license from The Brigham and Women's Hospital, Inc. "
                        "and are subject to the following terms and conditions:"),
        "shape_zyx": list(volume.shape),
        "spacing_xyz_mm": list(volume.spacing),
        "origin_lps_mm": list(volume.origin),
        "direction": volume.direction.tolist(),
        "coordinate_system": "LPS millimetres",
        "motion": "static",
        "target_annotations": False,
        "planning_obstacles": False,
        "patient_metadata": "Legacy anonymous public example; no patient context inferred.",
        "display_mask_version": DISPLAY_MASK_VERSION,
        "derived_masks": {name: "threshold-derived display only" for name in masks},
        "display_labels": {"left_lung": "Left lung (derived)",
                           "right_lung": "Right lung (derived)",
                           "vascular_display": LUNG_DETAIL_LABEL},
        "derivation": ("Internal CT air below -450 HU; image-edge air excluded per slice; "
                       "physical closing/filling/opening; largest region on each physical LPS side. "
                       f"{LUNG_DETAIL_LABEL} is CT above {LUNG_DETAIL_THRESHOLD_HU} HU "
                       "inside eroded lung envelopes; "
                       "it can include other dense tissue and is not an expert vessel annotation."),
        "modifications": "Source CT voxel values and geometry retained; display masks derived by MotionTwin.",
    }
    (cache_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return volume, masks, provenance


# ============================================================================
# simulation / needle
# ============================================================================

from dataclasses import dataclass

import numpy as np




@dataclass
class Needle:
    entry: np.ndarray
    endpoint: np.ndarray
    depth: float = 0.0
    radius: float = 0.8

    def __post_init__(self):
        self.entry = np.asarray(self.entry, dtype=float).copy()
        self.endpoint = np.asarray(self.endpoint, dtype=float).copy()
        if (self.entry.shape != (3,) or self.endpoint.shape != (3,)
                or not np.all(np.isfinite([self.entry, self.endpoint]))):
            raise ValueError("Needle endpoints must be finite xyz positions")
        if not np.isfinite(self.depth) or not np.isfinite(self.radius) or self.radius <= 0:
            raise ValueError("Needle depth must be finite and radius positive")
        self.depth = float(np.clip(self.depth, 0, self.length))
        self.radius = float(self.radius)

    @property
    def length(self):
        return float(np.linalg.norm(self.endpoint - self.entry))

    @property
    def tip(self):
        if self.length < 1e-9:
            return self.entry.copy()
        return self.entry + np.clip(self.depth, 0, self.length) * unit(self.endpoint - self.entry)

    def advance(self, distance):
        if not np.isfinite(distance):
            raise ValueError("Needle advance distance must be finite")
        self.depth = float(np.clip(self.depth + distance, 0, self.length))
        return self.tip


# ============================================================================
# prediction / baselines
# ============================================================================

"""Causal position forecasts in physical millimetres."""


from functools import lru_cache

import numpy as np
from scipy.optimize import minimize_scalar


def validate_history(times, positions):
    times = np.asarray(times, dtype=float)
    positions = np.asarray(positions, dtype=float)
    if times.ndim != 1 or not len(times) or positions.shape != (len(times), 3):
        raise ValueError("Expected nonempty times (n,) and xyz positions (n, 3).")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(positions)):
        raise ValueError("History must contain finite values.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Observation times must be strictly increasing.")
    return times, positions


def velocity_estimate(times, positions, window=0.6):
    times, positions = validate_history(times, positions)
    selected = times >= times[-1] - window
    if np.count_nonzero(selected) < 2:
        selected = np.arange(len(times)) >= max(0, len(times) - 2)
    recent = times[selected] - times[-1]
    if len(recent) < 2:
        return np.zeros(3)
    design = np.column_stack((np.ones(len(recent)), recent))
    return np.linalg.lstsq(design, positions[selected], rcond=None)[0][1]


def constant_position(times, positions, horizon):
    _, positions = validate_history(times, positions)
    return positions[-1].copy()


def constant_velocity(times, positions, horizon):
    times, positions = validate_history(times, positions)
    return positions[-1] + velocity_estimate(times, positions) * horizon


def fit_sinusoid(times, positions, max_history=12.0):
    """Estimate frequency and harmonic coefficients from observed samples only."""
    times, positions = validate_history(times, positions)
    selected = times >= times[-1] - max_history
    recent = times[selected] - times[-1]
    values = positions[selected]
    if len(recent) < 8 or np.ptp(recent) < 1.5:
        raise ValueError("Sinusoidal fitting needs at least eight samples over 1.5 s.")
    frequency, coefficients, origin = _fit_observed_sinusoid(recent.tobytes(), values.tobytes())
    return frequency, coefficients.copy(), origin.copy()


@lru_cache(maxsize=32)
def _fit_observed_sinusoid(time_bytes, position_bytes):
    """Reuse one observed-history fit while evaluating candidate arrival times."""
    recent = np.frombuffer(time_bytes, dtype=float)
    values = np.frombuffer(position_bytes, dtype=float).reshape(-1, 3)
    origin = values[-1]
    centred = values - origin

    def design(frequency, t):
        angle = 2 * np.pi * frequency * np.asarray(t)
        return np.column_stack((np.ones_like(angle), np.sin(angle), np.cos(angle),
                                np.sin(2 * angle), np.cos(2 * angle)))

    def fit(frequency):
        matrix = design(frequency, recent)
        coefficients = np.linalg.lstsq(matrix, centred, rcond=None)[0]
        residual = centred - matrix @ coefficients
        return float(np.mean(residual**2)), coefficients

    # A grid prevents local optimisation from selecting a remote frequency alias.
    frequencies = np.linspace(0.10, 0.50, 49)
    errors = [fit(frequency)[0] for frequency in frequencies]
    index = int(np.argmin(errors))
    low = frequencies[max(0, index - 1)]
    high = frequencies[min(len(frequencies) - 1, index + 1)]
    result = minimize_scalar(lambda f: fit(f)[0], bounds=(low, high), method="bounded")
    frequency = float(result.x)
    coefficients = fit(frequency)[1]
    return frequency, coefficients, origin


def sinusoidal(times, positions, horizon):
    times, positions = validate_history(times, positions)
    if horizon == 0:
        return positions[-1].copy()
    try:
        frequency, coefficients, origin = fit_sinusoid(times, positions)
    except ValueError:
        return constant_velocity(times, positions, horizon)
    angle = 2 * np.pi * frequency * horizon
    basis = np.array([1., np.sin(angle), np.cos(angle), np.sin(2 * angle), np.cos(2 * angle)])
    return origin + basis @ coefficients


# ============================================================================
# prediction / features
# ============================================================================

"""History encoding and train-only standardisation for the small predictor."""


from dataclasses import dataclass

import numpy as np




FEATURE_VERSION = 2


def respiratory_features(sampled, history_seconds, observed_duration):
    """Estimate a dominant frequency and phase from the observed window."""
    axis = int(np.argmax(np.ptp(sampled, axis=0)))
    signal = sampled[:, axis] - sampled[:, axis].mean()
    if observed_duration < 2 or np.ptp(signal) < 1e-6:
        return np.zeros(3)
    spacing = history_seconds / (len(sampled) - 1)
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)), n=512))
    frequencies = np.fft.rfftfreq(512, spacing)
    allowed = (frequencies >= .10) & (frequencies <= .50)
    if not np.any(allowed):
        return np.zeros(3)
    frequency = frequencies[np.flatnonzero(allowed)[np.argmax(spectrum[allowed])]]
    angles = 2 * np.pi * frequency * np.linspace(-history_seconds, 0, len(signal))
    design = np.column_stack((np.ones(len(signal)), np.sin(angles), np.cos(angles)))
    _, sine, cosine = np.linalg.lstsq(design, signal, rcond=None)[0]
    amplitude = np.hypot(sine, cosine)
    return np.array([frequency, cosine / max(amplitude, 1e-6), sine / max(amplitude, 1e-6)])


def history_features(times, positions, horizon, history_points=24, history_seconds=8.0):
    times, positions = validate_history(times, positions)
    if not np.isfinite(horizon) or horizon < 0:
        raise ValueError("Forecast horizon must be finite and nonnegative.")
    if history_points < 3 or history_seconds <= 0:
        raise ValueError("History requires at least three points and a positive duration.")
    grid = np.linspace(times[-1] - history_seconds, times[-1], history_points)
    sampled = np.column_stack([np.interp(grid, times, positions[:, axis]) for axis in range(3)])
    relative = sampled - positions[-1]
    velocity = velocity_estimate(times, positions)
    ranges = np.ptp(sampled, axis=0)
    observed_duration = min(history_seconds, times[-1] - times[0])
    respiratory = respiratory_features(sampled, history_seconds, observed_duration)
    return np.r_[relative.ravel(), velocity, ranges, respiratory, observed_duration, horizon].astype(np.float32)


@dataclass
class Standardiser:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, training_values):
        values = np.asarray(training_values, dtype=np.float32)
        if values.ndim != 2 or not len(values):
            raise ValueError("Standardisation requires a nonempty training matrix.")
        scale = values.std(axis=0)
        return cls(values.mean(axis=0), np.where(scale > 1e-6, scale, 1.0))

    def transform(self, values):
        return (np.asarray(values, dtype=np.float32) - self.mean) / self.scale

    def state(self):
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist()}

    @classmethod
    def from_state(cls, state):
        return cls(np.asarray(state["mean"], dtype=np.float32), np.asarray(state["scale"], dtype=np.float32))


# ============================================================================
# prediction / uncertainty
# ============================================================================

"""Empirical forecast-error distributions fitted on separate calibration patients."""


import numpy as np


def fit_residual_distribution(residuals, nominal_coverage=0.95):
    residuals = np.asarray(residuals, dtype=float)
    if residuals.ndim != 2 or residuals.shape[1] != 3 or len(residuals) < 4:
        raise ValueError("At least four calibration xyz residuals are required.")
    if not np.all(np.isfinite(residuals)) or not 0 < nominal_coverage < 1:
        raise ValueError("Residuals and nominal coverage must be valid.")
    bias = residuals.mean(axis=0)
    centred = residuals - bias
    # The small diagonal floor makes rank-deficient directional motion usable.
    covariance = np.cov(centred, rowvar=False) + np.eye(3) * 1e-6
    inverse = np.linalg.inv(covariance)
    scores = np.einsum("ni,ij,nj->n", centred, inverse, centred)
    quantile = float(np.quantile(scores, nominal_coverage, method="higher"))
    radius = float(np.quantile(np.linalg.norm(centred, axis=1), nominal_coverage, method="higher"))
    return {"bias": bias.tolist(), "covariance": covariance.tolist(),
            "mahalanobis_quantile": quantile, "radius_mm": radius,
            "nominal_coverage": nominal_coverage, "n_calibration": len(residuals),
            "residual_samples": centred.tolist(),
            "sampling_note": "Centred residuals from calibration patients; rows are paired by patient and observation time across horizons."}


def covered(residuals, distribution):
    residuals = np.asarray(residuals, dtype=float) - np.asarray(distribution["bias"])
    inverse = np.linalg.inv(np.asarray(distribution["covariance"]))
    scores = np.einsum("ni,ij,nj->n", residuals, inverse, residuals)
    return scores <= distribution["mahalanobis_quantile"]


def interpolate_distribution(calibrations, horizon):
    """Blend adjacent calibrated horizons without extrapolating uncertainty."""
    horizons = np.array(sorted(float(value) for value in calibrations))
    if horizon < horizons[0] - 1e-8 or horizon > horizons[-1] + 1e-8:
        raise ValueError(f"Learned horizon {horizon:g} s is outside calibrated range "
                         f"[{horizons[0]:g}, {horizons[-1]:g}] s.")
    upper = min(int(np.searchsorted(horizons, horizon)), len(horizons) - 1)
    lower = max(0, upper - 1)
    if abs(horizons[upper] - horizon) < 1e-8:
        return calibrations[str(float(horizons[upper]))]
    weight = (horizon - horizons[lower]) / (horizons[upper] - horizons[lower])
    first, second = (calibrations[str(float(horizons[index]))] for index in (lower, upper))
    first_samples = np.asarray(first["residual_samples"])
    second_samples = np.asarray(second["residual_samples"])
    if first_samples.shape != second_samples.shape:
        raise ValueError("Checkpoint calibration residuals cannot be paired across horizons.")
    samples = (1 - weight) * first_samples + weight * second_samples
    result = fit_residual_distribution(samples, first["nominal_coverage"])
    result["bias"] = ((1 - weight) * np.asarray(first["bias"]) + weight * np.asarray(second["bias"])).tolist()
    result["sampling_note"] = "Approximation: linear interpolation of centred residuals paired by calibration patient and observation time at adjacent horizons."
    return result


# ============================================================================
# prediction / training
# ============================================================================

"""Reproducible synthetic training with patient-disjoint evaluation and calibration."""


import copy
import json
import os
import platform
from pathlib import Path

import numpy as np






CHECKPOINT_VERSION = 1
TRAINING_DEFAULTS = {"seed": 42, "patients": 40, "samples_per_patient": 24, "history_points": 24,
            "history_seconds": 8.0, "horizons": [0.25, 0.5, 1., 2., 3., 4., 6., 8.],
            "epochs": 60, "patience": 10, "batch_size": 256, "hidden_units": 64,
            "learning_rate": 0.001, "device": "cpu", "cpu_threads": 2,
            "nominal_coverage": 0.95}


def training_config(config):
    result = dict(TRAINING_DEFAULTS)
    result.update({key: value for key, value in config.items() if key in TRAINING_DEFAULTS})
    for name in ("prediction", "training"):
        result.update({key: value for key, value in config.get(name, {}).items() if key in TRAINING_DEFAULTS})
    if int(result["patients"]) < 8 or int(result["samples_per_patient"]) < 4:
        raise ValueError("Training needs at least eight patients and four windows per patient.")
    if int(result["epochs"]) < 1 or int(result["batch_size"]) < 1 or int(result["patience"]) < 1:
        raise ValueError("Epochs, batch size and patience must be positive.")
    units = result["hidden_units"]
    if isinstance(units, (list, tuple)):
        if len(units) != 2 or any(int(value) < 1 for value in units):
            raise ValueError("Specify exactly two positive hidden-layer widths.")
        result["hidden_units"] = [int(value) for value in units]
    elif int(units) < 1:
        raise ValueError("Hidden units must be positive.")
    if float(result["learning_rate"]) <= 0:
        raise ValueError("Hidden units and learning rate must be positive.")
    horizons = sorted(set(float(value) for value in result["horizons"]))
    if not horizons or not np.all(np.isfinite(horizons)) or horizons[0] <= 0:
        raise ValueError("Training horizons must be finite, distinct positive seconds.")
    result["horizons"] = horizons
    return result


def patient_split(patient_count, seed):
    """Split identities before creating any sliding windows."""
    if patient_count < 8:
        raise ValueError("At least eight patient identities are required.")
    order = np.random.default_rng(seed).permutation(patient_count).tolist()
    n_train, n_valid, n_cal = int(patient_count * 0.60), max(1, int(patient_count * 0.15)), max(1, int(patient_count * 0.125))
    return {"train": order[:n_train], "validation": order[n_train:n_train + n_valid],
            "calibration": order[n_train + n_valid:n_train + n_valid + n_cal],
            "test": order[n_train + n_valid + n_cal:]}


def generate_dataset(config):
    """Return causal histories and true future labels; labels never enter features."""
    pass  # Shared definitions are in this file.
    pass  # Shared definitions are in this file.

    cfg = training_config(config)
    rng = np.random.default_rng(cfg["seed"])
    features, targets, patients, horizons, irregular, histories = [], [], [], [], [], []
    for patient in range(cfg["patients"]):
        amplitude = rng.uniform(4., 18.)
        irregularity = float(rng.choice([0., .15, .4, .75]))
        patient_config = VirtualPatient(seed=cfg["seed"] * 10000 + patient, amplitude=amplitude,
                                       frequency=rng.uniform(.15, .38), irregularity=irregularity,
                                       noise=rng.uniform(.05, .65))
        respiratory = RespiratoryModel(patient_config)
        origin = rng.uniform(-50, 50, 3)
        observation_times = np.arange(0, cfg["history_seconds"] + 24.01, .1)
        observations = respiratory.observe(observation_times, origin)
        cuts = np.linspace(int(np.ceil(cfg["history_seconds"] / .1)), len(observation_times) - 1,
                           cfg["samples_per_patient"]).astype(int)
        for cut in cuts:
            start = max(0, cut - int(np.ceil(cfg["history_seconds"] / .1)) - 1)
            times = observation_times[start:cut + 1]
            positions = observations[start:cut + 1]
            for horizon in cfg["horizons"]:
                future = origin + respiratory.displacement(times[-1] + horizon)
                features.append(history_features(times, positions, horizon, cfg["history_points"], cfg["history_seconds"]))
                targets.append(future - positions[-1])
                patients.append(patient)
                horizons.append(horizon)
                irregular.append(irregularity > 0)
                histories.append((times, positions))
    return {"features": np.asarray(features, dtype=np.float32), "displacement": np.asarray(targets, dtype=np.float32),
            "patients": np.asarray(patients), "horizons": np.asarray(horizons),
            "irregular": np.asarray(irregular), "histories": histories}


def prediction_error_metrics(residuals):
    residuals = np.asarray(residuals, dtype=float)
    errors = np.linalg.norm(residuals, axis=1)
    return {"n": len(errors), "mae_mm": float(errors.mean()),
            "rmse_mm": float(np.sqrt(np.mean(errors**2))), "median_mm": float(np.median(errors)),
            "std_mm": float(errors.std()), "coordinate_mae_mm": float(np.abs(residuals).mean())}


def train_model(config: dict, output_dir="outputs/model") -> dict:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    from motiontwin import MotionMLP

    cfg = training_config(config)
    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(cfg["seed"])
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(max(1, int(cfg["cpu_threads"])))
    requested = cfg["device"]
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "cpu"
    if str(requested).startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but this PyTorch installation has no available CUDA device.")
    device = torch.device(requested)
    data = generate_dataset(cfg)
    split = patient_split(cfg["patients"], cfg["seed"])
    patient_seeds_by_split = {name: [cfg["seed"] * 10000 + identity for identity in identities]
                              for name, identities in split.items()}
    masks = {name: np.isin(data["patients"], identities) for name, identities in split.items()}
    scaler = Standardiser.fit(data["features"][masks["train"]])
    target_scaler = Standardiser.fit(data["displacement"][masks["train"]])
    inputs = torch.from_numpy(scaler.transform(data["features"])).to(device)
    targets = torch.from_numpy(target_scaler.transform(data["displacement"])).to(device)
    indices = {name: torch.as_tensor(np.flatnonzero(mask), device=device) for name, mask in masks.items()}
    model = MotionMLP(inputs.shape[1], cfg["hidden_units"]).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    rng = np.random.default_rng(cfg["seed"])
    best_loss, best_state, best_epoch, stale = float("inf"), None, 0, 0
    history = []
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        train_indices = rng.permutation(np.flatnonzero(masks["train"]))
        losses = []
        for offset in range(0, len(train_indices), cfg["batch_size"]):
            batch = torch.as_tensor(train_indices[offset:offset + cfg["batch_size"]], device=device)
            optimiser.zero_grad(set_to_none=True)
            loss = torch.mean((model(inputs[batch]) - targets[batch])**2)
            loss.backward()
            optimiser.step()
            losses.append((float(loss.detach().cpu()), len(batch)))
        model.eval()
        with torch.no_grad():
            val_loss = float(torch.mean((model(inputs[indices["validation"]]) - targets[indices["validation"]])**2).cpu())
        history.append({"epoch": epoch, "train_mse_standardised": sum(v * n for v, n in losses) / sum(n for _, n in losses),
                        "validation_mse_standardised": val_loss})
        if val_loss < best_loss - 1e-6:
            best_loss, best_epoch, stale = val_loss, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
            if stale >= cfg["patience"]:
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        predictions = model(inputs).cpu().numpy() * target_scaler.scale + target_scaler.mean
    calibration = {}
    for horizon in cfg["horizons"]:
        selected = masks["calibration"] & np.isclose(data["horizons"], horizon)
        residuals = data["displacement"][selected] - predictions[selected]
        calibration[str(float(horizon))] = fit_residual_distribution(residuals, cfg["nominal_coverage"])
    test_indices = np.flatnonzero(masks["test"])
    residuals_by_method = {name: [] for name in ("static", "velocity", "sinusoidal", "learned")}
    coverage_values = []
    for index in test_indices:
        times, positions = data["histories"][index]
        horizon = float(data["horizons"][index])
        truth = positions[-1] + data["displacement"][index]
        for name, function in (("static", constant_position), ("velocity", constant_velocity), ("sinusoidal", sinusoidal)):
            residuals_by_method[name].append(truth - function(times, positions, horizon))
        distribution = calibration[str(horizon)]
        raw_residual = data["displacement"][index] - predictions[index]
        residuals_by_method["learned"].append(raw_residual - np.asarray(distribution["bias"]))
        coverage_values.append(bool(covered(raw_residual[None, :], distribution)[0]))
    residuals_by_method = {name: np.asarray(values) for name, values in residuals_by_method.items()}
    test_horizons = data["horizons"][test_indices]
    test_irregular = data["irregular"][test_indices]
    metrics = {name: prediction_error_metrics(values) for name, values in residuals_by_method.items()}
    by_horizon = {str(float(h)): {name: prediction_error_metrics(values[np.isclose(test_horizons, h)])
                                for name, values in residuals_by_method.items()} for h in cfg["horizons"]}
    for horizon, values in by_horizon.items():
        selected = np.isclose(test_horizons, float(horizon))
        values["learned"]["empirical_coverage"] = float(np.asarray(coverage_values)[selected].mean())
    metrics["learned"]["empirical_coverage"] = float(np.mean(coverage_values))
    irregular_metrics = {name: prediction_error_metrics(values[test_irregular]) for name, values in residuals_by_method.items()} if np.any(test_irregular) else {}
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    checkpoint_path = destination / "motion_predictor.pt"
    versions = {"python": platform.python_version(), "numpy": np.__version__, "torch": str(torch.__version__),
                "training_generator": "motiontwin.simulation.respiratory.RespiratoryModel v1"}
    checkpoint = {"checkpoint_version": CHECKPOINT_VERSION, "feature_version": FEATURE_VERSION,
                  "state_dict": {key: value.cpu() for key, value in model.state_dict().items()},
                  "input_features": inputs.shape[1], "config": cfg, "standardiser": scaler.state(),
                  "target_standardiser": target_scaler.state(), "patient_split": split,
                  "patient_seeds_by_split": patient_seeds_by_split,
                  "calibration": calibration, "versions": versions}
    torch.save(checkpoint, checkpoint_path)
    report = {"checkpoint": str(checkpoint_path.resolve()), "config": cfg, "patient_split": split,
              "patient_seeds_by_split": patient_seeds_by_split,
              "split_rows": {name: int(mask.sum()) for name, mask in masks.items()},
              "best_epoch": best_epoch, "epochs_run": len(history), "device": str(device),
              "test_metrics": metrics, "metrics_by_horizon": by_horizon, "irregular_test_metrics": irregular_metrics,
              "nominal_coverage": cfg["nominal_coverage"], "training_history": history, "versions": versions,
              "metric_definition": "mae_mm is mean Euclidean position error; rmse_mm is root mean squared Euclidean error.",
              "training_domain": {"source": "same RespiratoryModel family as the synthetic workstation",
                                  "base_amplitude_mm": [4., 18.], "base_frequency_hz": [.15, .38],
                                  "irregularity_values": [0., .15, .4, .75], "observation_noise_mm": [.05, .65],
                                  "note": "Calibration describes this synthetic population only; real-patient motion and out-of-range settings are unvalidated."},
              "uncertainty_note": "Calibration-patient residual bias, covariance, centred error samples and empirical ellipsoid quantiles. Intermediate horizons linearly interpolate residual vectors paired by calibration patient and observation time, an approximation. Coverage is measured on separate test patients. Synthetic results are not clinical validation."}
    (destination / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (destination / "training_config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return report


# ============================================================================
# prediction
# ============================================================================

"""Causal baseline and learned forecasts with explicitly calibrated uncertainty."""


from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import pickle

import numpy as np






@dataclass
class Forecast:
    mean: np.ndarray
    covariance: np.ndarray
    method: str
    calibrated: bool = False
    radius_mm: float = float("nan")
    mahalanobis_quantile: float = float("nan")
    nominal_coverage: float = float("nan")
    residual_samples: np.ndarray | None = None
    uncertainty_source: str | None = None


@lru_cache(maxsize=4)
def _load_checkpoint(path, modified_ns, size):
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Learned prediction requires the PyTorch dependency.") from exc
    from motiontwin import MotionMLP
    pass  # Shared definitions are in this file.

    try:
        state = torch.load(path, map_location="cpu", weights_only=True)
    except (OSError, RuntimeError, EOFError, pickle.UnpicklingError) as exc:
        raise ValueError("Unable to load the supplied MotionTwin checkpoint.") from exc
    if not isinstance(state, dict) or state.get("checkpoint_version") != CHECKPOINT_VERSION or state.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Unsupported model or feature version; retrain this checkpoint.")
    required = {"input_features", "config", "state_dict", "standardiser", "target_standardiser", "calibration"}
    if not required.issubset(state):
        raise ValueError("MotionTwin checkpoint is incomplete; retrain it.")
    model = MotionMLP(state["input_features"], state["config"]["hidden_units"])
    model.load_state_dict(state["state_dict"])
    model.eval()
    return model, state


def forecast(times, positions, horizon, method="sinusoidal", checkpoint=None) -> Forecast:
    """Forecast xyz at last observation time plus horizon, without future truth.

    Baselines expose NaN covariance because no held-out residual calibration is
    available for them. Learned uncertainty comes only from calibration patients.
    """
    times, positions = validate_history(times, positions)
    horizon = float(horizon)
    if not np.isfinite(horizon) or horizon < 0:
        raise ValueError("Forecast horizon must be finite and nonnegative.")
    methods = {"static": constant_position, "velocity": constant_velocity, "sinusoidal": sinusoidal}
    if method in methods:
        return Forecast(methods[method](times, positions, horizon), np.full((3, 3), np.nan), method)
    if method != "learned":
        raise ValueError(f"Unknown prediction method: {method}")
    if checkpoint is None or not Path(checkpoint).is_file():
        raise FileNotFoundError("Learned prediction requires a trained MotionTwin checkpoint. Run motiontwin train first.")
    path = Path(checkpoint).resolve()
    stat = path.stat()
    model, state = _load_checkpoint(str(path), stat.st_mtime_ns, stat.st_size)
    cfg = state["config"]
    if times[-1] - times[0] < cfg["history_seconds"] - 1e-6:
        raise ValueError(f"Learned prediction requires {cfg['history_seconds']:g} seconds of observed history.")
    distribution = interpolate_distribution(state["calibration"], horizon)
    feature = history_features(times, positions, horizon, cfg["history_points"], cfg["history_seconds"])
    x_scaler = Standardiser.from_state(state["standardiser"])
    y_scaler = Standardiser.from_state(state["target_standardiser"])
    import torch
    with torch.no_grad():
        output = model(torch.from_numpy(x_scaler.transform(feature)[None, :])).numpy()[0]
    displacement = output * y_scaler.scale + y_scaler.mean
    mean = positions[-1] + displacement + np.asarray(distribution["bias"])
    return Forecast(mean, np.asarray(distribution["covariance"]), method, True,
                    distribution["radius_mm"], distribution["mahalanobis_quantile"], distribution["nominal_coverage"],
                    np.asarray(distribution["residual_samples"]), distribution["sampling_note"])


# ============================================================================
# planning / planners
# ============================================================================

from dataclasses import dataclass, field
from time import perf_counter

import numpy as np





GAUSSIAN_95_QUANTILE = 7.8147279


@dataclass
class Plan:
    entry: np.ndarray | None = None
    endpoint: np.ndarray | None = None
    prediction: np.ndarray | None = None
    covariance: np.ndarray = field(default_factory=lambda: np.full((3, 3), np.nan))
    length: float = 0.0
    clearance: float = float("nan")
    horizon: float = 0.0
    latency_ms: float = 0.0
    miss_probability: float = float("nan")
    abstained: bool = True
    reason: str = "No plan calculated"
    method: str = "static"
    uncertainty_quantile: float = GAUSSIAN_95_QUANTILE
    uncertainty_calibrated: bool = False
    uncertainty_source: str = "unavailable"


def _forecast_distribution(prediction, enabled, rng):
    endpoint = np.asarray(prediction.mean, dtype=float)
    covariance = np.asarray(prediction.covariance, dtype=float)
    if endpoint.shape != (3,) or not np.all(np.isfinite(endpoint)) or covariance.shape != (3, 3):
        raise ValueError("Predictor returned an invalid physical position or covariance")
    calibrated = bool(enabled and getattr(prediction, "calibrated", False)
                      and np.all(np.isfinite(covariance)))
    quantile = float(getattr(prediction, "mahalanobis_quantile", GAUSSIAN_95_QUANTILE))
    if not np.isfinite(quantile) or quantile <= 0:
        quantile = GAUSSIAN_95_QUANTILE
    if not calibrated:
        return endpoint, covariance, endpoint[None], False, quantile, "unavailable"
    covariance = (covariance + covariance.T) / 2
    values, vectors = np.linalg.eigh(covariance)
    if values.min() < -1e-8:
        raise ValueError("Predictor covariance must be positive semidefinite")
    covariance = (vectors * np.maximum(values, 1e-9)) @ vectors.T
    residuals = getattr(prediction, "residual_samples", None)
    if residuals is not None:
        residuals = np.asarray(residuals, dtype=float)
        if residuals.ndim == 2 and residuals.shape[1] == 3 and len(residuals) >= 4 and np.all(np.isfinite(residuals)):
            selected = rng.choice(len(residuals), min(192, len(residuals)), replace=False)
            return endpoint, covariance, endpoint + residuals[selected], True, quantile, "held-out residual samples"
    # Approximate the calibrated ellipsoid with a Gaussian when residual draws
    # are unavailable. The empirical quantile still controls its radial scale.
    from scipy.stats import chi2
    nominal = float(getattr(prediction, "nominal_coverage", .95))
    nominal = nominal if np.isfinite(nominal) and 0 < nominal < 1 else .95
    sample_covariance = covariance * quantile / chi2.ppf(nominal, 3)
    samples = rng.multivariate_normal(endpoint, sample_covariance, 192)
    return endpoint, covariance, samples, True, quantile, "Gaussian approximation to calibrated ellipsoid"


def _path_costs(entries, endpoint, samples, radius, lengths, clearances, calibrated):
    distances = point_segment_distances(samples[None], entries[:, None], endpoint)
    misses = np.mean(distances > radius, axis=1)
    costs = np.mean(distances, axis=1) / radius + .18 * lengths / 250 + .12 / (1 + clearances / 5)
    if calibrated:
        costs += .7 * misses
    return costs, misses


def _solve_arrival(predict, entry, observed, delay, insertion_speed, method):
    arrival = delay+float(np.linalg.norm(observed-entry))/insertion_speed
    first_guess = arrival
    for _ in range(24):
        prediction = predict(arrival)
        endpoint = np.asarray(prediction.mean, dtype=float)
        if endpoint.shape != (3,) or not np.all(np.isfinite(endpoint)):
            raise ValueError("Predictor returned an invalid physical position")
        next_arrival = delay+float(np.linalg.norm(endpoint-entry))/insertion_speed
        if abs(next_arrival-arrival) <= 1e-6:
            return arrival, prediction
        arrival = next_arrival
    if method == "learned":
        raise ValueError("Predicted arrival-time iteration did not converge within calibrated inputs")
    from scipy.optimize import brentq, minimize_scalar

    def residual(horizon):
        position = np.asarray(predict(horizon).mean, dtype=float)
        return delay+float(np.linalg.norm(position-entry))/insertion_speed-horizon

    lower = delay
    upper = max(first_guess, delay+.25)
    for _ in range(12):
        if residual(upper) <= 0:
            arrival = float(brentq(residual, lower, upper, xtol=1e-8))
            return arrival, predict(arrival)
        # An approaching target can pass the entry and retreat before the
        # upper endpoint. Positive endpoint residuals alone do not rule out
        # an interception inside that interval (the linear case is convex).
        minimum = minimize_scalar(residual, bounds=(lower, upper), method="bounded",
                                  options={"xatol": 1e-9})
        if minimum.fun <= 0:
            arrival = float(brentq(residual, lower, float(minimum.x), xtol=1e-8))
            return arrival, predict(arrival)
        if abs(minimum.fun) <= 1e-7:
            return float(minimum.x), predict(float(minimum.x))
        lower = upper
        upper = delay+2*(upper-delay)
    raise ValueError("No consistent finite arrival was found within the horizon search")


def plan_trajectory(anatomy, times, observations, method="static", delay=1., insertion_speed=60.,
                    risk_tolerance=.1, checkpoint=None, uncertainty=True, delay_aware=True):
    start = perf_counter()
    result = Plan(method=method)
    if (not np.isfinite(risk_tolerance) or not 0 <= risk_tolerance <= 1
            or not np.isfinite(insertion_speed) or insertion_speed <= 0
            or not np.isfinite(delay) or delay < 0):
        raise ValueError("Invalid risk tolerance or insertion speed")
    pass  # Shared definitions are in this file.
    times, observations = validate_history(times, observations)
    if len(times) < 2:
        result.reason = "At least two observations are required"
        result.latency_ms = (perf_counter()-start)*1000
        return result
    observed = observations[-1]
    candidates = np.asarray(anatomy.entry_candidates, dtype=float)
    center, radii = np.asarray(anatomy.body_center), np.asarray(anatomy.body_radii)
    if (candidates.ndim != 2 or candidates.shape[1] != 3 or not np.all(np.isfinite(candidates))
            or center.shape != (3,) or radii.shape != (3,)
            or not np.all(np.isfinite(center)) or not np.all(np.isfinite(radii))
            or np.any(radii <= 0) or not np.isfinite(anatomy.target_radius) or anatomy.target_radius <= 0):
        raise ValueError("Candidate entries, body dimensions and target radius must be valid physical geometry")
    valid = np.abs(np.sum(((candidates-center)/radii)**2, axis=1)-1) <= .08
    candidates = candidates[valid]
    if not len(candidates):
        result.reason = "No valid entry point on the body surface"
        result.latency_ms = (perf_counter()-start)*1000
        return result

    modelled_delay = delay if delay_aware else 0.
    now_segments, now_radii = anatomy.obstacles_at(observed-anatomy.target)
    best = None
    result.reason = "No candidate meets entry, clearance and uncertainty constraints"

    def predict(horizon):
        return forecast(times, observations, horizon, method=method, checkpoint=checkpoint)

    for entry in candidates:
        try:
            arrival, prediction = _solve_arrival(predict, entry, observed, modelled_delay,
                                                 insertion_speed, method)
            endpoint, covariance, samples, calibrated, quantile, source = _forecast_distribution(
                prediction, uncertainty, np.random.default_rng(1931))
            length = float(np.linalg.norm(endpoint-entry))
            if length <= 1e-8:
                continue
            # Each hard rejection uses this entry's own converged arrival,
            # rather than another entry's distance or a shared screening time.
            later_segments, later_radii = anatomy.obstacles_at(endpoint-anatomy.target)
            clearance = min(capsule_clearance(entry, endpoint, now_segments, now_radii),
                            capsule_clearance(entry, endpoint, later_segments, later_radii))
            if clearance < 1.:
                continue
            costs, misses = _path_costs(entry[None], endpoint, samples, anatomy.target_radius,
                                       np.array([length]), np.array([clearance]), calibrated)
            miss = float(misses[0])
            if calibrated and miss > risk_tolerance:
                continue
            key = (float(costs[0]), length, *entry.tolist())
            if best is None or key < best[0]:
                best = (key, entry.copy(), endpoint, covariance, length, clearance, arrival,
                        miss, calibrated, quantile, source)
        except (FileNotFoundError, ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
            result.reason = f"Arrival-time refinement unavailable: {exc}"

    if best is not None:
        (_, result.entry, result.endpoint, result.covariance, result.length, result.clearance,
         result.horizon, miss, result.uncertainty_calibrated, result.uncertainty_quantile,
         result.uncertainty_source) = best
        result.prediction = result.endpoint.copy()
        result.miss_probability = miss if result.uncertainty_calibrated else float("nan")
        result.abstained = False
        result.reason = "Accepted simulated trajectory"
    result.latency_ms = (perf_counter()-start)*1000
    return result


# ============================================================================
# simulation / episode
# ============================================================================

from functools import lru_cache

import numpy as np







@lru_cache(maxsize=8)
def cached_anatomy(seed, target_radius):
    return generate_anatomy(seed=seed, target_radius=target_radius, spacing=6.)


def _cycle_gain(patient, times, variability):
    """Seeded smooth random cycle amplitudes; querying order does not change them."""
    times = np.asarray(times, dtype=float)
    if variability == 0:
        return np.ones_like(times)
    cycle = times * patient.frequency
    lower = np.floor(cycle).astype(int)
    rng = np.random.default_rng(np.random.SeedSequence([patient.seed, 3907]))
    values = rng.normal(0, variability, int(lower.max()) + 2)
    fraction = cycle - lower
    blend = fraction * fraction * (3 - 2 * fraction)
    return np.maximum(.05, 1 + values[lower] * (1 - blend) + values[lower + 1] * blend)


def run_episode(patient, method="static", checkpoint=None, risk_tolerance=.1, dt=.05,
                history_duration=8., history_step=.1, spatial_resolution=2.,
                delay_aware=True, uncertainty=True, integration_step=.02,
                delay_std=0.0, cycle_variability=0.0, planning_time=None,
                anatomy=None, planned_trajectory=None, motion_model=None):
    if (not np.all(np.isfinite([dt, history_step, history_duration, spatial_resolution, delay_std, cycle_variability]))
            or min(dt, history_step, history_duration, spatial_resolution) <= 0
            or delay_std < 0 or not 0 <= cycle_variability <= 1):
        raise ValueError("Time and spatial resolutions must be positive")
    anatomy = anatomy if anatomy is not None else cached_anatomy(patient.seed, patient.target_radius)
    motion = motion_model if motion_model is not None else RespiratoryModel(patient, integration_step=integration_step)
    instant=history_duration if planning_time is None else float(planning_time)
    if not np.isfinite(instant) or instant<history_duration:
        raise ValueError("Planning time must include the required causal history")
    times = np.linspace(instant-history_duration,instant,max(2,int(round(history_duration/history_step))+1))
    observations = motion.observe(times, anatomy.target)
    observations += motion.displacement(times) * (_cycle_gain(patient, times, cycle_variability) - 1)[..., None]
    plan = planned_trajectory if planned_trajectory is not None else plan_trajectory(anatomy, times, observations, method, patient.delay,
                           patient.insertion_speed, risk_tolerance, checkpoint,
                           uncertainty, delay_aware)
    outcome = dict(patient_id=patient.seed, method=method, amplitude=patient.amplitude,
                   delay=patient.delay, irregularity=patient.irregularity,
                   targeting_error=float("nan"), hit=False, obstacle_violation=False,
                   abstained=plan.abstained, path_length=plan.length,
                   planning_latency_ms=plan.latency_ms, forecast_error=float("nan"),
                   coverage=float("nan"), reason=plan.reason)
    outcome.update(delay_std=float(delay_std), cycle_variability=float(cycle_variability))
    outcome["planning_time"]=instant
    if plan.abstained:
        return outcome
    # This realised delay is withheld from planning and shared by every planner
    # for this patient. Truncation keeps an execution start from preceding t_now.
    rng = np.random.default_rng(np.random.SeedSequence([patient.seed, 7013]))
    actual_delay = max(0., patient.delay + float(rng.normal(0, delay_std)))
    begin = float(times[-1]) + actual_delay
    duration = plan.length / patient.insertion_speed
    execution = np.unique(np.append(np.arange(begin, begin + duration, dt), begin + duration))
    displacements = motion.displacement(execution) * _cycle_gain(patient, execution, cycle_variability)[..., None]
    actual = anatomy.target + displacements
    depths = np.clip((execution - begin) * patient.insertion_speed, 0, plan.length)
    direction = (plan.endpoint - plan.entry) / plan.length
    tips = plan.entry + depths[:, None] * direction
    # Whole inserted shaft can intersect the moving target during execution.
    distances = point_segment_distances(actual, plan.entry, tips)
    clearances = []
    sample_clearance = float("inf")
    for displacement, tip in zip(displacements, tips):
        segments, radii = anatomy.obstacles_at(displacement)
        clearances.append(capsule_clearance(plan.entry, tip, segments, radii))
        # The independent sampled check exposes spatial-discretisation error.
        count = max(2, int(np.ceil(np.linalg.norm(tip - plan.entry) / spatial_resolution)) + 1)
        points = np.linspace(plan.entry, tip, count)
        sample_clearance = min(sample_clearance, sampled_capsule_clearance(points, segments, radii))
    violation = bool(min(clearances) < 0)
    error = float(np.min(distances))
    residual = actual[-1] - plan.prediction
    coverage = float("nan")
    if uncertainty and plan.uncertainty_calibrated and np.all(np.isfinite(plan.covariance)):
        coverage = bool(residual @ np.linalg.pinv(plan.covariance) @ residual <= plan.uncertainty_quantile)
    outcome.update(targeting_error=error, hit=bool(error <= patient.target_radius and not violation),
                   obstacle_violation=violation, forecast_error=float(np.linalg.norm(residual)),
                   coverage=coverage, sampled_clearance=sample_clearance,
                   exact_clearance=float(min(clearances)), horizon=duration + actual_delay,
                   forecast_horizon=plan.horizon, realised_delay=actual_delay,
                   uncertainty_quantile=plan.uncertainty_quantile,
                   uncertainty_source=plan.uncertainty_source,
                   trace=dict(time=execution.tolist(), actual=actual.tolist(),
                              predicted=np.repeat(plan.prediction[None, :],len(actual),axis=0).tolist()))
    return outcome


# ============================================================================
# research / metrics
# ============================================================================

"""Metrics with explicit treatment of abstention and missing predictions."""



from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np


def _finite_outcomes(rows: list[Mapping[str, Any]], key: str) -> np.ndarray:
    values = []
    for row in rows:
        value = row.get(key)
        if value is not None:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if np.isfinite(number):
                values.append(number)
    return np.asarray(values, dtype=float)


def error_metrics(errors: Iterable[float]) -> dict[str, float]:
    """Summarise scalar errors; non-finite observations do not become zeros."""
    values = np.asarray(list(errors), dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return dict.fromkeys(("mae", "rmse", "median", "standard_deviation"), float("nan"))
    return {
        "mae": float(np.mean(np.abs(values))),
        "rmse": float(np.sqrt(np.mean(values**2))),
        "median": float(np.median(values)),
        "standard_deviation": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
    }


def summarise_outcomes(outcomes: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Hit rate includes abstentions; executed-only rates remain explicit.

    Targeting and clearance outcomes are undefined for a planner that abstains.
    Coverage is evaluated only for episodes with an available prediction interval.
    """
    rows = list(outcomes)
    executed = [row for row in rows if not bool(row.get("abstained", False))]
    errors = error_metrics(_finite_outcomes(executed, "targeting_error"))
    forecasts = error_metrics(_finite_outcomes(rows, "forecast_error"))
    latency = _finite_outcomes(rows, "planning_latency_ms")
    coverage = _finite_outcomes(rows, "coverage")
    forecast_coverage = _finite_outcomes(rows, "forecast_coverage")
    path_length = _finite_outcomes(executed, "path_length")
    hits = sum(bool(row.get("hit", False)) for row in executed)
    violations = sum(bool(row.get("obstacle_violation", False)) for row in executed)
    return {
        "targeting_mae_mm": errors["mae"],
        "targeting_rmse_mm": errors["rmse"],
        "targeting_median_mm": errors["median"],
        "targeting_sd_mm": errors["standard_deviation"],
        "forecast_mae_mm": forecasts["mae"],
        "forecast_rmse_mm": forecasts["rmse"],
        "forecast_median_mm": forecasts["median"],
        "forecast_sd_mm": forecasts["standard_deviation"],
        "hit_rate": hits / len(rows) if rows else float("nan"),
        "conditional_hit_rate": hits / len(executed) if executed else float("nan"),
        "obstacle_violation_rate": violations / len(executed) if executed else float("nan"),
        "attempted_obstacle_violation_rate": violations / len(rows) if rows else float("nan"),
        "abstention_rate": 1 - len(executed) / len(rows) if rows else float("nan"),
        "mean_path_length_mm": float(np.mean(path_length)) if len(path_length) else float("nan"),
        "mean_planning_latency_ms": float(np.mean(latency)) if len(latency) else float("nan"),
        "p95_planning_latency_ms": float(np.percentile(latency, 95)) if len(latency) else float("nan"),
        "empirical_interval_coverage": float(np.mean(coverage)) if len(coverage) else float("nan"),
        "independent_forecast_interval_coverage": float(np.mean(forecast_coverage)) if len(forecast_coverage) else float("nan"),
    }


# ============================================================================
# research / statistics
# ============================================================================

"""Patient-clustered percentile bootstrap, including paired method contrasts."""



from collections.abc import Callable, Iterable, Mapping
from typing import Any

import numpy as np




def cluster_bootstrap_interval(
    values: Iterable[float],
    clusters: Iterable[Any],
    *,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Resample whole patients, preserving their repeated observations."""
    data = np.asarray(list(values), dtype=float)
    labels = np.asarray(list(clusters), dtype=object)
    if data.ndim != 1 or len(data) != len(labels):
        raise ValueError("values and clusters must be equally sized one-dimensional sequences")
    if not 0 < confidence < 1 or n_resamples < 1:
        raise ValueError("confidence must be in (0, 1), with at least one resample")
    finite = np.isfinite(data)
    data, labels = data[finite], labels[finite]
    unique = list(dict.fromkeys(labels.tolist()))
    if len(unique) < 2:
        return float("nan"), float("nan")
    groups = [np.flatnonzero(labels == label) for label in unique]
    rng = np.random.default_rng(seed)
    estimates = np.empty(n_resamples)
    for index in range(n_resamples):
        chosen = rng.integers(0, len(groups), size=len(groups))
        sample = np.concatenate([groups[group] for group in chosen])
        estimates[index] = statistic(data[sample])
    tail = 100 * (1 - confidence) / 2
    lower, upper = np.percentile(estimates, [tail, 100 - tail])
    return float(lower), float(upper)


def summarise_with_intervals(
    outcomes: Iterable[Mapping[str, Any]],
    *,
    n_resamples: int = 200,
    confidence: float = 0.95,
    seed: int = 0,
) -> dict[str, Any]:
    rows = list(outcomes)
    metrics = summarise_outcomes(rows)
    labels = list(dict.fromkeys(row["patient_cluster"] for row in rows))
    intervals = {key: [float("nan"), float("nan")] for key in metrics}
    if len(labels) >= 2:
        groups = [[row for row in rows if row["patient_cluster"] == label] for label in labels]
        estimates: dict[str, list[float]] = {key: [] for key in metrics}
        rng = np.random.default_rng(seed)
        for _ in range(n_resamples):
            chosen = rng.integers(0, len(groups), size=len(groups))
            sample = [row for group in chosen for row in groups[group]]
            for key, value in summarise_outcomes(sample).items():
                if np.isfinite(value):
                    estimates[key].append(value)
        tail = 100 * (1 - confidence) / 2
        for key, values in estimates.items():
            if values:
                intervals[key] = np.percentile(values, [tail, 100 - tail]).tolist()
    return {
        "n_episodes": len(rows),
        "n_patients": len(labels),
        "confidence": confidence,
        "metrics": metrics,
        "confidence_intervals": intervals,
    }


def paired_comparisons(
    outcomes: Iterable[Mapping[str, Any]],
    *,
    baseline: str = "static",
    n_resamples: int = 200,
    confidence: float = 0.95,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Compare realised targeting error on matching non-abstained scenarios."""
    rows = list(outcomes)
    reference = {
        (row["experiment"], row["scenario_id"]): row
        for row in rows
        if row["method"] == baseline and row.get("variant", "full") == "full"
    }
    groups: dict[tuple[str, str, str], list[tuple[float, Any]]] = {}
    for row in rows:
        if row["method"] == baseline and row.get("variant", "full") == "full":
            continue
        other = reference.get((row["experiment"], row["scenario_id"]))
        if other is None or row.get("abstained") or other.get("abstained"):
            continue
        a, b = row.get("targeting_error"), other.get("targeting_error")
        if a is None or b is None or not np.isfinite(float(a)) or not np.isfinite(float(b)):
            continue
        key = (row["experiment"], row["method"], row.get("variant", "full"))
        groups.setdefault(key, []).append((float(a) - float(b), row["patient_cluster"]))
    result = []
    for index, ((experiment, method, variant), pairs) in enumerate(sorted(groups.items())):
        differences, labels = zip(*pairs)
        lower, upper = cluster_bootstrap_interval(
            differences, labels, n_resamples=n_resamples, confidence=confidence, seed=seed + index
        )
        result.append({
            "experiment": experiment,
            "method": method,
            "variant": variant,
            "baseline": baseline,
            "n_pairs": len(pairs),
            "n_patients": len(set(labels)),
            "mean_targeting_difference_mm": float(np.mean(differences)),
            "confidence_interval_mm": [lower, upper],
            "interpretation": "Negative differences favour the compared method; only jointly executed pairs are included.",
        })
    return result


def paired_ablation_comparisons(
    outcomes: Iterable[Mapping[str, Any]], *, n_resamples: int = 200,
    confidence: float = 0.95, seed: int = 0,
) -> list[dict[str, Any]]:
    """Compare each F variant with the same patient's complete method."""
    rows = [row for row in outcomes if row["experiment"] == "F"]
    reference = {(row["patient_cluster"], row["repetition"], row["method"]): row
                 for row in rows if row["variant"] == "full"}
    groups = {}
    for row in rows:
        other = reference.get((row["patient_cluster"], row["repetition"], row["method"]))
        if row["variant"] == "full" or other is None or row["abstained"] or other["abstained"]:
            continue
        a, b = row.get("targeting_error"), other.get("targeting_error")
        if a is None or b is None or not np.isfinite(float(a)) or not np.isfinite(float(b)):
            continue
        groups.setdefault((row["method"], row["variant"]), []).append((float(a) - float(b), row["patient_cluster"]))
    result = []
    for index, ((method, variant), pairs) in enumerate(sorted(groups.items())):
        differences, labels = zip(*pairs)
        interval = cluster_bootstrap_interval(differences, labels, n_resamples=n_resamples,
                                              confidence=confidence, seed=seed + index)
        result.append({"experiment": "F", "method": method, "variant": variant, "baseline_variant": "full",
                       "n_pairs": len(pairs), "n_patients": len(set(labels)),
                       "mean_targeting_difference_mm": float(np.mean(differences)),
                       "confidence_interval_mm": list(interval),
                       "interpretation": "Positive differences indicate larger error after ablation; jointly executed pairs only."})
    return result


# ============================================================================
# research / visualisations
# ============================================================================

"""Publication-style figures generated only from recorded episode outcomes."""



from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np




COLOURS = {"static": "#687681", "velocity": "#d59023", "sinusoidal": "#178e87", "learned": "#8663b3"}
LABELS = {"static": "Constant position", "velocity": "Constant velocity", "sinusoidal": "Sinusoidal", "learned": "Learned"}


def _style(ax: Any, title: str, xlabel: str, ylabel: str) -> None:
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)


def _empty(ax: Any, message: str = "No evaluated finite outcomes") -> None:
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, color="#687681")


def _finite_plot(value: Any) -> bool:
    return value is not None and np.isfinite(float(value))


def _line_plot(
    ax: Any,
    rows: list[dict[str, Any]],
    xkey: str,
    ykey: str,
    *,
    executed_only: bool = False,
    bootstrap_samples: int = 200,
    confidence: float = 0.95,
) -> None:
    groups: dict[str, dict[float, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if executed_only and row.get("abstained"):
            continue
        if _finite_plot(row.get(xkey)) and _finite_plot(row.get(ykey)):
            label = row["method"]
            variant = row.get("variant", "full")
            if variant != "full":
                label += f" / {variant.replace('_', ' ')}"
            groups[label][float(row[xkey])].append(row)
    for method, values in sorted(groups.items()):
        x, y, lows, highs = [], [], [], []
        for value, group in sorted(values.items()):
            data = [float(row[ykey]) for row in group]
            lower, upper = cluster_bootstrap_interval(
                data, [row["patient_cluster"] for row in group], n_resamples=bootstrap_samples,
                confidence=confidence, seed=113,
            )
            estimate = float(np.mean(data))
            x.append(value)
            y.append(estimate)
            lows.append(max(0.0, estimate - lower) if np.isfinite(lower) else 0)
            highs.append(max(0.0, upper - estimate) if np.isfinite(upper) else 0)
        ax.errorbar(x, y, yerr=[lows, highs], marker="o", capsize=3, linewidth=1.6,
                    color=COLOURS.get(method.split(" / ")[0]), label=LABELS.get(method, method))
    if groups:
        ax.legend(fontsize=8)
    else:
        _empty(ax)


def export_figures(
    outcomes: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    bootstrap_samples: int = 200,
    confidence: float = 0.95,
) -> list[str]:
    """Export all ten figures; unavailable experiments are labelled explicitly."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    def save(fig: Any, filename: str) -> None:
        fig.tight_layout()
        patient_count = len({row["patient_cluster"] for row in outcomes})
        note = f"Synthetic scenarios; {patient_count} virtual patients."
        if filename[:2] in {"02", "04", "05", "06", "07", "10"}:
            note += f" Error bars: {confidence:.0%} patient-cluster bootstrap intervals."
        if filename[:2] in {"03", "04", "05", "10"}:
            note += " Targeting uses executed plans."
        fig.text(.5, -.02, note, ha="center", fontsize=7, color="#687681")
        path = destination / filename
        fig.savefig(path, dpi=170, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        paths.append(str(path.resolve()))

    line_options = {"bootstrap_samples": bootstrap_samples, "confidence": confidence}
    with plt.rc_context({"font.size": 10, "axes.titlesize": 12, "figure.figsize": (7.2, 4.6)}):
        fig, ax = plt.subplots()
        plotted = False
        for trace in traces:
            time = np.asarray(trace.get("time", []), dtype=float)
            actual = np.asarray(trace.get("actual", trace.get("actual_displacement", [])), dtype=float)
            predicted = np.asarray(trace.get("predicted", trace.get("predicted_displacement", [])), dtype=float)
            if not len(time) or not len(actual):
                continue
            if actual.ndim == 2:
                actual = actual[:, 2]
            if predicted.ndim == 2:
                predicted = predicted[:, 2]
            if not plotted and len(time) == len(actual):
                ax.plot(time, actual - actual[0], color="#242b32", linewidth=2, label="Actual")
                plotted = True
            if len(predicted) == len(time) and np.isfinite(predicted).any():
                ax.plot(time, predicted - actual[0], linestyle="--", color=COLOURS.get(trace.get("method")),
                        label=LABELS.get(trace.get("method"), trace.get("method", "Predicted")))
        _style(ax, "Recorded respiratory displacement", "Time (s)", "Superior–inferior displacement (mm)")
        if plotted:
            ax.legend(fontsize=8)
        else:
            _empty(ax, "No episode trace recorded")
        save(fig, "01_predicted_actual_displacement.png")

        fig, ax = plt.subplots()
        rows = [row for row in outcomes if row["experiment"] == "B"]
        _line_plot(ax, rows, "forecast_horizon", "forecast_error", **line_options)
        _style(ax, "Forecast error at fixed future horizons", "Forecast horizon (s)", "Mean forecast error (mm)")
        save(fig, "02_prediction_error_horizon.png")

        fig, ax = plt.subplots()
        rows = [row for row in outcomes if row["experiment"] == "A"]
        groups = defaultdict(list)
        for row in rows:
            if not row.get("abstained") and _finite_plot(row.get("targeting_error")):
                groups[row["method"]].append(float(row["targeting_error"]))
        if groups:
            methods = sorted(groups)
            totals = {method: sum(row["method"] == method for row in rows) for method in methods}
            labels = [f"{LABELS.get(method, method)}\nn={len(groups[method])}/{totals[method]} executed" for method in methods]
            boxes = ax.boxplot([groups[method] for method in methods], tick_labels=labels,
                               patch_artist=True, showmeans=True)
            for box, method in zip(boxes["boxes"], methods):
                box.set_facecolor(COLOURS.get(method, "#687681"))
                box.set_alpha(0.55)
            unavailable = sorted({row["method"] for row in rows} - set(groups))
            if unavailable:
                ax.text(.01, .99, "No executed outcomes: " + ", ".join(LABELS.get(method, method) for method in unavailable),
                        transform=ax.transAxes, va="top", fontsize=8, color="#687681")
        else:
            _empty(ax)
        _style(ax, "Realised targeting error", "Planning method", "Targeting error (mm)")
        save(fig, "03_targeting_error_methods.png")

        fig, ax = plt.subplots()
        _line_plot(ax, rows, "amplitude", "targeting_error", executed_only=True, **line_options)
        _style(ax, "Targeting under increasing respiratory motion", "Respiratory amplitude (mm)", "Mean targeting error (mm)")
        save(fig, "04_targeting_error_amplitude.png")

        fig, ax = plt.subplots()
        rows = [row for row in outcomes if row["experiment"] == "C"]
        _line_plot(ax, rows, "delay", "targeting_error", executed_only=True, **line_options)
        _style(ax, "Execution-delay sensitivity", "Execution delay (s)", "Mean targeting error (mm)")
        save(fig, "05_targeting_error_delay.png")

        fig, ax = plt.subplots()
        _line_plot(ax, rows, "irregularity", "hit", **line_options)
        _style(ax, "Target hits under irregular breathing", "Breathing irregularity (relative)", "Hit rate per attempted episode")
        ax.set_ylim(-0.04, 1.04)
        save(fig, "06_hit_rate_irregular_breathing.png")

        fig, ax = plt.subplots()
        rows = [row for row in outcomes if row["experiment"] == "D"]
        _line_plot(ax, rows, "risk_tolerance", "obstacle_violation", executed_only=True, **line_options)
        _style(ax, "Risk tolerance and realised obstacle violations", "Allowed planning risk", "Obstacle violation rate among executed plans")
        ax.set_ylim(-0.04, 1.04)
        save(fig, "07_obstacle_violations_risk.png")

        fig, ax = plt.subplots()
        groups = defaultdict(list)
        for row in rows:
            groups[(row["method"], row["risk_tolerance"])].append(row)
        by_method = defaultdict(dict)
        for (method, risk), group in groups.items():
            abstention = float(np.mean([bool(row["abstained"]) for row in group]))
            success = float(np.mean([bool(row["hit"]) and not bool(row["abstained"]) for row in group]))
            by_method[method].setdefault((abstention, success), []).append(risk)
        markers = ("o", "s", "^", "D")
        for index, (method, coordinates) in enumerate(sorted(by_method.items())):
            points = np.asarray(list(coordinates))
            ax.scatter(points[:, 0], points[:, 1], color=COLOURS.get(method), s=42,
                       marker=markers[index % len(markers)], label=LABELS.get(method, method), alpha=.8)
            for point, risks in coordinates.items():
                ax.annotate("r=" + ",".join(f"{risk:g}" for risk in sorted(risks)), point,
                            xytext=(6, 9 - index * 13), textcoords="offset points", fontsize=7,
                            color=COLOURS.get(method))
        if not groups:
            _empty(ax)
        else:
            ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.01, .5))
        _style(ax, "Abstention and simulated success", "Abstention rate", "Hit rate per attempted episode")
        ax.set(xlim=(-0.06, 1.06), ylim=(-0.06, 1.06))
        save(fig, "08_abstention_success.png")

        fig, ax = plt.subplots()
        groups = defaultdict(list)
        for row in outcomes:
            if _finite_plot(row.get("planning_latency_ms")):
                groups[row["method"]].append(float(row["planning_latency_ms"]))
        if groups:
            methods = sorted(groups)
            ax.boxplot([groups[method] for method in methods], tick_labels=[LABELS.get(method, method) for method in methods], showfliers=False)
        else:
            _empty(ax)
        _style(ax, "Measured planning latency, including abstention", "Planning method", "Planning latency (ms)")
        save(fig, "09_planning_latency_distributions.png")

        fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.1))
        for ax, kind, label in zip(axes, ("time_step", "spatial_resolution", "integration_step"),
                                   ("Insertion time step (s)", "Trajectory sample spacing (mm)", "Motion integration step (s)")):
            selected = [row for row in outcomes if row["experiment"] == "E" and row["condition_type"] == kind]
            metric = "clearance_discretisation_error" if kind == "spatial_resolution" else "targeting_change_from_finest"
            ylabel = "Mean clearance discrepancy (mm)" if kind == "spatial_resolution" else "Mean targeting change from finest (mm)"
            _line_plot(ax, selected, "condition_value", metric, executed_only=True, **line_options)
            _style(ax, kind.replace("_", " ").capitalize(), label, ylabel)
        fig.suptitle("Numerical sensitivity: paired patients at each resolution", y=1.04)
        save(fig, "10_numerical_sensitivity.png")
    return paths


# ============================================================================
# research / experiments
# ============================================================================

"""Controlled, paired synthetic experiments with inspectable exports."""



import csv
from collections import defaultdict
from collections.abc import Mapping
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import yaml










RESEARCH_DEFAULTS = {
    "seed": 104729,
    "patients": 4,
    "repetitions": 1,
    "bootstrap_samples": 200,
    "confidence": 0.95,
    "experiments": ["A", "B", "C", "D", "E", "F"],
    "methods": ["static", "sinusoidal", "learned"],
    "amplitudes": [0.0, 6.0, 12.0, 20.0],
    "forecast_delays": [0.25, 1.0, 2.0],
    "delays": [0.25, 1.0, 2.0],
    "irregularities": [0.0, 0.2, 0.5],
    "risk_tolerances": [0.01, 0.1, 0.25],
    "time_steps": [0.1, 0.05, 0.025],
    "spatial_resolutions": [4.0, 2.0, 1.0],
    "integration_steps": [0.04, 0.02, 0.01],
    "episode": {
        "risk_tolerance": 0.1,
        "dt": 0.05,
        "history_duration": 8.0,
        "history_step": 0.1,
        "spatial_resolution": 2.0,
        "integration_step": 0.02,
        "delay_aware": True,
        "uncertainty": True,
    },
}


def _configuration(config: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(config)
    if isinstance(source.get("research"), Mapping):
        source = dict(source["research"])
    elif isinstance(source.get("experiments"), Mapping):
        source = dict(source["experiments"])
    result = {**RESEARCH_DEFAULTS, **source}
    result["episode"] = {**RESEARCH_DEFAULTS["episode"], **source.get("episode", {})}
    for key in ("patients", "repetitions", "bootstrap_samples"):
        if not isinstance(result[key], int) or result[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if not 0 < result["confidence"] < 1:
        raise ValueError("confidence must be between zero and one")
    if not result["experiments"] or set(result["experiments"]) - set("ABCDEF"):
        raise ValueError("experiments must contain one or more of A, B, C, D, E, F")
    if not result["methods"] or set(result["methods"]) - {"static", "velocity", "sinusoidal", "learned"}:
        raise ValueError("Unknown prediction/planning method")
    for key in ("amplitudes", "forecast_delays", "delays", "irregularities", "risk_tolerances", "time_steps", "spatial_resolutions", "integration_steps"):
        if not result[key] or any(not np.isfinite(float(value)) or float(value) < 0 for value in result[key]):
            raise ValueError(f"{key} must contain finite nonnegative values")
    for key in ("time_steps", "spatial_resolutions", "integration_steps"):
        if min(result[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    if any(not 0 <= value <= 1 for value in result["risk_tolerances"]):
        raise ValueError("risk_tolerances must be between zero and one inclusive")
    if max(result["irregularities"]) > 1:
        raise ValueError("irregularities must be between zero and one")
    return result


def _patient_bank(config: dict[str, Any]) -> list[dict[str, Any]]:
    rng = np.random.default_rng(config["seed"])
    bank = []
    for index in range(config["patients"]):
        bank.append({
            "patient_cluster": f"patient-{index:04d}",
            "seed": int(rng.integers(100_000_000, 2_000_000_000)),
            "amplitude": float(rng.uniform(7.0, 16.0)),
            "frequency": float(rng.uniform(0.18, 0.34)),
            "irregularity": float(rng.uniform(0.05, 0.2)),
            "target_radius": float(rng.uniform(3.5, 7.0)),
            "noise": float(rng.uniform(0.2, 0.8)),
            "delay": float(rng.uniform(0.5, 1.5)),
            "insertion_speed": float(rng.uniform(45.0, 75.0)),
        })
    return bank


def _conditions(config: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = []

    def add(experiment: str, kind: str, value: float, *, patient: dict | None = None,
            episode: dict | None = None, methods: list[str] | None = None, variant: str = "full", suffix: str = "") -> None:
        conditions.append({
            "experiment": experiment,
            "condition_type": kind,
            "condition_value": float(value),
            "condition": f"{kind}={value:g}{suffix}",
            "patient_changes": patient or {},
            "episode_changes": episode or {},
            "methods": methods or config["methods"],
            "variant": variant,
        })

    if "A" in config["experiments"]:
        for amplitude in config["amplitudes"]:
            add("A", "amplitude", amplitude, patient={"amplitude": amplitude})
    if "B" in config["experiments"]:
        methods = list(dict.fromkeys(["static", "velocity", "sinusoidal", *config["methods"]]))
        for delay in config["forecast_delays"]:
            add("B", "forecast_delay", delay, patient={"delay": delay}, methods=methods)
    if "C" in config["experiments"]:
        for irregularity in config["irregularities"]:
            for delay in config["delays"]:
                add("C", "irregularity", irregularity, patient={"irregularity": irregularity, "delay": delay}, suffix=f";delay={delay:g}")
    if "D" in config["experiments"]:
        for risk in config["risk_tolerances"]:
            add("D", "risk_tolerance", risk, episode={"risk_tolerance": risk})
    if "E" in config["experiments"]:
        methods = [method for method in config["methods"] if method != "static"] or ["static"]
        for key, values, argument in (("time_step", config["time_steps"], "dt"),
                                      ("spatial_resolution", config["spatial_resolutions"], "spatial_resolution"),
                                      ("integration_step", config["integration_steps"], "integration_step")):
            for value in values:
                add("E", key, value, episode={argument: value}, methods=methods)
    if "F" in config["experiments"]:
        for index, (variant, changes) in enumerate((
            ("full", {}),
            ("without_uncertainty", {"uncertainty": False}),
            ("without_delay_awareness", {"delay_aware": False}),
            ("short_history", {"history_duration": 0.4}),
        )):
            add("F", "ablation", index, episode=changes, variant=variant)
    return conditions


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        serialised = []
        for row in rows:
            converted = {}
            for key, value in row.items():
                value = _json_safe(value)
                converted[key] = json.dumps(value, allow_nan=False) if isinstance(value, (list, dict)) else value
            serialised.append(converted)
        writer.writerows(serialised)


def _software_versions(checkpoint: str | None) -> dict[str, Any]:
    versions: dict[str, Any] = {"python": sys.version, "platform": platform.platform()}
    for package in ("motiontwin", "numpy", "scipy", "torch", "pandas", "matplotlib", "PyYAML", "SimpleITK"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed as a distribution"
    versions["checkpoint"] = None
    if checkpoint:
        path = Path(checkpoint).resolve()
        import torch

        state = torch.load(path, map_location="cpu", weights_only=True)
        versions["checkpoint"] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "checkpoint_version": state.get("checkpoint_version"),
                                  "feature_version": state.get("feature_version"),
                                  "training_config": state.get("config"),
                                  "patient_seeds_by_split": state.get("patient_seeds_by_split"),
                                  "training_versions": state.get("versions")}
    return versions


def _validate_seed_provenance(patients: list[dict[str, Any]], versions: dict[str, Any]) -> bool:
    checkpoint = versions.get("checkpoint")
    if not checkpoint or not checkpoint.get("patient_seeds_by_split"):
        return False
    seen = {int(seed) for split, seeds in checkpoint["patient_seeds_by_split"].items()
            if split in {"train", "validation", "calibration"} for seed in seeds}
    overlap = seen & {int(patient["seed"]) for patient in patients}
    if overlap:
        raise ValueError(f"Evaluation patient seeds overlap training/validation/calibration patients: {sorted(overlap)}")
    return True


def _numerical_stability(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for row in rows:
        if row["experiment"] == "E" and not row["abstained"]:
            groups[(row["condition_type"], row["method"])].append(row)
    results = []
    for (kind, method), group in sorted(groups.items()):
        finest = min(row["condition_value"] for row in group)
        reference = {(row["patient_cluster"], row["repetition"]): row for row in group if row["condition_value"] == finest}
        for value in sorted({row["condition_value"] for row in group}):
            changes = []
            for row in group:
                other = reference.get((row["patient_cluster"], row["repetition"]))
                if other is None or row["condition_value"] != value:
                    continue
                a, b = row.get("targeting_error"), other.get("targeting_error")
                if a is not None and b is not None and np.isfinite(float(a)) and np.isfinite(float(b)):
                    changes.append(abs(float(a) - float(b)))
            results.append({"parameter": kind, "method": method, "value": value, "reference_value": finest,
                            "n_pairs": len(changes), "mean_absolute_targeting_change_mm": float(np.mean(changes)) if changes else None})
    return results


def _add_numerical_references(rows: list[dict[str, Any]]) -> None:
    groups = defaultdict(list)
    for row in rows:
        if row["experiment"] == "E":
            groups[(row["condition_type"], row["method"], row["patient_cluster"], row["repetition"])].append(row)
    for group in groups.values():
        reference = min(group, key=lambda row: row["condition_value"])
        for row in group:
            a, b = row.get("targeting_error"), reference.get("targeting_error")
            if not row["abstained"] and not reference["abstained"] and a is not None and b is not None and np.isfinite(float(a)) and np.isfinite(float(b)):
                row["targeting_change_from_finest"] = abs(float(a) - float(b))
            row["finest_tested_resolution"] = reference["condition_value"]
            exact, sampled = row.get("exact_clearance"), row.get("sampled_clearance")
            if exact is not None and sampled is not None and np.isfinite(float(exact)) and np.isfinite(float(sampled)):
                row["clearance_discretisation_error"] = abs(float(sampled) - float(exact))


def _independent_forecast(patient: VirtualPatient, episode: dict[str, Any], horizon: float,
                          method: str, checkpoint: str | None) -> dict[str, Any]:
    """Evaluate a causal predictor even if its associated planner abstains."""
    motion = RespiratoryModel(patient, integration_step=episode["integration_step"])
    times = np.arange(0, episode["history_duration"] + episode["history_step"] / 2, episode["history_step"])
    positions = motion.observe(times, np.zeros(3))
    variability = episode.get("cycle_variability", 0.0)
    positions += motion.displacement(times) * (_cycle_gain(patient, times, variability) - 1)[..., None]
    future = times[-1] + horizon
    truth = motion.displacement(future) * _cycle_gain(patient, future, variability)
    result = {"forecast_error": float("nan"), "forecast_coverage": float("nan"),
              "forecast_horizon": horizon, "forecast_evaluation": "fixed horizon independent of planning acceptance"}
    try:
        prediction = forecast(times, positions, horizon, method=method, checkpoint=checkpoint)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        result["forecast_reason"] = str(exc)
        return result
    residual = truth - prediction.mean
    result["forecast_error"] = float(np.linalg.norm(residual))
    if prediction.calibrated and np.isfinite(prediction.mahalanobis_quantile):
        result["forecast_coverage"] = bool(residual @ np.linalg.pinv(prediction.covariance) @ residual <= prediction.mahalanobis_quantile)
    return result


def _forecast_trace(patient: VirtualPatient, episode: dict[str, Any], methods: list[str],
                    checkpoint: str | None, horizon: float) -> list[dict[str, Any]]:
    """Forecast a curve from one fixed observed history, without future frames."""
    motion = RespiratoryModel(patient, integration_step=episode["integration_step"])
    times = np.arange(0, episode["history_duration"] + episode["history_step"] / 2, episode["history_step"])
    positions = motion.observe(times, np.zeros(3))
    variability = episode.get("cycle_variability", 0.0)
    positions += motion.displacement(times) * (_cycle_gain(patient, times, variability) - 1)[..., None]
    horizons = np.linspace(0.0, max(4.0, horizon), 45)
    future_times = times[-1] + horizons
    actual = motion.displacement(future_times) * _cycle_gain(patient, future_times, variability)[..., None]
    traces = []
    for method in methods:
        predicted = []
        reasons = set()
        for ahead in horizons:
            try:
                predicted.append(forecast(times, positions, ahead, method=method, checkpoint=checkpoint).mean.tolist())
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                predicted.append([float("nan")] * 3)
                reasons.add(str(exc))
        traces.append({"time": future_times.tolist(), "actual": actual.tolist(), "predicted": predicted,
                       "method": method, "patient_seed": patient.seed, "observation_end": float(times[-1]),
                       "description": "All horizons forecast from one fixed causal history", "unavailable_reasons": sorted(reasons)})
    return traces


def run_experiments(config: dict, output_dir: str = "outputs/experiments", checkpoint: str | None = None) -> dict:
    """Run actual A–F simulations and export the complete reproducibility bundle.

    Repeated episodes are deterministic replays of the same patient and remain
    in one bootstrap cluster. A missing learned checkpoint records abstention.
    """
    settings = _configuration(config)
    if checkpoint and not Path(checkpoint).is_file():
        raise FileNotFoundError(f"Learned checkpoint does not exist: {checkpoint}")
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    patients = _patient_bank(settings)
    conditions = _conditions(settings)
    outcomes: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    trace_scenario = None
    trace_case = None
    with (destination / "config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(_json_safe(settings), handle, sort_keys=False)
    _write_csv(destination / "patient_seeds.csv", patients)
    versions = _software_versions(checkpoint)
    split_verified = _validate_seed_provenance(patients, versions)
    (destination / "software_versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")

    for condition_index, condition in enumerate(conditions):
        for patient_index, patient_definition in enumerate(patients):
            for repetition in range(settings["repetitions"]):
                patient_parameters = {key: value for key, value in patient_definition.items() if key != "patient_cluster"}
                patient_parameters.update(condition["patient_changes"])
                # Repetitions retain anatomical identity and identical observation
                # noise. They measure replay stability, not independent patients.
                scenario_id = f"{condition['experiment']}-{condition_index:03d}-{patient_index:04d}-{repetition:03d}"
                episode_parameters = {**settings["episode"], **condition["episode_changes"]}
                for method in condition["methods"]:
                    patient = VirtualPatient(**patient_parameters)
                    outcome = dict(run_episode(patient, method=method, checkpoint=checkpoint, **episode_parameters))
                    trace = outcome.pop("trace", None)
                    row = {"experiment": condition["experiment"], "scenario_id": scenario_id,
                           "patient_cluster": patient_definition["patient_cluster"], "repetition": repetition,
                           "condition": condition["condition"], "condition_type": condition["condition_type"],
                           "condition_value": condition["condition_value"], "variant": condition["variant"],
                           **patient_parameters, **episode_parameters, **outcome, "method": method,
                           "checkpoint_available": bool(checkpoint)}
                    # The endpoint horizon includes both execution delay and insertion
                    # travel. It must come from the simulator, never a relabelled delay.
                    row["forecast_horizon"] = outcome.get("forecast_horizon", outcome.get("horizon"))
                    row["forecast_evaluation"] = "realised arrival of an executed plan"
                    if condition["experiment"] == "B":
                        row["planned_arrival_forecast_error"] = row.get("forecast_error")
                        row.update(_independent_forecast(patient, episode_parameters, condition["condition_value"], method, checkpoint))
                    row = {key: value for key, value in row.items() if np.isscalar(value) or value is None}
                    outcomes.append(row)
                    if trace and patient_parameters["amplitude"] > 0:
                        if trace_scenario is None:
                            trace_scenario = scenario_id
                            trace_case = (patient_parameters, episode_parameters)
                        if scenario_id == trace_scenario:
                            traces.append({**trace, "method": method, "scenario_id": scenario_id})

    if trace_case is not None:
        parameters, episode = trace_case
        traces = _forecast_trace(VirtualPatient(**parameters), episode, list(dict.fromkeys([*settings["methods"], "velocity"])),
                                 checkpoint, max(settings["forecast_delays"]))
    _add_numerical_references(outcomes)
    _write_csv(destination / "outcomes.csv", outcomes)
    groups = defaultdict(list)
    for row in outcomes:
        groups[(row["experiment"], row["condition"], row["method"], row["variant"])].append(row)
    summaries = []
    for index, ((experiment, condition, method, variant), group) in enumerate(sorted(groups.items())):
        summaries.append({"experiment": experiment, "condition": condition, "method": method, "variant": variant,
                          **summarise_with_intervals(group, n_resamples=settings["bootstrap_samples"],
                                                    confidence=settings["confidence"], seed=settings["seed"] + index)})
    contrasts = paired_comparisons(outcomes, n_resamples=settings["bootstrap_samples"], confidence=settings["confidence"], seed=settings["seed"])
    ablation_contrasts = paired_ablation_comparisons(outcomes, n_resamples=settings["bootstrap_samples"], confidence=settings["confidence"], seed=settings["seed"])
    flat_summaries = []
    for group in summaries:
        flat = {key: value for key, value in group.items() if key not in {"metrics", "confidence_intervals"}}
        flat.update(group["metrics"])
        for metric, (lower, upper) in group["confidence_intervals"].items():
            flat[f"{metric}_ci_lower"] = lower
            flat[f"{metric}_ci_upper"] = upper
        flat_summaries.append(flat)
    _write_csv(destination / "summary.csv", flat_summaries)
    _write_csv(destination / "paired_comparisons.csv", contrasts)
    _write_csv(destination / "paired_ablations.csv", ablation_contrasts)
    (destination / "representative_traces.json").write_text(json.dumps(_json_safe(traces), indent=2, allow_nan=False), encoding="utf-8")
    plots = export_figures(outcomes, traces, destination / "figures", bootstrap_samples=settings["bootstrap_samples"], confidence=settings["confidence"])
    limitations = [
        "All experiments use generated synthetic anatomy and breathing, not measured patient scans.",
        "Patient-clustered percentile bootstrap intervals are descriptive and unstable with very small patient counts; intervals are unavailable for one patient.",
        "Hit rate includes abstentions as unsuccessful attempts; obstacle-violation rate and targeting error condition on executed plans.",
        "Paired targeting contrasts include only jointly executed scenarios; abstention rates must be reviewed alongside them.",
        "Planning latency is measured wall-clock time and depends on hardware, warm-up and concurrent activity.",
        "Uncertainty and delay-awareness removal are evaluated; short history uses 0.4 seconds and is not complete history removal or feature retraining.",
        "Patient-specific adjustment ablation is not separately implemented.",
        "Optional repetitions replay identical patient seeds; they are not independent clinical cases.",
    ]
    if not checkpoint:
        limitations.append("No learned checkpoint supplied: learned plans abstain and no learned performance is inferred.")
    elif not split_verified:
        limitations.append("Checkpoint has no patient-seed provenance; evaluation disjointness cannot be verified.")
    result = {"output_dir": str(destination), "completed_experiments": sorted(set(row["experiment"] for row in outcomes)),
              "outcome_count": len(outcomes), "patient_count": len(patients), "seed": settings["seed"],
              "checkpoint_patient_disjointness_verified": split_verified,
              "bootstrap_unit": "virtual patient", "summary": summaries, "paired_comparisons": contrasts,
              "paired_ablations": ablation_contrasts,
              "numerical_stability": _numerical_stability(outcomes), "software_versions": versions,
              "plots": plots, "limitations": limitations,
              "files": {"config": str(destination / "config.yaml"), "patient_seeds": str(destination / "patient_seeds.csv"),
                        "outcomes": str(destination / "outcomes.csv"), "summary_csv": str(destination / "summary.csv"),
                        "summary_json": str(destination / "summary.json"), "paired_comparisons": str(destination / "paired_comparisons.csv"),
                        "paired_ablations": str(destination / "paired_ablations.csv"),
                        "traces": str(destination / "representative_traces.json"), "software_versions": str(destination / "software_versions.json")}}
    result = _json_safe(result)
    (destination / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


if __name__=="__main__":
    import sys
    sys.modules["motiontwin"]=sys.modules[__name__]
    from run import main
    raise SystemExit(main())
