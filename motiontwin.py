from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from pathlib import Path
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import BadZipFile
import json
import os
import shutil

import numpy as np
from scipy import ndimage
from scipy.ndimage import map_coordinates
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import CubicHermiteSpline

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



@dataclass(frozen=True)
class StructureStyle:
    name: str
    color: str
    opacity: float = .35
    visible: bool = True
    ct_coloring: bool = True
    kind: str = "lung"

    def __post_init__(self):
        if (not isinstance(self.name, str)
                or any(character in self.name for character in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")):
            raise ValueError("A structure name must be a single line of at most 80 characters.")
        name = self.name.strip()
        if not name or len(name) > 80:
            raise ValueError("A structure name must be a nonblank single line of at most 80 characters.")
        if (not isinstance(self.color, str) or len(self.color) != 7
                or not self.color.startswith("#")
                or any(character not in "0123456789abcdefABCDEF" for character in self.color[1:])):
            raise ValueError("A structure color must use #RRGGBB hexadecimal notation.")
        if (isinstance(self.opacity, (bool, np.bool_))
                or not isinstance(self.opacity, (int, float, np.integer, np.floating))
                or not np.isfinite(self.opacity) or not 0 <= self.opacity <= 1):
            raise ValueError("Structure opacity must be finite and between 0 and 1.")
        if type(self.visible) is not bool or type(self.ct_coloring) is not bool:
            raise ValueError("Structure visibility and CT coloring must be boolean values.")
        if not isinstance(self.kind, str) or self.kind not in ("lung", "other"):
            raise ValueError("Structure kind must be lung or other.")
        object.__setattr__(self, "name", name)



@dataclass
class SlicePlane:
    """rows increase along v, columns along u; coordinates are pixel centres.

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
        rows, columns = np.indices(self.shape, dtype=float)
        return self.pixel_to_world(np.stack((columns, rows), axis=-1))



@dataclass
class Volume:
    """array indexing is z,y,x; physical metadata is x,y,z in LPS millimetres."""

    data: np.ndarray
    spacing: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    direction: np.ndarray = field(default_factory=lambda: np.eye(3))
    name: str = "CT volume"

    def __post_init__(self):
        self.data = np.asarray(self.data)
        self.spacing = tuple(float(value) for value in self.spacing)
        self.origin = tuple(float(value) for value in self.origin)
        self.direction = np.asarray(self.direction, dtype=float).reshape(3, 3)
        if self.data.ndim != 3 or 0 in self.data.shape:
            raise ValueError("A volume must contain a non-empty 3D scalar z,y,x array.")
        if self.data.dtype.kind not in "buif":
            raise ValueError("Image intensities must be real numeric values.")
        if self.data.dtype.kind == "f" and any(not np.isfinite(section).all() for section in self.data):
            raise ValueError("Image intensities must be finite.")
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
        """sample source voxels directly and return floating-point HU values.

        sub-voxel values are preserved without copying an integer 3D source
        into floating-point storage.
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
        """sample the exact physical grid of another SlicePlane.

        the optional mapper converts output-world positions to source-world
        positions, including an inverse deformation without a 3D frame.
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
        section = self.slice_grid(plane, crosshair, max_pixels=max_pixels)
        return self.reslice_like(section, interpolation=interpolation,
                                 coordinate_mapper=coordinate_mapper, cval=cval)

    def slice_grid(self, plane, crosshair, *, max_pixels=1024):
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
        raise ValueError("Select a 3D scalar CT image. This viewer supports static scans.")
    return Volume(sitk.GetArrayFromImage(image), image.GetSpacing(), image.GetOrigin(),
                  np.array(image.GetDirection()).reshape(3, 3), name)



def load_volume(path):
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
        try:
            image = reader.Execute()
        except RuntimeError as error:
            raise ValueError("The selected DICOM series could not be read. Choose a complete, supported CT series.") from error
    else:
        if not path.is_file():
            raise FileNotFoundError(f"The CT or mask file no longer exists: {path.name}")
        try:
            image = sitk.ReadImage(str(path))
        except RuntimeError as error:
            raise ValueError("This file could not be read. Choose a supported NIfTI, NRRD or MetaImage volume.") from error
    return _from_sitk(image, path.name)



def save_volume(volume, path):
    import SimpleITK as sitk
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(_to_sitk(volume), str(path), True)



def load_segmentation(path, reference: Volume, *, resample=False):
    mask = load_volume(path)
    if any(np.any(section < 0) or not np.equal(section, np.rint(section)).all()
           for section in mask.data):
        raise ValueError("A segmentation must contain discrete nonnegative labels, not image intensities or probabilities.")
    if not mask.same_geometry(reference):
        if not resample:
            raise ValueError("Segmentation geometry does not match its CT. Supply an aligned mask or explicitly resample it.")
        import SimpleITK as sitk
        image = sitk.Resample(_to_sitk(mask), _to_sitk(reference), sitk.Transform(),
                              sitk.sitkNearestNeighbor, 0, sitk.sitkUInt16)
        mask = _from_sitk(image, mask.name)
    return mask



def load_mask(path, reference: Volume, *, label=None, resample=False):
    if label is not None and (not np.isfinite(label) or label < 0 or int(label) != label):
        raise ValueError("A segmentation label must be a nonnegative integer.")
    mask = load_segmentation(path, reference, resample=resample)
    return np.asarray(mask.data == label if label is not None else mask.data > 0, dtype=bool)



def mesh_from_mask(mask, volume: Volume, *, smooth_iterations=8):
    import pyvista as pv
    mask = np.asarray(mask, dtype=bool)
    if mask.shape != volume.shape:
        raise ValueError("Mask array must match the reference volume's z,y,x shape.")
    if not np.any(mask):
        return pv.PolyData()
    # padding closes structures touching an image boundary.
    padded = np.pad(mask, 1)
    grid = pv.ImageData(dimensions=padded.shape[::-1], spacing=volume.spacing,
                        origin=-np.asarray(volume.spacing))
    grid.point_data["structure"] = padded.astype(np.uint8).ravel(order="C")
    mesh = grid.contour([0.5], scalars="structure").triangulate()
    if smooth_iterations:
        mesh = mesh.smooth(n_iter=int(smooth_iterations), relaxation_factor=0.08)
    mesh.points = mesh.points @ volume.direction.T + np.asarray(volume.origin)
    return mesh



def _bounded_surface(mesh, max_cells):
    if mesh.n_cells > max_cells:
        mesh = mesh.decimate(1.0 - max_cells / mesh.n_cells)
    return mesh



def attach_ct_scalars(mesh, volume, *, inset_mm=0.0):
    """sample source HU at surface points in LPS millimetres.

    inset_mm samples inward along surface normals without moving vertices.
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



DISPLAY_MAX_CELLS = 40000


def prepare_display_meshes(volume, masks, *, max_cells=DISPLAY_MAX_CELLS):
    """prepare bounded CT-linked surfaces without modifying the volume or masks."""
    if isinstance(max_cells, bool) or int(max_cells) != max_cells or max_cells < 100:
        raise ValueError("Display surface cell limit must be an integer of at least 100.")
    result = {}
    for name, mask in masks.items():
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



SAMPLE_SHA256 = "4507b664690840abb6cb9af2d919377ffc4ef75b167cb6fd0f747befdb12e38e"
SAMPLE_URL = ("https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/"
              + SAMPLE_SHA256)
LICENSE_URL = "https://raw.githubusercontent.com/Slicer/Slicer/main/License.txt"
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 25
TOTAL_TIMEOUT_SECONDS = 180
DISPLAY_MASK_VERSION = "ct-threshold-display-v2"
DISPLAY_CACHE_VERSION = "static-ct-display-v1"
LUNG_DETAIL_THRESHOLD_HU = -450
LUNG_DETAIL_LABEL = "High-density lung detail (derived)"


def _digest(path):
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



def cached_public_sample_available(cache_dir="data/public-example"):
    """validate the optional local CT without downloading or creating files."""
    source = Path(cache_dir) / "CT-chest.nrrd"
    try:
        return (source.is_file() and 0 < source.stat().st_size <= MAX_DOWNLOAD_BYTES
                and _digest(source) == SAMPLE_SHA256)
    except OSError:
        return False



def _download_verified(url, destination, expected_digest, *, max_bytes=MAX_DOWNLOAD_BYTES,
                       socket_timeout=SOCKET_TIMEOUT_SECONDS,
                       total_timeout=TOTAL_TIMEOUT_SECONDS):
    """stream a bounded HTTPS file and replace the destination only after hashing."""
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
    """a small physical-radius morphology kernel on the unchanged source grid."""
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
    """derive lung envelopes and dense tissue layers from CT thresholds.

    these display masks are not verified anatomical segmentations.
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

    # physical opening suppresses the narrow trachea and detached bowel gas.
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



def _read_display_cache(path, volume):
    import pyvista as pv
    try:
        with np.load(path, allow_pickle=False) as saved:
            if (str(saved["version"].item()) != DISPLAY_CACHE_VERSION
                    or str(saved["source_sha256"].item()) != SAMPLE_SHA256
                    or str(saved["mask_version"].item()) != DISPLAY_MASK_VERSION
                    or int(saved["max_cells"].item()) != DISPLAY_MAX_CELLS
                    or not np.array_equal(saved["shape"], volume.shape)
                    or not np.array_equal(saved["spacing"], volume.spacing)
                    or not np.array_equal(saved["origin"], volume.origin)
                    or not np.array_equal(saved["direction"], volume.direction)):
                return None
            masks, meshes = {}, {}
            count = int(np.prod(volume.shape))
            for name in ("left_lung", "right_lung", "vascular_display"):
                packed = saved[f"{name}_mask"]
                if packed.dtype != np.uint8 or packed.shape != ((count+7)//8,):
                    return None
                masks[name] = np.unpackbits(packed, count=count).reshape(volume.shape).astype(bool)
                points, faces = saved[f"{name}_points"], saved[f"{name}_faces"]
                hu, rgb = saved[f"{name}_hu"], saved[f"{name}_rgb"]
                if (points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all()
                        or faces.ndim != 2 or faces.shape[1] != 4 or faces.dtype.kind not in "iu"
                        or len(faces) > DISPLAY_MAX_CELLS or not np.all(faces[:,0] == 3)
                        or np.any(faces[:,1:] < 0) or np.any(faces[:,1:] >= len(points))
                        or hu.shape != (len(points),) or not np.isfinite(hu).all()
                        or rgb.shape != (len(points),3) or rgb.dtype != np.uint8):
                    return None
                if len(points):
                    mesh = pv.PolyData(points, faces.ravel())
                    mesh.point_data["CT_HU"], mesh.point_data["CT_RGB"] = hu, rgb
                    mesh.field_data["CT_sampling_inset_mm"] = [min(volume.spacing)*.65 if "lung" in name else 0.]
                    mesh.field_data["source"] = ["reference CT in physical LPS millimetres"]
                    meshes[name] = mesh
            if not masks["left_lung"].any() or not masks["right_lung"].any():
                return None
            if np.any(masks["left_lung"] & masks["right_lung"]):
                return None
            return masks, meshes
    except (OSError, ValueError, KeyError, EOFError, BadZipFile):
        return None


def _write_display_cache(path, volume, masks, meshes):
    content = dict(version=np.array(DISPLAY_CACHE_VERSION), source_sha256=np.array(SAMPLE_SHA256),
                   mask_version=np.array(DISPLAY_MASK_VERSION), max_cells=np.array(DISPLAY_MAX_CELLS),
                   shape=np.array(volume.shape), spacing=np.array(volume.spacing),
                   origin=np.array(volume.origin), direction=volume.direction)
    for name, mask in masks.items():
        mesh = meshes.get(name)
        content[f"{name}_mask"] = np.packbits(mask.ravel())
        content[f"{name}_points"] = mesh.points if mesh is not None else np.empty((0,3))
        content[f"{name}_faces"] = mesh.faces.reshape(-1,4) if mesh is not None else np.empty((0,4),dtype=np.int64)
        content[f"{name}_hu"] = mesh["CT_HU"] if mesh is not None else np.empty(0)
        content[f"{name}_rgb"] = mesh["CT_RGB"] if mesh is not None else np.empty((0,3),dtype=np.uint8)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as output:
            np.savez_compressed(output, **content)
        os.replace(temporary, path)
    except OSError:
        pass  # a read-only data directory must not prevent viewing the scan.
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def load_public_sample(cache_dir="data/public-example"):
    """load the public CT and return its volume, masks, meshes and provenance.

    verified local data works offline; missing data requires a roughly 40 MB download.
    """
    cache_dir = Path(cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    source_path = cache_dir / "CT-chest.nrrd"
    if not cached_public_sample_available(cache_dir):
        try:
            _download_verified(SAMPLE_URL, source_path, SAMPLE_SHA256)
        except (OSError, ValueError) as error:
            raise RuntimeError("The optional public CT could not be downloaded and verified. "
                               "Check the connection or import a local CT volume.") from error
    volume = load_volume(source_path)
    volume.name = "Slicer CTChest — public static CT example"
    if np.issubdtype(volume.data.dtype, np.integer):
        # the public source can use int32 storage for ordinary CT HU values.
        # lossless int16 storage avoids retaining twice the required RAM.
        if np.min(volume.data) >= -32768 and np.max(volume.data) <= 32767:
            volume.data = volume.data.astype(np.int16, copy=False)
    display_path = cache_dir / "display-cache.npz"
    cached = _read_display_cache(display_path, volume)
    if cached is None:
        masks = derive_display_masks(volume)
        meshes = prepare_display_meshes(volume, masks)
        _write_display_cache(display_path, volume, masks, meshes)
    else:
        masks, meshes = cached
    bundled_license = Path(__file__).resolve().with_name("THIRD_PARTY_LICENSES.txt")
    license_path = cache_dir / "Slicer-CTChest-LICENSE.txt"
    if bundled_license.is_file():
        try:
            shutil.copyfile(bundled_license, license_path)
        except OSError:
            license_path = bundled_license
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
    try:
        (cache_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    except OSError:
        pass  # verified attribution is still returned when local metadata is read-only.
    return volume, masks, meshes, provenance


LOBE_SEGMENTS = (
    (1, "left_upper_lung_lobe", "Left upper lobe", "#80b18b"),
    (2, "left_lower_lung_lobe", "Left lower lobe", "#d8cc91"),
    (3, "right_upper_lung_lobe", "Right upper lobe", "#bb8c76"),
    (4, "right_middle_lung_lobe", "Right middle lobe", "#6db9cb"),
    (5, "right_lower_lung_lobe", "Right lower lobe", "#cf756b"),
)
LOBE_CACHE_VERSION = "lung-lobes-v1"


def _lobe_masks_and_styles(label_data, reference):
    labels = np.asarray(label_data)
    if (labels.shape != reference.shape or labels.dtype.kind not in "buif"
            or not np.isfinite(labels).all() or np.any(labels < 0)
            or np.any(labels > 5) or not np.equal(labels, np.rint(labels)).all()):
        raise ValueError("Lobe labels must match the CT grid and contain only integers from 0 to 5.")
    if not np.all(np.isin(np.arange(1, 6), np.unique(labels))):
        raise ValueError("The segmentation must contain all five lung lobes using labels 1 to 5.")
    masks = {key: labels == label for label, key, _, _ in LOBE_SEGMENTS}
    styles = {key: StructureStyle(name, color, .35, ct_coloring=False, kind="lung")
              for _, key, name, color in LOBE_SEGMENTS}
    return masks, styles


def load_lobe_segmentation(path, reference):
    image = load_segmentation(path, reference)
    return _lobe_masks_and_styles(image.data, reference)


def _lobe_source_digest(volume):
    digest = sha256()
    geometry = dict(shape_zyx=list(volume.shape), spacing_xyz_mm=list(volume.spacing),
                    origin_lps_mm=list(volume.origin), direction=volume.direction.tolist())
    digest.update(json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for section in volume.data:
        canonical = np.array(section, dtype="<f8", order="C", copy=True)
        if not np.isfinite(canonical).all():
            raise ValueError("Lobe segmentation requires finite CT intensities.")
        canonical[canonical == 0] = 0
        digest.update(canonical.tobytes())
    return digest.hexdigest()


def _lobe_array_digest(arrays):
    digest = sha256()
    for array in arrays:
        array = np.ascontiguousarray(array)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(json.dumps(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _lobe_metadata(metadata, volume, label_data, source_digest):
    if not isinstance(metadata, dict):
        raise ValueError("Lobe provenance must be a metadata dictionary.")
    for name in ("method", "model", "model_version"):
        if not isinstance(metadata.get(name), str) or not metadata[name].strip():
            raise ValueError(f"Lobe provenance requires a nonblank {name}.")
    try:
        result = json.loads(json.dumps(metadata, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError("Lobe provenance must contain finite JSON-compatible values.") from error
    result.update(
        source_ct_sha256=source_digest,
        label_sha256=_lobe_array_digest([np.asarray(label_data, dtype=np.uint8)]),
        shape_zyx=list(volume.shape), spacing_xyz_mm=list(volume.spacing),
        origin_lps_mm=list(volume.origin), direction=volume.direction.tolist(),
        coordinate_system="LPS millimetres", expert_reviewed=False,
        segments=[dict(label=label, key=key, name=name, color=color)
                  for label, key, name, color in LOBE_SEGMENTS],
    )
    return result


def _valid_lobe_mesh_arrays(points, faces, hu, rgb, volume):
    if (points.ndim != 2 or points.shape[1] != 3 or points.dtype.kind != "f"
            or not len(points) or not np.isfinite(points).all()
            or faces.ndim != 2 or faces.shape[1] != 4 or faces.dtype.kind not in "iu"
            or not 0 < len(faces) <= DISPLAY_MAX_CELLS or not np.all(faces[:, 0] == 3)
            or np.any(faces[:, 1:] < 0) or np.any(faces[:, 1:] >= len(points))
            or hu.shape != (len(points),) or hu.dtype.kind not in "fiu"
            or not np.isfinite(hu).all()
            or rgb.shape != (len(points), 3) or rgb.dtype != np.uint8):
        return False
    indices = volume.world_to_index(points)
    return bool(np.all(indices >= -.6) and np.all(indices <= np.array(volume.shape[::-1]) - .4))


def build_lobe_cache(volume, label_data, metadata, cache_dir="data/lobes"):
    masks, styles = _lobe_masks_and_styles(label_data, volume)
    labels = np.asarray(label_data, dtype=np.uint8)
    source_digest = _lobe_source_digest(volume)
    metadata = _lobe_metadata(metadata, volume, labels, source_digest)
    meshes = prepare_display_meshes(volume, masks)
    metadata_json = json.dumps(metadata, sort_keys=True, allow_nan=False)
    content = dict(version=np.array(LOBE_CACHE_VERSION), max_cells=np.array(DISPLAY_MAX_CELLS),
                   metadata=np.array(metadata_json),
                   metadata_sha256=np.array(sha256(metadata_json.encode("utf-8")).hexdigest()),
                   labels=labels, source_ct_sha256=np.array(source_digest))
    for _, key, _, _ in LOBE_SEGMENTS:
        mesh = meshes.get(key)
        if mesh is None:
            raise ValueError("Every lung lobe must have a nonempty reconstructed surface.")
        arrays = (np.asarray(mesh.points), np.asarray(mesh.faces).reshape(-1, 4),
                  np.asarray(mesh["CT_HU"]), np.asarray(mesh["CT_RGB"]))
        if not _valid_lobe_mesh_arrays(*arrays, volume):
            raise ValueError("A reconstructed lung lobe has invalid surface data.")
        for suffix, array in zip(("points", "faces", "hu", "rgb"), arrays):
            content[f"{key}_{suffix}"] = array
        content[f"{key}_sha256"] = np.array(_lobe_array_digest(arrays))
    path = Path(cache_dir).resolve() / "lobe-cache.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.part")
    try:
        with temporary.open("xb") as output:
            np.savez_compressed(output, **content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return masks, meshes, styles, metadata


def load_lobe_cache(volume, cache_dir="data/lobes"):
    path = Path(cache_dir) / "lobe-cache.npz"
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as saved:
            if (str(saved["version"].item()) != LOBE_CACHE_VERSION
                    or int(saved["max_cells"].item()) != DISPLAY_MAX_CELLS):
                return None
            metadata_json = str(saved["metadata"].item())
            if (str(saved["metadata_sha256"].item())
                    != sha256(metadata_json.encode("utf-8")).hexdigest()):
                return None
            metadata = json.loads(metadata_json)
            if (not isinstance(metadata, dict) or metadata.get("shape_zyx") != list(volume.shape)
                    or metadata.get("spacing_xyz_mm") != list(volume.spacing)
                    or metadata.get("origin_lps_mm") != list(volume.origin)
                    or metadata.get("direction") != volume.direction.tolist()):
                return None
            source_digest = _lobe_source_digest(volume)
            if str(saved["source_ct_sha256"].item()) != source_digest:
                return None
            labels = saved["labels"]
            if labels.dtype != np.uint8:
                return None
            masks, styles = _lobe_masks_and_styles(labels, volume)
            if _lobe_metadata(metadata, volume, labels, source_digest) != metadata:
                return None
            import pyvista as pv
            meshes = {}
            for _, key, _, _ in LOBE_SEGMENTS:
                arrays = tuple(saved[f"{key}_{suffix}"] for suffix in ("points", "faces", "hu", "rgb"))
                if (not _valid_lobe_mesh_arrays(*arrays, volume)
                        or str(saved[f"{key}_sha256"].item()) != _lobe_array_digest(arrays)):
                    return None
                points, faces, hu, rgb = arrays
                mesh = pv.PolyData(points, faces.ravel())
                mesh.point_data["CT_HU"], mesh.point_data["CT_RGB"] = hu, rgb
                mesh.field_data["CT_sampling_inset_mm"] = [min(volume.spacing) * .65]
                mesh.field_data["source"] = ["reference CT in physical LPS millimetres"]
                meshes[key] = mesh
            return masks, meshes, styles, metadata
    except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile, OverflowError):
        return None


LOBE_WEIGHTS = {
    "LTRCLobes": ("unet_ltrclobes-3a07043d.pth",
                  "3a07043d9252efd04ece4adc9b47538b68f1a976b1bce6e4692b9f447e3f0665"),
    "R231": ("unet_r231-d5d2fc3d.pth",
             "d5d2fc3df432115933491f115b283e94d1f5c841c0e82f6e7bd2d65d3ccde69f"),
}


def generate_lobe_segmentation(volume, cache_dir="data/lobes"):
    cached = load_lobe_cache(volume, cache_dir)
    if cached is not None:
        return cached
    try:
        import torch
        from lungmask import LMInferer
        from importlib.metadata import version
    except ImportError as error:
        raise RuntimeError("Lobe generation requires the optional lungmask package. From this project folder run:\n"
                           '.\\.venv\\Scripts\\python.exe -m pip install ".[lobes]"\n'
                           "You can also import an existing aligned five-lobe label image.") from error
    weights = {}
    for name, (filename, digest) in LOBE_WEIGHTS.items():
        path = Path(cache_dir) / "models" / filename
        url = "https://github.com/JoHof/lungmask/releases/download/v0.0/" + filename
        if not path.is_file() or _digest(path) != digest:
            _download_verified(url, path, digest, max_bytes=140 * 1024 * 1024,
                               total_timeout=300)
        weights[name] = dict(path=str(path), url=url, sha256=digest, bytes=path.stat().st_size)
    previous_threads = torch.get_num_threads()
    started = monotonic()
    try:
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        inferer = LMInferer(modelname="LTRCLobes", modelpath=weights["LTRCLobes"]["path"],
                           fillmodel="R231", fillmodel_path=weights["R231"]["path"],
                           force_cpu=True, batch_size=1, tqdm_disable=True)
        labels = inferer.apply(_to_sitk(volume))
    finally:
        torch.set_num_threads(previous_threads)
    metadata = dict(method="automated lobe segmentation", model="LTRCLobes_R231",
                    model_version=version("lungmask"), weights=weights,
                    runtime_seconds=monotonic() - started,
                    model_url="https://github.com/JoHof/lungmask", license="Apache-2.0",
                    license_url="https://github.com/JoHof/lungmask/blob/master/LICENSE")
    return build_lobe_cache(volume, labels, metadata, cache_dir)


BREATHING_PATTERNS = ("Regular", "Mild irregularity", "Strong irregularity", "Stress test")


@dataclass(frozen=True)
class BreathingSettings:
    amplitude: float = 8.
    rate_bpm: float = 15.
    pattern: str = "Regular"
    seed: int = 17

    def __post_init__(self):
        if not np.isfinite(self.amplitude) or self.amplitude < 0:
            raise ValueError("Breathing amplitude must be finite and nonnegative.")
        if not np.isfinite(self.rate_bpm) or self.rate_bpm <= 0:
            raise ValueError("Breathing rate must be finite and positive.")
        if self.pattern not in BREATHING_PATTERNS:
            raise ValueError("Choose a supported breathing pattern.")
        if isinstance(self.seed, bool) or not isinstance(self.seed,(int,np.integer)) or self.seed < 0:
            raise ValueError("The breathing seed must be a nonnegative integer.")


def _smooth_step(values):
    values = np.clip(values, 0., 1.)
    return values*values*(3.-2.*values)


def _breathing_profile(times, settings):
    """positive, seeded frequency/amplitude profiles, independent of render calls."""
    times = np.asarray(times, dtype=float)
    if settings.pattern == "Regular":
        return (np.full_like(times, settings.rate_bpm/60.),
                np.full_like(times, settings.amplitude))
    rng = np.random.default_rng(settings.seed)
    phase = rng.uniform(0., 2*np.pi, 4)
    frequency_strength, amplitude_strength = {
        "Mild irregularity": (.07, .08), "Strong irregularity": (.24, .22),
        "Stress test": (.20, .18)}[settings.pattern]
    frequency = 1.+frequency_strength*(.7*np.sin(.21*times+phase[0])+.3*np.sin(.53*times+phase[1]))
    amplitude = 1.+amplitude_strength*(.6*np.sin(.17*times+phase[2])+.4*np.sin(.43*times+phase[3]))
    if settings.pattern == "Stress test":
        onset = np.array([12., 24., 38.])+rng.uniform(-1., 1., 3)
        changes = [_smooth_step((times-start)/.8) for start in onset]
        frequency += .50*changes[0]-.60*changes[1]+.30*changes[2]
        amplitude += .35*changes[0]-.45*changes[1]+.40*changes[2]
    return settings.rate_bpm/60.*frequency, settings.amplitude*amplitude


class RespiratoryModel:
    """compute 3D displacement and velocity over a bounded time interval.

    frequency is integrated on a fixed grid and interpolated with a C1 Hermite
    spline. setting changes preserve motion history and blend over one second.
    velocity differentiates the same amplitude and phase splines.
    """

    axes = np.array([.15, .25, -1.])  # in LPS, positive inspiration moves inferiorly.

    def __init__(self, settings=None, *, duration=60., integration_step=.01):
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError("Motion duration must be finite and positive.")
        if not np.isfinite(integration_step) or not 0 < integration_step <= duration/2:
            raise ValueError("Choose a positive integration step shorter than half the duration.")
        self.duration = float(duration)
        self._grid = np.linspace(0., duration, int(np.ceil(duration/integration_step))+1)
        self._phase = self._amplitude = None
        self.events = []
        self.configure(0., settings or BreathingSettings())

    def _times(self, times):
        times = np.asarray(times, dtype=float)
        if not np.isfinite(times).all() or np.any(times < 0) or np.any(times > self.duration):
            raise ValueError(f"Motion time must lie between 0 and {self.duration:g} seconds.")
        return times

    def configure(self, time, settings, *, transition_seconds=1.):
        time = float(self._times(time))
        if time >= self.duration:
            raise ValueError("Reset or seek before the end before changing breathing settings.")
        if not isinstance(settings, BreathingSettings):
            raise ValueError("Supply validated breathing settings.")
        if not np.isfinite(transition_seconds) or transition_seconds <= 0:
            raise ValueError("Breathing transitions must take a positive finite time.")
        future = np.r_[time, self._grid[self._grid > time]]
        frequency, amplitude = _breathing_profile(future-time, settings)
        history = np.empty(0)
        phase_at_start = 0.
        if self._phase is not None and time > 0:
            history = self._phase.x[self._phase.x < time]
            weight = _smooth_step((future-time)/transition_seconds)
            frequency = (1.-weight)*self._phase(future, 1)/(2*np.pi)+weight*frequency
            amplitude = (1.-weight)*self._amplitude(future)+weight*amplitude
            phase_at_start = float(self._phase(time))
        phase = phase_at_start+2*np.pi*cumulative_trapezoid(frequency, future, initial=0.)
        amplitude_velocity = (np.gradient(amplitude, future, edge_order=2 if len(future)>2 else 1))
        if len(history):
            amplitude_velocity[0] = self._amplitude(time, 1)
        knots = np.r_[history, future]
        phase_values = np.r_[self._phase(history) if len(history) else [], phase]
        phase_velocity = np.r_[self._phase(history, 1) if len(history) else [], 2*np.pi*frequency]
        amplitude_values = np.r_[self._amplitude(history) if len(history) else [], amplitude]
        amplitude_velocity = np.r_[self._amplitude(history, 1) if len(history) else [], amplitude_velocity]
        self._phase = CubicHermiteSpline(knots, phase_values, phase_velocity)
        self._amplitude = CubicHermiteSpline(knots, amplitude_values, amplitude_velocity)
        self.events = [(start, value) for start, value in self.events if start < time]+[(time, settings)]

    def settings_at(self, time):
        time = float(self._times(time))
        return next(settings for start, settings in reversed(self.events) if start <= time)

    def evaluate(self, times):
        times = self._times(times)
        phase = self._phase(times)
        amplitude = self._amplitude(times)
        scalar = amplitude*np.sin(phase)
        speed = self._amplitude(times, 1)*np.sin(phase)+amplitude*self._phase(times, 1)*np.cos(phase)
        return scalar[...,None]*self.axes, speed[...,None]*self.axes, phase

    def position(self, times, origin=(0., 0., 0.)):
        origin = np.asarray(origin, dtype=float)
        if origin.shape != (3,) or not np.isfinite(origin).all():
            raise ValueError("Motion origin must be a finite physical xyz point.")
        return origin+self.evaluate(times)[0]

    def velocity(self, times):
        return self.evaluate(times)[1]


@dataclass(frozen=True)
class LungDeformation:
    """apply u(p,t) = (apex_z-p.z)/height * d(t) in LPS millimetres.

    this affine field has an exact inverse and fixes the apex. It provides a
    geometric preview rather than a tissue-mechanics model.
    """

    base_z: float
    apex_z: float

    def __post_init__(self):
        if not np.isfinite([self.base_z,self.apex_z]).all() or self.apex_z <= self.base_z:
            raise ValueError("The motion reference requires a finite lung height above zero.")

    @property
    def height(self):
        return self.apex_z-self.base_z

    def matrix(self, displacement):
        displacement = np.asarray(displacement, dtype=float)
        if displacement.shape != (3,) or not np.isfinite(displacement).all():
            raise ValueError("Displacement must be a finite physical xyz vector.")
        if 1.-displacement[2]/self.height < .5:
            raise ValueError("This displacement would excessively compress the preview anatomy.")
        matrix = np.eye(4)
        matrix[:3,2] -= displacement/self.height
        matrix[:3,3] = displacement*self.apex_z/self.height
        return matrix

    def forward(self, points, displacement):
        matrix = self.matrix(displacement)
        points = np.asarray(points, dtype=float)
        return points@matrix[:3,:3].T+matrix[:3,3]

    def inverse(self, points, displacement):
        matrix = self.matrix(displacement)
        points = np.asarray(points, dtype=float)
        return (points-matrix[:3,3])@np.linalg.inv(matrix[:3,:3]).T


def respiratory_slice(volume, name, crosshair, deformation, displacement, *, masks=None, max_pixels=256):
    """sample CT and nearest-neighbour labels on one shared deformed world grid."""
    plane = volume.slice_grid(name, crosshair, max_pixels=max_pixels)
    # compose row/column -> world -> inverse motion -> source index once.
    # use SciPy to sample the original 3D image directly onto the 2D plane, avoiding
    # dense world-coordinate arrays and repeated large matrix multiplications.
    world = np.eye(4)
    world[:3,0],world[:3,1] = plane.v*plane.spacing[1],plane.u*plane.spacing[0]
    world[:3,3] = plane.origin
    source = np.linalg.inv(volume.affine)@np.linalg.inv(deformation.matrix(displacement))@world
    coordinates = source[[2,1,0]][:,[0,1,3]]
    coordinates = np.where(np.abs(coordinates-np.rint(coordinates))<1e-12,
                           np.rint(coordinates),coordinates)
    def sample(data, order, outside):
        return ndimage.affine_transform(data, coordinates[:,:2], offset=coordinates[:,2],
            output_shape=plane.shape, output=np.float32, order=order, mode="constant",
            cval=outside, prefilter=False)
    image = sample(volume.data,1,-1000.)
    overlays = {}
    for role, mask in (masks or {}).items():
        if np.asarray(mask).shape != volume.shape:
            raise ValueError("Motion preview masks must match the CT geometry.")
        overlays[role] = replace(plane, image=sample(mask,0,0.))
    return replace(plane, image=image), overlays


if __name__ == "__main__":
    import sys
    sys.modules["motiontwin"] = sys.modules[__name__]
    from run import main
    raise SystemExit(main())
