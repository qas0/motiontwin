from __future__ import annotations

from dataclasses import dataclass, field, replace
from collections import OrderedDict
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
import re
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


class CTSequence:
    def __init__(self, name, phases, sources, segments, manifest, signature, *,
                 max_cached_phases=2, max_cache_bytes=512 * 1024 ** 2):
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
            meshes = prepare_display_meshes(volume, masks)
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


def load_ct_sequence(path, *, max_cached_phases=2, max_cache_bytes=512 * 1024 ** 2):
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
                          max_cached_phases=max_cached_phases, max_cache_bytes=max_cache_bytes)
    return sequence



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
                      packed_masks=None):
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
