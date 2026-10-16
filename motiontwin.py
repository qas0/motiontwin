"""CT loading, physical reslicing and lung display geometry.

The desktop viewer is in run.py. Prediction, planning, simulation and
research stages have been removed pending separate implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from pathlib import Path
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4
import json
import os
import shutil

import numpy as np
from scipy import ndimage
from scipy.ndimage import map_coordinates

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
    name: str = "CT volume"

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
        raise ValueError("Select a 3D scalar CT image. This viewer supports static scans.")
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



def prepare_display_meshes(volume, masks, *, max_cells=40000):
    """Prepare bounded CT-linked surfaces without modifying volume or masks.

    The retained smoothing and CT colour sampling are display operations.
    Source scan values, physical geometry and mask arrays stay unchanged.
    """
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
                               "Check the connection or import a local CT volume.") from error
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


if __name__ == "__main__":
    import sys
    sys.modules["motiontwin"] = sys.modules[__name__]
    from run import main
    raise SystemExit(main())
