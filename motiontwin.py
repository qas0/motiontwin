from __future__ import annotations

from dataclasses import dataclass, field, replace
from collections import OrderedDict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError
import csv
import json
import os
import platform
import re
import shutil
import tarfile

import numpy as np
from scipy import ndimage
from scipy import __version__ as _scipy_version
from scipy.ndimage import map_coordinates
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import brentq, minimize_scalar

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

    def slice_grid(self, plane, crosshair, *, max_pixels=1024, bounds=None):
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
        if bounds is None:
            bounds = self.bounds
        else:
            try:
                bounds = np.asarray(bounds, dtype=float)
            except (TypeError, ValueError) as error:
                raise ValueError("Slice bounds must be finite lower and upper physical xyz coordinates.") from error
            if (bounds.shape != (2, 3) or not np.isfinite(bounds).all()
                    or np.any(bounds[1] <= bounds[0])):
                raise ValueError("Slice bounds must be finite lower and upper physical xyz coordinates.")
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


@dataclass(frozen=True)
class CTPhase:
    percent: float
    time_s: float | None
    image: Path
    segmentation: Path | None = None


@dataclass
class PhaseData:
    volume: Volume
    masks: dict
    meshes: dict
    styles: dict


@dataclass(frozen=True)
class _CTHeader:
    shape: tuple
    spacing: tuple
    origin: tuple
    direction: tuple

    def matches(self, other):
        return (self.shape == other.shape
                and all(np.allclose(getattr(self, key), getattr(other, key),
                                    rtol=0, atol=1e-4)
                        for key in ("spacing", "origin", "direction")))

    def index_to_world(self, indices):
        return index_to_world(indices, self.spacing, self.origin,
                              np.asarray(self.direction).reshape(3, 3))

    def world_to_index(self, points):
        return world_to_index(points, self.spacing, self.origin,
                              np.asarray(self.direction).reshape(3, 3))


@dataclass(frozen=True)
class _CTSource:
    path: Path
    files: tuple
    signature: tuple
    header: _CTHeader
    identifiers: tuple = ()


def _ct_file_signature(paths):
    try:
        return tuple((str(path), stat.st_size, stat.st_mtime_ns,
                      stat.st_ctime_ns, stat.st_ino)
                     for path in paths for stat in [path.stat()])
    except OSError as error:
        raise ValueError("A sequence source is missing or cannot be read. Reopen the sequence manifest.") from error


def _ct_header_from_reader(reader):
    if reader.GetDimension() != 3 or reader.GetNumberOfComponents() != 1:
        raise ValueError("Each respiratory phase must be a 3D scalar image.")
    shape = tuple(int(value) for value in reader.GetSize()[::-1])
    spacing = tuple(float(value) for value in reader.GetSpacing())
    origin = tuple(float(value) for value in reader.GetOrigin())
    direction = tuple(float(value) for value in reader.GetDirection())
    matrix = np.asarray(direction).reshape(3, 3)
    if (min(shape) < 1 or not np.all(np.isfinite(spacing)) or min(spacing) <= 0
            or not np.all(np.isfinite(origin)) or not np.all(np.isfinite(matrix))
            or not np.allclose(matrix.T @ matrix, np.eye(3), rtol=0, atol=1e-4)):
        raise ValueError("A respiratory phase has invalid physical image geometry.")
    return _CTHeader(shape, spacing, origin, direction)


def _ct_external_payload(path):
    suffix = path.suffix.lower()
    if suffix not in (".mhd", ".mha", ".nhdr", ".nrrd"):
        return ()
    directive = None
    try:
        with path.open("rb") as source:
            for _ in range(2048):
                line = source.readline(65537)
                if len(line) > 65536:
                    raise ValueError("The image header is too large to validate safely.")
                if not line or (suffix in (".nhdr", ".nrrd") and not line.strip()):
                    break
                text = line.decode("ascii", errors="replace").strip()
                if suffix in (".mhd", ".mha") and "=" in text:
                    key, value = text.split("=", 1)
                    if key.strip().casefold() == "elementdatafile":
                        directive = value.strip()
                        break
                elif suffix in (".nhdr", ".nrrd") and ":" in text:
                    key, value = text.split(":", 1)
                    if key.strip().casefold() in ("data file", "datafile"):
                        directive = value.strip()
                        break
    except OSError as error:
        raise ValueError("A sequence image header cannot be read.") from error
    if not directive or directive.upper() == "LOCAL":
        return ()
    if directive.upper().startswith("LIST") or "%" in directive:
        raise ValueError("Use one-file images or a header with a single external data file for each phase.")
    payload = Path(directive.strip('"'))
    if not payload.is_absolute():
        payload = path.parent / payload
    payload = Path(os.path.abspath(payload))
    if not payload.is_file():
        raise ValueError("An image's external voxel data file is missing.")
    return (payload,)


def _ct_dicom_source(path):
    import SimpleITK as sitk
    identifiers = {}
    try:
        series = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(path))
        if not series or len(series) != 1:
            raise ValueError("Each phase directory must contain exactly one readable DICOM series.")
        files = tuple(Path(value) for value in
                      sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(path), series[0]))
        if not files:
            raise ValueError("A phase DICOM series contains no readable image files.")
        observed_paths = (path,) + files
        signature = _ct_file_signature(observed_paths)
        header = None
        positions = []
        for filename in files:
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(filename))
            reader.ReadImageInformation()
            current = _ct_header_from_reader(reader)
            unsupported = "Export multiframe or enhanced DICOM as separate 3D phase files or classic single-frame CT slices."
            if (reader.HasMetaDataKey("0008|0016")
                    and reader.GetMetaData("0008|0016").strip() in
                    ("1.2.840.10008.5.1.4.1.1.2.1", "1.2.840.10008.5.1.4.1.1.2.2")):
                raise ValueError(unsupported)
            if reader.HasMetaDataKey("0028|0008"):
                try:
                    number_of_frames = int(reader.GetMetaData("0028|0008").strip())
                except ValueError as error:
                    raise ValueError(unsupported) from error
                if number_of_frames != 1:
                    raise ValueError(unsupported)
            if current.shape[0] != 1:
                raise ValueError(unsupported)
            if reader.HasMetaDataKey("0008|0060") and reader.GetMetaData("0008|0060").strip() != "CT":
                raise ValueError("Respiratory phase directories must contain CT images.")
            for key in ("0010|0020", "0020|000d", "0020|0052"):
                value = reader.GetMetaData(key).strip() if reader.HasMetaDataKey(key) else ""
                if value:
                    if key in identifiers and identifiers[key] != value:
                        raise ValueError("A phase DICOM series has inconsistent patient, study or frame-of-reference metadata.")
                    identifiers[key] = value
            if header is None:
                header = current
            elif (header.shape[1:] != current.shape[1:]
                  or not np.allclose(header.spacing[:2], current.spacing[:2], rtol=0, atol=1e-4)
                  or not np.allclose(header.direction, current.direction, rtol=0, atol=1e-4)):
                raise ValueError("A phase DICOM series has inconsistent slice geometry.")
            positions.append(current.origin)
        if len(files) > 1:
            matrix = np.asarray(header.direction).reshape(3, 3)
            offsets = np.diff(np.asarray(positions), axis=0)
            normal_offsets = offsets @ matrix[:, 2]
            spacing_z = float(np.mean(normal_offsets))
            if (spacing_z <= 0 or not np.allclose(normal_offsets, spacing_z, rtol=0, atol=1e-3)
                    or not np.allclose(offsets, spacing_z * matrix[:, 2], rtol=0, atol=1e-3)):
                raise ValueError("A phase DICOM series has missing, duplicate, tilted or irregularly spaced slices.")
            header = _CTHeader((len(files), *header.shape[1:]),
                               (*header.spacing[:2], spacing_z), header.origin, header.direction)
        if signature != _ct_file_signature(observed_paths):
            raise ValueError("A DICOM source changed while its geometry was being checked.")
        return _CTSource(path, observed_paths, signature, header, tuple(identifiers.items()))
    except RuntimeError as error:
        raise ValueError("A phase DICOM series could not be inspected. Select a complete, supported CT series.") from error


def _ct_sequence_source(path):
    import SimpleITK as sitk
    if path.is_dir():
        return _ct_dicom_source(path)
    if not path.is_file():
        raise ValueError("A phase image or segmentation source does not exist.")
    if not any(path.name.lower().endswith(suffix)
               for suffix in (".nii", ".nii.gz", ".nrrd", ".nhdr", ".mha", ".mhd")):
        raise ValueError("Use NIfTI, NRRD, MetaImage or a single-series DICOM directory for each phase.")
    files = (path,) + _ct_external_payload(path)
    signature = _ct_file_signature(files)
    try:
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(path))
        reader.ReadImageInformation()
        header = _ct_header_from_reader(reader)
    except RuntimeError as error:
        raise ValueError("A phase image header could not be read. Choose a supported 3D image.") from error
    if signature != _ct_file_signature(files):
        raise ValueError("A source changed while its geometry was being checked.")
    return _CTSource(path, files, signature, header)


def _ct_phase_bytes(phase):
    arrays = [phase.volume.data, *phase.masks.values()]
    for mesh in phase.meshes.values():
        arrays.extend([mesh.points, mesh.faces, mesh.lines, mesh.verts, mesh.strips])
        for attributes in (mesh.point_data, mesh.cell_data, mesh.field_data):
            arrays.extend(attributes.values())
    return sum(np.asarray(array).nbytes for array in arrays)


_CT_SURFACE_VERSION = 1
_CT_SURFACE_BYTES = 64 * 1024 ** 2


def _ct_surface_archive_valid(path):
    with ZipFile(path) as archive:
        members = archive.infolist()
        if (not 1 <= len(members) <= 128
                or len({item.filename for item in members}) != len(members)
                or sum(item.file_size for item in members) > _CT_SURFACE_BYTES):
            return False
        for item in members:
            if not re.fullmatch(r"[A-Za-z0-9_]+\.npy", item.filename):
                return False
            with archive.open(item) as source:
                version = np.lib.format.read_magic(source)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(source)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(source)
                else:
                    return False
                size = int(np.prod(shape, dtype=object)) * dtype.itemsize
                if (dtype.hasobject or size > _CT_SURFACE_BYTES
                        or size != item.file_size - source.tell()):
                    return False
    return True


def _ct_surface_arrays_valid(arrays, volume):
    points, faces, hu, rgb, normals = arrays
    # smoothed caps on padded masks can extend past the outer voxel faces.
    return (len(points) <= DISPLAY_MAX_CELLS * 3
            and _valid_lobe_mesh_arrays(points, faces, hu, rgb, volume, margin_voxels=1.)
            and normals.dtype.kind == "f" and np.isfinite(normals).all()
            and normals.shape in ((0, 3), (len(points), 3)))


def _ct_read_surfaces(path, identity, names, volume):
    try:
        if not path.is_file() or path.stat().st_size > _CT_SURFACE_BYTES:
            return None
        if not _ct_surface_archive_valid(path):
            return None
        with np.load(path, allow_pickle=False) as saved:
            if str(saved["identity"].item()) != identity:
                return None
            keys = json.loads(str(saved["keys"].item()))
            if (not isinstance(keys, list) or len(set(keys)) != len(keys)
                    or set(keys) != set(names)):
                return None
            expected = {"identity", "keys"}
            for index in range(len(keys)):
                expected.update(f"m{index}_{suffix}" for suffix in
                                ("points", "faces", "hu", "rgb", "normals", "sha256"))
            if set(saved.files) != expected:
                return None
            import pyvista as pv
            meshes = {}
            for index, name in enumerate(keys):
                arrays = tuple(saved[f"m{index}_{suffix}"] for suffix in
                               ("points", "faces", "hu", "rgb", "normals"))
                if (not _ct_surface_arrays_valid(arrays, volume)
                        or str(saved[f"m{index}_sha256"].item()) != _lobe_array_digest(arrays)):
                    return None
                points, faces, hu, rgb, normals = arrays
                mesh = pv.PolyData(points, faces.ravel())
                mesh.point_data["CT_HU"], mesh.point_data["CT_RGB"] = hu, rgb
                if len(normals):
                    mesh.point_data["Normals"] = normals
                    mesh.point_data.active_normals_name = "Normals"
                mesh.field_data["CT_sampling_inset_mm"] = [min(volume.spacing) * .65 if "lung" in name else 0.]
                mesh.field_data["source"] = ["reference CT in physical LPS millimetres"]
                meshes[name] = mesh
            return meshes
    except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile, OverflowError,
            RuntimeError, NotImplementedError, ZlibError):
        return None


def _ct_write_surfaces(path, identity, masks, meshes, volume):
    if set(meshes) != set(masks):
        return False
    content = dict(identity=np.array(identity), keys=np.array(json.dumps(list(meshes))))
    for index, mesh in enumerate(meshes.values()):
        arrays = (np.asarray(mesh.points), np.asarray(mesh.faces).reshape(-1, 4),
                  np.asarray(mesh["CT_HU"]), np.asarray(mesh["CT_RGB"]),
                  np.asarray(mesh.point_data["Normals"]) if "Normals" in mesh.point_data
                  else np.empty((0, 3), dtype=np.float32))
        if not _ct_surface_arrays_valid(arrays, volume):
            return False
        for suffix, array in zip(("points", "faces", "hu", "rgb", "normals"), arrays):
            content[f"m{index}_{suffix}"] = array
        content[f"m{index}_sha256"] = np.array(_lobe_array_digest(arrays))
    if (len(content) > 128
            or sum(value.nbytes + 256 for value in content.values()) > _CT_SURFACE_BYTES):
        return False
    temporary = path.with_name(f"{uuid4().hex}.part")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as output:
            np.savez_compressed(output, **content)
        os.replace(temporary, path)
        return True
    except OSError:
        return False
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


class CTSequence:
    def __init__(self, name, phases, sources, segments, manifest, signature, *,
                 max_cached_phases=2, max_cache_bytes=512 * 1024 ** 2,
                 surface_cache_dir=None):
        if (type(max_cached_phases) is not int or max_cached_phases < 1
                or type(max_cache_bytes) is not int or max_cache_bytes < 1):
            raise ValueError("Sequence cache limits must be positive integers.")
        self.name = name
        self.phases = tuple(phases)
        self.max_cached_phases = max_cached_phases
        self.max_cache_bytes = max_cache_bytes
        self._sources = tuple(sources)
        self._segments = tuple(segments)
        self._manifest = manifest
        self._manifest_signature = signature
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self.surface_cache_dir = (Path(surface_cache_dir).expanduser().resolve()
                                  if surface_cache_dir is not None else None)

    @property
    def geometry(self):
        return self._sources[0][0].header

    @property
    def cache_bytes(self):
        return self._cache_bytes

    @property
    def cache_count(self):
        return len(self._cache)

    @property
    def styles(self):
        return {key: style for key, _, style in self._segments}

    def _check_sources(self, index):
        if self._manifest_signature != _ct_file_signature((self._manifest,)):
            raise ValueError("The sequence manifest changed. Reopen it before navigating phases.")
        for source in self._sources[index]:
            if source.signature != _ct_file_signature(source.files):
                raise ValueError("A phase source changed. Reopen the sequence manifest before continuing.")

    def _surface_identity(self, index):
        sources = [dict(files=source.signature, shape=source.header.shape,
                        spacing=source.header.spacing, origin=source.header.origin,
                        direction=source.header.direction) for source in self._sources[index]]
        content = dict(version=_CT_SURFACE_VERSION, max_cells=DISPLAY_MAX_CELLS,
                       phase=self.phases[index].percent, sources=sources,
                       segments=[(key, label) for key, label, _ in self._segments])
        return sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()

    def _surface_path(self, index):
        return self.surface_cache_dir / f"{self._surface_identity(index)[:32]}.npz"

    def prepare_surfaces(self, progress=None):
        if self.surface_cache_dir is None:
            raise ValueError("Choose a surface cache directory before preparing respiratory phases.")
        if progress is not None:
            progress(0, len(self.phases))
        for index in range(len(self.phases)):
            data = self.phase(index)
            if data.masks:
                identity = self._surface_identity(index)
                path = self._surface_path(index)
                if (_ct_read_surfaces(path, identity, data.masks, data.volume) is None
                        and not _ct_write_surfaces(path, identity, data.masks, data.meshes, data.volume)):
                    raise ValueError("Phase surfaces could not be cached. Choose a writable cache directory with a shorter path and enough free space.")
            self._check_sources(index)
            if progress is not None:
                progress(index + 1, len(self.phases))

    def phase(self, index):
        if type(index) is not int or not 0 <= index < len(self.phases):
            raise ValueError("Select a valid respiratory phase index.")
        self._check_sources(index)
        if index in self._cache:
            self._cache.move_to_end(index)
            return self._cache[index][0]
        descriptor = self.phases[index]
        volume = load_volume(descriptor.image)
        expected = self._sources[index][0].header
        actual = _CTHeader(volume.shape, volume.spacing, volume.origin,
                           tuple(volume.direction.ravel()))
        if not expected.matches(actual):
            raise ValueError("A phase's loaded geometry differs from its checked header.")
        masks, meshes, styles = {}, {}, {}
        if descriptor.segmentation is not None:
            segmentation = load_volume(descriptor.segmentation)
            actual = _CTHeader(segmentation.shape, segmentation.spacing,
                               segmentation.origin, tuple(segmentation.direction.ravel()))
            if not expected.matches(actual):
                raise ValueError("The phase segmentation is not aligned with its CT image.")
            labels = set()
            for section in segmentation.data:
                if (np.any(section < 0)
                        or (segmentation.data.dtype.kind == "f"
                            and not np.equal(section, np.rint(section)).all())):
                    raise ValueError("Phase segmentations must contain discrete nonnegative labels.")
                labels.update(np.unique(section).tolist())
            known = {label for _, label, _ in self._segments}
            if labels - known - {0}:
                raise ValueError("A phase segmentation contains foreground labels absent from the manifest's segments.")
            for key, label, style in self._segments:
                if label in labels:
                    masks[key] = segmentation.data == label
                    styles[key] = style
            identity = self._surface_identity(index)
            path = (self._surface_path(index)
                    if self.surface_cache_dir is not None else None)
            cached = _ct_read_surfaces(path, identity, masks, volume) if path is not None else None
            meshes = cached if cached is not None else prepare_display_meshes(volume, masks)
            if path is not None and cached is None:
                self._check_sources(index)
                _ct_write_surfaces(path, identity, masks, meshes, volume)
        result = PhaseData(volume, masks, meshes, styles)
        self._check_sources(index)
        size = _ct_phase_bytes(result)
        if size <= self.max_cache_bytes:
            while self._cache and (len(self._cache) >= self.max_cached_phases
                                   or self._cache_bytes + size > self.max_cache_bytes):
                _, (_, removed_bytes) = self._cache.popitem(last=False)
                self._cache_bytes -= removed_bytes
            self._cache[index] = (result, size)
            self._cache_bytes += size
        return result


def _ct_unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("The sequence manifest contains duplicate JSON keys.")
        result[key] = value
    return result


def _ct_sequence_path(value, parent):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Every phase source must be a nonblank file or directory path.")
    path = Path(value).expanduser()
    return Path(os.path.abspath(path if path.is_absolute() else parent / path))


def _ct_finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return bool(np.isfinite(float(value)))
    except OverflowError:
        return False


def load_ct_sequence(path, *, max_cached_phases=2, max_cache_bytes=512 * 1024 ** 2,
                     surface_cache_dir=None):
    path = Path(os.path.abspath(Path(path).expanduser()))
    signature = _ct_file_signature((path,))
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("The sequence manifest must be a JSON file smaller than 1 MiB.")
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_ct_unique_json)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("The respiratory CT sequence manifest is not readable JSON.") from error
    if not isinstance(document, dict) or set(document) - {"version", "name", "segments", "phases"}:
        raise ValueError("Use a sequence manifest containing version, name, phases and optional segments.")
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("The respiratory CT sequence manifest version must be 1.")
    name = StructureStyle(document.get("name"), "#000000").name
    items = document.get("phases")
    if not isinstance(items, list) or not 2 <= len(items) <= 100:
        raise ValueError("A respiratory CT sequence must contain 2 to 100 ordered phases.")
    segment_items = document.get("segments", [])
    if not isinstance(segment_items, list):
        raise ValueError("The manifest's segments must be a list of named positive labels.")
    segments, segment_ids, segment_labels, segment_names = [], set(), set(), set()
    for item in segment_items:
        if (not isinstance(item, dict)
                or set(item) - {"id", "label", "name", "color", "kind"}):
            raise ValueError("Each segment needs an id, label, name, color and optional kind.")
        key, label = item.get("id"), item.get("label")
        if (not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", key)
                or key in segment_ids or type(label) is not int or label < 1
                or label in segment_labels):
            raise ValueError("Segment ids and positive integer labels must be valid and unique.")
        style = StructureStyle(item.get("name"), item.get("color"), ct_coloring=False,
                               kind=item.get("kind", "lung"))
        if style.name.casefold() in segment_names:
            raise ValueError("Segment display names must be unique.")
        segments.append((key, label, style))
        segment_ids.add(key)
        segment_labels.add(label)
        segment_names.add(style.name.casefold())
    phases, sources, identities = [], [], {}
    image_paths, segmentation_paths, image_files, segmentation_files = set(), set(), set(), set()
    reference = None
    previous_percent, previous_time = -1., -1.
    timing = any(isinstance(item, dict) and "time_s" in item for item in items)
    for item in items:
        if not isinstance(item, dict) or set(item) - {"percent", "time_s", "image", "segmentation"}:
            raise ValueError("Each phase needs percent, image and optional time_s and segmentation.")
        percent = item.get("percent")
        if (not _ct_finite_number(percent) or not 0 <= percent < 100
                or percent <= previous_percent):
            raise ValueError("Respiratory phase percentages must be finite, unique and strictly increasing from 0 up to 100.")
        time_s = item.get("time_s")
        if timing and (not _ct_finite_number(time_s) or time_s < 0 or time_s <= previous_time):
            raise ValueError("Supply finite, nonnegative, increasing time_s values for every phase, or omit timing entirely.")
        image = _ct_sequence_path(item.get("image"), path.parent)
        segmentation = (_ct_sequence_path(item["segmentation"], path.parent)
                        if "segmentation" in item else None)
        if segmentation is not None and not segments:
            raise ValueError("Declare named segments when a phase includes a segmentation.")
        phase_sources = [_ct_sequence_source(image)]
        resolved = image.resolve()
        stat = image.stat()
        identity = (stat.st_dev, stat.st_ino)
        if resolved in image_paths or (stat.st_ino and identity in image_files):
            raise ValueError("Each respiratory phase must reference a distinct CT source.")
        image_paths.add(resolved)
        if stat.st_ino:
            image_files.add(identity)
        current = phase_sources[0].header
        if reference is None:
            reference = current
        elif not reference.matches(current):
            raise ValueError("All respiratory phases must have matching size, spacing, origin and direction. No resampling is performed.")
        for key, value in phase_sources[0].identifiers:
            if key in identities and identities[key] != value:
                raise ValueError("DICOM phases must belong to the same patient, study and frame of reference.")
            identities[key] = value
        if segmentation is not None:
            source = _ct_sequence_source(segmentation)
            resolved = segmentation.resolve()
            stat = segmentation.stat()
            identity = (stat.st_dev, stat.st_ino)
            if resolved in segmentation_paths or (stat.st_ino and identity in segmentation_files):
                raise ValueError("Supply a distinct, phase-specific segmentation for each phase, or omit it.")
            segmentation_paths.add(resolved)
            if stat.st_ino:
                segmentation_files.add(identity)
            if not current.matches(source.header):
                raise ValueError("Each phase segmentation must already match its CT's physical geometry.")
            phase_sources.append(source)
        phases.append(CTPhase(float(percent), float(time_s) if timing else None, image, segmentation))
        sources.append(tuple(phase_sources))
        previous_percent = percent
        if timing:
            previous_time = time_s
    if image_paths & segmentation_paths or image_files & segmentation_files:
        raise ValueError("CT images and segmentation label images must be separate source files.")
    if signature != _ct_file_signature((path,)):
        raise ValueError("The sequence manifest changed while it was being checked.")
    sequence = CTSequence(name, phases, sources, segments, path, signature,
                          max_cached_phases=max_cached_phases, max_cache_bytes=max_cache_bytes,
                          surface_cache_dir=surface_cache_dir)
    return sequence


LANDMARK_CSV_FIELDS = ("version", "sequence_id", "sequence_name", "landmark_name", "provenance",
                       "reference_phase_percent", "phase_index", "phase_percent", "time_s",
                       "image", "segmentation", "x_lps_mm", "y_lps_mm", "z_lps_mm", "source",
                       "dx_mm", "dy_mm", "dz_mm", "distance_mm")


def _landmark_text(value, label, *, maximum=80, blank=False):
    if (not isinstance(value, str) or len(value) > maximum
            or any(character in value for character in
                   "\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
            or (not blank and not value.strip())):
        raise ValueError(f"{label} must be a single line of at most {maximum} characters.")
    return value.strip()


def _landmark_sequence_id(sequence):
    def signature(items):
        return [(os.path.normcase(str(Path(item[0]).resolve())), *item[1:]) for item in items]

    phases = []
    for phase, sources in zip(sequence.phases, sequence._sources):
        phases.append(dict(percent=phase.percent, time_s=phase.time_s, sources=[
            dict(path=os.path.normcase(str(source.path.resolve())), files=signature(source.signature),
                 shape=source.header.shape, spacing=source.header.spacing, origin=source.header.origin,
                 direction=source.header.direction, identifiers=source.identifiers)
            for source in sources]))
    snapshot = dict(name=sequence.name, manifest=signature(sequence._manifest_signature), phases=phases)
    return sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


class LandmarkSeries:
    def __init__(self, sequence, name="Landmark 1", reference_index=0, *, provenance=""):
        if not isinstance(sequence, CTSequence):
            raise ValueError("Landmarks require a respiratory CT sequence.")
        self._sequence = sequence
        self._points = {}
        self._sources = {}
        self.name = name
        self.provenance = provenance
        self.reference_index = reference_index
        self._check_sources()
        # this binds annotations to the same unchanged local source snapshot, without hashing voxel data.
        self._sequence_id = _landmark_sequence_id(sequence)

    @property
    def sequence(self):
        return self._sequence

    @property
    def sequence_id(self):
        return self._sequence_id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = _landmark_text(value, "Landmark name")

    @property
    def provenance(self):
        return self._provenance

    @provenance.setter
    def provenance(self, value):
        self._provenance = _landmark_text(value, "Landmark provenance", maximum=1000, blank=True)

    @property
    def points(self):
        return {index: point.copy() for index, point in self._points.items()}

    @property
    def sources(self):
        return self._sources.copy()

    @property
    def reference_index(self):
        return self._reference_index

    @reference_index.setter
    def reference_index(self, index):
        self._validate_index(index)
        self._reference_index = index

    def _validate_index(self, index):
        if type(index) is not int or not 0 <= index < len(self.sequence.phases):
            raise ValueError("Select a valid landmark phase index.")

    def _check_sources(self):
        for index in range(len(self.sequence.phases)):
            self.sequence._check_sources(index)

    def validate_sources(self):
        self._check_sources()

    def _check_export_destination(self, path):
        destination = path.resolve()
        protected = [self.sequence._manifest]
        protected.extend(file for sources in self.sequence._sources
                         for source in sources for file in source.files)
        for source in protected:
            if (os.path.normcase(str(destination)) == os.path.normcase(str(source.resolve()))
                    or (path.exists() and os.path.samefile(path, source))):
                raise ValueError("Landmark CSV export cannot overwrite a CT source, segmentation, payload or sequence manifest.")

    def set_point(self, index, point, source="manual"):
        self._validate_index(index)
        if not isinstance(source, str) or source not in ("manual", "dataset"):
            raise ValueError("A landmark source must be manual or dataset.")
        try:
            values = np.asarray(point)
            if values.shape != (3,) or values.dtype.kind not in "iuf":
                raise ValueError
            values = values.astype(float)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("A landmark must contain three finite physical LPS coordinates in millimetres.") from error
        if not np.isfinite(values).all():
            raise ValueError("A landmark must contain three finite physical LPS coordinates in millimetres.")
        self.sequence._check_sources(index)
        header = self.sequence._sources[index][0].header
        voxel = header.world_to_index(values)
        maximum = np.asarray(header.shape[::-1]) - 1
        if np.any(voxel < -1e-8) or np.any(voxel > maximum + 1e-8):
            raise ValueError("The landmark lies outside this phase's oriented CT voxel grid.")
        self._points[index] = values.copy()
        self._sources[index] = source

    def remove_point(self, index):
        self._validate_index(index)
        self.sequence._check_sources(index)
        self._points.pop(index, None)
        self._sources.pop(index, None)

    def measurements(self):
        self._check_sources()
        reference = self._points.get(self.reference_index)
        rows = []
        for index, phase in enumerate(self.sequence.phases):
            point = self._points.get(index)
            with np.errstate(over="ignore", invalid="ignore"):
                delta = point - reference if point is not None and reference is not None else None
            if delta is not None and not np.isfinite(delta).all():
                raise ValueError("Landmark displacement cannot be represented by finite millimetre coordinates.")
            position = tuple(float(value) for value in point) if point is not None else (None,) * 3
            displacement = tuple(float(value) for value in delta) if delta is not None else (None,) * 3
            rows.append(dict(phase_index=index, phase_percent=phase.percent, time_s=phase.time_s,
                             **dict(zip(("x_lps_mm", "y_lps_mm", "z_lps_mm"), position)),
                             **dict(zip(("dx_mm", "dy_mm", "dz_mm"), displacement)),
                             distance_mm=float(np.hypot.reduce(delta)) if delta is not None else None,
                             source=self._sources.get(index)))
        return rows

    def export_csv(self, path):
        path = Path(path)
        self._check_export_destination(path)
        rows = self.measurements()
        temporary = path.with_name(f"{uuid4().hex}.part")
        try:
            with temporary.open("x", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=LANDMARK_CSV_FIELDS)
                writer.writeheader()
                for phase, measurement in zip(self.sequence.phases, rows):
                    writer.writerow(dict(version=1, sequence_id=self.sequence_id,
                                         sequence_name=self.sequence.name, landmark_name=self.name,
                                         provenance=self.provenance,
                                         reference_phase_percent=self.sequence.phases[self.reference_index].percent,
                                         image=str(phase.image),
                                         segmentation=str(phase.segmentation) if phase.segmentation else "",
                                         **measurement))
            self._check_sources()
            self._check_export_destination(path)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path


def load_landmarks(path, sequence):
    if not isinstance(sequence, CTSequence):
        raise ValueError("Landmarks require a respiratory CT sequence.")
    path = Path(path)
    try:
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("The landmark CSV must be smaller than 1 MiB.")
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if tuple(reader.fieldnames or ()) != LANDMARK_CSV_FIELDS:
                raise ValueError("Use a landmark CSV exported for this respiratory CT sequence.")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError("The landmark CSV cannot be read.") from error
    if len(rows) != len(sequence.phases):
        raise ValueError("The landmark CSV must contain exactly one row for every respiratory phase.")
    first = rows[0]
    if any(set(row) != set(LANDMARK_CSV_FIELDS) or any(value is None for value in row.values())
           for row in rows):
        raise ValueError("Every landmark CSV row must contain the declared columns.")
    if first["version"] != "1":
        raise ValueError("The landmark CSV version must be 1.")
    try:
        reference_percent = float(first["reference_phase_percent"])
        reference_index = next(index for index, phase in enumerate(sequence.phases)
                               if phase.percent == reference_percent)
    except (ValueError, StopIteration) as error:
        raise ValueError("The landmark reference phase must belong to this respiratory CT sequence.") from error
    series = LandmarkSeries(sequence, first["landmark_name"], reference_index,
                            provenance=first["provenance"])
    if first["sequence_id"] != series.sequence_id or first["sequence_name"] != sequence.name:
        raise ValueError("This landmark CSV belongs to a different or changed CT sequence source snapshot.")
    metadata = ("version", "sequence_id", "sequence_name", "landmark_name", "provenance",
                "reference_phase_percent")
    for index, (row, phase) in enumerate(zip(rows, sequence.phases)):
        if any(row[key] != first[key] for key in metadata):
            raise ValueError("Landmark CSV metadata must agree across every phase row.")
        try:
            valid_phase = (row["phase_index"] == str(index)
                           and float(row["phase_percent"]) == phase.percent
                           and (float(row["time_s"]) == phase.time_s if phase.time_s is not None
                                else row["time_s"] == "")
                           and row["image"] == str(phase.image)
                           and row["segmentation"] == (str(phase.segmentation) if phase.segmentation else ""))
        except ValueError:
            valid_phase = False
        if not valid_phase:
            raise ValueError("Landmark CSV phases, timing and CT paths must match the sequence exactly.")
        position = [row[key] for key in ("x_lps_mm", "y_lps_mm", "z_lps_mm")]
        if any(position):
            try:
                point = [float(value) for value in position]
            except ValueError as error:
                raise ValueError("Each landmark row needs all three LPS coordinates or three empty cells.") from error
            series.set_point(index, point, row["source"])
        elif row["source"]:
            raise ValueError("A missing landmark must have an empty source cell.")
    for row, measured in zip(rows, series.measurements()):
        for key in ("dx_mm", "dy_mm", "dz_mm", "distance_mm"):
            try:
                valid = (row[key] == "" if measured[key] is None
                         else np.isfinite(float(row[key]))
                         and np.isclose(float(row[key]), measured[key], rtol=1e-12, atol=1e-12))
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Landmark CSV displacements must agree with its confirmed LPS coordinates and reference phase.")
    return series



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
                       total_timeout=TOTAL_TIMEOUT_SECONDS, expected_bytes=None,
                       progress=None, cancelled=None):
    """stream a bounded HTTPS file and replace the destination only after hashing."""
    if not url.lower().startswith("https://"):
        raise ValueError("Public example downloads require HTTPS.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.{uuid4().hex}.part")
    started, received = monotonic(), 0
    digest = sha256()
    try:
        if cancelled is not None and cancelled():
            raise InterruptedError("Respiratory example setup cancelled.")
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
                if (declared < 0 or declared > max_bytes
                        or (expected_bytes is not None and declared != expected_bytes)):
                    raise ValueError("The public example exceeds the download size limit.")
            with partial.open("xb") as target:
                while True:
                    if cancelled is not None and cancelled():
                        raise InterruptedError("Respiratory example setup cancelled.")
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
                    if progress is not None:
                        progress(received, expected_bytes if expected_bytes is not None else max_bytes)
            if length is not None and received != declared:
                raise ValueError("The public example download was incomplete.")
        if digest.hexdigest() != expected_digest:
            raise ValueError("Public example SHA-256 verification failed; the file was not installed.")
        if expected_bytes is not None and received != expected_bytes:
            raise ValueError("The public example download was incomplete.")
        if cancelled is not None and cancelled():
            raise InterruptedError("Respiratory example setup cancelled.")
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return received


RESPIRATORY_SHAPE_ZYX = (141, 360, 482)
RESPIRATORY_SPACING = (.97656, .97656, 2.)
RESPIRATORY_SOURCE_URL = "https://www.creatis.insa-lyon.fr/~srit/POPI/"
RESPIRATORY_PROVIDER_URL = "https://github.com/open-vv/popi-model/blob/master/popi-model.md"
_RESPIRATORY_HASHES = (
    (0,
     "ae1e46952739eb3f5258ac0937f138db0e8df092102a471f97c6fa049375887a", "01090410c27ed32dd9ddd8c0cc571b7474386d747fc716df14c759607e354ac1",
     "5badfb71f04a040ee88dac31dbae0550b935cf85bbb53eb173dbc7cc13f132cf", "6c667b64372ef2df9ed997666a64b8ebfcab1f5adf97f54c9d476764f2d66141",
     "f4933074ed93f123401b2f7eb3d054667195fc101ab4d7a93e3138f9b397fc97", "5fedb3f1e94ce658665168ba257800eed79197036b3bce47894342fa11825676",
     "782b64992a340f3d42675d1ffafcd234aa98e4ff91e5da1431e777fb0d3e7a95", 715, "bb7423dc2a72bac593782cf6b872b96fbb2429cbdf759f4c9d8aeb5ff2843071"),
    (10,
     "3a97cf0227811de677e293e9365375d32cb997ee8f467ac23878610e02156cbb", "3585cd71523070d11dfe2d173f57f1b0d6ab7522fc0c128050fbd63a50fee57d",
     "077ea466a5ad8355c4afb4c4f0f27d71912c1d9f7a64607ca45858b38f6b167c", "2866acbd835355e80ce89144bcbcdc132fe10ef4ad34f12ce895fdaeff8602c8",
     "469aa3863e86b4194e40484881c88d841d7c2d2351dc7b419dcff7c1f4c21d9a", "eab0e6ca2c1ba4f99a8f2285c7cec2c1fa5b15d581c108be75686db92117632a",
     "a9a5dc85020a6810d8a764d44536cc796b44f2dcd359c6c80091396130b3dbba", 727, "ed543c2297161a348c1740260a0bcf8fcf67e0873e996d4518bf3876850cf03d"),
    (20,
     "7a4d019b404c0167b0c47de8654c5e9741fac27eb3c8a63313444811489c7e50", "6f3c730b2846120fb05d823957d6054ec3ab610adc23f3f628b8695a51b50970",
     "650dfa125d0b15d8c55db8fffefaaab15d430964141892bf42e46d1234b90ae4", "8292e1f344cc42cdf9499ca3133ae2f17271bc15778a0fc17c03a5c7ccfc3633",
     "7ff6595d9abf0c2e599ddf5870a8408f2f34ec2321f738a817d97e53fa7d06a1", "ed588d44cd8f6885d693984c51a70d4c3df18a43816bdc0f5bf246a602be9067",
     "fd32910ccabe0ff28d95782381a3f2e4571d09bdea9a87c3f01f4d93bf00fdaf", 712, "9a831d197c39bd1b6cee5492f572637e0700212ccce6669ea4915c3e853b797d"),
    (30,
     "42f917e2bb7fb5b720fa6ad74c28547f92ad83cdbcea173696b70707b24c5878", "7580f21377d38c499d53d21e49a9c1df37cf6b5590503cc5024d543f17815580",
     "7bbeba1f7704e94e06874d730cb24f7cefca8363b95c8c6372cbeb0bb28f07f2", "1070d179242cf61267491cf219809aa6a8fa57460b0a5f3495892b2a0de26af5",
     "be3103f072b32105476a91a5c50bcedbb9b83743f32ea7c49b06d90bb1b96340", "d1020876f5751f1a1f7c907abf3e201c73656586071da04a8b5e8609a3dfc422",
     "1ce3065bafc42bd46ba40ae4aed7f5e0876f7c72767a69bc9f87b7b67abc3c78", 713, "d0bcf994bf37356764e7a95db024e631cde269f128032b08f30defc693d2ae7f"),
    (40,
     "481ca94b8fea133ceed8fad48721770e298caaf39416f75652409036e0170bed", "d339aec3b3eddefd0066259058391fa4f17a191353cd621a6530557de39a77fc",
     "a13f4b31f375e6b3718dca26f2c1fa396cb78a6425bf9c0399292fb3fcc6f053", "e9a9308bf720d6b45fa87ee22aa79f8babbb510cf8d0bd4b486eb6f1e386e5ba",
     "cc4cf656ce18b0dece5fa23373d705a3947e068a61baf8c2f1c01f8e89a3b60d", "4f231b4ae8d53003a64d4ac705cc655085c9c79e7b21a1be915c46865fae154c",
     "7b235b9e60f5f972e07f4728aea8a690a508f2979b34464868061f5073b6de85", 714, "463d0ea01370234b534836b9b23945842d5cc9725e75456044724d1dd6106d6a"),
    (50,
     "e1085b9ea0d67177d7a9afbf4b51d169af51661c382e5abd19ca21d700b26e1a", "e37a1edd38d82b6013d60417c97ac092d083dd9029f1d9913e149b2cf24d9238",
     "fbea6a342b6dc57d6a9c199a69c6ad07b53befb919ea467862c8d1e388cbf19c", "2461a0aa3c16f2631c8dd2af6b86729b4951fc2668f12055225576890568d2d7",
     "5e0055e0c274f7eff66c819648948fb932488dc8abe2c58c5bed4f2e8e8510eb", "0ec773f0265891dae1e055ca0fcb09ebc0a07b5eb2ed1f172ed90038177cc2b3",
     "3b73be2b6b0c2331e65bac7bbf40bc8ff5d58e435a9149e9cfc1f273571ddb30", 719, "b0ca30ed15a3c1f47878b70ac15a7d6cc26a99069dbc41ef031ed6d66098004d"),
    (60,
     "d465a253d5e14473301a3e40d1b377f366628fd89e53a4b7efde521601976023", "f0f5bab019faebdb4dd96ea96cd81e345369d8cdfaf3248ca336a15b948441d3",
     "8b762948ce9b6341acbbc4665a9e3cf2ea217c56041290fdeefdc7a099185d02", "9828db0966b4e6f68eedf361701ce2880a1b493ce0f55a3240f85c25241937dc",
     "117f99fe21ce9503889be3717fa62015f3ecbe95bdc0223c29ba141bed8594de", "e5809c63b4f305033d55148fd7712c89ade08a4387e4349dffa96a4fa8fccaa2",
     "cb6356258017fb9f52e20a46e9f270cb216d4153dcb24a3ff5a7dff6ef089f69", 729, "6606363963976555db99bd075c537dea9a7e3cd569e5542aee75ffadf5dbd80b"),
    (70,
     "05cd99e267efecbebbc2201c45db77899a80b63ade5a045027dbcbd0c02101a7", "00bc7c6757dac604ca906fb2524d52f39e39815cdeb0c0a7eaa341ed20d5fc1d",
     "3173f5306d54d7a418d48feb4645aa4540f3450b4dbc8f0621fda602aa10c6da", "30dd938294cadc22a0c7b37e083a3fa2e7e75d1c3aa5850e8527e96118977881",
     "85036cada9ebbb7124c357c9267677c865f9b91650e86e4f6e1417bd9bcf0a8f", "a5692eeff17a62f321166bc310ecb1245770d85bb7607b7e474b82fc64e5cf20",
     "2c6ef50ac3f79f79f6cc2fc2186a73acdccfcb8a7996c9a231e6a9cb8783bb7e", 716, "70dbbd666090a196a005c6b8ef49f73fa407967089691081dd58be5c8da511a4"),
    (80,
     "7395c2494dd5b7132a3084524c55f5d96f3dd985d6c1df53fbae98c6e5ec28c5", "714abc3d0808bf21602661c193bce112bd34cac310f22f4e8ce9f848139fd098",
     "aca904d3c06319e6bcf04c4de10d252e67a613b20ae00431c04f49f345baf988", "0d2879a68caeccda8b98875b8517ba4b2ef42beb31644f8d956d217a3b75b59c",
     "0829f9084c29fd026320c906473c58c6fe6960345013acd96018fcf51755c26c", "9e084bc810383a6b098f2a08345974b2643e3d8ac03ad1ad6cec3bb5f84b0a05",
     "69dd50e8826bcb647f0366bc828bdef3cafaf4ba848548e7e9820a8f9713c6c5", 718, "0aed640975377cf7efabb851958d7a690a3b243bc11eee957f75c818b2d68448"),
    (90,
     "e5a95e0e378055383af60b8927d83be410125bec465d31f0341789805d45965f", "88b7735c1d29f7d6c494dc97d1fc7af3cc42f42e9d2d137eec2402b7f9e7b495",
     "d29852537f36a36fa3f0dbe30eb54faaed58d975ea707623eb10c8dd8e5a8025", "556c9a968c73724a80d1d3fc14d26985492d29e10e3b71a8bda44370f6cafc0f",
     "85e9f84e9a0b9b19ade3b2e3e79f93a5458b0cf87c9a23c568979a7798e9a23a", "e08909da4c3afbe12da2f8e9c6e7512414ddfcf92c623816f0e9986fd9bf2013",
     "58a27a98f8f462a0fdfc753cbd45b5d010f001fd7e0900601b29c25155de6807", 711, "5db23cbbbae30c6168945d8fe1bd0a89029e4e3aeb5cbdc8c08b4dda56334a77"),
)


def _respiratory_phase_sources(row):
    percent, ct_archive, ct_header, ct_voxels, mask_archive, mask_header, mask_raw, mask_voxels, point_size, point_hash = row
    return dict(percent=percent,
        image=dict(file=f"{percent:02}-MetaImage.tar", source=f"Images/MetaImage/{percent:02}-MetaImage.tar",
                   bytes=48936960, sha256=ct_archive, members=((313, ct_header), (48932640, ct_voxels)),
                   voxel_sha256=ct_voxels),
        mask=dict(file=f"{percent:02}Mask-MetaImage.tar", source=f"Masks/{percent:02}Mask-MetaImage.tar",
                  bytes=24473600, sha256=mask_archive, members=((326, mask_header), (24466320, mask_raw)),
                  voxel_sha256=mask_voxels),
        landmarks=dict(file=f"{percent:02}-Landmarks.pts", source=f"Landmarks/{percent:02}-Landmarks.pts",
                       bytes=point_size, sha256=point_hash))


RESPIRATORY_PHASES = tuple(_respiratory_phase_sources(row) for row in _RESPIRATORY_HASHES)


def cached_respiratory_example_available(cache_dir="data/respiratory-example"):
    root = Path(cache_dir)
    paths = [root / "sequence.json", root / "published-landmark-39.csv"]
    for phase in RESPIRATORY_PHASES:
        percent = phase["percent"]
        paths.extend((root / f"images/phase{percent:02}.mha",
                      root / f"masks/phase{percent:02}-lungs.mha",
                      root / f"source/{percent:02}-Landmarks.pts"))
    try:
        return bool(RESPIRATORY_PHASES) and all(path.is_file() and path.stat().st_size > 0
                                               for path in paths)
    except OSError:
        return False


def _respiratory_check_cancelled(cancelled):
    if cancelled is not None and cancelled():
        raise InterruptedError("Respiratory example setup cancelled.")


def _respiratory_valid_volume(path, expected_digest, dtype):
    try:
        volume = load_volume(path)
        return (volume.shape == RESPIRATORY_SHAPE_ZYX and volume.data.dtype == np.dtype(dtype)
                and np.allclose(volume.spacing, RESPIRATORY_SPACING, rtol=0, atol=1e-10)
                and np.array_equal(volume.origin, (0., 0., 0.))
                and np.array_equal(volume.direction, np.eye(3))
                and sha256(memoryview(np.ascontiguousarray(volume.data)).cast("B")).hexdigest()
                == expected_digest)
    except (OSError, ValueError, RuntimeError):
        return False


def _respiratory_convert_archive(archive, destination, phase, kind, staging, cancelled):
    record = phase[kind]
    prefix = f"{phase['percent']:02}-" + ("P" if kind == "image" else "air-body-lungs")
    expected = {prefix + suffix: member for suffix, member in
                zip((".mhd", ".raw"), record["members"])}
    with tarfile.open(archive, "r:") as source:
        members = source.getmembers()
        if (len(members) != 2 or {member.name for member in members} != set(expected)
                or any(not member.isfile() or member.size != expected[member.name][0]
                       for member in members)):
            raise ValueError("The respiratory archive has unexpected files, links or sizes.")
        raw = None
        for member in members:
            _respiratory_check_cancelled(cancelled)
            with source.extractfile(member) as stream:
                data = stream.read(member.size + 1)
            if (len(data) != member.size
                    or sha256(data).hexdigest() != expected[member.name][1]):
                raise ValueError("Respiratory archive member SHA-256 verification failed.")
            if member.name.endswith(".raw"):
                raw = data
        values = np.frombuffer(raw, dtype="<i2" if kind == "image" else np.uint8)
        values = values.reshape(RESPIRATORY_SHAPE_ZYX)
        if kind == "mask":
            values = (values == 2).astype(np.uint8)
        volume = Volume(values, RESPIRATORY_SPACING)
        converted = Path(staging) / f"{uuid4().hex}.mha"
        save_volume(volume, converted)
    _respiratory_check_cancelled(cancelled)
    if not _respiratory_valid_volume(converted, record["voxel_sha256"],
                                     "int16" if kind == "image" else "uint8"):
        raise ValueError("Respiratory conversion changed the source voxels or physical geometry.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(converted, destination)


def _respiratory_write_json(path, document):
    temporary = path.with_name(f"{uuid4().hex}.part")
    try:
        temporary.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_respiratory_example(cache_dir="data/respiratory-example", *, progress=None,
                               cancelled=None):
    root = Path(cache_dir).resolve()
    total = sum(phase[kind]["bytes"] for phase in RESPIRATORY_PHASES
                for kind in ("image", "mask", "landmarks"))
    completed = 0
    network_started = False
    points = []
    _respiratory_check_cancelled(cancelled)
    root.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(prefix=".popi-", dir=root) as staging:
            for phase in RESPIRATORY_PHASES:
                percent = phase["percent"]
                for kind in ("image", "mask", "landmarks"):
                    _respiratory_check_cancelled(cancelled)
                    record = phase[kind]
                    if kind == "landmarks":
                        destination = root / f"source/{percent:02}-Landmarks.pts"
                        valid = (destination.is_file() and destination.stat().st_size == record["bytes"]
                                 and _digest(destination) == record["sha256"])
                    else:
                        relative = (f"images/phase{percent:02}.mha" if kind == "image"
                                    else f"masks/phase{percent:02}-lungs.mha")
                        destination = root / relative
                        valid = _respiratory_valid_volume(destination, record["voxel_sha256"],
                                                          "int16" if kind == "image" else "uint8")
                    if not valid:
                        network_started = True
                        downloaded = Path(staging) / record["file"]
                        _download_verified(RESPIRATORY_SOURCE_URL + record["source"], downloaded,
                                           record["sha256"], max_bytes=record["bytes"],
                                           expected_bytes=record["bytes"], total_timeout=900,
                                           cancelled=cancelled,
                                           progress=(lambda received, limit: progress(completed + received, total))
                                           if progress is not None else None)
                        _respiratory_check_cancelled(cancelled)
                        if kind == "landmarks":
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            os.replace(downloaded, destination)
                        else:
                            _respiratory_convert_archive(downloaded, destination, phase, kind,
                                                         staging, cancelled)
                            downloaded.unlink()
                    completed += record["bytes"]
                    if progress is not None and network_started:
                        progress(completed, total)
                values = np.loadtxt(root / f"source/{percent:02}-Landmarks.pts", comments="#")
                if values.shape != (41, 3) or not np.isfinite(values).all():
                    raise ValueError("The provider landmarks must contain 41 finite physical points.")
                indices = values[:40] / np.asarray(RESPIRATORY_SPACING)
                if np.any(indices < 0) or np.any(indices > np.asarray(RESPIRATORY_SHAPE_ZYX[::-1]) - 1):
                    raise ValueError("A provider landmark lies outside its unchanged CT voxel grid.")
                points.append(dict(percent=percent, points=[
                    dict(id=f"POPI_{number:02}", source_point_number=number,
                         lps_mm=point.tolist(), continuous_index_xyz=index.tolist())
                    for number, (point, index) in enumerate(zip(values[:40], indices), 1)]))
            _respiratory_check_cancelled(cancelled)
            manifest = root / "sequence.json"
            document = dict(version=1, name="POPI research CT - complete ten-phase cycle",
                            segments=[dict(id="lungs", label=1, name="Lungs (source mask)",
                                           color="#98C5B6", kind="lung")],
                            phases=[dict(percent=phase["percent"],
                                         image=f"images/phase{phase['percent']:02}.mha",
                                         segmentation=f"masks/phase{phase['percent']:02}-lungs.mha")
                                    for phase in RESPIRATORY_PHASES])
            existing = None
            if manifest.is_file():
                try:
                    existing = json.loads(manifest.read_text(encoding="utf-8"))
                except (OSError, ValueError, UnicodeError):
                    pass
            if existing != document:
                _respiratory_write_json(manifest, document)
            sequence = load_ct_sequence(manifest)
            csv_path = root / "published-landmark-39.csv"
            try:
                series = load_landmarks(csv_path, sequence)
                valid = (series.reference_index == 1 and len(series.points) == len(points)
                         and all(np.array_equal(series.points[index], phase["points"][38]["lps_mm"])
                                 and series.sources[index] == "dataset"
                                 for index, phase in enumerate(points)))
            except (OSError, ValueError):
                valid = False
            if not valid:
                series = LandmarkSeries(sequence, "POPI expert landmark 39", 1,
                    provenance="POPI expert point39; Leon Berard Cancer Center and CREATIS Laboratory; "
                               "Vandemeulebroucke et al., ICCR2007. Source physical LPS millimetres; "
                               "artifact point41 excluded. Research reference, not a detected lesion.")
                for index, phase in enumerate(points):
                    series.set_point(index, phase["points"][38]["lps_mm"], "dataset")
                series.export_csv(csv_path)
            if not (root / "reference-landmarks.json").exists():
                _respiratory_write_json(root / "reference-landmarks.json",
                    dict(coordinate_system="LPS_mm_in_source_cropped_first_voxel_frame", units="mm",
                         index_base=0, source="POPI expert landmarks", excluded_point_number=41,
                         exclusion_reason="provider declares final point an image artifact", phases=points))
            if not (root / "provenance.json").exists():
                _respiratory_write_json(root / "provenance.json",
                    dict(dataset="POPI: Point-validated Pixel-based Breathing Thorax Model",
                         provider="Leon Berard Cancer Center and CREATIS Laboratory, Lyon, France",
                         current_provider_page=RESPIRATORY_PROVIDER_URL,
                         publication="Vandemeulebroucke, Sarrut and Clarysse, ICCR2007",
                         reuse="Research use with institutional acknowledgement and publication citation; "
                               "consult provider terms for other uses. No standard data licence asserted.",
                         conversion="Lossless compressed CT; source lung label2 to binary1; "
                                    "unchanged cropped LPS geometry; no registration or interpolation.",
                         time_seconds_available=False, source_files=RESPIRATORY_PHASES))
            _respiratory_check_cancelled(cancelled)
            return manifest
    except InterruptedError:
        raise
    except (OSError, ValueError, RuntimeError, tarfile.TarError) as error:
        raise RuntimeError("The respiratory CT example could not be prepared. Check the internet connection "
                           "and available disk space, then retry; verified phases are kept for resuming. "
                           + str(error)) from error



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
            or np.any(labels < 0) or np.any(labels > 5)
            or (labels.dtype.kind == "f" and (not np.isfinite(labels).all()
                or not np.equal(labels, np.rint(labels)).all()))):
        raise ValueError("Lobe labels must match the CT grid and contain only integers from 0 to 5.")
    masks = {key: labels == label for label, key, _, _ in LOBE_SEGMENTS}
    if not all(mask.any() for mask in masks.values()):
        raise ValueError("The segmentation must contain all five lung lobes using labels 1 to 5.")
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


def _valid_lobe_mesh_arrays(points, faces, hu, rgb, volume, *, margin_voxels=.6):
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
    return bool(np.all(indices >= -margin_voxels)
                and np.all(indices <= np.array(volume.shape[::-1]) - 1 + margin_voxels))


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
    temporary = path.with_name(f"{uuid4().hex}.part")
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


AIRWAY_CACHE_VERSION = "central-airways-v1"
AIRWAY_SEED_HU_RANGE = (-1100, -850)
AIRWAY_KEY = "airways"
AIRWAY_STYLE = StructureStyle("Trachea and bronchi", "#a5dce6", .9,
                              ct_coloring=False, kind="other")


def _airway_mask(mask, reference):
    labels = np.asarray(mask)
    if (labels.shape != reference.shape or labels.dtype.kind not in "buif"
            or np.any(labels < 0)
            or (labels.dtype.kind == "f" and (not np.isfinite(labels).all()
                or not np.equal(labels, np.rint(labels)).all()))):
        raise ValueError("An airway mask must match the CT grid and contain discrete nonnegative labels.")
    positive = np.unique(labels[labels > 0])
    if len(positive) != 1:
        raise ValueError("An airway mask must contain one nonempty foreground label.")
    result = np.asarray(labels > 0, dtype=bool)
    region = ndimage.find_objects(result, max_label=1)[0]
    if ndimage.label(result[region])[1] != 1:
        raise ValueError("An airway mask must form one connected trachea and bronchial tree.")
    return result


def load_airway_segmentation(path, reference):
    image = load_segmentation(path, reference)
    return _airway_mask(image.data, reference)


def _airway_metadata(metadata, volume, mask, source_digest):
    if not isinstance(metadata, dict):
        raise ValueError("Airway provenance must be a metadata dictionary.")
    for name in ("method", "model", "model_version"):
        if not isinstance(metadata.get(name), str) or not metadata[name].strip():
            raise ValueError(f"Airway provenance requires a nonblank {name}.")
    source_kind = metadata.get("source_kind", "supplied")
    if source_kind not in ("automated", "supplied"):
        raise ValueError("Airway provenance source_kind must be automated or supplied.")
    try:
        result = json.loads(json.dumps(metadata, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError("Airway provenance must contain finite JSON-compatible values.") from error
    result.update(
        source_kind=source_kind, source_ct_sha256=source_digest,
        mask_sha256=_lobe_array_digest([np.asarray(mask, dtype=np.uint8)]),
        shape_zyx=list(volume.shape), spacing_xyz_mm=list(volume.spacing),
        origin_lps_mm=list(volume.origin), direction=volume.direction.tolist(),
        coordinate_system="LPS millimetres", expert_reviewed=False,
        segments=[dict(label=1, key=AIRWAY_KEY, name=AIRWAY_STYLE.name,
                       color=AIRWAY_STYLE.color)],
    )
    return result


def build_airway_cache(volume, mask, metadata, cache_dir="data/airways"):
    mask = _airway_mask(mask, volume)
    source_digest = _lobe_source_digest(volume)
    metadata = _airway_metadata(metadata, volume, mask, source_digest)
    masks = {AIRWAY_KEY: mask}
    meshes = prepare_display_meshes(volume, masks)
    mesh = meshes.get(AIRWAY_KEY)
    if mesh is None:
        raise ValueError("The airway mask must have a nonempty reconstructed surface.")
    arrays = (np.asarray(mesh.points), np.asarray(mesh.faces).reshape(-1, 4),
              np.asarray(mesh["CT_HU"]), np.asarray(mesh["CT_RGB"]))
    if not _valid_lobe_mesh_arrays(*arrays, volume):
        raise ValueError("The reconstructed airway has invalid surface data.")
    metadata_json = json.dumps(metadata, sort_keys=True, allow_nan=False)
    content = dict(version=np.array(AIRWAY_CACHE_VERSION), max_cells=np.array(DISPLAY_MAX_CELLS),
                   metadata=np.array(metadata_json),
                   metadata_sha256=np.array(sha256(metadata_json.encode("utf-8")).hexdigest()),
                   mask=mask.astype(np.uint8), source_ct_sha256=np.array(source_digest),
                   mesh_sha256=np.array(_lobe_array_digest(arrays)))
    content.update(zip(("points", "faces", "hu", "rgb"), arrays))
    path = Path(cache_dir).resolve() / "airways-cache.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{uuid4().hex}.part")
    try:
        with temporary.open("xb") as output:
            np.savez_compressed(output, **content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return masks, meshes, {AIRWAY_KEY: AIRWAY_STYLE}, metadata


def load_airway_cache(volume, cache_dir="data/airways"):
    path = Path(cache_dir) / "airways-cache.npz"
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as saved:
            if (str(saved["version"].item()) != AIRWAY_CACHE_VERSION
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
            stored_mask = saved["mask"]
            if stored_mask.dtype != np.uint8 or np.any(stored_mask > 1):
                return None
            mask = _airway_mask(stored_mask, volume)
            source_digest = _lobe_source_digest(volume)
            if (str(saved["source_ct_sha256"].item()) != source_digest
                    or _airway_metadata(metadata, volume, mask, source_digest) != metadata):
                return None
            arrays = tuple(saved[name] for name in ("points", "faces", "hu", "rgb"))
            if (not _valid_lobe_mesh_arrays(*arrays, volume)
                    or str(saved["mesh_sha256"].item()) != _lobe_array_digest(arrays)):
                return None
            import pyvista as pv
            points, faces, hu, rgb = arrays
            mesh = pv.PolyData(points, faces.ravel())
            mesh.point_data["CT_HU"], mesh.point_data["CT_RGB"] = hu, rgb
            mesh.field_data["CT_sampling_inset_mm"] = [0.]
            mesh.field_data["source"] = ["reference CT in physical LPS millimetres"]
            return {AIRWAY_KEY: mask}, {AIRWAY_KEY: mesh}, {AIRWAY_KEY: AIRWAY_STYLE}, metadata
    except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile, OverflowError):
        return None


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


def _target_number(value, label, *, minimum=0., maximum=np.inf, positive=False):
    if (isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))):
        raise ValueError(f"{label} must be a finite number.")
    try:
        value = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a finite number.") from error
    if (not np.isfinite(value) or value < minimum or value > maximum
            or positive and value <= 0):
        raise ValueError(f"{label} is outside its supported range.")
    return value


def _target_point(value):
    try:
        point = np.asarray(value)
        if point.shape != (3,) or point.dtype.kind not in "iuf":
            raise ValueError
        point = point.astype(float)
        if not np.isfinite(point).all():
            raise ValueError
        return tuple(float(coordinate) for coordinate in point)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("A target centre must contain three finite LPS millimetre coordinates.") from error


@dataclass(frozen=True)
class ResearchTarget:
    name: str
    center_lps_mm: tuple
    radius_mm: float
    study_id: str
    kind: str = "simulated"

    def __post_init__(self):
        object.__setattr__(self, "name", _landmark_text(self.name, "Target name"))
        object.__setattr__(self, "center_lps_mm", _target_point(self.center_lps_mm))
        object.__setattr__(self, "radius_mm", _target_number(self.radius_mm, "Target radius", positive=True))
        if (not isinstance(self.study_id, str) or len(self.study_id) != 64
                or any(character not in "0123456789abcdef" for character in self.study_id)):
            raise ValueError("A target must identify its reference CT source snapshot.")
        if not isinstance(self.kind, str) or self.kind != "simulated":
            raise ValueError("This target is a user-defined simulation sphere, not a patient lesion annotation.")


def target_study_id(volume):
    if not isinstance(volume, Volume):
        raise ValueError("A simulated target requires a reference CT volume.")
    return _lobe_source_digest(volume)


def create_research_target(volume, lung_mask, center, radius_mm, name="Simulated target"):
    if not isinstance(volume, Volume):
        raise ValueError("A simulated target requires a reference CT volume.")
    center = _target_point(center)
    radius = _target_number(radius_mm, "Target radius", positive=True)
    if (not isinstance(lung_mask, np.ndarray) or lung_mask.dtype != bool
            or lung_mask.shape != volume.shape):
        raise ValueError("Target containment requires a boolean lung mask aligned with the reference CT.")
    voxel = volume.world_to_index(center)
    spacing = np.asarray(volume.spacing)
    limits = np.asarray(volume.shape[::-1]) - 1
    margin = radius / spacing
    if np.any(voxel - margin < -1e-9) or np.any(voxel + margin > limits + 1e-9):
        raise ValueError("The complete simulated target must lie inside the oriented CT voxel grid.")
    low = np.maximum(0, np.ceil(voxel - margin - .5).astype(int))
    high = np.minimum(limits, np.floor(voxel + margin + .5).astype(int))
    x = np.maximum(np.abs(np.arange(low[0], high[0] + 1) - voxel[0]) - .5, 0.) * spacing[0]
    y = np.maximum(np.abs(np.arange(low[1], high[1] + 1) - voxel[1]) - .5, 0.) * spacing[1]
    xy_distance_squared = y[:, None] ** 2 + x[None, :] ** 2
    # voxel-cell distances avoid approximate surface sampling and a full-volume distance transform.
    for z in range(low[2], high[2] + 1):
        dz = max(abs(z - voxel[2]) - .5, 0.) * spacing[2]
        intersects = xy_distance_squared + dz * dz < radius * radius
        if np.any(intersects & ~lung_mask[z, low[1]:high[1] + 1, low[0]:high[0] + 1]):
            raise ValueError("The complete simulated target must lie inside the available lung segmentation.")
    return ResearchTarget(name, center, radius, target_study_id(volume))


def target_position(target, deformation, model, time):
    if (not isinstance(target, ResearchTarget) or not isinstance(deformation, LungDeformation)
            or not isinstance(model, RespiratoryModel)):
        raise ValueError("Target motion requires a defined target and the shared respiratory deformation.")
    time = _target_number(time, "Target time", maximum=model.duration)
    return deformation.forward(target.center_lps_mm, model.evaluate(time)[0])


def target_slice_contour(target, plane, matrix, segments=64):
    if not isinstance(target, ResearchTarget) or not isinstance(plane, SlicePlane):
        raise ValueError("A target section requires a target and a physical slice plane.")
    if isinstance(segments, (bool, np.bool_)) or not isinstance(segments, (int, np.integer)) or not 8 <= segments <= 512:
        raise ValueError("A target contour must use between 8 and 512 segments.")
    try:
        matrix = np.asarray(matrix, dtype=float)
        basis = np.column_stack((plane.u, plane.v))
        if (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
                or not np.allclose(matrix[3], [0., 0., 0., 1.], rtol=0, atol=1e-12)
                or not np.isfinite(basis).all() or not np.isfinite(plane.origin).all()
                or not np.allclose(basis.T @ basis, np.eye(2), rtol=0, atol=1e-8)):
            raise ValueError
        inverse = np.linalg.inv(matrix[:3, :3])
        offset = inverse @ (plane.origin - matrix[:3, 3]) - target.center_lps_mm
        pulled_basis = inverse @ basis
        gram = pulled_basis.T @ pulled_basis
        centre = -np.linalg.solve(gram, pulled_basis.T @ offset)
        closest = offset + pulled_basis @ centre
        remaining = target.radius_mm ** 2 - float(closest @ closest)
        if remaining <= 1e-10 * target.radius_mm ** 2:
            return None
        values, vectors = np.linalg.eigh(gram)
        if np.any(values <= 0) or not np.isfinite(values).all():
            raise ValueError
        angle = np.linspace(0., 2. * np.pi, int(segments) + 1)
        circle = np.stack((np.cos(angle), np.sin(angle)))
        ellipse = centre[:, None] + vectors @ (np.sqrt(remaining / values)[:, None] * circle)
        points = plane.origin + (basis @ ellipse).T
        if not np.isfinite(points).all():
            raise ValueError
        return points
    except (ValueError, TypeError, np.linalg.LinAlgError) as error:
        raise ValueError("Target sections require a finite invertible affine transform and an orthonormal slice plane.") from error


@dataclass(frozen=True)
class ObservationSettings:
    rate_hz: float = 10.
    noise_std_mm: float = .5
    seed: int = 17

    def __post_init__(self):
        object.__setattr__(self, "rate_hz", _target_number(self.rate_hz, "Observation rate", minimum=.1, maximum=100.))
        object.__setattr__(self, "noise_std_mm", _target_number(self.noise_std_mm, "Observation noise", maximum=20.))
        if (isinstance(self.seed, (bool, np.bool_)) or not isinstance(self.seed, (int, np.integer))
                or not 0 <= self.seed <= 2 ** 32 - 1):
            raise ValueError("The observation seed must be an integer between 0 and 4294967295.")
        object.__setattr__(self, "seed", int(self.seed))


def respiratory_model_id(model):
    if not isinstance(model, RespiratoryModel):
        raise ValueError("Observation history requires the shared respiratory model.")
    digest = sha256()
    for values in (np.asarray([model.duration]), model.axes, model._phase.x, model._phase.c,
                   model._amplitude.x, model._amplitude.c):
        array = np.asarray(values, dtype="<f8")
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def check_export_destination(path, protected_paths=()):
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Save observation history to a .csv file.")
    resolved = path.resolve()
    destination = os.path.normcase(str(resolved))
    sources = [Path(source) for source in protected_paths]
    for source in tuple(sources):
        if source.is_dir():
            if resolved.is_relative_to(source.resolve()):
                raise ValueError("Observation export cannot write inside a protected CT source directory.")
            sources.extend(member for member in source.iterdir() if member.is_file())
        elif source.is_file():
            sources.extend(_ct_external_payload(source))
    for source in sources:
        if (destination == os.path.normcase(str(source.resolve()))
                or path.exists() and source.exists() and os.path.samefile(path, source)):
            raise ValueError("Observation export cannot overwrite a CT source, segmentation or protected project file.")
    return path


@dataclass(frozen=True)
class TargetObservations:
    target: ResearchTarget
    settings: ObservationSettings
    through_s: float
    model_id: str
    deformation: LungDeformation
    _times_s: np.ndarray = field(repr=False)
    _observed_lps_mm: np.ndarray = field(repr=False)
    _truth_lps_mm: np.ndarray = field(repr=False)
    _events: tuple = field(repr=False)

    def __post_init__(self):
        if (not isinstance(self.target, ResearchTarget) or not isinstance(self.settings, ObservationSettings)
                or not isinstance(self.deformation, LungDeformation)):
            raise ValueError("Observation history requires validated target and sampling settings.")
        cutoff = _target_number(self.through_s, "Observation cutoff")
        object.__setattr__(self, "through_s", cutoff)
        if cutoff > 100000 / self.settings.rate_hz:
            raise ValueError("Observation history must contain at most 100001 samples.")
        expected_times = np.arange(int(np.floor(np.nextafter(cutoff * self.settings.rate_hz, np.inf))) + 1) / self.settings.rate_hz
        expected_times = expected_times[expected_times <= cutoff]
        times = np.asarray(self._times_s, dtype=float)
        if (times.ndim != 1 or not 1 <= times.size <= 100001 or not np.isfinite(times).all()
                or times[0] != 0. or np.any(np.diff(times) <= 0) or times[-1] > cutoff
                or times.shape != expected_times.shape
                or not np.allclose(times, expected_times, rtol=0, atol=1e-12)):
            raise ValueError("Observation timestamps must follow the fixed sampling grid through the selected cutoff.")
        for name, array in (("_times_s", times), ("_observed_lps_mm", self._observed_lps_mm),
                            ("_truth_lps_mm", self._truth_lps_mm)):
            array = np.asarray(array, dtype=float)
            expected = times.shape if name == "_times_s" else (times.size, 3)
            if array.shape != expected or not np.isfinite(array).all():
                raise ValueError("Observation and evaluation positions must match their finite timestamps.")
            # immutable byte storage prevents later model edits or caller writes from changing a snapshot.
            object.__setattr__(self, name, np.frombuffer(array.tobytes(), dtype=float).reshape(array.shape))
        if (not isinstance(self.model_id, str) or len(self.model_id) != 64
                or any(character not in "0123456789abcdef" for character in self.model_id)):
            raise ValueError("Observation history must identify its captured respiratory model.")
        events = tuple((float(start), settings) for start, settings in self._events)
        if any(not np.isfinite(start) or not 0 <= start <= cutoff or not isinstance(settings, BreathingSettings)
               for start, settings in events):
            raise ValueError("Observation provenance may contain only available breathing settings.")
        object.__setattr__(self, "_events", events)

    @property
    def times_s(self):
        return self._times_s.copy()

    @property
    def observed_lps_mm(self):
        return self._observed_lps_mm.copy()

    @property
    def evaluation_ground_truth_lps_mm(self):
        return self._truth_lps_mm.copy()

    def observations_through(self, time_s):
        cutoff = _target_number(time_s, "Observation time", maximum=self.through_s)
        count = np.searchsorted(self._times_s, cutoff, side="right")
        return self._times_s[:count].copy(), self._observed_lps_mm[:count].copy()

    def export_csv(self, path, *, include_truth=False, protected_paths=()):
        if type(include_truth) is not bool:
            raise ValueError("Choose explicitly whether the export includes evaluation ground truth.")
        path = Path(path)
        protected_paths = tuple(Path(source) for source in protected_paths)

        def check_destination():
            check_export_destination(path, protected_paths)

        events = [dict(time_s=start, amplitude_mm=float(settings.amplitude), rate_bpm=float(settings.rate_bpm),
                       pattern=settings.pattern, seed=int(settings.seed)) for start, settings in self._events]
        metadata = dict(version=1, record_kind="evaluation_ground_truth" if include_truth else "noisy_observations",
                        study_id=self.target.study_id, target_name=self.target.name, target_kind=self.target.kind,
                        **dict(zip(("reference_x_lps_mm", "reference_y_lps_mm", "reference_z_lps_mm"), self.target.center_lps_mm)),
                        reference_radius_mm=self.target.radius_mm, coordinate_frame="LPS", position_unit="mm", time_unit="s",
                        rate_hz=self.settings.rate_hz, noise_std_mm=self.settings.noise_std_mm,
                        through_s=self.through_s, model_id=self.model_id, base_z_mm=self.deformation.base_z,
                        apex_z_mm=self.deformation.apex_z)
        if include_truth:
            metadata.update(noise_seed=self.settings.seed,
                            breathing_events_json=json.dumps(events, separators=(",", ":"), allow_nan=False))
        fields = [*metadata, "time_s", "observed_x_lps_mm", "observed_y_lps_mm", "observed_z_lps_mm"]
        if include_truth:
            fields += ["true_x_lps_mm", "true_y_lps_mm", "true_z_lps_mm"]
        check_destination()
        temporary = path.with_name(f"{uuid4().hex}.part")
        try:
            with temporary.open("x", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                for index, time in enumerate(self._times_s):
                    row = dict(metadata, time_s=float(time),
                               **dict(zip(fields[len(metadata) + 1:len(metadata) + 4], self._observed_lps_mm[index])))
                    if include_truth:
                        row.update(zip(fields[-3:], self._truth_lps_mm[index]))
                    writer.writerow(row)
            check_destination()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path


def generate_target_observations(target, model, deformation, settings=None, *, through_s):
    settings = ObservationSettings() if settings is None else settings
    if (not isinstance(target, ResearchTarget) or not isinstance(model, RespiratoryModel)
            or not isinstance(deformation, LungDeformation) or not isinstance(settings, ObservationSettings)):
        raise ValueError("Observation generation requires a target and validated motion and sampling settings.")
    cutoff = _target_number(through_s, "Observation cutoff", maximum=model.duration)
    if cutoff > 100000 / settings.rate_hz:
        raise ValueError("Generate at most 100001 observations at once.")
    sample_count = int(np.floor(np.nextafter(cutoff * settings.rate_hz, np.inf))) + 1
    times = np.arange(sample_count, dtype=float) / settings.rate_hz
    times = times[times <= cutoff]
    displacement = model.evaluate(times)[0]
    if np.any(1. - displacement[:, 2] / deformation.height < .5):
        raise ValueError("The selected motion would excessively compress the simulated target anatomy.")
    weight = (deformation.apex_z - target.center_lps_mm[2]) / deformation.height
    truth = np.asarray(target.center_lps_mm) + weight * displacement
    noise = np.random.default_rng(settings.seed).normal(0., settings.noise_std_mm, size=truth.shape)
    events = tuple((start, value) for start, value in model.events if start <= cutoff)
    return TargetObservations(target, settings, cutoff, respiratory_model_id(model), deformation,
                              times, truth + noise, truth, events)


BASELINE_METHODS = ("Constant position", "Constant velocity", "Sinusoidal fit")


@dataclass(frozen=True)
class ForecastSettings:
    history_window_s: float = 20.
    velocity_window_s: float = 1.
    min_rate_bpm: float = 6.
    max_rate_bpm: float = 36.

    def __post_init__(self):
        for name, minimum, maximum in (("history_window_s", .1, 120.),
                                       ("velocity_window_s", .1, 10.),
                                       ("min_rate_bpm", 1., 120.), ("max_rate_bpm", 1., 120.)):
            object.__setattr__(self, name, _target_number(getattr(self, name), name.replace("_", " "),
                                                         minimum=minimum, maximum=maximum))
        if self.min_rate_bpm >= self.max_rate_bpm:
            raise ValueError("The frequency search requires an increasing breathing-rate range.")
        if self.velocity_window_s > self.history_window_s:
            raise ValueError("The velocity window cannot exceed the available history window.")


@dataclass(frozen=True)
class BaselineFit:
    method: str
    origin_s: float
    last_observation_s: float
    history_start_s: float
    n_samples: int
    settings: ForecastSettings
    frequency_hz: float | None
    _coefficients: np.ndarray = field(repr=False)
    note: str = ""

    def __post_init__(self):
        if self.method not in BASELINE_METHODS or not isinstance(self.settings, ForecastSettings):
            raise ValueError("A baseline fit requires a known method and validated settings.")
        for name in ("origin_s", "last_observation_s", "history_start_s"):
            object.__setattr__(self, name, _target_number(getattr(self, name), name.replace("_", " ")))
        if (not self.history_start_s <= self.last_observation_s <= self.origin_s
                or isinstance(self.n_samples, (bool, np.bool_))
                or not isinstance(self.n_samples, (int, np.integer)) or not 1 <= self.n_samples <= 512):
            raise ValueError("A baseline fit must identify its available observation history.")
        object.__setattr__(self, "n_samples", int(self.n_samples))
        if self.frequency_hz is not None:
            value = _target_number(self.frequency_hz, "Fitted frequency", positive=True)
            if self.method != "Sinusoidal fit" or not self.settings.min_rate_bpm / 60 <= value <= self.settings.max_rate_bpm / 60:
                raise ValueError("The fitted frequency must lie in the declared search range.")
            object.__setattr__(self, "frequency_hz", value)
        expected = 2 if self.method == "Constant velocity" else 3 if self.frequency_hz is not None else 1
        coefficients = np.asarray(self._coefficients, dtype=float)
        if coefficients.shape != (expected, 3) or not np.isfinite(coefficients).all():
            raise ValueError("A baseline fit requires finite physical position coefficients.")
        object.__setattr__(self, "_coefficients", np.frombuffer(coefficients.tobytes(), dtype=float).reshape(coefficients.shape))
        if not isinstance(self.note, str):
            raise ValueError("A baseline note must be text.")

    def predict(self, query_times_s):
        raw = np.asarray(query_times_s)
        if raw.dtype.kind not in "iuf" or raw.ndim > 1 or raw.size > 2001:
            raise ValueError("Prediction times must be a scalar or a bounded numeric time vector.")
        query = raw.astype(float)
        if (not np.isfinite(query).all() or np.any(query < self.origin_s - 1e-10)
                or np.any(query > self.origin_s + 5. + 1e-10)):
            raise ValueError("Predictions must be between the origin and five seconds ahead.")
        relative = query - self.origin_s
        if self.method == "Constant velocity":
            result = self._coefficients[0] + relative[..., None] * self._coefficients[1]
        elif self.frequency_hz is not None:
            angle = 2. * np.pi * self.frequency_hz * relative
            result = (self._coefficients[0] + np.sin(angle)[..., None] * self._coefficients[1]
                      + np.cos(angle)[..., None] * self._coefficients[2])
        else:
            result = np.broadcast_to(self._coefficients[0], (*query.shape, 3)).copy()
        if not np.isfinite(result).all():
            raise ValueError("The baseline extrapolation produced a non-finite position.")
        return result

    @property
    def position_lps_mm(self):
        return self.predict(self.origin_s)

    @property
    def velocity_lps_mm_s(self):
        if self.method == "Constant velocity":
            return self._coefficients[1].copy()
        if self.frequency_hz is not None:
            return 2. * np.pi * self.frequency_hz * self._coefficients[1]
        return np.zeros(3)


def _forecast_settings(settings):
    if settings is None:
        return ForecastSettings()
    if not isinstance(settings, ForecastSettings):
        raise ValueError("Forecasting requires validated history and frequency settings.")
    return settings


def _forecast_arrays(times_s, positions=None):
    raw = np.asarray(times_s)
    if raw.dtype.kind not in "iuf" or raw.ndim != 1 or not 1 <= raw.size <= 100001:
        raise ValueError("Observation times must be a nonempty, bounded numeric vector.")
    times = raw.astype(float)
    if not np.isfinite(times).all() or np.any(times < 0) or np.any(np.diff(times) <= 0):
        raise ValueError("Observation times must be finite, nonnegative and strictly increasing.")
    if positions is None:
        return times
    raw = np.asarray(positions)
    if raw.dtype.kind not in "iuf" or raw.shape != (times.size, 3):
        raise ValueError("Observed LPS positions must have one numeric xyz row per timestamp.")
    return times, raw


def _baseline_window(times, positions, duration):
    lower = times[-1] - duration
    start = int(np.searchsorted(times, lower - 1e-10))
    # retain the preceding sample when an irregular grid straddles the window boundary.
    if start and times[-1] - times[start] < duration - 1e-9:
        start -= 1
    times, positions = times[start:], positions[start:]
    if times.size > 512:
        indices = np.unique(np.rint(np.linspace(0, times.size - 1, 512)).astype(int))
        times, positions = times[indices], positions[indices]
    return times, positions


def fit_baseline(times_s, observed_lps_mm, method, *, origin_s, settings=None):
    settings = _forecast_settings(settings)
    if not isinstance(method, str) or method not in BASELINE_METHODS:
        raise ValueError("Choose a known mathematical baseline.")
    origin = _target_number(origin_s, "Forecast origin")
    times, raw = _forecast_arrays(times_s, observed_lps_mm)
    count = int(np.searchsorted(times, origin, side="right"))
    if not count:
        raise ValueError("No observations are available at the forecast origin.")
    times, positions = times[:count], raw[:count].astype(float)
    if not np.isfinite(positions).all():
        raise ValueError("Available observed positions must be finite.")
    if method == "Constant position":
        return BaselineFit(method, origin, float(times[-1]), float(times[-1]), 1,
                           settings, None, positions[-1:].copy(), "Last available noisy observation.")
    duration = settings.velocity_window_s if method == "Constant velocity" else settings.history_window_s
    times, positions = _baseline_window(times, positions, duration)
    span = times[-1] - times[0]
    relative = times - origin
    centre = positions.mean(axis=0)
    centred = positions - centre
    if method == "Constant velocity":
        if times.size < 2 or span < 1e-8:
            raise ValueError("Constant velocity needs at least two distinct observed timestamps.")
        coefficients = np.linalg.lstsq(np.column_stack((np.ones(times.size), relative)), centred, rcond=None)[0]
        coefficients[0] += centre
        return BaselineFit(method, origin, float(times[-1]), float(times[0]), times.size,
                           settings, None, coefficients, "Local least-squares velocity from noisy observations.")
    required_span = 2. * 60. / settings.min_rate_bpm
    if times.size < 12 or span < required_span - 1e-8:
        raise ValueError(f"Sinusoidal fit needs at least {required_span:g} seconds and 12 samples of observed history.")
    if np.max(np.diff(times)) * (settings.max_rate_bpm / 60.) >= .5:
        raise ValueError("Sampling is too sparse for the sinusoidal frequency search range.")
    if np.max(np.ptp(positions, axis=0)) <= 1e-8:
        return BaselineFit(method, origin, float(times[-1]), float(times[0]), times.size,
                           settings, None, centre[None, :], "Flat observed history; frequency is not identifiable.")

    def profile(frequency, *, coefficients=False):
        angle = 2. * np.pi * frequency * relative
        design = np.column_stack((np.ones(times.size), np.sin(angle), np.cos(angle)))
        fitted = np.linalg.lstsq(design, centred, rcond=None)[0]
        residual = centred - design @ fitted
        error = float(np.sum(residual * residual))
        if coefficients:
            fitted[0] += centre
            return error, fitted
        return error

    frequencies = np.linspace(settings.min_rate_bpm / 60., settings.max_rate_bpm / 60., 201)
    errors = np.array([profile(frequency) for frequency in frequencies])
    local = [index for index in range(errors.size)
             if (index == 0 or errors[index] <= errors[index - 1])
             and (index == errors.size - 1 or errors[index] <= errors[index + 1])]
    best = int(np.argmin(errors))
    frequency, error = float(frequencies[best]), float(errors[best])
    for index in sorted(local, key=lambda item: errors[item])[:5]:
        lower, upper = frequencies[max(0, index - 1)], frequencies[min(frequencies.size - 1, index + 1)]
        refined = minimize_scalar(profile, bounds=(lower, upper), method="bounded",
                                  options={"xatol": 1e-10, "maxiter": 60})
        if refined.success and refined.fun < error:
            frequency, error = float(refined.x), float(refined.fun)
    constant_error = float(np.sum(centred * centred))
    if 1. - error / constant_error < .25:
        raise ValueError("Observed history has no clear periodic signal for a sinusoidal fit.")
    _, coefficients = profile(frequency, coefficients=True)
    note = "Shared frequency estimated from past noisy LPS observations."
    if min(abs(frequency - frequencies[0]), abs(frequency - frequencies[-1])) < 1e-6:
        note += " Frequency is at a search limit."
    return BaselineFit(method, origin, float(times[-1]), float(times[0]), times.size,
                       settings, frequency, coefficients, note)


def select_validation_origins(times_s, *, through_s, horizon_s, settings=None, max_origins=40):
    settings = _forecast_settings(settings)
    times = _forecast_arrays(times_s)
    through = _target_number(through_s, "Validation cutoff")
    horizon = _target_number(horizon_s, "Prediction horizon", minimum=.1, maximum=5.)
    if isinstance(max_origins, (bool, np.bool_)) or not isinstance(max_origins, (int, np.integer)) or not 1 <= max_origins <= 100:
        raise ValueError("Validation requires between 1 and 100 origin times.")
    available = times[(times >= times[0] + settings.history_window_s - 1e-10)
                      & (times + horizon <= through + 1e-10)]
    if available.size > max_origins:
        available = available[np.unique(np.rint(np.linspace(0, available.size - 1, max_origins)).astype(int))]
    return available.copy()


@dataclass(frozen=True)
class BaselineEvaluation:
    horizon_s: float
    methods: tuple
    candidate_count: int
    paired_count: int
    _rows: tuple = field(repr=False)
    _unavailable: tuple = field(repr=False)

    @property
    def rows(self):
        return tuple(dict(method=row[0], origin_s=row[1], query_s=row[2], predicted_lps_mm=row[3],
                          true_lps_mm=row[4], error_mm=row[5]) for row in self._rows)

    @property
    def unavailable(self):
        return tuple(dict(method=row[0], origin_s=row[1], reason=row[2]) for row in self._unavailable)

    @property
    def summaries(self):
        result = []
        for method in self.methods:
            errors = np.array([row[5] for row in self._rows if row[0] == method])
            result.append(dict(method=method, count=errors.size,
                               mean_error_mm=float(errors.mean()) if errors.size else None,
                               rmse_mm=float(np.sqrt(np.mean(errors * errors))) if errors.size else None))
        return tuple(result)


def evaluate_baselines(times_s, observed_lps_mm, origins_s, evaluation_truth_lps_mm, *,
                       horizon_s, settings=None, methods=None):
    settings = _forecast_settings(settings)
    times, observations = _forecast_arrays(times_s, observed_lps_mm)
    horizon = _target_number(horizon_s, "Prediction horizon", minimum=.1, maximum=5.)
    methods = BASELINE_METHODS if methods is None else tuple(methods)
    if (not methods or any(not isinstance(method, str) or method not in BASELINE_METHODS for method in methods)
            or len(methods) != len(set(methods))):
        raise ValueError("Validation requires unique, known baseline methods.")
    origins = np.asarray(origins_s)
    labels = np.asarray(evaluation_truth_lps_mm)
    if (origins.dtype.kind not in "iuf" or origins.ndim != 1 or origins.size > 100
            or not np.isfinite(origins).all() or np.any(origins < 0) or np.any(np.diff(origins) <= 0)
            or labels.dtype.kind not in "iuf" or labels.shape != (origins.size, 3) or not np.isfinite(labels).all()):
        raise ValueError("Validation requires ordered origins and one finite evaluation-only xyz label per origin.")
    rows, unavailable, paired = [], [], 0
    for origin, label in zip(origins.astype(float), labels.astype(float)):
        count = int(np.searchsorted(times, origin, side="right"))
        predictions = []
        for method in methods:
            try:
                fit = fit_baseline(times[:count], observations[:count], method, origin_s=float(origin), settings=settings)
                prediction = fit.predict(float(origin + horizon))
                predictions.append((method, prediction))
            except ValueError as error:
                unavailable.append((method, float(origin), str(error)))
        if len(predictions) != len(methods):
            continue
        paired += 1
        for method, prediction in predictions:
            rows.append((method, float(origin), float(origin + horizon), tuple(float(value) for value in prediction),
                         tuple(float(value) for value in label), float(np.linalg.norm(prediction - label))))
    return BaselineEvaluation(horizon, tuple(methods), origins.size, paired, tuple(rows), tuple(unavailable))


@dataclass(frozen=True)
class UncertaintySettings:
    nominal_coverage: float = .9
    min_scores: int = 9
    max_scores: int = 40
    min_spacing_s: float = .5

    def __post_init__(self):
        object.__setattr__(self, "nominal_coverage", _target_number(self.nominal_coverage,
            "Nominal observation coverage", minimum=.5, maximum=.99))
        object.__setattr__(self, "min_spacing_s", _target_number(self.min_spacing_s,
            "Calibration spacing", minimum=.1, maximum=5.))
        for name in ("min_scores", "max_scores"):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or not 2 <= value <= 100:
                raise ValueError("Calibration score limits must be integers between two and 100.")
            object.__setattr__(self, name, int(value))
        if self.max_scores < self.min_scores:
            raise ValueError("The maximum calibration count cannot be below the minimum count.")

    @property
    def required_score_count(self):
        count = int(np.ceil(self.nominal_coverage/(1.-self.nominal_coverage)-1e-12))
        return max(self.min_scores, count)


@dataclass(frozen=True)
class ForecastRegionCalibration:
    fit: BaselineFit
    horizon_s: float
    settings: UncertaintySettings
    radius_mm: float | None
    reason: str
    prefix_sha256: str
    _rows: tuple = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.fit, BaselineFit) or not isinstance(self.settings, UncertaintySettings):
            raise ValueError("A forecast region requires a causal baseline fit and calibration settings.")
        object.__setattr__(self, "horizon_s", _target_number(self.horizon_s,
            "Region horizon", minimum=.1, maximum=5.))
        if (not isinstance(self.prefix_sha256, str) or len(self.prefix_sha256) != 64
                or any(value not in "0123456789abcdef" for value in self.prefix_sha256)):
            raise ValueError("A forecast region must identify its observation prefix.")
        rows = tuple(tuple(row) for row in self._rows)
        if len(rows) > self.settings.max_scores or not isinstance(self.reason, str):
            raise ValueError("A forecast region requires bounded historical calibration records.")
        checked = []
        for row in rows:
            if (len(row) != 7 or row[5] not in ("scored", "fit_unavailable")
                    or not np.isfinite([row[0], row[1]]).all() or not 0 <= row[0] < row[1] <= self.origin_s
                    or abs(row[1]-row[0]-self.horizon_s) > 1e-8 or not isinstance(row[6], str)):
                raise ValueError("Calibration records must identify completed causal forecast outcomes.")
            observed = _target_point(row[3])
            prediction, score = None, None
            if row[5] == "scored":
                prediction = _target_point(row[2])
                score = _target_number(row[4], "Calibration error")
                if not np.isclose(score, np.linalg.norm(np.asarray(observed)-prediction), rtol=1e-10, atol=1e-10):
                    raise ValueError("Calibration errors must match their joint physical residuals.")
            elif row[2] is not None or row[4] is not None:
                raise ValueError("Unavailable historical fits cannot provide a scored residual.")
            checked.append((float(row[0]), float(row[1]), prediction, observed, score, row[5], row[6]))
        rows = tuple(checked)
        if rows and any(rows[index+1][1]-rows[index][1] < max(self.horizon_s, self.settings.min_spacing_s)-1e-8
                        for index in range(len(rows)-1)):
            raise ValueError("Calibration forecast windows must be chronologically ordered and non-overlapping.")
        object.__setattr__(self, "_rows", rows)
        scores = sorted(row[4] for row in rows if row[5] == "scored")
        rank = int(np.ceil(np.nextafter((len(scores)+1)*self.settings.nominal_coverage, -np.inf)))
        eligible = len(scores) >= self.required_score_count and 1 <= rank <= len(scores)
        if (self.radius_mm is not None) != eligible:
            raise ValueError("Forecast-region availability must match its completed score count and finite rank.")
        if self.radius_mm is not None:
            radius = _target_number(self.radius_mm, "Observation-error radius")
            if radius != scores[rank-1]:
                raise ValueError("A forecast-region radius must use its declared finite historical rank.")
            object.__setattr__(self, "radius_mm", radius)

    @property
    def available(self):
        return self.radius_mm is not None

    @property
    def origin_s(self):
        return self.fit.origin_s

    @property
    def query_s(self):
        return self.origin_s+self.horizon_s

    @property
    def forecast_settings(self):
        return self.fit.settings

    @property
    def prediction_lps_mm(self):
        return self.fit.predict(self.query_s)

    @property
    def rows(self):
        return tuple(dict(origin_s=row[0], query_s=row[1], predicted_lps_mm=row[2],
            observed_lps_mm=row[3], error_mm=row[4], status=row[5], reason=row[6]) for row in self._rows)

    @property
    def n_scores(self):
        return sum(row[5] == "scored" for row in self._rows)

    @property
    def required_score_count(self):
        return self.settings.required_score_count

    @property
    def candidate_count(self):
        return len(self._rows)

    @property
    def excluded_count(self):
        return self.candidate_count-self.n_scores

    @property
    def last_outcome_s(self):
        return max((row[1] for row in self._rows if row[5] == "scored"), default=None)


def calibrate_forecast_region(times_s, observed_lps_mm, method, *, origin_s, horizon_s,
                              settings=None, forecast_settings=None, cancelled=None):
    settings = UncertaintySettings() if settings is None else settings
    forecast = _forecast_settings(forecast_settings)
    if not isinstance(settings, UncertaintySettings) or cancelled is not None and not callable(cancelled):
        raise ValueError("Forecast regions require validated uncertainty settings and a callable cancellation hook.")
    def check_cancelled():
        if cancelled is not None and cancelled():
            raise InterruptedError("Forecast-region calibration cancelled.")
    check_cancelled()
    origin = _target_number(origin_s, "Forecast origin")
    horizon = _target_number(horizon_s, "Region horizon", minimum=.1, maximum=5.)
    times, raw = _forecast_arrays(times_s, observed_lps_mm)
    count = int(np.searchsorted(times, origin, side="right"))
    times, observed = times[:count], raw[:count].astype(float)
    if not count or not np.isfinite(observed).all():
        raise ValueError("Region calibration requires finite observations at or before its origin.")
    fit = fit_baseline(times, observed, method, origin_s=origin, settings=forecast)
    digest = sha256(np.asarray(times, dtype="<f8").tobytes()+np.asarray(observed, dtype="<f8").tobytes()).hexdigest()
    warmup = max(forecast.history_window_s, 2.*60./forecast.min_rate_bpm)
    earliest = times[0]+warmup
    eligible = np.flatnonzero(times-horizon >= earliest-1e-10)
    spacing = max(horizon, settings.min_spacing_s)
    indices, last = [], None
    for index in eligible[::-1]:
        query = float(times[index])
        if last is None or last-query >= spacing-1e-10:
            indices.append(int(index))
            last = query
            if len(indices) == settings.max_scores:
                break
    rows, scores = [], []
    for index in reversed(indices):
        check_cancelled()
        query, historical_origin = float(times[index]), float(times[index]-horizon)
        # snap only floating-point round-off to an existing origin timestamp; outcomes are never interpolated.
        nearest = int(np.searchsorted(times, historical_origin))
        for candidate in (nearest, nearest-1):
            if 0 <= candidate < len(times) and abs(times[candidate]-historical_origin) <= 1e-12:
                historical_origin = float(times[candidate])
                break
        prefix = int(np.searchsorted(times, historical_origin, side="right"))
        label = tuple(float(value) for value in observed[index])
        try:
            historical_fit = fit_baseline(times[:prefix], observed[:prefix], method,
                origin_s=historical_origin, settings=forecast)
            prediction = historical_fit.predict(query)
        except ValueError as error:
            rows.append((historical_origin, query, None, label, None, "fit_unavailable", str(error)))
        else:
            score = float(np.linalg.norm(observed[index]-prediction))
            scores.append(score)
            rows.append((historical_origin, query, tuple(float(value) for value in prediction), label, score,
                         "scored", "Historical forecast fitted before its actual noisy observation outcome."))
    check_cancelled()
    rank = int(np.ceil(np.nextafter((len(scores)+1)*settings.nominal_coverage, -np.inf)))
    available = len(scores) >= settings.required_score_count and 1 <= rank <= len(scores)
    radius = float(np.sort(scores)[rank-1]) if available else None
    reason = ("Empirical joint 3D noisy-observation error radius; dependent rolling histories do not provide a coverage guarantee."
              if available else f"Only {len(scores)} completed historical residuals; {settings.required_score_count} are required at nominal {settings.nominal_coverage:.0%} coverage. "
              "No observation-error radius is available; choose a shorter horizon or record more history.")
    return ForecastRegionCalibration(fit, horizon, settings, radius, reason, digest, tuple(rows))


def evaluate_forecast_region(region, *, observed_lps_mm=None, true_lps_mm=None):
    if not isinstance(region, ForecastRegionCalibration):
        raise ValueError("Forecast-region evaluation requires a frozen calibration result.")
    result = dict(query_s=region.query_s, radius_mm=region.radius_mm, nominal_coverage=region.settings.nominal_coverage,
        observed_error_mm=None, observed_covered=None, true_error_mm=None, true_covered=None)
    for name, point in (("observed", observed_lps_mm), ("true", true_lps_mm)):
        if point is not None:
            label = np.asarray(_target_point(point))
            if region.available:
                error = float(np.linalg.norm(label-region.prediction_lps_mm))
                result[name+"_error_mm"] = error
                result[name+"_covered"] = bool(error <= region.radius_mm+1e-8)
    return result


FORECAST_STUDY_HORIZONS = (.5, 1., 2., 3., 5.)


@dataclass(frozen=True)
class ForecastStudySettings:
    preset: str = "Quick"
    seed: int = 17
    nominal_coverage: float = .9
    observation_rate_hz: float = 10.
    forecast_settings: ForecastSettings = field(default_factory=ForecastSettings)

    def __post_init__(self):
        if not isinstance(self.preset, str) or self.preset not in ("Quick", "Extended"):
            raise ValueError("Choose the Quick or Extended forecast study.")
        if (isinstance(self.seed, (bool, np.bool_)) or not isinstance(self.seed, (int, np.integer))
                or not 0 <= self.seed <= 2**32-1):
            raise ValueError("The forecast-study seed must be an integer between 0 and 4294967295.")
        object.__setattr__(self, "seed", int(self.seed))
        coverage = UncertaintySettings(nominal_coverage=self.nominal_coverage).nominal_coverage
        object.__setattr__(self, "nominal_coverage", coverage)
        rate = _target_number(self.observation_rate_hz, "Study observation rate", minimum=2., maximum=60.)
        if rate % 2:
            raise ValueError("The forecast-study sampling rate must be an even integer, so all declared horizons have exact recorded samples.")
        object.__setattr__(self, "observation_rate_hz", rate)
        if not isinstance(self.forecast_settings, ForecastSettings):
            raise ValueError("The forecast study requires validated forecasting settings.")

    @property
    def subjects_per_split(self):
        return 32 if self.preset == "Quick" else 64


def forecast_study_subjects(settings=None):
    settings = ForecastStudySettings() if settings is None else settings
    if not isinstance(settings, ForecastStudySettings):
        raise ValueError("Subject generation requires validated forecast-study settings.")
    seed_base = int(np.random.SeedSequence([settings.seed, 1701]).generate_state(1)[0])
    subjects = []
    rate = settings.observation_rate_hz
    for split_index, split in enumerate(("calibration", "evaluation")):
        for index in range(settings.subjects_per_split):
            key = [settings.seed, 1702, split_index, index]
            rng = np.random.default_rng(np.random.SeedSequence(key))
            ordinal = split_index*65536+index
            origin_sample = int(rng.integers(int(30*rate), int(45*rate)+1))
            subjects.append(dict(subject_id=f"{split}-{index+1:03d}", split=split,
                parameter_seed_key=key, amplitude_mm=float(rng.uniform(4., 16.)),
                rate_bpm=float(rng.uniform(8., 24.)),
                pattern=BREATHING_PATTERNS[int(rng.integers(len(BREATHING_PATTERNS)))],
                noise_std_mm=float(rng.uniform(0., 1.5)), origin_s=origin_sample/rate,
                profile_seed=(seed_base+2*ordinal) % 2**32,
                observation_seed=(seed_base+2*ordinal+1) % 2**32))
    return tuple(subjects)


def _forecast_study_calibrations(rows, settings):
    output = []
    required = UncertaintySettings(nominal_coverage=settings.nominal_coverage).required_score_count
    for method, horizon, kind in product(BASELINE_METHODS, FORECAST_STUDY_HORIZONS, ("observed", "true")):
        group = [row for row in rows if row["split"] == "calibration" and row["method"] == method
                 and row["horizon_s"] == horizon and row["status"] == "available"]
        scores = sorted(row[kind+"_error_mm"] for row in group)
        rank = int(np.ceil(np.nextafter((len(scores)+1)*settings.nominal_coverage, -np.inf)))
        available = len(scores) >= required and 1 <= rank <= len(scores)
        output.append(dict(method=method, horizon_s=horizon, error_kind=kind,
            status="available" if available else "unavailable",
            reason=("Frozen pooled calibration-subject residual radius." if available else
                f"Only {len(scores)} valid calibration subjects; {required} are required at nominal {settings.nominal_coverage:.0%} coverage."),
            calibration_count=len(scores), required_count=required, rank=rank,
            radius_mm=float(scores[rank-1]) if available else None, nominal_coverage=settings.nominal_coverage))
    return tuple(output)


def _forecast_study_summaries(rows, calibrations):
    output = []
    lookup = {(row["method"], row["horizon_s"], row["error_kind"]): row for row in calibrations}
    for method, horizon, kind in product(BASELINE_METHODS, FORECAST_STUDY_HORIZONS, ("observed", "true")):
        group = [row for row in rows if row["split"] == "evaluation" and row["method"] == method and row["horizon_s"] == horizon]
        if not group:
            continue
        calibration = lookup[method, horizon, kind]
        errors = np.array([row[kind+"_error_mm"] for row in group if row["status"] == "available"], dtype=float)
        assessed = [row for row in group if row[kind+"_covered"] is not None]
        covered = sum(row[kind+"_covered"] for row in assessed)
        fit_unavailable = sum(row["status"] == "fit_unavailable" for row in group)
        output.append(dict(method=method, horizon_s=horizon, error_kind=kind,
            attempted_count=len(group), fit_available_count=len(group)-fit_unavailable,
            fit_unavailable_count=fit_unavailable,
            outcome_unavailable_count=sum(row["status"] == "outcome_unavailable" for row in group),
            error_assessed_count=int(errors.size), assessed_count=len(assessed),
            region_unavailable_count=sum(row["status"] == "available" and row[kind+"_covered"] is None for row in group),
            covered_count=int(covered), coverage=covered/len(assessed) if assessed else None,
            mean_error_mm=float(np.mean(errors)) if errors.size else None,
            rmse_mm=float(np.sqrt(np.mean(errors**2))) if errors.size else None,
            radius_mm=calibration["radius_mm"], calibration_count=calibration["calibration_count"],
            nominal_coverage=calibration["nominal_coverage"]))
    return tuple(output)


@dataclass(frozen=True)
class ForecastStudyResult:
    settings: ForecastStudySettings
    _manifest_json: str = field(repr=False)
    _rows_json: str = field(repr=False)
    _calibrations_json: str = field(repr=False)
    _summaries_json: str = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.settings, ForecastStudySettings):
            raise ValueError("A forecast-study result requires validated settings.")
        manifest, rows = self.manifest, self.rows
        if not isinstance(manifest, dict):
            raise ValueError("A forecast-study manifest must be a protocol dictionary.")
        _benchmark_json(manifest)
        _benchmark_json(rows)
        subjects = manifest.get("subjects", [])
        forecast = self.settings.forecast_settings
        expected_settings = dict(preset=self.settings.preset, master_seed=self.settings.seed,
            nominal_coverage=self.settings.nominal_coverage, observation_rate_hz=self.settings.observation_rate_hz,
            forecast_settings=dict(history_window_s=forecast.history_window_s, velocity_window_s=forecast.velocity_window_s,
                min_rate_bpm=forecast.min_rate_bpm, max_rate_bpm=forecast.max_rate_bpm))
        if any(manifest.get(key) != value for key, value in expected_settings.items()):
            raise ValueError("Study settings must agree with their exported protocol manifest.")
        if (not isinstance(manifest, dict) or not 2 <= len(subjects) <= 128
                or len(rows) != len(subjects)*len(BASELINE_METHODS)*len(FORECAST_STUDY_HORIZONS)
                or manifest.get("trial_count") != len(rows)
                or manifest.get("subject_count") != len(subjects)
                or any(manifest.get(split+"_subject_count") != sum(row["split"] == split for row in subjects)
                       for split in ("calibration", "evaluation"))
                or len({row["subject_id"] for row in subjects}) != len(subjects)
                or len({row["model_id"] for row in subjects}) != len(subjects)
                or {row["split"] for row in subjects} != {"calibration", "evaluation"}):
            raise ValueError("A forecast study must retain distinct calibration and evaluation subjects and all trials.")
        subjects_by_id = {row["subject_id"]: row for row in subjects}
        expected = set(product(BASELINE_METHODS, FORECAST_STUDY_HORIZONS))
        for subject_id, subject in subjects_by_id.items():
            group = [row for row in rows if row["subject_id"] == subject_id]
            if (len(group) != len(expected) or {(row["method"], row["horizon_s"]) for row in group} != expected
                    or any(row["split"] != subject["split"] or row["model_id"] != subject["model_id"]
                           or row["origin_s"] != subject["origin_s"] or row["pattern"] != subject["pattern"]
                           or row["observation_prefix_sha256"] != subject["observation_prefix_sha256"]
                           or row["status"] not in ("available", "fit_unavailable", "outcome_unavailable") for row in group)):
                raise ValueError("Each study subject requires a complete, consistently identified method/horizon grid.")
        for row in rows:
            if (row["pattern"] not in BREATHING_PATTERNS
                    or not np.isfinite([row["origin_s"], row["query_s"]]).all()
                    or not np.isclose(row["query_s"]-row["origin_s"], row["horizon_s"], rtol=0, atol=1e-10)):
                raise ValueError("Study trials must retain their declared physical forecast horizon.")
            if row["status"] == "available":
                prediction = np.asarray(_target_point(row["predicted_lps_mm"]))
                for kind in ("observed", "true"):
                    label = np.asarray(_target_point(row[kind+"_lps_mm"]))
                    residual = np.asarray(_target_point(row[kind+"_residual_lps_mm"]))
                    error = _target_number(row[kind+"_error_mm"], "Study residual error")
                    if (not np.allclose(label-prediction, residual, rtol=1e-10, atol=1e-10)
                            or not np.isclose(error, np.linalg.norm(residual), rtol=1e-10, atol=1e-10)):
                        raise ValueError("Study errors must match their signed joint LPS residual vectors.")
            else:
                if any(row[kind+suffix] is not None for kind in ("observed", "true")
                       for suffix in ("_lps_mm", "_residual_lps_mm", "_error_mm", "_covered")):
                    raise ValueError("Unavailable study outcomes cannot contain labels, errors or coverage scores.")
                if row["status"] == "fit_unavailable":
                    if row["predicted_lps_mm"] is not None or row["fit_n_samples"] is not None:
                        raise ValueError("An unavailable study fit cannot provide a prediction.")
                else:
                    _target_point(row["predicted_lps_mm"])
        calibrations = _forecast_study_calibrations(rows, self.settings)
        lookup = {(item["method"], item["horizon_s"], item["error_kind"]): item for item in calibrations}
        for row in rows:
            for kind in ("observed", "true"):
                radius = lookup[row["method"], row["horizon_s"], kind]["radius_mm"]
                covered = (row[kind+"_error_mm"] <= radius+1e-8
                    if row["split"] == "evaluation" and row["status"] == "available" and radius is not None else None)
                if row[kind+"_covered"] is not covered:
                    raise ValueError("Study coverage must use frozen calibration radii and evaluation outcomes only.")
        if (_benchmark_json(calibrations) != self._calibrations_json
                or _benchmark_json(_forecast_study_summaries(rows, calibrations)) != self._summaries_json):
            raise ValueError("Frozen study calibration and evaluation summaries must agree with their separate subject partitions.")

    @property
    def manifest(self):
        return json.loads(self._manifest_json)

    @property
    def rows(self):
        return tuple(json.loads(self._rows_json))

    @property
    def calibrations(self):
        return tuple(json.loads(self._calibrations_json))

    @property
    def summaries(self):
        return tuple(json.loads(self._summaries_json))

    @property
    def pattern_summaries(self):
        rows = self.rows
        return tuple(dict(summary, pattern=pattern)
            for pattern in BREATHING_PATTERNS
            for summary in _forecast_study_summaries([row for row in rows if row["pattern"] == pattern], self.calibrations))

    @property
    def result_id(self):
        return sha256((self._manifest_json+self._rows_json+self._calibrations_json).encode("utf-8")).hexdigest()


def run_forecast_study(target, deformation, *, settings=None, progress=None, cancelled=None):
    settings = ForecastStudySettings() if settings is None else settings
    if (not isinstance(target, ResearchTarget) or not isinstance(deformation, LungDeformation)
            or not isinstance(settings, ForecastStudySettings)):
        raise ValueError("A forecast study requires a simulated target, shared deformation and validated settings.")
    if any(hook is not None and not callable(hook) for hook in (progress, cancelled)):
        raise ValueError("Study progress and cancellation hooks must be callable.")
    weight = (deformation.apex_z-target.center_lps_mm[2])/deformation.height
    if not 0 < weight <= 1:
        raise ValueError("The study target must lie between the shared field's base and apex, below its fixed apex.")
    def check_cancelled():
        if cancelled is not None and cancelled():
            raise InterruptedError("Forecast study cancelled; no partial result was published.")
    check_cancelled()
    subjects = forecast_study_subjects(settings)
    if (not 2 <= len(subjects) <= 128 or {row["split"] for row in subjects} != {"calibration", "evaluation"}
            or len({row["subject_id"] for row in subjects}) != len(subjects)
            or any(sum(row["split"] == split for row in subjects) > 64 for split in ("calibration", "evaluation"))
            or len({row["profile_seed"] for row in subjects}) != len(subjects)
            or len({row["observation_seed"] for row in subjects}) != len(subjects)):
        raise ValueError("The study requires bounded, disjoint calibration and evaluation subject identities and random streams.")
    rows, catalog, identities = [], [], set()
    calibrations, completed = (), 0
    for split in ("calibration", "evaluation"):
        for subject in (row for row in subjects if row["split"] == split):
            check_cancelled()
            model = RespiratoryModel(BreathingSettings(subject["amplitude_mm"], subject["rate_bpm"],
                                                       subject["pattern"], subject["profile_seed"]))
            identity = respiratory_model_id(model)
            if identity in identities:
                raise ValueError("A respiratory profile was duplicated across study subjects.")
            identities.add(identity)
            origin = subject["origin_s"]
            observation_settings = ObservationSettings(settings.observation_rate_hz, subject["noise_std_mm"], subject["observation_seed"])
            fits, unavailable = {}, {}
            prefix_sha = None
            try:
                prefix = generate_target_observations(target, model, deformation, observation_settings, through_s=origin)
                times, observed = prefix.observations_through(origin)
                prefix_sha = sha256(np.asarray(times, dtype="<f8").tobytes()+np.asarray(observed, dtype="<f8").tobytes()).hexdigest()
            except ValueError as error:
                unavailable = {method: "Past observation generation unavailable: "+str(error) for method in BASELINE_METHODS}
            else:
                for method in BASELINE_METHODS:
                    check_cancelled()
                    try:
                        fits[method] = fit_baseline(times, observed, method, origin_s=origin, settings=settings.forecast_settings)
                    except ValueError as error:
                        unavailable[method] = str(error)
            check_cancelled()
            catalog.append(dict(subject, model_id=identity, observation_prefix_sha256=prefix_sha))
            queries = (round(origin*settings.observation_rate_hz)+np.array(FORECAST_STUDY_HORIZONS)*settings.observation_rate_hz)/settings.observation_rate_hz
            future, outcome_reason = None, ""
            if fits:
                try:
                    # future labels are obtained only after all of this subject's past-only fits exist.
                    future = generate_target_observations(target, model, deformation, observation_settings, through_s=float(queries[-1]))
                except ValueError as error:
                    outcome_reason = "Future evaluation outcome unavailable: "+str(error)
            for method in BASELINE_METHODS:
                check_cancelled()
                fit = fits.get(method)
                predictions = fit.predict(queries) if fit is not None else None
                for index, horizon in enumerate(FORECAST_STUDY_HORIZONS):
                    row = dict(split=split, subject_id=subject["subject_id"], pattern=subject["pattern"], model_id=identity,
                        observation_prefix_sha256=prefix_sha, method=method, horizon_s=horizon, origin_s=origin,
                        query_s=float(queries[index]), status="available", reason="",
                        fit_n_samples=fit.n_samples if fit is not None else None,
                        fitted_frequency_hz=fit.frequency_hz if fit is not None else None,
                        predicted_lps_mm=predictions[index].tolist() if predictions is not None else None,
                        observed_lps_mm=None, true_lps_mm=None, observed_residual_lps_mm=None, true_residual_lps_mm=None,
                        observed_error_mm=None, true_error_mm=None, observed_covered=None, true_covered=None)
                    if fit is None:
                        row.update(status="fit_unavailable", reason=unavailable[method])
                    elif future is None:
                        row.update(status="outcome_unavailable", reason=outcome_reason)
                    else:
                        query = float(queries[index])
                        sample = int(round(query*settings.observation_rate_hz))
                        if sample >= len(future.times_s) or not np.isclose(future.times_s[sample], query, rtol=0, atol=1e-10):
                            raise ValueError("The exact declared study horizon has no recorded outcome sample.")
                        for kind, positions in (("observed", future.observed_lps_mm), ("true", future.evaluation_ground_truth_lps_mm)):
                            label = positions[sample]
                            residual = label-predictions[index]
                            row[kind+"_lps_mm"] = label.tolist()
                            row[kind+"_residual_lps_mm"] = residual.tolist()
                            row[kind+"_error_mm"] = float(np.linalg.norm(residual))
                            if split == "evaluation":
                                calibration = next(value for value in calibrations if value["method"] == method
                                    and value["horizon_s"] == horizon and value["error_kind"] == kind)
                                radius = calibration["radius_mm"]
                                row[kind+"_covered"] = bool(row[kind+"_error_mm"] <= radius+1e-8) if radius is not None else None
                    rows.append(row)
            completed += 1
            if progress is not None:
                progress(completed, len(subjects))
            check_cancelled()
        if split == "calibration":
            # pooled radii are frozen before any evaluation subject or future evaluation label is generated.
            calibrations = _forecast_study_calibrations(rows, settings)
            check_cancelled()
    forecast = settings.forecast_settings
    manifest = dict(format_version=1, algorithm="held_out_synthetic_forecast_study_v1", preset=settings.preset,
        master_seed=settings.seed, subjects=catalog, subject_count=len(catalog),
        calibration_subject_count=sum(row["split"] == "calibration" for row in catalog),
        evaluation_subject_count=sum(row["split"] == "evaluation" for row in catalog), trial_count=len(rows),
        horizons_s=list(FORECAST_STUDY_HORIZONS), methods=list(BASELINE_METHODS), nominal_coverage=settings.nominal_coverage,
        observation_rate_hz=settings.observation_rate_hz, minimum_calibration_scores=9,
        forecast_settings=dict(history_window_s=forecast.history_window_s, velocity_window_s=forecast.velocity_window_s,
            min_rate_bpm=forecast.min_rate_bpm, max_rate_bpm=forecast.max_rate_bpm),
        study_id=target.study_id, target=dict(name=target.name, center_lps_mm=target.center_lps_mm, radius_mm=target.radius_mm),
        deformation=dict(base_z=deformation.base_z, apex_z=deformation.apex_z, target_weight=weight),
        generation=dict(amplitude_mm=[4., 16.], rate_bpm=[8., 24.], noise_std_mm=[0., 1.5], origin_s=[30., 45.],
            pattern_distribution="uniform over the four existing breathing patterns", duration_s=60.,
            origin_distribution="uniform over actual observation-grid samples from 30 through 45 seconds",
            axes_lps=RespiratoryModel.axes.tolist(), subject_parameter_seed="SeedSequence(master,1702,split,index)",
            noise_and_profile_seed="distinct uint32 streams from SeedSequence(master,1701), with separate split/index offsets"),
        software=dict(python=platform.python_version(), numpy=np.__version__, scipy=_scipy_version,
            core_sha256=sha256(Path(__file__).read_bytes()).hexdigest()),
        definitions=dict(partitions="Separate synthetic subjects; no subject, respiratory profile or noise stream is reused between calibration and evaluation.",
            fitting="Every fit receives only its subject's noisy observations through its one declared origin. All five horizons share that fit.",
            calibration="One joint 3D LPS residual per calibration subject/method/horizon. Noisy-future-observation and simulated true-centre residuals have separate frozen pooled radii.",
            radius="Sorted calibration error at ceil((n+1)*nominal coverage), requiring at least nine scores and a finite rank; 95% needs at least nineteen. No interpolation or fallback.",
            evaluation="Calibration radii are frozen before evaluation subjects are generated. Coverage uses only labelled evaluation outcomes with available radii; attempted, fit, outcome and radius availability are reported separately.",
            error="Euclidean 3D millimetre error; mean and RMSE use available labelled outcomes even when no radius can be calibrated.",
            residual_vector="Future label minus prediction in LPS millimetres. Calibration vectors are retained separately for later empirical modelling.",
            population="Independent seeded virtual respiratory trajectories on the selected target/shared affine field, not independent acquired patient scans.",
            limitations="Declared simulator mixture and one reference anatomy; fixed respiratory axes and no mechanics or registration. Regular breathing matches the sinusoidal family. Pooled radii do not establish pattern-conditional or clinical coverage and do not alter needle planning."))
    manifest["protocol_id"] = sha256(_benchmark_json(manifest).encode("utf-8")).hexdigest()
    check_cancelled()
    return ForecastStudyResult(settings, _benchmark_json(manifest), _benchmark_json(rows),
        _benchmark_json(calibrations), _benchmark_json(_forecast_study_summaries(rows, calibrations)))


@dataclass(frozen=True)
class NeedleSettings:
    radius_mm: float = .7
    speed_mm_s: float = 30.
    delay_s: float = .5

    def __post_init__(self):
        for name, lower, upper in (("radius_mm", .2, 2.), ("speed_mm_s", 1., 100.), ("delay_s", 0., 5.)):
            object.__setattr__(self, name, _target_number(getattr(self, name),
                "Needle " + name.replace("_", " "), minimum=lower, maximum=upper))


def _needle_point(value, label):
    try:
        return _target_point(value)
    except ValueError as error:
        raise ValueError(f"{label} requires three finite LPS millimetre coordinates.") from error


def _needle_values(value, label, maximum=np.inf):
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf" or raw.ndim > 1 or raw.size > 100001:
        raise ValueError(f"{label} must be a finite scalar or bounded numeric vector.")
    values = raw.astype(float)
    if not np.isfinite(values).all() or np.any(values < 0) or np.any(values > maximum):
        raise ValueError(f"{label} is outside its supported range.")
    return values


@dataclass(frozen=True)
class NeedlePlan:
    entry_lps_mm: tuple
    endpoint_lps_mm: tuple
    planning_time_s: float
    settings: NeedleSettings
    target: ResearchTarget
    model_id: str
    deformation: LungDeformation

    def __post_init__(self):
        for name in ("entry_lps_mm", "endpoint_lps_mm"):
            object.__setattr__(self, name, _needle_point(getattr(self, name), "Needle " + name.split("_")[0]))
        object.__setattr__(self, "planning_time_s", _target_number(self.planning_time_s, "Planning time"))
        if (not isinstance(self.settings, NeedleSettings) or not isinstance(self.target, ResearchTarget)
                or not isinstance(self.deformation, LungDeformation)):
            raise ValueError("A needle path requires validated settings, a target and its deformation.")
        if (not isinstance(self.model_id, str) or len(self.model_id) != 64
                or any(value not in "0123456789abcdef" for value in self.model_id)):
            raise ValueError("A needle path must identify its captured respiratory scenario.")
        if not 1e-6 < self.length_mm <= 1000.:
            raise ValueError("A finite needle path must have distinct endpoints and be at most 1000 mm long.")

    @property
    def length_mm(self):
        return float(np.linalg.norm(np.asarray(self.endpoint_lps_mm) - self.entry_lps_mm))

    @property
    def direction(self):
        return (np.asarray(self.endpoint_lps_mm) - self.entry_lps_mm) / self.length_mm

    @property
    def start_s(self):
        return self.planning_time_s + self.settings.delay_s

    @property
    def arrival_s(self):
        return self.start_s + self.length_mm / self.settings.speed_mm_s

    def depth_at(self, time):
        times = _needle_values(time, "Needle time")
        return np.clip((times - self.start_s) * self.settings.speed_mm_s, 0., self.length_mm)

    def tip_at_depth(self, depth):
        depths = _needle_values(depth, "Insertion depth", self.length_mm)
        return np.asarray(self.entry_lps_mm) + depths[..., None] * self.direction

    def tip_at_time(self, time):
        return self.tip_at_depth(self.depth_at(time))


def validate_needle_entry(volume, lung_mask, reference_entry):
    if (not isinstance(volume, Volume) or not isinstance(lung_mask, np.ndarray)
            or lung_mask.dtype != bool or lung_mask.shape != volume.shape or not np.any(lung_mask)):
        raise ValueError("Needle entry selection requires a nonempty boolean lung mask aligned with the CT.")
    entry = _needle_point(reference_entry, "Needle entry")
    voxel = volume.world_to_index(entry)
    limits = np.asarray(volume.shape[::-1]) - 1
    if np.any(voxel < -1e-9) or np.any(voxel > limits + 1e-9):
        raise ValueError("The manual entry must lie inside the oriented reference CT grid.")
    index = np.clip(np.floor(voxel + .5).astype(int), 0, limits)
    if lung_mask[tuple(index[::-1])]:
        raise ValueError("Select a manual chest-wall entry outside the available lung segmentation.")
    return entry


def create_needle_plan(volume, lung_mask, target, deformation, model, entry_lps_mm,
                       settings=None, *, planning_time_s):
    settings = NeedleSettings() if settings is None else settings
    if (not isinstance(target, ResearchTarget) or not isinstance(deformation, LungDeformation)
            or not isinstance(model, RespiratoryModel) or not isinstance(settings, NeedleSettings)):
        raise ValueError("Needle planning requires a target and validated motion and insertion settings.")
    time = _target_number(planning_time_s, "Planning time", maximum=model.duration)
    identity = respiratory_model_id(model)
    checked = create_research_target(volume, lung_mask, target.center_lps_mm, target.radius_mm, target.name)
    if target.study_id != checked.study_id:
        raise ValueError("The target belongs to a different reference CT snapshot.")
    entry = _needle_point(entry_lps_mm, "Needle entry")
    displacement = model.position(time)
    validate_needle_entry(volume, lung_mask, deformation.inverse(entry, displacement))
    endpoint = deformation.forward(target.center_lps_mm, displacement)
    plan = NeedlePlan(entry, endpoint, time, settings, target, identity, deformation)
    if plan.arrival_s > model.duration:
        raise ValueError("The insertion would finish beyond the available motion timeline. Plan earlier or increase speed.")
    if identity != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed while building the needle path.")
    return plan


def _check_needle_scenario(plan, model):
    if not isinstance(plan, NeedlePlan) or not isinstance(model, RespiratoryModel):
        raise ValueError("Needle evaluation requires a fixed path and its respiratory scenario.")
    if plan.model_id != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed. Rebuild the needle path before evaluating it.")
    if plan.arrival_s > model.duration:
        raise ValueError("The insertion extends beyond the available motion timeline.")


def _needle_states(plan, model, times):
    displacement = model.position(times)
    height, apex = plan.deformation.height, plan.deformation.apex_z
    denominator = height - displacement[..., 2]
    if np.any(denominator < .5 * height):
        raise ValueError("The selected motion excessively compresses the simulated target anatomy.")
    depth = plan.depth_at(times)
    tip = plan.tip_at_depth(depth)
    entry = np.asarray(plan.entry_lps_mm)
    # the rank-one affine field has this exact batched inverse in physical LPS coordinates.
    pulled_entry = entry - ((apex - entry[2]) / denominator)[..., None] * displacement
    pulled_tip = tip - ((apex - tip[..., 2]) / denominator)[..., None] * displacement
    centre = np.asarray(plan.target.center_lps_mm)
    target = centre + ((apex - centre[2]) / height) * displacement
    segment = pulled_tip - pulled_entry
    offset = centre - pulled_entry
    squared_length = np.sum(segment * segment, axis=-1)
    fraction = np.divide(np.sum(offset * segment, axis=-1), squared_length,
                         out=np.zeros_like(squared_length), where=squared_length > 1e-20)
    closest = pulled_entry + np.clip(fraction, 0., 1.)[..., None] * segment
    return dict(depth_mm=depth, tip_lps_mm=tip, target_lps_mm=target,
        tip_error_mm=np.linalg.norm(tip - target, axis=-1),
        tip_normalized_distance=np.linalg.norm(pulled_tip - centre, axis=-1) / plan.target.radius_mm,
        shaft_normalized_distance=np.linalg.norm(closest - centre, axis=-1) / plan.target.radius_mm)


def evaluate_needle_state(plan, model, time):
    _check_needle_scenario(plan, model)
    time = _target_number(time, "Needle preview time", maximum=model.duration)
    values = _needle_states(plan, model, np.asarray(time))
    if plan.model_id != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed during needle evaluation.")
    return {name: value.copy() if value.ndim else float(value) for name, value in values.items()}


@dataclass(frozen=True)
class NeedleEvaluation:
    plan: NeedlePlan
    step_s: float
    min_tip_error_mm: float
    min_tip_error_time_s: float
    arrival_tip_error_mm: float
    first_tip_hit_s: float | None
    first_shaft_hit_s: float | None
    min_tip_normalized_distance: float
    min_shaft_normalized_distance: float
    _times_s: np.ndarray = field(repr=False)
    _depth_mm: np.ndarray = field(repr=False)
    _tip_lps_mm: np.ndarray = field(repr=False)
    _target_lps_mm: np.ndarray = field(repr=False)
    _tip_error_mm: np.ndarray = field(repr=False)
    _tip_normalized_distance: np.ndarray = field(repr=False)
    _shaft_normalized_distance: np.ndarray = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.plan, NeedlePlan):
            raise ValueError("An insertion result must identify its fixed needle path.")
        object.__setattr__(self, "step_s", _target_number(self.step_s, "Evaluation step", minimum=.001, maximum=.02))
        times = np.asarray(self._times_s, dtype=float)
        if (times.ndim != 1 or not 2 <= times.size <= 100001 or not np.isfinite(times).all()
                or np.any(np.diff(times) <= 0) or times[0] != self.plan.planning_time_s
                or times[-1] != self.plan.arrival_s or self.plan.start_s not in times):
            raise ValueError("An insertion trace requires ordered times including planning, insertion start and arrival.")
        for name in ("times_s", "depth_mm", "tip_lps_mm", "target_lps_mm", "tip_error_mm",
                     "tip_normalized_distance", "shaft_normalized_distance"):
            values = np.asarray(getattr(self, "_" + name), dtype=float)
            shape = (times.size, 3) if name in ("tip_lps_mm", "target_lps_mm") else times.shape
            if values.shape != shape or not np.isfinite(values).all():
                raise ValueError("Insertion trace values must be finite and match their timestamps.")
            object.__setattr__(self, "_" + name, np.frombuffer(values.tobytes(), dtype=float).reshape(shape))
        for name in ("min_tip_error_mm", "arrival_tip_error_mm", "min_tip_normalized_distance", "min_shaft_normalized_distance"):
            object.__setattr__(self, name, _target_number(getattr(self, name), name.replace("_", " ")))
        for name in ("min_tip_error_time_s", "first_tip_hit_s", "first_shaft_hit_s"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _target_number(value, name.replace("_", " "),
                    minimum=self.plan.start_s, maximum=self.plan.arrival_s))

    @property
    def interval_start_s(self):
        return self.plan.start_s

    @property
    def interval_end_s(self):
        return self.plan.arrival_s

    @property
    def times_s(self):
        return self._times_s.copy()

    @property
    def depth_mm(self):
        return self._depth_mm.copy()

    @property
    def tip_lps_mm(self):
        return self._tip_lps_mm.copy()

    @property
    def target_lps_mm(self):
        return self._target_lps_mm.copy()

    @property
    def tip_error_mm(self):
        return self._tip_error_mm.copy()

    @property
    def tip_normalized_distance(self):
        return self._tip_normalized_distance.copy()

    @property
    def shaft_normalized_distance(self):
        return self._shaft_normalized_distance.copy()


def evaluate_needle(plan, model, *, step_s=.005):
    _check_needle_scenario(plan, model)
    step = _target_number(step_s, "Evaluation step", minimum=.001, maximum=.02)
    count = int(np.ceil((plan.arrival_s - plan.planning_time_s) / step)) + 1
    if count > 99000:
        raise ValueError("The insertion interval exceeds the bounded numerical evaluation budget.")
    times = np.unique(np.r_[np.linspace(plan.planning_time_s, plan.arrival_s, count), plan.start_s])
    states = _needle_states(plan, model, times)
    execution = times >= plan.start_s
    execution_times = times[execution]
    refined = []
    cache = {}
    def scalar(time, name):
        key = float(time)
        if key not in cache:
            cache[key] = _needle_states(plan, model, np.asarray(key))
        return float(cache[key][name])
    for name in ("tip_error_mm", "tip_normalized_distance", "shaft_normalized_distance"):
        values = states[name][execution]
        local = np.flatnonzero((values[1:-1] <= values[:-2]) & (values[1:-1] <= values[2:])
            & (np.maximum(values[:-2], values[2:]) - values[1:-1] > 1e-12)) + 1
        brackets = [(execution_times[max(0, i-1)], execution_times[min(len(values)-1, i+1)]) for i in local]
        brackets.extend(((execution_times[0], execution_times[1]), (execution_times[-2], execution_times[-1])))
        if len(brackets) > 256:
            raise ValueError("The motion has too many local extrema for the bounded insertion evaluator.")
        for lower, upper in brackets:
            fit = minimize_scalar(lambda time: scalar(time, name), bounds=(lower, upper), method="bounded",
                                  options={"xatol": 1e-10, "maxiter": 80})
            if fit.success:
                refined.append(float(fit.x))
    # a dense grid plus local refinement is a numerical interval check, not a proof of continuous collision freedom.
    times = np.unique(np.r_[times, refined])
    states = _needle_states(plan, model, times)
    execution = times >= plan.start_s
    first_hits = []
    for name in ("tip_normalized_distance", "shaft_normalized_distance"):
        candidates = np.flatnonzero(execution & (states[name] <= 1. + 1e-9))
        contact = None
        if candidates.size:
            index = int(candidates[0])
            contact = float(times[index])
            if times[index] > plan.start_s and states[name][index] < 1.:
                previous = index - 1
                if times[previous] >= plan.start_s and states[name][previous] > 1.:
                    contact = float(brentq(lambda time: scalar(time, name) - 1.,
                        times[previous], times[index], xtol=1e-10, rtol=1e-12))
        first_hits.append(contact)
    times = np.unique(np.r_[times, [time for time in first_hits if time is not None]])
    states = _needle_states(plan, model, times)
    execution_indices = np.flatnonzero(times >= plan.start_s)
    minimum = int(execution_indices[np.argmin(states["tip_error_mm"][execution_indices])])
    if plan.model_id != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed during insertion evaluation.")
    return NeedleEvaluation(plan, step, float(states["tip_error_mm"][minimum]), float(times[minimum]),
        float(states["tip_error_mm"][-1]), *first_hits,
        float(states["tip_normalized_distance"][execution_indices].min()),
        float(states["shaft_normalized_distance"][execution_indices].min()),
        times, states["depth_mm"], states["tip_lps_mm"], states["target_lps_mm"], states["tip_error_mm"],
        states["tip_normalized_distance"], states["shaft_normalized_distance"])


def clip_segment_to_slice(entry, endpoint, plane, half_thickness_mm):
    entry, endpoint = np.asarray(_needle_point(entry, "Segment entry")), np.asarray(_needle_point(endpoint, "Segment endpoint"))
    half = _target_number(half_thickness_mm, "Slice half thickness")
    if (not isinstance(plane, SlicePlane) or np.asarray(plane.normal).shape != (3,)
            or np.asarray(plane.origin).shape != (3,) or not np.isfinite(plane.normal).all()
            or not np.isfinite(plane.origin).all() or not np.isclose(np.linalg.norm(plane.normal), 1., atol=1e-8)):
        raise ValueError("Needle overlays require a physical slice plane with a finite unit normal.")
    start = float(plane.distance_to_plane(entry))
    difference = float((endpoint - entry) @ plane.normal)
    if abs(difference) < 1e-12:
        return np.stack((entry, endpoint)) if abs(start) <= half + 1e-9 else np.empty((0, 3))
    bounds = sorted(((-half - start) / difference, (half - start) / difference))
    lower, upper = max(0., bounds[0]), min(1., bounds[1])
    if lower > upper + 1e-12:
        return np.empty((0, 3))
    lower = min(lower, upper)
    return entry + np.asarray([lower, upper])[:, None] * (endpoint - entry)


@dataclass(frozen=True)
class ExclusionRegion:
    name: str
    center_lps_mm: tuple
    radius_mm: float
    study_id: str
    kind: str = "simulated_exclusion"

    def __post_init__(self):
        checked = ResearchTarget(self.name, self.center_lps_mm, self.radius_mm, self.study_id)
        object.__setattr__(self, "name", checked.name)
        object.__setattr__(self, "center_lps_mm", checked.center_lps_mm)
        object.__setattr__(self, "radius_mm", _target_number(checked.radius_mm, "Exclusion radius", minimum=1., maximum=25.))
        if self.kind != "simulated_exclusion":
            raise ValueError("Exclusion regions are explicitly designated simulation geometry.")


def create_exclusion_region(volume, center, radius, name="Exclusion 1"):
    if not isinstance(volume, Volume):
        raise ValueError("An exclusion region requires a reference CT volume.")
    center = _needle_point(center, "Exclusion centre")
    radius = _target_number(radius, "Exclusion radius", minimum=1., maximum=25.)
    voxel = volume.world_to_index(center)
    margin = radius / np.asarray(volume.spacing)
    limits = np.asarray(volume.shape[::-1]) - 1
    if np.any(voxel-margin < -1e-9) or np.any(voxel+margin > limits+1e-9):
        raise ValueError("The complete exclusion sphere must lie inside the oriented reference CT.")
    return ExclusionRegion(name, center, radius, target_study_id(volume))


@dataclass(frozen=True)
class RouteSettings:
    patch_radius_mm: float = 8.
    clearance_mm: float = 2.

    def __post_init__(self):
        for name, maximum in (("patch_radius_mm", 20.), ("clearance_mm", 10.)):
            object.__setattr__(self, name, _target_number(getattr(self, name), name.replace("_", " "), maximum=maximum))


def _exclusion_regions(exclusions, study_id=None):
    try:
        values = tuple(exclusions)
    except TypeError as error:
        raise ValueError("Supply a bounded sequence of simulated exclusion regions.") from error
    if (len(values) > 8 or any(not isinstance(value, ExclusionRegion) for value in values)
            or len({value.name.casefold() for value in values}) != len(values)):
        raise ValueError("Use at most eight distinctly named simulated exclusion regions.")
    if study_id is not None and any(value.study_id != study_id for value in values):
        raise ValueError("Exclusion regions must belong to this reference CT snapshot.")
    return values


def _route_matrix(value):
    try:
        matrix = np.asarray(value, dtype=float)
        if (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
                or not np.allclose(matrix[3], [0., 0., 0., 1.], rtol=0, atol=1e-12)):
            raise ValueError
        singular = np.linalg.svd(matrix[:3, :3], compute_uv=False)
        if singular[-1] < 1e-8 or singular[0] > 1e6 or singular[0]/singular[-1] > 1e8:
            raise ValueError
        return matrix.copy(), float(singular[-1])
    except (TypeError, ValueError, np.linalg.LinAlgError) as error:
        raise ValueError("Route constraints require a finite invertible physical affine transform.") from error


def exclusion_clearance_lower_bounds(entry, tip, matrix, exclusions, needle_radius_mm):
    entry, tip = np.asarray(_needle_point(entry, "Needle entry")), np.asarray(_needle_point(tip, "Needle tip"))
    matrix, sigma = _route_matrix(matrix)
    regions = _exclusion_regions(exclusions)
    radius = _target_number(needle_radius_mm, "Physical needle radius", minimum=.2, maximum=2.)
    if not regions:
        return np.empty(0)
    inverse = np.linalg.inv(matrix[:3, :3])
    entry = inverse @ (entry-matrix[:3, 3])
    tip = inverse @ (tip-matrix[:3, 3])
    segment = tip-entry
    centres = np.array([region.center_lps_mm for region in regions])
    length_squared = float(segment @ segment)
    fraction = ((centres-entry) @ segment/length_squared if length_squared > 1e-20 else np.zeros(len(regions)))
    closest = entry+np.clip(fraction, 0., 1.)[:, None]*segment
    # sigma_min converts a reference-space distance into a conservative world-space lower bound.
    return sigma*(np.linalg.norm(centres-closest, axis=1)-[region.radius_mm for region in regions])-radius


@dataclass(frozen=True)
class RouteSelection:
    target: ResearchTarget
    entry_reference: tuple
    endpoint_lps_mm: tuple
    needle_settings: NeedleSettings
    route_settings: RouteSettings
    exclusions: tuple
    planning_time_s: float
    available_until_s: float
    chosen_index: int | None
    _matrix: np.ndarray = field(repr=False)
    _rows: tuple = field(repr=False)

    def __post_init__(self):
        matrix, _ = _route_matrix(self._matrix)
        object.__setattr__(self, "_matrix", np.frombuffer(matrix.tobytes(), dtype=float).reshape(4, 4))
        object.__setattr__(self, "exclusions", _exclusion_regions(self.exclusions, self.target.study_id))

    @property
    def matrix(self):
        return self._matrix.copy()

    @property
    def rows(self):
        return tuple(dict(index=row[0], entry_reference=row[1], entry_lps_mm=row[2], length_mm=row[3],
            clearance_lower_bound_mm=row[4], status=row[5], reason=row[6], chosen=row[0] == self.chosen_index) for row in self._rows)

    @property
    def chosen_entry_reference(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][1]

    @property
    def chosen_entry_lps_mm(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][2]


def _route_geometry(volume, lung_mask, target, entry_reference, matrix, exclusions, route_settings):
    checked = create_research_target(volume, lung_mask, target.center_lps_mm, target.radius_mm, target.name)
    if checked.study_id != target.study_id:
        raise ValueError("The target belongs to a different reference CT snapshot.")
    entry = np.asarray(validate_needle_entry(volume, lung_mask, entry_reference))
    matrix, _ = _route_matrix(matrix)
    regions = _exclusion_regions(exclusions, checked.study_id)
    limits = np.asarray(volume.shape[::-1])-1
    for region in regions:
        voxel = volume.world_to_index(region.center_lps_mm)
        margin = region.radius_mm/np.asarray(volume.spacing)
        if np.any(voxel-margin < -1e-9) or np.any(voxel+margin > limits+1e-9):
            raise ValueError("The complete exclusion sphere must lie inside the oriented reference CT.")
    centre = np.asarray(target.center_lps_mm)
    normal = centre-entry
    normal /= np.linalg.norm(normal)
    u = np.cross(np.eye(3)[np.argmin(np.abs(normal))], normal)
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    offsets = [(x, y) for x in range(-2, 3) for y in range(-2, 3) if x*x+y*y <= 4]
    offsets.sort(key=lambda pair: (pair[0]*pair[0]+pair[1]*pair[1], *pair))
    if route_settings.patch_radius_mm == 0:
        offsets = [(0, 0)]
    candidates = tuple(entry+(x*u+y*v)*(route_settings.patch_radius_mm/2.) for x, y in offsets)
    endpoint = matrix[:3, :3] @ centre+matrix[:3, 3]
    return entry, matrix, regions, candidates, endpoint


def select_geometric_route(volume, lung_mask, target, entry_reference, matrix, needle_settings=None,
                           exclusions=(), route_settings=None, *, planning_time_s, available_until_s=60.):
    needle_settings = NeedleSettings() if needle_settings is None else needle_settings
    route_settings = RouteSettings() if route_settings is None else route_settings
    if not isinstance(needle_settings, NeedleSettings) or not isinstance(route_settings, RouteSettings) or not isinstance(target, ResearchTarget):
        raise ValueError("Entry selection requires a target and validated needle and route settings.")
    available = _target_number(available_until_s, "Available motion endpoint", positive=True)
    time = _target_number(planning_time_s, "Planning time", maximum=available)
    entry, matrix, regions, candidates, endpoint = _route_geometry(
        volume, lung_mask, target, entry_reference, matrix, exclusions, route_settings)
    rows = []
    for index, candidate in enumerate(candidates):
        world = matrix[:3, :3] @ candidate+matrix[:3, 3]
        length = float(np.linalg.norm(endpoint-world))
        status, reason, bound = "eligible", "Meets declared planning-time geometric constraints.", None
        try:
            validate_needle_entry(volume, lung_mask, candidate)
            if not 1e-6 < length <= 1000.:
                raise ValueError("The finite path length is outside its supported range.")
            if time+needle_settings.delay_s+length/needle_settings.speed_mm_s > available:
                raise ValueError("Arrival would exceed the available motion timeline.")
            values = exclusion_clearance_lower_bounds(world, endpoint, matrix, regions, needle_settings.radius_mm)
            bound = float(values.min()) if values.size else None
            if bound is not None and bound <= route_settings.clearance_mm+1e-9:
                raise ValueError("Conservative clearance bound does not exceed the required margin.")
        except ValueError as error:
            status, reason = "rejected", str(error)
        rows.append((index, tuple(candidate), tuple(world), length, bound, status, reason))
    eligible = [row for row in rows if row[5] == "eligible"]
    chosen = min(eligible, key=lambda row: (row[3], -row[4] if row[4] is not None else 0., row[0]))[0] if eligible else None
    return RouteSelection(target, tuple(entry), tuple(endpoint), needle_settings, route_settings, regions,
        time, available, chosen, matrix, tuple(rows))


def _forecast_intercept_horizons(fit, entry, speed, delay, maximum):
    if maximum <= delay:
        return ()
    entry = np.asarray(entry)
    if fit.method != "Constant velocity" and fit.frequency_hz is None:
        horizon = delay+float(np.linalg.norm(fit.position_lps_mm-entry))/speed
        return (horizon,) if delay < horizon <= maximum else ()
    roots = []
    if fit.method == "Constant velocity":
        velocity = fit.velocity_lps_mm_s
        offset = fit.predict(fit.origin_s+delay)-entry
        a = float(velocity @ velocity-speed*speed)
        b, c = 2.*float(offset @ velocity), float(offset @ offset)
        if not np.isfinite([a, b, c]).all():
            return ()
        scale = max(float(velocity @ velocity), speed*speed, 1.)
        if abs(a) <= 32.*np.finfo(float).eps*scale:
            if abs(b) > 32.*np.finfo(float).eps*max(abs(b), c, 1.):
                roots.append(delay-c/b)
        else:
            discriminant = b*b-4.*a*c
            tolerance = 64.*np.finfo(float).eps*max(b*b, abs(4.*a*c), 1.)
            if discriminant >= -tolerance:
                discriminant = max(0., discriminant)
                q = -.5*(b+np.copysign(np.sqrt(discriminant), b))
                roots.extend((delay+q/a, delay+c/q) if q else (delay-b/(2.*a),))
    else:
        def residual(horizon):
            return float(np.linalg.norm(fit.predict(fit.origin_s+horizon)-entry)-speed*(horizon-delay))
        count = min(2001, max(33, int(np.ceil((maximum-delay)/.0025))+1))
        grid = np.linspace(delay, maximum, count)
        values = np.linalg.norm(fit.predict(fit.origin_s+grid)-entry, axis=1)-speed*(grid-delay)
        roots.extend(float(grid[index]) for index in np.flatnonzero(values == 0.))
        if abs(values[-1]) <= 1e-10:
            roots.append(float(maximum))
        for index in np.flatnonzero(np.signbit(values[:-1]) != np.signbit(values[1:])):
            roots.append(float(brentq(residual, grid[index], grid[index+1], xtol=1e-13, rtol=1e-14)))
        brackets = []
        for sign in (1., -1.):
            signed = sign*values
            local = np.flatnonzero((signed[1:-1] <= signed[:-2]) & (signed[1:-1] <= signed[2:])
                & (np.maximum(signed[:-2], signed[2:])-signed[1:-1] > 1e-12))+1
            brackets.extend((grid[index-1], grid[index+1], sign) for index in local)
            brackets.extend(((grid[0], grid[1], sign), (grid[-2], grid[-1], sign)))
        for lower, upper, sign in brackets:
            minimum = minimize_scalar(lambda horizon: sign*residual(horizon), bounds=(lower, upper), method="bounded",
                                      options={"xatol": 1e-13, "maxiter": 100})
            if not minimum.success:
                continue
            if abs(minimum.fun) <= 1e-9:
                roots.append(float(minimum.x))
            elif minimum.fun < 0.:
                for boundary in (lower, upper):
                    if sign*residual(boundary) > 0.:
                        roots.append(float(brentq(residual, min(boundary, minimum.x), max(boundary, minimum.x),
                                                  xtol=1e-13, rtol=1e-14)))
    ordered = []
    for horizon in sorted(roots):
        if (np.isfinite(horizon) and delay < horizon <= maximum
                and (not ordered or horizon-ordered[-1] > 1e-8)):
            ordered.append(float(horizon))
    return tuple(ordered)


EXCLUSION_POLICIES = ("Current geometry", "Predicted motion")


@dataclass(frozen=True)
class ExclusionMotionForecast:
    fit: BaselineFit
    target: ResearchTarget
    deformation: LungDeformation
    _matrix: np.ndarray = field(repr=False)

    def __post_init__(self):
        if (not isinstance(self.fit, BaselineFit) or not isinstance(self.target, ResearchTarget)
                or not isinstance(self.deformation, LungDeformation)):
            raise ValueError("Exclusion-motion prediction requires a past-only target fit and its declared deformation.")
        matrix, _ = _route_matrix(self._matrix)
        displacement = self.deformation.height*(np.eye(3)-matrix[:3, :3])[:, 2]
        if not np.allclose(matrix, self.deformation.matrix(displacement), rtol=1e-10, atol=1e-9):
            raise ValueError("The current transform does not match the declared shared affine deformation.")
        if not 1e-6 < self.target_weight <= 1.+1e-9:
            raise ValueError("Target height cannot identify exclusion movement near the fixed apex or outside the motion reference.")
        object.__setattr__(self, "_matrix", np.frombuffer(matrix.tobytes(), dtype=float).reshape(4, 4))

    @property
    def target_weight(self):
        return (self.deformation.apex_z-self.target.center_lps_mm[2])/self.deformation.height

    @property
    def matrix(self):
        return self._matrix.copy()

    @property
    def anchor_displacement(self):
        return self.deformation.height*(np.eye(3)-self._matrix[:3, :3])[:, 2]

    def displacement(self, times):
        raw = np.asarray(times)
        if raw.dtype.kind not in "iuf" or raw.ndim > 1 or raw.size > 100001:
            raise ValueError("Predicted exclusion times must be a bounded scalar or numeric vector.")
        query = raw.astype(float)
        flat = query.reshape(-1)
        positions = np.concatenate([self.fit.predict(flat[start:start+2001]) for start in range(0, len(flat), 2001)], axis=0) if flat.size else np.empty((0, 3))
        displacement = self.anchor_displacement+(positions-self.fit.predict(self.fit.origin_s))/self.target_weight
        if not np.isfinite(displacement).all() or np.any(1.-displacement[:, 2]/self.deformation.height < .5):
            raise ValueError("Predicted exclusion motion exceeds the supported affine compression range.")
        matrices = np.broadcast_to(np.eye(3), (len(flat), 3, 3)).copy()
        matrices[:, :, 2] -= displacement/self.deformation.height
        singular = np.linalg.svd(matrices, compute_uv=False)
        if (np.any(singular[:, -1] < 1e-8) or np.any(singular[:, 0] > 1e6)
                or np.any(singular[:, 0]/singular[:, -1] > 1e8)):
            raise ValueError("Predicted exclusion motion has an unsupported affine condition number.")
        return displacement.reshape((*query.shape, 3))


@dataclass(frozen=True)
class PredictedConstraintEvaluation:
    motion_forecast: ExclusionMotionForecast
    entry_lps_mm: tuple
    endpoint_lps_mm: tuple
    needle_settings: NeedleSettings
    exclusions: tuple
    clearance_mm: float
    step_s: float
    interval_start_s: float
    interval_end_s: float
    min_clearance_lower_bound_mm: float | None
    min_clearance_time_s: float | None
    first_violation_s: float | None
    _times_s: np.ndarray = field(repr=False)
    _clearance_lower_bounds_mm: np.ndarray = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.motion_forecast, ExclusionMotionForecast) or not isinstance(self.needle_settings, NeedleSettings):
            raise ValueError("A predicted constraint trace requires its frozen motion estimate and needle settings.")
        object.__setattr__(self, "entry_lps_mm", _needle_point(self.entry_lps_mm, "Predicted needle entry"))
        object.__setattr__(self, "endpoint_lps_mm", _needle_point(self.endpoint_lps_mm, "Predicted needle endpoint"))
        object.__setattr__(self, "exclusions", _exclusion_regions(self.exclusions, self.motion_forecast.target.study_id))
        times, values = np.asarray(self._times_s, dtype=float), np.asarray(self._clearance_lower_bounds_mm, dtype=float)
        if (times.ndim != 1 or not 2 <= times.size <= 100001 or not np.isfinite(times).all()
                or np.any(np.diff(times) <= 0) or times[0] != self.interval_start_s or times[-1] != self.interval_end_s
                or values.shape != (times.size, len(self.exclusions)) or not np.isfinite(values).all()):
            raise ValueError("Predicted clearance requires a finite ordered insertion trace.")
        object.__setattr__(self, "_times_s", np.frombuffer(times.tobytes(), dtype=float))
        object.__setattr__(self, "_clearance_lower_bounds_mm", np.frombuffer(values.tobytes(), dtype=float).reshape(values.shape))

    @property
    def times_s(self):
        return self._times_s.copy()

    @property
    def clearance_lower_bounds_mm(self):
        return self._clearance_lower_bounds_mm.copy()

    @property
    def violated(self):
        return self.first_violation_s is not None


def predict_needle_constraints(entry, endpoint, fit, target, deformation, current_matrix, needle_settings,
                               exclusions, *, clearance_mm=2., step_s=.005, cancelled=None):
    if not isinstance(needle_settings, NeedleSettings):
        raise ValueError("Predicted clearance requires validated insertion settings.")
    if cancelled is not None and not callable(cancelled):
        raise ValueError("Predicted screening cancellation must be callable.")
    def check_cancelled():
        if cancelled is not None and cancelled():
            raise InterruptedError("Predicted exclusion screening cancelled.")
    check_cancelled()
    motion = ExclusionMotionForecast(fit, target, deformation, current_matrix)
    entry, endpoint = np.asarray(_needle_point(entry, "Needle entry")), np.asarray(_needle_point(endpoint, "Needle endpoint"))
    regions = _exclusion_regions(exclusions, target.study_id)
    clearance = _target_number(clearance_mm, "Required clearance", maximum=10.)
    step = _target_number(step_s, "Predicted constraint step", minimum=.001, maximum=.02)
    length = float(np.linalg.norm(endpoint-entry))
    if not 1e-6 < length <= 1000.:
        raise ValueError("Predicted constraint screening requires a finite nonzero supported path.")
    start = fit.origin_s+needle_settings.delay_s
    arrival = start+length/needle_settings.speed_mm_s
    if arrival > fit.origin_s+5.:
        raise ValueError("Predicted exclusion screening exceeds the five-second forecast horizon.")
    direction = (endpoint-entry)/length
    def states(times):
        check_cancelled()
        times = np.asarray(times)
        depth = np.clip((times-start)*needle_settings.speed_mm_s, 0., length)
        tip = entry+depth[..., None]*direction
        return _constraint_geometry(entry, tip, deformation, regions, needle_settings.radius_mm, motion.displacement(times))
    count = int(np.ceil((arrival-start)/step))+1
    times = np.linspace(start, arrival, count)
    values = states(times)
    cache, refined = {}, []
    def scalar(time, index):
        key = float(time)
        if key not in cache:
            cache[key] = states(np.asarray(key))
        return float(cache[key][index])
    for index in range(len(regions)):
        column = values[:, index]
        local = np.flatnonzero((column[1:-1] <= column[:-2]) & (column[1:-1] <= column[2:])
            & (np.maximum(column[:-2], column[2:])-column[1:-1] > 1e-12))+1
        brackets = [(times[i-1], times[i+1]) for i in local]
        brackets.extend(((times[0], times[1]), (times[-2], times[-1])))
        if len(brackets) > 256:
            raise ValueError("Predicted motion has too many local minima for the bounded clearance screen.")
        for lower, upper in brackets:
            minimum = minimize_scalar(lambda time: scalar(time, index), bounds=(lower, upper), method="bounded",
                                      options={"xatol": 1e-10, "maxiter": 80})
            if not minimum.success or not np.isfinite(minimum.fun):
                raise ValueError("Predicted clearance refinement did not converge; the route was not admitted.")
            refined.append(float(minimum.x))
    times = np.unique(np.r_[times, refined])
    values = states(times)
    contacts = []
    for index in range(len(regions)):
        violated = np.flatnonzero(values[:, index] <= clearance+1e-9)
        if violated.size:
            i = int(violated[0])
            contact = float(times[i])
            if i and values[i-1, index] > clearance and values[i, index] < clearance:
                contact = float(brentq(lambda time: scalar(time, index)-clearance, times[i-1], times[i], xtol=1e-10, rtol=1e-12))
            contacts.append(contact)
    first = min(contacts) if contacts else None
    if first is not None:
        times = np.unique(np.r_[times, first])
        values = states(times)
    minimum = np.unravel_index(np.argmin(values), values.shape) if regions else None
    bound = float(values[minimum]) if regions else None
    minimum_time = float(times[minimum[0]]) if regions else None
    return PredictedConstraintEvaluation(motion, tuple(entry), tuple(endpoint), needle_settings, regions, clearance,
        step, start, arrival, bound, minimum_time, first, times, values)


@dataclass(frozen=True)
class ForecastRouteSelection:
    target: ResearchTarget
    fit: BaselineFit
    entry_reference: tuple
    needle_settings: NeedleSettings
    route_settings: RouteSettings
    exclusions: tuple
    available_until_s: float
    chosen_index: int | None
    _matrix: np.ndarray = field(repr=False)
    _rows: tuple = field(repr=False)
    exclusion_policy: str = "Current geometry"
    predicted_constraint_evaluation: PredictedConstraintEvaluation | None = field(default=None, repr=False)

    def __post_init__(self):
        if (not isinstance(self.target, ResearchTarget) or not isinstance(self.fit, BaselineFit)
                or not isinstance(self.needle_settings, NeedleSettings) or not isinstance(self.route_settings, RouteSettings)):
            raise ValueError("Forecast routes require a target, a past-only baseline fit and validated settings.")
        if self.exclusion_policy not in EXCLUSION_POLICIES:
            raise ValueError("Choose a supported exclusion-screening policy.")
        matrix, _ = _route_matrix(self._matrix)
        object.__setattr__(self, "_matrix", np.frombuffer(matrix.tobytes(), dtype=float).reshape(4, 4))
        object.__setattr__(self, "entry_reference", _needle_point(self.entry_reference, "Entry patch centre"))
        object.__setattr__(self, "exclusions", _exclusion_regions(self.exclusions, self.target.study_id))
        object.__setattr__(self, "available_until_s", _target_number(self.available_until_s,
            "Available motion endpoint", minimum=self.fit.origin_s, positive=True))
        if (not 1 <= len(self._rows) <= 13 or self.chosen_index is not None
                and (isinstance(self.chosen_index, (bool, np.bool_)) or not isinstance(self.chosen_index, (int, np.integer))
                     or not 0 <= self.chosen_index < len(self._rows) or self._rows[self.chosen_index][5] != "eligible")):
            raise ValueError("A forecast selection must identify a bounded candidate set and an eligible chosen entry.")

    @property
    def planning_time_s(self):
        return self.fit.origin_s

    @property
    def origin_s(self):
        return self.fit.origin_s

    @property
    def matrix(self):
        return self._matrix.copy()

    @property
    def rows(self):
        return tuple(dict(index=row[0], entry_reference=row[1], entry_lps_mm=row[2], length_mm=row[3],
            clearance_lower_bound_mm=row[4], status=row[5], reason=row[6], chosen=row[0] == self.chosen_index,
            endpoint_lps_mm=row[7], prediction_time_s=row[8], arrival_s=row[9], horizon_s=row[10],
            intercept_residual_mm=row[11], predicted_clearance_lower_bound_mm=row[12] if len(row) > 12 else None,
            predicted_clearance_time_s=row[13] if len(row) > 13 else None,
            predicted_first_violation_s=row[14] if len(row) > 14 else None,
            predicted_screening_reason=row[15] if len(row) > 15 else "") for row in self._rows)

    @property
    def chosen_entry_reference(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][1]

    @property
    def chosen_entry_lps_mm(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][2]

    @property
    def chosen_endpoint_lps_mm(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][7]

    @property
    def endpoint_lps_mm(self):
        return self.chosen_endpoint_lps_mm

    @property
    def chosen_prediction_time_s(self):
        return None if self.chosen_index is None else self._rows[self.chosen_index][8]


def select_forecast_route(volume, lung_mask, target, entry_reference, current_matrix, fit,
                          needle_settings=None, exclusions=(), route_settings=None, *, available_until_s=60.,
                          exclusion_policy="Current geometry", deformation=None, cancelled=None):
    needle_settings = NeedleSettings() if needle_settings is None else needle_settings
    route_settings = RouteSettings() if route_settings is None else route_settings
    if (not isinstance(fit, BaselineFit) or not isinstance(target, ResearchTarget)
            or not isinstance(needle_settings, NeedleSettings) or not isinstance(route_settings, RouteSettings)):
        raise ValueError("Forecast route selection requires a past-only baseline fit and validated geometry/settings.")
    if exclusion_policy not in EXCLUSION_POLICIES:
        raise ValueError("Choose a supported exclusion-screening policy.")
    if cancelled is not None and not callable(cancelled):
        raise ValueError("Route selection cancellation must be callable.")
    def check_cancelled():
        if cancelled is not None and cancelled():
            raise InterruptedError("Forecast route selection cancelled.")
    check_cancelled()
    available = _target_number(available_until_s, "Available motion endpoint", minimum=fit.origin_s, positive=True)
    entry, matrix, regions, candidates, _ = _route_geometry(
        volume, lung_mask, target, entry_reference, current_matrix, exclusions, route_settings)
    inverse = np.linalg.inv(matrix[:3, :3])
    limits = np.asarray(volume.shape[::-1])-1
    maximum = min(5., available-fit.origin_s)
    rows, predicted_checks = [], {}
    for index, candidate in enumerate(candidates):
        check_cancelled()
        world = matrix[:3, :3] @ candidate+matrix[:3, 3]
        result = [None, None, "rejected", "No finite predicted intercept is reachable within five seconds and the available timeline.",
                  None, None, None, None, None, None, None, None, ""]
        try:
            validate_needle_entry(volume, lung_mask, candidate)
            horizons = _forecast_intercept_horizons(fit, world, needle_settings.speed_mm_s, needle_settings.delay_s, maximum)
            first_rejection = None
            for horizon in horizons:
                check_cancelled()
                query = fit.origin_s+horizon
                endpoint = fit.predict(query)
                length = float(np.linalg.norm(endpoint-world))
                arrival = fit.origin_s+needle_settings.delay_s+length/needle_settings.speed_mm_s
                residual = abs(length-needle_settings.speed_mm_s*(horizon-needle_settings.delay_s))
                bound, status, reason = None, "eligible", "Earliest feasible predicted intercept; current-geometry constraints satisfied."
                predicted, predicted_reason = None, ""
                try:
                    if not 1e-6 < length <= 1000.:
                        raise ValueError("The predicted finite path length is outside its supported range.")
                    if arrival > available or arrival > fit.origin_s+5.:
                        raise ValueError("Physical arrival exceeds the available timeline or five-second prediction range.")
                    if residual > 1e-5 or np.linalg.norm(fit.predict(arrival)-endpoint) > 1e-5:
                        raise ValueError("The predicted intercept is not numerically consistent with physical needle arrival.")
                    reference_endpoint = inverse @ (endpoint-matrix[:3, 3])
                    voxel = volume.world_to_index(reference_endpoint)
                    if np.any(voxel < -1e-9) or np.any(voxel > limits+1e-9):
                        raise ValueError("The predicted endpoint lies outside the current oriented CT image coverage.")
                    values = exclusion_clearance_lower_bounds(world, endpoint, matrix, regions, needle_settings.radius_mm)
                    bound = float(values.min()) if values.size else None
                    if bound is not None and bound <= route_settings.clearance_mm+1e-9:
                        raise ValueError("The predicted path's conservative clearance bound does not exceed the required margin.")
                    if exclusion_policy == "Predicted motion" and regions:
                        predicted_reason = "Predicted insertion screening unavailable."
                        predicted = predict_needle_constraints(world, endpoint, fit, target, deformation, matrix,
                            needle_settings, regions, clearance_mm=route_settings.clearance_mm, cancelled=cancelled)
                        check_cancelled()
                        predicted_reason = ("Predicted moving-exclusion clearance violates the required margin during insertion."
                            if predicted.violated else "No violation found numerically in predicted moving-exclusion clearance during insertion.")
                        if predicted.violated:
                            raise ValueError(predicted_reason)
                        reason = "Earliest feasible intercept satisfies current geometry and numerical predicted moving-exclusion screening."
                except ValueError as error:
                    status, reason = "rejected", str(error)
                    if predicted_reason and predicted is None:
                        predicted_reason = "Predicted insertion screening unavailable: "+str(error)
                trial = [length, bound, status, reason, tuple(float(value) for value in endpoint),
                         float(query), float(arrival), float(arrival-fit.origin_s), float(residual),
                         predicted.min_clearance_lower_bound_mm if predicted else None,
                         predicted.min_clearance_time_s if predicted else None,
                         predicted.first_violation_s if predicted else None, predicted_reason]
                if first_rejection is None:
                    first_rejection = trial
                if status == "eligible":
                    result = trial
                    predicted_checks[index] = predicted
                    break
            else:
                if first_rejection is not None:
                    result = first_rejection
        except ValueError as error:
            result[3] = str(error)
        rows.append((index, tuple(float(value) for value in candidate), tuple(float(value) for value in world), *result))
    eligible = [row for row in rows if row[5] == "eligible"]
    chosen = min(eligible, key=lambda row: (row[3], -row[4] if row[4] is not None else 0., row[0]))[0] if eligible else None
    return ForecastRouteSelection(target, fit, tuple(entry), needle_settings, route_settings, regions,
                                  available, chosen, matrix, tuple(rows), exclusion_policy, predicted_checks.get(chosen))


def create_forecast_needle_plan(selection, model_id, deformation):
    if not isinstance(selection, ForecastRouteSelection):
        raise ValueError("A forecast needle path requires a completed forecast route selection.")
    if selection.chosen_index is None:
        return None
    plan = NeedlePlan(selection.chosen_entry_lps_mm, selection.chosen_endpoint_lps_mm,
        selection.planning_time_s, selection.needle_settings, selection.target, model_id, deformation)
    query = selection.chosen_prediction_time_s
    if (plan.arrival_s > selection.available_until_s or plan.arrival_s > selection.fit.origin_s+5.
            or np.linalg.norm(selection.fit.predict(plan.arrival_s)-plan.endpoint_lps_mm) > 1e-5
            or abs(query-plan.arrival_s)*plan.settings.speed_mm_s > 1e-5):
        raise ValueError("The forecast endpoint and physical needle arrival are inconsistent.")
    return plan


def _constraint_states(plan, model, regions, times):
    displacement = model.position(times)
    return _constraint_geometry(plan.entry_lps_mm, plan.tip_at_time(times), plan.deformation, regions,
                                plan.settings.radius_mm, displacement)


def _constraint_geometry(entry, tip, deformation, regions, needle_radius_mm, displacement):
    displacement = np.asarray(displacement, dtype=float)
    height, apex = deformation.height, deformation.apex_z
    denominator = height-displacement[..., 2]
    if np.any(denominator < .5*height):
        raise ValueError("The selected motion excessively compresses the simulated exclusion geometry.")
    tip, entry = np.asarray(tip, dtype=float), np.asarray(entry, dtype=float)
    pulled_entry = entry-((apex-entry[2])/denominator)[..., None]*displacement
    pulled_tip = tip-((apex-tip[..., 2])/denominator)[..., None]*displacement
    segment = pulled_tip-pulled_entry
    centres = np.array([region.center_lps_mm for region in regions], dtype=float).reshape(-1, 3)
    offset = centres-pulled_entry[..., None, :]
    squared = np.sum(segment*segment, axis=-1)
    fraction = np.divide(np.sum(offset*segment[..., None, :], axis=-1), squared[..., None],
        out=np.zeros(offset.shape[:-1]), where=squared[..., None] > 1e-20)
    closest = pulled_entry[..., None, :]+np.clip(fraction, 0., 1.)[..., None]*segment[..., None, :]
    matrices = np.broadcast_to(np.eye(3), (*displacement.shape[:-1], 3, 3)).copy()
    matrices[..., :, 2] -= displacement/height
    sigma = np.linalg.svd(matrices, compute_uv=False)[..., -1]
    return sigma[..., None]*(np.linalg.norm(centres-closest, axis=-1)-[region.radius_mm for region in regions])-needle_radius_mm


def evaluate_constraint_state(plan, model, exclusions, *, clearance_mm=2., time):
    _check_needle_scenario(plan, model)
    regions = _exclusion_regions(exclusions, plan.target.study_id)
    clearance = _target_number(clearance_mm, "Required clearance", maximum=10.)
    time = _target_number(time, "Constraint preview time", maximum=model.duration)
    values = _constraint_states(plan, model, regions, np.asarray(time))
    if plan.model_id != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed during constraint evaluation.")
    bound = float(values.min()) if values.size else None
    return dict(clearance_lower_bounds_mm=values, min_clearance_lower_bound_mm=bound,
                violated=bool(bound is not None and bound <= clearance+1e-9))


@dataclass(frozen=True)
class ConstraintEvaluation:
    plan: NeedlePlan
    exclusions: tuple
    clearance_mm: float
    step_s: float
    min_clearance_lower_bound_mm: float | None
    min_clearance_time_s: float | None
    first_violation_s: float | None
    _times_s: np.ndarray = field(repr=False)
    _clearance_lower_bounds_mm: np.ndarray = field(repr=False)

    def __post_init__(self):
        object.__setattr__(self, "exclusions", _exclusion_regions(self.exclusions, self.plan.target.study_id))
        times = np.asarray(self._times_s, dtype=float)
        values = np.asarray(self._clearance_lower_bounds_mm, dtype=float)
        if (times.ndim != 1 or not 2 <= times.size <= 100001 or not np.isfinite(times).all()
                or np.any(np.diff(times) <= 0) or times[0] != self.plan.start_s or times[-1] != self.plan.arrival_s
                or values.shape != (times.size, len(self.exclusions)) or not np.isfinite(values).all()):
            raise ValueError("Constraint evaluation requires a finite ordered execution trace.")
        object.__setattr__(self, "_times_s", np.frombuffer(times.tobytes(), dtype=float))
        object.__setattr__(self, "_clearance_lower_bounds_mm", np.frombuffer(values.tobytes(), dtype=float).reshape(values.shape))

    @property
    def times_s(self):
        return self._times_s.copy()

    @property
    def clearance_lower_bounds_mm(self):
        return self._clearance_lower_bounds_mm.copy()

    @property
    def violated(self):
        return self.first_violation_s is not None


def evaluate_needle_constraints(plan, model, exclusions, *, clearance_mm=2., step_s=.005):
    _check_needle_scenario(plan, model)
    regions = _exclusion_regions(exclusions, plan.target.study_id)
    clearance = _target_number(clearance_mm, "Required clearance", maximum=10.)
    step = _target_number(step_s, "Constraint evaluation step", minimum=.001, maximum=.02)
    count = int(np.ceil((plan.arrival_s-plan.start_s)/step))+1
    if count > 99000:
        raise ValueError("The insertion interval exceeds the bounded constraint evaluation budget.")
    times = np.linspace(plan.start_s, plan.arrival_s, count)
    values = _constraint_states(plan, model, regions, times)
    cache, refined = {}, []
    def scalar(time, index):
        key = float(time)
        if key not in cache:
            cache[key] = _constraint_states(plan, model, regions, np.asarray(key))
        return float(cache[key][index])
    for index in range(len(regions)):
        column = values[:, index]
        local = np.flatnonzero((column[1:-1] <= column[:-2]) & (column[1:-1] <= column[2:])
            & (np.maximum(column[:-2], column[2:])-column[1:-1] > 1e-12))+1
        brackets = [(times[i-1], times[i+1]) for i in local]
        brackets.extend(((times[0], times[1]), (times[-2], times[-1])))
        if len(brackets) > 256:
            raise ValueError("The motion has too many local minima for the bounded constraint evaluator.")
        for lower, upper in brackets:
            fit = minimize_scalar(lambda time: scalar(time, index), bounds=(lower, upper), method="bounded",
                                  options={"xatol": 1e-10, "maxiter": 80})
            if fit.success:
                refined.append(float(fit.x))
    times = np.unique(np.r_[times, refined])
    values = _constraint_states(plan, model, regions, times)
    first = None
    if regions:
        contacts = []
        for index in range(len(regions)):
            violated = np.flatnonzero(values[:, index] <= clearance+1e-9)
            if violated.size:
                i = int(violated[0])
                contact = float(times[i])
                if i and values[i-1, index] > clearance and values[i, index] < clearance:
                    contact = float(brentq(lambda time: scalar(time, index)-clearance,
                        times[i-1], times[i], xtol=1e-10, rtol=1e-12))
                contacts.append(contact)
        first = min(contacts) if contacts else None
    if first is not None:
        times = np.unique(np.r_[times, first])
        values = _constraint_states(plan, model, regions, times)
    if regions:
        minimum = np.unravel_index(np.argmin(values), values.shape)
        bound, minimum_time = float(values[minimum]), float(times[minimum[0]])
    else:
        bound, minimum_time = None, None
    if plan.model_id != respiratory_model_id(model):
        raise ValueError("The respiratory scenario changed during constraint evaluation.")
    return ConstraintEvaluation(plan, regions, clearance, step, bound, minimum_time, first, times, values)


@dataclass(frozen=True)
class PlanningBenchmarkSettings:
    preset: str = "Quick"
    seed: int = 17
    amplitude_mm: float = 8.
    rate_bpm: float = 15.
    observation_rate_hz: float = 10.
    forecast_settings: ForecastSettings = field(default_factory=ForecastSettings)
    compare_exclusion_policies: bool = False
    assess_forecast_uncertainty: bool = False
    uncertainty_settings: UncertaintySettings = field(default_factory=UncertaintySettings)
    uncertainty_horizon_s: float = .5

    def __post_init__(self):
        if self.preset not in ("Quick", "Extended"):
            raise ValueError("Choose the Quick or Extended planning comparison.")
        if (isinstance(self.seed, (bool, np.bool_)) or not isinstance(self.seed, (int, np.integer))
                or not 0 <= self.seed <= 2**32-1):
            raise ValueError("The comparison seed must be an integer between 0 and 4294967295.")
        object.__setattr__(self, "seed", int(self.seed))
        for name, lower, upper in (("amplitude_mm", 0., 30.), ("rate_bpm", 6., 36.),
                                   ("observation_rate_hz", .1, 100.)):
            object.__setattr__(self, name, _target_number(getattr(self, name), name.replace("_", " "),
                                                        minimum=lower, maximum=upper))
        if not isinstance(self.forecast_settings, ForecastSettings):
            raise ValueError("The comparison requires validated forecasting settings.")
        for name in ("compare_exclusion_policies", "assess_forecast_uncertainty"):
            if not isinstance(getattr(self, name), (bool, np.bool_)):
                raise ValueError("Comparison options must be enabled or disabled explicitly.")
            object.__setattr__(self, name, bool(getattr(self, name)))
        if not isinstance(self.uncertainty_settings, UncertaintySettings):
            raise ValueError("The comparison requires validated empirical uncertainty settings.")
        object.__setattr__(self, "uncertainty_horizon_s", _target_number(self.uncertainty_horizon_s,
            "Uncertainty audit horizon", minimum=.1, maximum=5.))


def planning_benchmark_cases(settings=None):
    settings = PlanningBenchmarkSettings() if settings is None else settings
    if not isinstance(settings, PlanningBenchmarkSettings):
        raise ValueError("Supply validated planning comparison settings.")
    repeats = (0,) if settings.preset == "Quick" else (0, 1)
    origins = (31.15,) if settings.preset == "Quick" else (31.15, 42.65)
    rows = []
    for pattern_index, pattern in enumerate(BREATHING_PATTERNS):
        for repeat in repeats:
            seed = np.random.SeedSequence([settings.seed, pattern_index, repeat, 1401])
            profile_seed, observation_seed = (int(value) for value in seed.generate_state(2))
            for origin, noise, delay, speed in product(origins, (0., 1.), (0., 1.5), (15., 30.)):
                rows.append(dict(case_id=f"case-{len(rows)+1:03d}", pattern=pattern, replicate=repeat,
                    origin_s=origin, noise_std_mm=noise, delay_s=delay, speed_mm_s=speed,
                    profile_seed=profile_seed, observation_seed=observation_seed))
    return tuple(rows)


def _benchmark_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _planning_benchmark_summaries(rows):
    summaries = []
    policies = [policy for policy in EXCLUSION_POLICIES if any(row.get("exclusion_policy", "Current geometry") == policy for row in rows)]
    for method, policy in product(BASELINE_METHODS, policies):
        group = [row for row in rows if row["method"] == method and row.get("exclusion_policy", "Current geometry") == policy]
        executed = [row for row in group if row["status"] == "executed"]
        errors = np.array([row["arrival_tip_error_mm"] for row in executed])
        assessed = [row for row in executed if row["constraint_violated"] is not None]
        declared = bool(assessed) or any(row.get("exclusions_declared", False) for row in group)
        hits = sum(row["arrival_tip_centre_inside_target"] for row in executed)
        violations = sum(row["constraint_violated"] for row in assessed)
        clear_hits = sum(row["arrival_tip_centre_inside_target"] and not row["constraint_violated"] for row in assessed)
        summaries.append(dict(method=method, exclusion_policy=policy, case_count=len(group), executed_count=len(executed),
            fit_unavailable_count=sum(row["status"] == "fit_unavailable" for row in group),
            abstained_count=sum(row["status"] == "abstained" for row in group),
            execution_failed_count=sum(row["status"] == "execution_failed" for row in group),
            arrival_error_count=len(executed),
            mean_arrival_error_mm=float(np.mean(errors)) if errors.size else None,
            median_arrival_error_mm=float(np.median(errors)) if errors.size else None,
            p95_arrival_error_mm=float(np.percentile(errors, 95)) if errors.size else None,
            arrival_hit_count=int(hits), arrival_hit_rate_all_cases=hits/len(group) if group else None,
            arrival_hit_rate_executed=hits/len(executed) if executed else None,
            execution_coverage=len(executed)/len(group) if group else None,
            tip_contact_count=sum(row["first_tip_hit_s"] is not None for row in executed),
            shaft_contact_count=sum(row["first_shaft_hit_s"] is not None for row in executed),
            exclusions_declared=declared, obstacle_assessed_count=len(assessed), obstacle_violation_count=int(violations),
            obstacle_violation_rate_assessed=violations/len(assessed) if assessed else None,
            arrival_hit_clear_count=int(clear_hits) if declared else None,
            arrival_hit_clear_rate_all_cases=clear_hits/len(group) if declared and group else None))
    baseline = {(row["case_id"], row.get("exclusion_policy", "Current geometry")): row for row in rows if row["method"] == "Constant position"}
    paired = []
    for method, policy in product(BASELINE_METHODS[1:], policies):
        group = [row for row in rows if row["method"] == method and row.get("exclusion_policy", "Current geometry") == policy]
        pairs = [(row, baseline[(row["case_id"], policy)]) for row in group
                 if row["status"] == "executed" and baseline[(row["case_id"], policy)]["status"] == "executed"]
        delta = np.array([row["arrival_tip_error_mm"]-reference["arrival_tip_error_mm"] for row, reference in pairs])
        paired.append(dict(method=method, exclusion_policy=policy, baseline_method="Constant position", paired_count=len(pairs),
            excluded_count=len(group)-len(pairs),
            mean_error_delta_mm=float(np.mean(delta)) if delta.size else None,
            median_error_delta_mm=float(np.median(delta)) if delta.size else None,
            wins=int(np.count_nonzero(delta < -1e-6)), ties=int(np.count_nonzero(np.abs(delta) <= 1e-6)),
            losses=int(np.count_nonzero(delta > 1e-6))))
    return tuple(summaries), tuple(paired)


def _planning_policy_summaries(rows):
    if not all(any(row.get("exclusion_policy") == policy for row in rows) for policy in EXCLUSION_POLICIES):
        return ()
    summaries = []
    for method in BASELINE_METHODS:
        current = {row["case_id"]: row for row in rows if row["method"] == method and row["exclusion_policy"] == "Current geometry"}
        predicted = {row["case_id"]: row for row in rows if row["method"] == method and row["exclusion_policy"] == "Predicted motion"}
        if set(current) != set(predicted):
            raise ValueError("Exclusion-policy comparisons require identical case identities.")
        common = [key for key in current if current[key]["status"] == predicted[key]["status"] == "executed"]
        delta = [predicted[key]["arrival_tip_error_mm"]-current[key]["arrival_tip_error_mm"] for key in common]
        result = dict(method=method, case_count=len(current), paired_executed_count=len(common),
            excluded_count=len(current)-len(common), paired_error_delta_mm=float(np.mean(delta)) if delta else None,
            samecase_different_entry_count=sum(current[key]["chosen_candidate_index"] != predicted[key]["chosen_candidate_index"] for key in common))
        for label, group in (("current", current), ("predicted", predicted)):
            executed = [row for row in group.values() if row["status"] == "executed"]
            assessed = [row for row in executed if row["constraint_violated"] is not None]
            hits = sum(row["arrival_tip_centre_inside_target"] for row in executed)
            clear_hits = sum(bool(row["arrival_hit_clear"]) for row in assessed)
            result.update({f"{label}_executed_count": len(executed),
                f"{label}_abstained_count": sum(row["status"] == "abstained" for row in group.values()),
                f"{label}_fit_unavailable_count": sum(row["status"] == "fit_unavailable" for row in group.values()),
                f"{label}_execution_failed_count": sum(row["status"] == "execution_failed" for row in group.values()),
                f"{label}_arrival_hit_count": int(hits), f"{label}_arrival_hit_clear_count": int(clear_hits),
                f"{label}_arrival_hit_clear_rate_all_cases": clear_hits/len(group) if group else None,
                f"{label}_obstacle_assessed_count": len(assessed),
                f"{label}_obstacle_violation_count": sum(row["constraint_violated"] for row in assessed)})
        summaries.append(result)
    return tuple(summaries)


def _planning_uncertainty_summaries(rows):
    unique = {}
    for row in rows:
        key = row["case_id"], row["method"]
        diagnostic = {name: value for name, value in row.items() if name.startswith("uncertainty_")}
        if key in unique and diagnostic != {name: value for name, value in unique[key].items() if name.startswith("uncertainty_")}:
            raise ValueError("Each method/case uncertainty audit must be identical across exclusion policies.")
        unique[key] = row
    if not any(row.get("uncertainty_status", "not_requested") != "not_requested" for row in unique.values()):
        return ()
    summaries = []
    for method in BASELINE_METHODS:
        group = [row for row in unique.values() if row["method"] == method]
        requested = [row for row in group if row.get("uncertainty_status", "not_requested") != "not_requested"]
        if any(row["uncertainty_status"] not in ("available", "unavailable") for row in requested):
            raise ValueError("An uncertainty audit must report availability explicitly.")
        available = [row for row in requested if row["uncertainty_status"] == "available"]
        probes = {}
        for row in requested:
            key = (row.get("model_id"), row.get("observation_seed"), row.get("noise_std_mm"),
                   row["uncertainty_prefix_sha256"], row["uncertainty_query_s"])
            if key in probes and {name: value for name, value in row.items() if name.startswith("uncertainty_")} != {
                    name: value for name, value in probes[key].items() if name.startswith("uncertainty_")}:
                raise ValueError("A repeated prospective probe cannot have different uncertainty outcomes.")
            probes[key] = row
        available_probes = [row for row in probes.values() if row["uncertainty_status"] == "available"]
        radii = np.array([row["uncertainty_radius_mm"] for row in available_probes])
        observed = [row for row in available_probes if row["uncertainty_observed_covered"] is not None]
        truth = [row for row in available_probes if row["uncertainty_true_covered"] is not None]
        observed_hits = sum(row["uncertainty_observed_covered"] for row in observed)
        true_hits = sum(row["uncertainty_true_covered"] for row in truth)
        coverage = {row["uncertainty_nominal_coverage"] for row in requested}
        summaries.append(dict(method=method, case_count=len(group), requested_count=len(requested),
            available_count=len(available), unavailable_count=len(requested)-len(available),
            not_requested_count=len(group)-len(requested), nominal_coverage=next(iter(coverage)) if len(coverage) == 1 else None,
            distinct_probe_count=len(probes), available_probe_count=len(available_probes),
            observation_assessed_count=len(observed), observed_covered_count=int(observed_hits),
            observed_coverage=observed_hits/len(observed) if observed else None,
            truth_assessed_count=len(truth), true_covered_count=int(true_hits),
            true_coverage=true_hits/len(truth) if truth else None,
            mean_radius_mm=float(np.mean(radii)) if radii.size else None,
            median_radius_mm=float(np.median(radii)) if radii.size else None,
            p95_radius_mm=float(np.percentile(radii, 95)) if radii.size else None))
    return tuple(summaries)


def _benchmark_uncertainty_audit(settings, model, target, deformation, times, positions, case, method, cancelled):
    diagnostic = dict(uncertainty_status="not_requested", uncertainty_reason="", uncertainty_query_s=None,
        uncertainty_horizon_s=None, uncertainty_nominal_coverage=None, uncertainty_score_count=None,
        uncertainty_required_count=None, uncertainty_excluded_count=None, uncertainty_last_calibration_outcome_s=None,
        uncertainty_prefix_sha256=None, uncertainty_radius_mm=None, uncertainty_observed_error_mm=None,
        uncertainty_observed_covered=None, uncertainty_true_error_mm=None, uncertainty_true_covered=None)
    if not settings.assess_forecast_uncertainty:
        return diagnostic
    if cancelled is not None and cancelled():
        raise InterruptedError("Forecast-region audit cancelled.")
    coverage = settings.uncertainty_settings.nominal_coverage
    sample = int(np.ceil(np.nextafter((case["origin_s"]+settings.uncertainty_horizon_s)*settings.observation_rate_hz, -np.inf)))
    query = sample/settings.observation_rate_hz
    horizon = query-case["origin_s"]
    digest = sha256(np.asarray(times, dtype="<f8").tobytes()+np.asarray(positions, dtype="<f8").tobytes()).hexdigest()
    diagnostic.update(uncertainty_status="unavailable", uncertainty_query_s=query, uncertainty_horizon_s=horizon,
        uncertainty_nominal_coverage=coverage, uncertainty_required_count=settings.uncertainty_settings.required_score_count,
        uncertainty_prefix_sha256=digest)
    if not .1-1e-10 <= horizon <= 5.+1e-10 or query > model.duration:
        diagnostic["uncertainty_reason"] = "No future observation-grid probe lies inside the supported forecast range and simulation timeline."
        return diagnostic
    try:
        region = calibrate_forecast_region(times, positions, method, origin_s=case["origin_s"], horizon_s=horizon,
            settings=settings.uncertainty_settings, forecast_settings=settings.forecast_settings, cancelled=cancelled)
    except ValueError as error:
        diagnostic["uncertainty_reason"] = str(error)
        return diagnostic
    diagnostic.update(uncertainty_score_count=region.n_scores, uncertainty_excluded_count=region.excluded_count,
        uncertainty_last_calibration_outcome_s=region.last_outcome_s, uncertainty_radius_mm=region.radius_mm,
        uncertainty_prefix_sha256=region.prefix_sha256, uncertainty_reason=region.reason)
    if not region.available:
        return diagnostic
    if cancelled is not None and cancelled():
        raise InterruptedError("Forecast-region audit cancelled.")
    # the future observation and truth are generated only after the past-only region has been frozen.
    extension = generate_target_observations(target, model, deformation,
        ObservationSettings(settings.observation_rate_hz, case["noise_std_mm"], case["observation_seed"]), through_s=query)
    if not np.isclose(extension.times_s[-1], query, rtol=0, atol=1e-10):
        diagnostic["uncertainty_reason"] = "The prospective observation probe is absent from the generated sampling grid."
        return diagnostic
    assessment = evaluate_forecast_region(region, observed_lps_mm=extension.observed_lps_mm[-1],
        true_lps_mm=extension.evaluation_ground_truth_lps_mm[-1])
    diagnostic.update(uncertainty_status="available", uncertainty_observed_error_mm=assessment["observed_error_mm"],
        uncertainty_observed_covered=assessment["observed_covered"], uncertainty_true_error_mm=assessment["true_error_mm"],
        uncertainty_true_covered=assessment["true_covered"])
    return diagnostic


@dataclass(frozen=True)
class PlanningBenchmarkResult:
    settings: PlanningBenchmarkSettings
    _manifest_json: str = field(repr=False)
    _rows_json: str = field(repr=False)
    _summaries_json: str = field(repr=False)
    _paired_json: str = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.settings, PlanningBenchmarkSettings):
            raise ValueError("A planning comparison result requires its validated settings.")
        manifest, rows = json.loads(self._manifest_json), json.loads(self._rows_json)
        if (not isinstance(manifest, dict) or not isinstance(rows, list) or not 3 <= len(rows) <= 768
                or len(rows) != manifest.get("trial_count")
                or len({(row["case_id"], row["method"], row.get("exclusion_policy", "Current geometry")) for row in rows}) != len(rows)
                or any(row["method"] not in BASELINE_METHODS for row in rows)
                or any(row.get("exclusion_policy", "Current geometry") not in EXCLUSION_POLICIES for row in rows)
                or any(row["status"] not in ("fit_unavailable", "abstained", "execution_failed", "executed") for row in rows)):
            raise ValueError("A planning comparison result must contain complete, distinctly identified method trials.")
        policies = manifest.get("exclusion_policies", ["Current geometry"])
        expected = set(product(BASELINE_METHODS, policies))
        counts = {case: {(row["method"], row.get("exclusion_policy", "Current geometry")) for row in rows if row["case_id"] == case} for case in {row["case_id"] for row in rows}}
        if len(counts) != manifest.get("case_count") or any(value != expected for value in counts.values()):
            raise ValueError("Every comparison case must retain one trial for every method.")
        expected_summaries, expected_paired = _planning_benchmark_summaries(rows)
        if (_benchmark_json(expected_summaries) != self._summaries_json
                or _benchmark_json(expected_paired) != self._paired_json):
            raise ValueError("Comparison summaries must agree with their complete trial rows.")

    @property
    def manifest(self):
        return json.loads(self._manifest_json)

    @property
    def rows(self):
        return tuple(json.loads(self._rows_json))

    @property
    def summaries(self):
        return tuple(json.loads(self._summaries_json))

    @property
    def paired_summaries(self):
        return tuple(json.loads(self._paired_json))

    @property
    def pattern_summaries(self):
        rows = self.rows
        return tuple(dict(row, pattern=pattern) for pattern in BREATHING_PATTERNS
            if any(row["pattern"] == pattern for row in rows)
            for row in _planning_benchmark_summaries([row for row in rows if row["pattern"] == pattern])[0])

    @property
    def pattern_paired_summaries(self):
        rows = self.rows
        return tuple(dict(row, pattern=pattern) for pattern in BREATHING_PATTERNS
            if any(row["pattern"] == pattern for row in rows)
            for row in _planning_benchmark_summaries([row for row in rows if row["pattern"] == pattern])[1])

    @property
    def policy_summaries(self):
        return _planning_policy_summaries(self.rows)

    @property
    def pattern_policy_summaries(self):
        rows = self.rows
        return tuple(dict(row, pattern=pattern) for pattern in BREATHING_PATTERNS
            if any(row["pattern"] == pattern for row in rows)
            for row in _planning_policy_summaries([row for row in rows if row["pattern"] == pattern]))

    @property
    def uncertainty_summaries(self):
        return _planning_uncertainty_summaries(self.rows)

    @property
    def pattern_uncertainty_summaries(self):
        rows = self.rows
        return tuple(dict(row, pattern=pattern) for pattern in BREATHING_PATTERNS
            if any(row["pattern"] == pattern for row in rows)
            for row in _planning_uncertainty_summaries([row for row in rows if row["pattern"] == pattern]))

    @property
    def result_id(self):
        return sha256((self._manifest_json+self._rows_json).encode("utf-8")).hexdigest()


def run_planning_benchmark(volume, lung_mask, target, entry_reference, deformation, *, settings=None,
                           needle_radius_mm=.7, route_settings=None, exclusions=(), progress=None, cancelled=None):
    settings = PlanningBenchmarkSettings() if settings is None else settings
    route_settings = RouteSettings() if route_settings is None else route_settings
    if (not isinstance(settings, PlanningBenchmarkSettings) or not isinstance(route_settings, RouteSettings)
            or not isinstance(target, ResearchTarget) or not isinstance(deformation, LungDeformation)):
        raise ValueError("Planning comparisons require a target, deformation and validated settings.")
    if any(callback is not None and not callable(callback) for callback in (progress, cancelled)):
        raise ValueError("Comparison progress and cancellation hooks must be callable.")
    radius = NeedleSettings(radius_mm=needle_radius_mm).radius_mm
    entry, _, regions, candidates, _ = _route_geometry(
        volume, lung_mask, target, entry_reference, np.eye(4), exclusions, route_settings)
    cases = planning_benchmark_cases(settings)
    if not cases or len(cases) > 128 or len({row["case_id"] for row in cases}) != len(cases):
        raise ValueError("The planning comparison requires a bounded set of distinctly identified cases.")
    def check_cancelled():
        if cancelled is not None and cancelled():
            raise InterruptedError("Planning comparison cancelled; no partial result was published.")
    check_cancelled()
    candidate_digest = sha256(np.asarray(candidates, dtype="<f8").tobytes()).hexdigest()
    forecast = settings.forecast_settings
    policies = EXCLUSION_POLICIES if settings.compare_exclusion_policies and regions else EXCLUSION_POLICIES[:1]
    manifest = dict(format_version=3, algorithm="causal_arrival_planning_comparison_v3", preset=settings.preset,
        software=dict(python=platform.python_version(), numpy=np.__version__, scipy=_scipy_version,
            core_sha256=sha256(Path(__file__).read_bytes()).hexdigest()),
        master_seed=settings.seed, case_count=len(cases), trial_count=len(cases)*len(BASELINE_METHODS)*len(policies),
        methods=list(BASELINE_METHODS), exclusion_policies=list(policies), compare_exclusion_policies=settings.compare_exclusion_policies,
        assess_forecast_uncertainty=settings.assess_forecast_uncertainty,
        uncertainty_settings=dict(nominal_coverage=settings.uncertainty_settings.nominal_coverage,
            min_scores=settings.uncertainty_settings.min_scores, max_scores=settings.uncertainty_settings.max_scores,
            min_spacing_s=settings.uncertainty_settings.min_spacing_s, requested_horizon_s=settings.uncertainty_horizon_s),
        baseline_method="Constant position", case_grid=cases,
        amplitude_mm=settings.amplitude_mm, rate_bpm=settings.rate_bpm,
        observation_rate_hz=settings.observation_rate_hz,
        forecast_settings=dict(history_window_s=forecast.history_window_s, velocity_window_s=forecast.velocity_window_s,
            min_rate_bpm=forecast.min_rate_bpm, max_rate_bpm=forecast.max_rate_bpm),
        study_id=target.study_id, source_name=volume.name, shape_zyx=list(volume.shape),
        spacing_xyz_mm=list(volume.spacing), origin_lps_mm=list(volume.origin), direction=volume.direction.tolist(),
        union_lung_sha256=sha256(np.ascontiguousarray(lung_mask).tobytes()).hexdigest(),
        target=dict(name=target.name, center_lps_mm=target.center_lps_mm, radius_mm=target.radius_mm),
        entry_reference_lps_mm=tuple(entry), deformation=dict(base_z=deformation.base_z, apex_z=deformation.apex_z),
        needle_radius_mm=radius, route_settings=dict(patch_radius_mm=route_settings.patch_radius_mm,
            clearance_mm=route_settings.clearance_mm),
        exclusions=[dict(name=region.name, center_lps_mm=region.center_lps_mm, radius_mm=region.radius_mm) for region in regions],
        candidate_entries_reference_lps_mm=[tuple(point) for point in candidates],
        candidate_entries_sha256=candidate_digest, evaluation_step_s=.005, intercept_limit_s=5.,
        definitions=dict(statuses=["fit_unavailable", "abstained", "execution_failed", "executed"],
            arrival_error="Euclidean tip-centre to simulated target-centre distance at actual arrival, mm; executed cases only.",
            arrival_hit="Tip centre lies in the affine-deformed target at actual arrival; unexecuted cases count as no hit in all-case rate.",
            contact="First tip-centre or finite inserted-centreline intersection during insertion; excludes the waiting period.",
            obstacle_violation="Conservative finite-capsule clearance bound is at or below the requested margin during execution.",
            arrival_hit_clear="Arrival hit and no numerical exclusion violation; unavailable without declared exclusions.",
            paired_delta="Method arrival error minus observed constant-position error, mutually executed cases only; negative favors method.",
            paired_tie_tolerance_mm=1e-6,
            selection="Past noisy positions only; identical reference entry candidates. Current full-path clearance is screened first; the predicted policy additionally screens the finite inserted capsule over predicted exclusion movement. Future truth is evaluated after selection.",
            exclusion_motion="Current affine geometry anchored at the planning instant; target forecast changes divided by its reference height weight transfer movement to declared exclusions. Absolute target forecast bias is not transferred to the anchor.",
            policy_comparison="Compare within each method and case. All-case arrival-hit-and-clear counts retain failures and abstentions; conditional violation rates alone cannot establish improvement.",
            uncertainty="Empirical joint 3D noisy-observation residual ball from completed past forecast windows, ranked at ceil((n+1)*nominal coverage). Shared rolling histories are dependent; no formal coverage guarantee or latent-position calibration is claimed.",
            uncertainty_probe="First actual observation-grid timestamp at or after the requested look-ahead. All methods and policies share that prospective query; observed and simulated-truth coverage are scored separately after calibration. Diagnostics never alter route admission or ranking.",
            uncertainty_count="Availability uses attempted cases, deduplicated across exclusion policies. Coverage and radius statistics use unique probes identified by model identity, observation seed, noise level, past-prefix checksum and future query; execution-factor repetitions count once. Seeded profiles can remain correlated, so unique probes are not independent patients or coverage experiments.",
            population="Controlled scenarios on one reference anatomy; correlated repetitions, not independent patients or clinical outcomes.",
            limitations="Shared affine simulator; regular breathing matches the sinusoidal model. Predicted exclusion motion assumes the same height-weighted field; numerical screening is not continuous clearance proof. Observation-error regions are empirical diagnostics, not calibrated latent-target probabilities or planner constraints."))
    manifest["protocol_id"] = sha256(_benchmark_json(manifest).encode("utf-8")).hexdigest()
    rows, model_cache, observation_cache, fit_cache, uncertainty_cache = [], {}, {}, {}, {}
    total = len(cases)*len(BASELINE_METHODS)*len(policies)
    for case in cases:
        check_cancelled()
        model_key = (case["pattern"], case["profile_seed"])
        if model_key not in model_cache:
            model_cache[model_key] = RespiratoryModel(BreathingSettings(settings.amplitude_mm, settings.rate_bpm,
                case["pattern"], case["profile_seed"]))
        model = model_cache[model_key]
        identity = respiratory_model_id(model)
        observation_key = (*model_key, case["origin_s"], case["noise_std_mm"], case["observation_seed"])
        if observation_key not in observation_cache:
            data = generate_target_observations(target, model, deformation,
                ObservationSettings(settings.observation_rate_hz, case["noise_std_mm"], case["observation_seed"]),
                through_s=case["origin_s"])
            times, positions = data.observations_through(case["origin_s"])
            digest = sha256(np.asarray(times, dtype="<f8").tobytes()+np.asarray(positions, dtype="<f8").tobytes()).hexdigest()
            observation_cache[observation_key] = times, positions, digest
        times, positions, observation_digest = observation_cache[observation_key]
        matrix = deformation.matrix(model.position(case["origin_s"]))
        for method, policy in product(BASELINE_METHODS, policies):
            check_cancelled()
            row = dict(case, method=method, exclusion_policy=policy, status="fit_unavailable", reason="", model_id=identity,
                observation_prefix_sha256=observation_digest, observation_count=len(times),
                last_observation_s=float(times[-1]), fit_n_samples=None, fitted_frequency_hz=None,
                candidate_entries_sha256=candidate_digest, candidate_count=len(candidates), eligible_count=0,
                exclusions_declared=bool(regions),
                chosen_candidate_index=None, entry_lps_mm=None, endpoint_lps_mm=None,
                prediction_time_s=None, arrival_s=None, horizon_s=None, path_length_mm=None,
                planning_clearance_lower_bound_mm=None, intercept_residual_mm=None,
                predicted_clearance_lower_bound_mm=None, predicted_clearance_time_s=None, predicted_first_violation_s=None,
                predicted_screening_reason="",
                arrival_tip_error_mm=None, min_tip_error_mm=None, arrival_tip_normalized_distance=None,
                arrival_tip_centre_inside_target=None, first_tip_hit_s=None, first_shaft_hit_s=None,
                min_execution_clearance_lower_bound_mm=None, first_constraint_violation_s=None,
                constraint_violated=None, arrival_hit_clear=None)
            fit_key = (*observation_key, method)
            if fit_key not in fit_cache:
                try:
                    fit_cache[fit_key] = fit_baseline(times, positions, method, origin_s=case["origin_s"], settings=forecast)
                except ValueError as error:
                    fit_cache[fit_key] = str(error)
            fit = fit_cache[fit_key]
            check_cancelled()
            if fit_key not in uncertainty_cache:
                uncertainty_cache[fit_key] = _benchmark_uncertainty_audit(settings, model, target, deformation,
                    times, positions, case, method, cancelled)
            row.update(uncertainty_cache[fit_key])
            check_cancelled()
            if isinstance(fit, str):
                row["reason"] = fit
            else:
                row.update(fit_n_samples=fit.n_samples, fitted_frequency_hz=fit.frequency_hz)
                insertion = NeedleSettings(radius, case["speed_mm_s"], case["delay_s"])
                selection = select_forecast_route(volume, lung_mask, target, entry, matrix, fit, insertion,
                    regions, route_settings, available_until_s=model.duration, exclusion_policy=policy, deformation=deformation,
                    cancelled=cancelled)
                check_cancelled()
                row["eligible_count"] = sum(item["status"] == "eligible" for item in selection.rows)
                if selection.chosen_index is None:
                    row.update(status="abstained", reason="; ".join(dict.fromkeys(item["reason"] for item in selection.rows)))
                else:
                    selected = selection.rows[selection.chosen_index]
                    row.update(chosen_candidate_index=selection.chosen_index+1, entry_lps_mm=selected["entry_lps_mm"],
                        endpoint_lps_mm=selected["endpoint_lps_mm"], prediction_time_s=selected["prediction_time_s"],
                        arrival_s=selected["arrival_s"], horizon_s=selected["horizon_s"], path_length_mm=selected["length_mm"],
                        planning_clearance_lower_bound_mm=selected["clearance_lower_bound_mm"],
                        intercept_residual_mm=selected["intercept_residual_mm"],
                        predicted_clearance_lower_bound_mm=selected["predicted_clearance_lower_bound_mm"],
                        predicted_clearance_time_s=selected["predicted_clearance_time_s"],
                        predicted_first_violation_s=selected["predicted_first_violation_s"],
                        predicted_screening_reason=selected["predicted_screening_reason"])
                    plan = create_forecast_needle_plan(selection, identity, deformation)
                    try:
                        evaluation = evaluate_needle(plan, model)
                        check_cancelled()
                        constraints = (evaluate_needle_constraints(plan, model, regions, clearance_mm=route_settings.clearance_mm)
                                       if regions else None)
                        check_cancelled()
                    except ValueError as error:
                        row.update(status="execution_failed", reason=str(error))
                    else:
                        hit = bool(evaluation.tip_normalized_distance[-1] <= 1.+1e-9)
                        violated = bool(constraints.violated) if constraints is not None else None
                        row.update(status="executed", reason="Causal route selected; simulated execution evaluated separately.",
                            arrival_tip_error_mm=evaluation.arrival_tip_error_mm, min_tip_error_mm=evaluation.min_tip_error_mm,
                            arrival_tip_normalized_distance=float(evaluation.tip_normalized_distance[-1]),
                            arrival_tip_centre_inside_target=hit, first_tip_hit_s=evaluation.first_tip_hit_s,
                            first_shaft_hit_s=evaluation.first_shaft_hit_s,
                            min_execution_clearance_lower_bound_mm=constraints.min_clearance_lower_bound_mm if constraints else None,
                            first_constraint_violation_s=constraints.first_violation_s if constraints else None,
                            constraint_violated=violated, arrival_hit_clear=bool(hit and not violated) if constraints else None)
            rows.append(row)
            if progress is not None:
                progress(len(rows), total)
    check_cancelled()
    summaries, paired = _planning_benchmark_summaries(rows)
    return PlanningBenchmarkResult(settings, _benchmark_json(manifest), _benchmark_json(rows),
                                   _benchmark_json(summaries), _benchmark_json(paired))


class PackedMasks:
    def __init__(self, masks):
        self.masks = dict(masks)
        self.groups = []
        shape = None
        for name, mask in self.masks.items():
            if (not isinstance(mask, np.ndarray) or mask.dtype != bool
                    or mask.ndim != 3 or 0 in mask.shape):
                raise ValueError("Packed display masks must be boolean 3D arrays.")
            if shape is not None and mask.shape != shape:
                raise ValueError("Packed display masks must share one source grid.")
            shape = mask.shape
        entries = list(self.masks.items())
        for start in range(0, len(entries), 8):
            group = entries[start:start + 8]
            packed = np.zeros(shape, dtype=np.uint8)
            bits = {}
            for index, (name, mask) in enumerate(group):
                bit = 1 << index
                np.bitwise_or(packed, bit, out=packed, where=mask)
                bits[name] = bit
            self.groups.append((packed, bits))

    def matches(self, masks):
        return (tuple(masks) == tuple(self.masks)
                and all(mask is self.masks[name] for name, mask in masks.items()))

    def sample(self, sampler, masks=None):
        selected = self.masks if masks is None else masks
        if any(name not in self.masks or mask is not self.masks[name]
               for name, mask in selected.items()):
            raise ValueError("Packed display masks no longer match the source masks.")
        images = {}
        for data, bits in self.groups:
            requested = {name: bit for name, bit in bits.items() if name in selected}
            if requested:
                # nearest-neighbour sampling preserves each overlapping binary layer.
                labels = np.asarray(sampler(data), dtype=np.uint8)
                images.update({name: (labels & bit) != 0 for name, bit in requested.items()})
        return {name: images[name] for name in selected}


def respiratory_slice(volume, name, crosshair, deformation, displacement, *, masks=None, max_pixels=256,
                      packed_masks=None, bounds=None):
    """sample CT and nearest-neighbour labels on one shared deformed world grid."""
    plane = volume.slice_grid(name, crosshair, max_pixels=max_pixels, bounds=bounds)
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
    for mask in (masks or {}).values():
        if np.asarray(mask).shape != volume.shape:
            raise ValueError("Motion preview masks must match the CT geometry.")
    images = (packed_masks.sample(lambda data: sample(data, 0, 0.), masks or {})
              if packed_masks is not None else
              {role: sample(mask, 0, 0.) for role, mask in (masks or {}).items()})
    overlays = {role: replace(plane, image=image) for role, image in images.items()}
    return replace(plane, image=image), overlays


def extract_airways(volume, seed_lps):
    import SimpleITK as sitk

    seed = np.asarray(seed_lps, dtype=float)
    if seed.shape != (3,) or not np.isfinite(seed).all():
        raise ValueError("The tracheal seed must contain three finite LPS coordinates.")
    continuous = volume.world_to_index(seed)
    limits = np.asarray(volume.shape[::-1]) - 1
    if np.any(continuous < 0) or np.any(continuous > limits):
        raise ValueError("The tracheal seed is outside the CT volume.")
    index = np.rint(continuous).astype(int)
    seed_zyx = tuple(index[::-1])
    intensity = float(volume.data[seed_zyx])
    lower_seed_hu,upper_seed_hu=AIRWAY_SEED_HU_RANGE
    if not lower_seed_hu <= intensity <= upper_seed_hu:
        raise ValueError("Place the seed inside the air-filled centre of the trachea (-1100 to -850 HU).")

    # reject broad parenchymal or exterior air before starting three-dimensional growth.
    superior_xyz_axis = int(np.argmax(np.abs(volume.direction[2])))
    superior_array_axis = 2 - superior_xyz_axis
    transverse_axes = tuple(axis for axis in range(3) if axis != superior_array_axis)
    plane = np.take(volume.data, index[superior_xyz_axis], axis=superior_array_axis)
    plane_air = (plane >= lower_seed_hu) & (plane <= upper_seed_hu)
    labels, _ = ndimage.label(plane_air)
    plane_seed = tuple(seed_zyx[axis] for axis in transverse_axes)
    section = labels == labels[plane_seed]
    points = np.argwhere(section)
    plane_spacing = np.asarray(volume.spacing[::-1])[list(transverse_axes)]
    pixel_area = float(np.prod(plane_spacing))
    area = len(points) * pixel_area
    diameter = (np.ptp(points, axis=0) + 1) * plane_spacing
    if (area < 5 or area > 700 or diameter.max() > 40
            or section[0].any() or section[-1].any()
            or section[:, 0].any() or section[:, -1].any()):
        raise ValueError("The seed does not lie in a bounded tracheal air space. Choose its centre above the carina.")

    image = _to_sitk(volume)
    voxel_ml = float(np.prod(volume.spacing) / 1000)
    accepted = None
    accepted_count = 0
    accepted_threshold = None
    stopped = False
    start = max(-980, int(np.ceil(intensity / 5) * 5))

    def grow(threshold):
        result = sitk.ConnectedThreshold(image, [tuple(int(value) for value in index)],
                                         -1100, float(threshold), 1,
                                         sitk.ConnectedThresholdImageFilter.FaceConnectivity)
        mask = sitk.GetArrayFromImage(result).astype(bool)
        count = int(np.count_nonzero(mask))
        excessive = (count * voxel_ml > 100
                     or mask.sum(axis=transverse_axes).max() * pixel_area > 1200
                     or any(np.take(mask, boundary, axis=axis).any()
                            for axis in transverse_axes for boundary in (0, -1)))
        if accepted_count:
            excessive |= (count > 2 * accepted_count
                          and (count - accepted_count) * voxel_ml > 10)
        return mask, count, bool(excessive)

    # stop before a narrow connection admits a large lung region; refine that boundary by one HU.
    for threshold in range(start, -699, 5):
        mask, count, excessive = grow(threshold)
        if excessive:
            stopped = True
            if accepted_threshold is not None:
                for refined in range(accepted_threshold + 1, threshold):
                    candidate, candidate_count, excessive = grow(refined)
                    if excessive:
                        break
                    accepted, accepted_count, accepted_threshold = candidate, candidate_count, refined
            break
        accepted, accepted_count, accepted_threshold = mask, count, threshold
    if accepted is None or accepted_count * voxel_ml < 2:
        raise ValueError("A supported central airway could not be extracted from this seed. Choose another point in the trachea.")
    indices = np.argwhere(accepted)
    physical = volume.index_to_world(indices[:, ::-1])
    if np.ptp(physical[:, 2]) < 35:
        raise ValueError("The extracted air space is too short to identify central airways. Choose a tracheal seed above the carina.")
    metadata = {
        "method": "seeded connected threshold with physical leakage guards",
        "model": "adaptive connected threshold",
        "model_version": "1",
        "source_kind": "automated",
        "algorithm_version": 1,
        "seed_lps": [float(value) for value in seed],
        "seed_index_xyz": [int(value) for value in index],
        "lower_threshold_hu": -1100,
        "threshold_hu": int(accepted_threshold),
        "voxel_count": accepted_count,
        "volume_ml": accepted_count * voxel_ml,
        "leakage_guard_reached": stopped,
        "expert_reviewed": False,
        "scope": "central airways; distal branches may be incomplete",
    }
    return accepted, metadata


if __name__ == "__main__":
    import sys
    sys.modules["motiontwin"] = sys.modules[__name__]
    from run import main
    raise SystemExit(main())
