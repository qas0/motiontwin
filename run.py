"""Run MotionTwin, including VS Code's Run Python File action.

This file contains the desktop interface, linked CT/3D renderers and CLI.
The scientific algorithms are in motiontwin.py.
"""
from __future__ import annotations

# Select the local interpreter before importing any GUI/scientific dependencies.
if __name__=="__main__":
    from pathlib import Path
    import os
    import subprocess
    import sys
    project=Path(__file__).resolve().parent
    interpreter=project/".venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if interpreter.is_file() and Path(sys.executable).resolve()!=interpreter.resolve():
        raise SystemExit(subprocess.call([str(interpreter),str(Path(__file__).resolve()),*sys.argv[1:]],cwd=project))
    os.chdir(project)


# ============================================================================
# interface / workstation_theme
# ============================================================================

"""Shared desktop styling for the imaging workstation."""

STYLE = """
QMainWindow, QWidget { background:#10151d; color:#d9e1e9; font-family:'Segoe UI'; font-size:12px; }
QWidget#studyStrip { background:#142136; border-bottom:1px solid #2b3f59; }
QWidget#navigationStrip { background:#151d29; border-bottom:1px solid #2b3748; }
QLabel#brand { font-size:22px; font-weight:650; color:#f0f6fb; background:transparent; }
QLabel#studySubtitle { font-size:10px; color:#9bb0c6; background:transparent; }
QLabel#studyMetadata { color:#aebfd0; font-size:11px; background:transparent; }
QLabel#badge { color:#76dde2; background:#173b46; border:1px solid #285464; border-radius:3px; padding:5px 8px; font-size:10px; font-weight:650; }
QLabel#researchBadge { color:#92a7bd; font-size:10px; background:transparent; }
QLabel#statusLine { color:#a7b8c9; font-size:11px; padding:1px 2px; }
QWidget#viewportPanel { background:#05080d; border:1px solid #364555; }
QWidget#viewportToolbar { background:#1d2a3d; border-bottom:2px solid #7091b7; }
QWidget#viewportToolbar QLabel { background:transparent; font-size:10px; color:#c9d8e8; font-weight:600; }
QWidget#phaseStrip { background:#151e2b; border:1px solid #2e3c4e; }
QWidget#analysisPanel { background:#151d28; }
QLabel#panelTitle { color:#b9cfdd; font-size:11px; font-weight:650; padding:7px 0 5px 0; }
QLabel#metricName { color:#92a7ba; font-size:10px; }
QLabel#metric { font-size:13px; color:#b5e5ec; padding:0 0 6px 0; }
QPushButton, QToolButton { background:#26354a; border:1px solid #3c4e66; padding:6px 9px; border-radius:3px; }
QPushButton:hover, QToolButton:hover { background:#354c65; border-color:#6888a6; }
QPushButton:pressed, QToolButton:pressed { background:#182e42; }
QPushButton:disabled, QToolButton:disabled { color:#64778d; background:#1a2533; }
QPushButton#primary { background:#1d6074; border:1px solid #3c8a9e; color:#effcff; }
QToolButton:checked { color:#8de8ef; background:#1e4354; border-color:#4f91a3; }
QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit { background:#0d141f; border:1px solid #354359; padding:5px; border-radius:3px; selection-background-color:#285a75; }
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color:#5f7b97; }
QComboBox::drop-down { width:18px; border:0; }
QComboBox QAbstractItemView { background:#172334; selection-background-color:#2e526c; }
QTabWidget::pane { border:1px solid #2e3d50; background:#151d28; }
QTabBar::tab { padding:8px 8px; background:#192332; border-bottom:2px solid transparent; color:#9fb2c5; }
QTabBar::tab:selected { color:#9de4ed; background:#223247; border-bottom:2px solid #61c8d8; }
QTabBar::tab:hover { color:#d2e7f5; background:#27394f; }
QGroupBox { border:1px solid #314053; border-radius:3px; margin-top:11px; padding-top:13px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; color:#b1c4d7; }
QCheckBox { spacing:7px; padding:2px 0; }
QCheckBox::indicator { width:13px; height:13px; border:1px solid #60768d; border-radius:2px; background:#101a28; }
QCheckBox::indicator:checked { background:#54b9c9; border:1px solid #8cdeea; }
QSlider::groove:horizontal { height:3px; background:#34465d; border-radius:1px; }
QSlider::sub-page:horizontal { background:#4e90a8; }
QSlider::handle:horizontal { width:10px; margin:-5px 0; border-radius:3px; background:#8ccbdc; }
QScrollArea { border:0; background:#151d28; }
QScrollBar:vertical { width:8px; background:#111a26; margin:0; }
QScrollBar::handle:vertical { min-height:28px; background:#3a4d63; border-radius:3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSplitter::handle { background:#253347; }
QToolTip { background:#263b52; color:#f0f7fb; border:1px solid #5e7c99; padding:4px; }
"""


# ============================================================================
# interface / scan_reconstruction
# ============================================================================

"""HU-driven 3D CT reconstruction, with a physical coronal cut surface.

The GPU ray caster receives scalar CT data, never a painted anatomy image.
For synthetic respiration a bounded display grid samples the very same
moving-tissue/fixed-wall composition as the diagnostic slice views.  Display
decimation changes rendering resolution only; planning and CT slices retain
their source resolution.  No new anatomical structures are invented here.
"""



from time import perf_counter

import numpy as np
import pyvista as pv
from scipy.ndimage import map_coordinates
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction, vtkPlane
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction, vtkVolume, vtkVolumeProperty
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkOpenGLGPUVolumeRayCastMapper

from motiontwin import SyntheticSliceSource
from motiontwin import Volume


DISPLAY_LIMITS = {"Interactive": 150_000, "Balanced": 700_000, "High": 1_500_000}
STATIC_DISPLAY_LIMITS = {"Interactive": 1_200_000, "Balanced": 3_000_000, "High": 8_000_000}
STYLES = ("CT reconstruction", "Lung detail")


def display_stride(shape, quality):
    """Integer source stride bounds memory while retaining physical coordinates."""
    if quality not in DISPLAY_LIMITS:
        raise ValueError("CT quality must be Interactive, Balanced or High.")
    stride = 1
    while np.prod((np.asarray(shape) + stride - 1) // stride) > DISPLAY_LIMITS[quality]:
        stride += 1
    return stride


def static_display_strides(shape, spacing, quality):
    """XYZ strides balance physical resolution under a static-image memory cap.

    Thin in-plane CT pixels must be decimated before thick source slices. A
    uniform index stride would turn a 2.5 mm slice gap into 10 mm while still
    oversampling the transverse plane. Static scans can retain larger GPU
    textures because no full 3D respiratory resampling occurs each frame.
    """
    if quality not in STATIC_DISPLAY_LIMITS:
        raise ValueError("CT quality must be Interactive, Balanced or High.")
    dimensions = np.asarray(shape, dtype=np.int64)[::-1]
    spacing = np.asarray(spacing, dtype=float)
    if (dimensions.shape != (3,) or np.any(dimensions < 1)
            or spacing.shape != (3,) or not np.all(np.isfinite(spacing))
            or np.any(spacing <= 0)):
        raise ValueError("CT display geometry requires positive ZYX dimensions and XYZ spacing.")
    strides = np.ones(3, dtype=np.int64)
    counts = dimensions.copy()
    while np.prod(counts) > STATIC_DISPLAY_LIMITS[quality]:
        effective = np.where(counts > 1, spacing * strides, np.inf)
        axis = int(np.argmin(effective))
        strides[axis] += 1
        counts = (dimensions + strides - 1) // strides
    return tuple(int(value) for value in strides)


def ct_cutface_rgba(hu):
    """A lightly tinted CT lung window; air remains transparent at the field edge."""
    hu = np.asarray(hu, dtype=float)
    intensity = np.clip((hu + 1250.) / 1500., 0, 1)
    # This is an explicitly presented CT colour map, not segmented tissue colour.
    cold = np.array([.81, .94, .94])
    warm = np.array([1., .89, .81])
    weight = np.clip((hu + 350.) / 500., 0, 1)[..., None]
    tint = cold * (1 - weight) + warm * weight
    rgb = np.clip(intensity[..., None] * tint * 255, 0, 255)
    # A partial tissue cut surface leaves depth and vessels behind it visible.
    alpha = np.where(hu < -400., 142., np.where(hu > 350., 92., 54.))
    alpha = np.where(hu > -985., alpha, 0.)
    return np.concatenate((rgb, alpha[..., None]), axis=-1).astype(np.uint8)


class ScanReconstruction:
    """Small renderer adapter owned by a SceneViewer.

    All setters defer rendering to the scene.  ``update`` returns True only
    when scalar data changed.  At most one displayed frame is retained, so
    arbitrary respiratory timestamps cannot grow a volume cache.
    """

    def __init__(self, quality="Balanced", style="CT reconstruction"):
        if quality not in DISPLAY_LIMITS:
            raise ValueError("Unknown CT reconstruction quality.")
        if style not in STYLES:
            raise ValueError("Unknown CT reconstruction style.")
        self.quality, self.style = quality, style
        self.plotter = self.volume = self.anatomy = self.source = None
        self.actor = self.mapper = self.grid = None
        self.cut_actor = self.cut_mesh = None
        self._cut_plane = vtkPlane()
        self._cut_plane.SetNormal(0., 1., 0.)
        self.cutaway_enabled = False
        self.visible = True
        self.opacity = .7
        self.frame_time_ms = 0.
        self.display_spacing = None
        self._last_displacement = None
        self._displacement = np.zeros(3)
        self._structure_visibility = {"ribs": False, "body": False}
        self.masks = {}
        self._organ_mask = None

    def attach(self, plotter, volume, anatomy=None, masks=None):
        self.detach()
        self.plotter, self.volume, self.anatomy = plotter, volume, anatomy
        self.source = SyntheticSliceSource(anatomy) if anatomy is not None else None
        self._displacement = np.zeros(3)
        self.masks = (anatomy.masks if anatomy is not None else masks) or {}
        if any(np.asarray(mask).shape != volume.shape for mask in self.masks.values()):
            raise ValueError("CT reconstruction masks must match the source image geometry.")
        organ_masks = [mask for name, mask in self.masks.items()
                       if name not in ("body", "ribs")]
        self._organ_mask = (np.logical_or.reduce(organ_masks) if organ_masks else None)
        self._cut_plane.SetOrigin(*volume.center)
        self._build_grid()
        self.mapper = vtkOpenGLGPUVolumeRayCastMapper()
        self.mapper.SetInputData(self.grid)
        self.mapper.SetBlendModeToComposite()
        self.mapper.SetAutoAdjustSampleDistances(False)
        self.mapper.SetSampleDistance(min(self.display_spacing) * .65)
        self.actor = vtkVolume()
        self.actor.SetMapper(self.mapper)
        prop = vtkVolumeProperty()
        prop.SetInterpolationTypeToLinear()
        prop.ShadeOn()
        prop.SetAmbient(.34)
        prop.SetDiffuse(.64)
        prop.SetSpecular(.16)
        prop.SetSpecularPower(18.)
        # Opacity is defined per 4 mm, independent of the display grid stride.
        prop.SetScalarOpacityUnitDistance(4.)
        self.actor.SetProperty(prop)
        self.plotter.add_actor(self.actor, name="ct_reconstruction", reset_camera=False,
                               render=False)
        self._apply_style()
        self._make_cutface()
        self.set_cutaway(self.cutaway_enabled)
        self.set_visible(self.visible)
        return self

    def detach(self):
        if self.plotter is not None:
            for actor in (self.actor, self.cut_actor):
                if actor is not None:
                    self.plotter.remove_actor(actor, render=False)
        self.actor = self.mapper = self.grid = self.cut_actor = self.cut_mesh = None
        self.plotter = self.volume = self.anatomy = self.source = None
        self.masks = {}
        self._organ_mask = None
        self._last_displacement = None

    def _build_grid(self):
        if self.source is None:
            self.stride_xyz = static_display_strides(
                self.volume.shape, self.volume.spacing, self.quality)
            # ``stride`` remains available for legacy diagnostics; imported
            # scans must use ``stride_xyz`` for physical indexing.
            self.stride = max(self.stride_xyz)
        else:
            self.stride = display_stride(self.volume.shape, self.quality)
            self.stride_xyz = (self.stride,) * 3
        self._display_slices = tuple(slice(None, None, stride)
                                     for stride in self.stride_xyz[::-1])
        data = np.asarray(self.volume.data[self._display_slices], dtype=np.float32).copy()
        self.display_spacing = tuple(np.asarray(self.volume.spacing) * self.stride_xyz)
        self.grid = pv.ImageData(dimensions=data.shape[::-1], spacing=self.display_spacing,
                                 origin=self.volume.origin,
                                 direction_matrix=self.volume.direction)
        self.grid.point_data["HU"] = data.ravel()
        self.grid.set_active_scalars("HU")
        self._raw_data = data.ravel().copy()
        self._moving_display = None
        self._display_volume = Volume(data, self.display_spacing, self.volume.origin,
                                      self.volume.direction, self.volume.name)
        # Imported/static scans never need a full coordinate grid. Synthetic
        # deformation retains integer source nodes, avoiding float world grids.
        self._nodes = (None if self.source is None else
                       np.indices(data.shape, dtype=np.int32)[::-1]
                       .reshape(3, -1).T.copy() * self.stride)
        if self.source is not None and np.array_equal(self.volume.direction, np.eye(3)):
            step = self.stride
            self._fixed_display = self.anatomy._fixed_ct[::step, ::step, ::step].copy()
            self._rib_display = self.anatomy.masks["ribs"][::step, ::step, ::step]
            self._reference_display = data.copy()
            self._moving_display = self.source.moving[::step, ::step, ::step].ravel()
            self._x_nodes = np.arange(data.shape[2], dtype=np.float32)[None, None, :] * step
            self._y_nodes = np.arange(data.shape[1], dtype=np.float32)[None, :, None] * step
        self._last_displacement = None
        self._apply_gates()

    def _apply_style(self):
        if self.actor is None:
            return
        colours = vtkColorTransferFunction()
        colours.AddRGBPoint(-1000., .005, .009, .012)
        colours.AddRGBPoint(-900., .23, .36, .36)
        colours.AddRGBPoint(-830., .46, .60, .58)
        colours.AddRGBPoint(-710., .60, .69, .65)
        colours.AddRGBPoint(-350., .52, .55, .50)
        colours.AddRGBPoint(-100., .69, .52, .42)
        colours.AddRGBPoint(45., .76, .49, .37)
        colours.AddRGBPoint(140., .86, .73, .62)
        colours.AddRGBPoint(450., .92, .83, .69)
        colours.AddRGBPoint(1000., 1., .93, .82)
        opacity = vtkPiecewiseFunction()
        # Lung is predominantly air. Its integrated opacity should retain
        # textured tissue depth while allowing intrapulmonary vessels to read
        # through it, rather than building an opaque pair of grey balloons.
        lung = .018 if self.style == "CT reconstruction" else .009
        tissue = .0018 if self.style == "CT reconstruction" else .0003
        bone = .004 if self.style == "CT reconstruction" else .0007
        for hu, value in ((-1000, 0), (-960, 0), (-900, lung * .2),
                          (-840, lung), (-740, lung * .65), (-450, .001),
                          (-150, .0004), (0, tissue), (55, tissue * 1.8),
                          (95, .15), (180, .25), (300, .018), (650, bone),
                          (1100, bone * 1.8)):
            opacity.AddPoint(float(hu), float(value * self.opacity))
        self.actor.GetProperty().SetColor(colours)
        self.actor.GetProperty().SetScalarOpacity(opacity)

    def set_style(self, style):
        if style not in STYLES:
            raise ValueError(f"CT style must be one of {STYLES}.")
        self.style = style
        self._apply_style()
        self._apply_visibility()

    def _synthetic_data(self, displacement):
        """Separable source coordinates avoid a large N by 3 temporary per frame."""
        if not np.array_equal(self.volume.direction, np.eye(3)):
            return self.source._ct_nodes(self._nodes, displacement)
        if not np.any(displacement):
            self._moving_display = self.source.moving[
                ::self.stride, ::self.stride, ::self.stride].ravel()
            return self._reference_display.ravel().copy()
        inverse_z, factors = self.source._depth_coordinates(displacement)
        inverse_z = inverse_z[::self.stride, None, None]
        factor = factors[::self.stride, None, None]
        coordinates = np.broadcast_arrays(inverse_z,
            (self._y_nodes - displacement[1] * factor / self.volume.spacing[1]).astype(np.float32),
            (self._x_nodes - displacement[0] * factor / self.volume.spacing[0]).astype(np.float32))
        moving = map_coordinates(self.source.moving, coordinates, order=0,
                                  mode="constant", cval=0, prefilter=False).astype(bool)
        self._moving_display = moving.ravel()
        data = self._fixed_display.copy()
        data[moving] = map_coordinates(self.volume.data,
            [component[moving] for component in coordinates], order=1,
            mode="constant", cval=-1000., prefilter=False)
        data[self._rib_display] = self._reference_display[self._rib_display]
        return data.ravel()

    def set_opacity(self, value):
        if not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("CT opacity must be between zero and one.")
        self.opacity = float(value)
        self._apply_style()
        self._apply_visibility()

    def set_structure_visibility(self, name, visible):
        """Suppress a segmented structure in the 3D volume only.

        The unmodified scalar CT is retained for the cut surface and slices.
        For static scans with lung masks but no body mask, ``body=False``
        isolates those lung masks and other supplied visible structures.
        ``body=True`` restores the original CT context. Without any such
        segmentations an imported scan is left intact.
        """
        self._structure_visibility[name] = bool(visible)
        if self.grid is not None:
            self._apply_gates()
            if self.cut_actor is not None and self.cut_actor.GetVisibility():
                self._update_cutface()

    @property
    def suppressed_structures(self):
        return tuple(name for name, visible in self._structure_visibility.items()
                     if not visible and name in self.masks)

    @property
    def isolated_lung_context(self):
        """Whether static ray casting excludes voxels outside known lung masks."""
        return (self.source is None and "body" not in self.masks
                and not self._structure_visibility.get("body", False)
                and any("lung" in name for name in self.masks))

    def _mask_at_display(self, name, coordinates=None):
        mask = self.masks[name]
        if self.source is None or name in ("body", "ribs") or not np.any(self._displacement):
            return np.asarray(mask)[self._display_slices].ravel().astype(bool)
        if coordinates is None:
            coordinates = self.source._source_indices(self._nodes, self._displacement)
        return self.source._sample(mask, coordinates, 0, 0) > 0

    def _apply_gates(self):
        if self.grid is None:
            return
        data = self._raw_data.copy()
        coordinates = None
        suppressed = self.suppressed_structures
        if self.isolated_lung_context:
            # Public/imported CT can have lung masks without a chest-wall
            # segmentation. Isolating their known display regions is an
            # explicit context operation; it does not invent a body mask or
            # alter source HU values. Preserve other supplied visible roles.
            kept_names = [name for name in self.masks
                          if name != "body" and ("lung" in name or
                             self._structure_visibility.get(name, name != "ribs"))]
            keep = np.logical_or.reduce([self._mask_at_display(name)
                                         for name in kept_names])
            data[~keep] = -1000.
        if self.source is not None and np.any(self._displacement) and any(
                name not in ("body", "ribs") or
                (name == "body" and self._moving_display is None)
                for name in suppressed):
            coordinates = self.source._source_indices(self._nodes, self._displacement)
        for name in suppressed:
            mask = self._mask_at_display(name, coordinates)
            if name == "body":
                # A body mask encloses organs; suppress only the chest-wall tissue.
                if self._organ_mask is not None:
                    if self.source is not None and self._moving_display is not None:
                        organs = self._moving_display
                    elif coordinates is None:
                        organs = self._organ_mask[self._display_slices].ravel()
                    else:
                        organs = self.source._sample(self._organ_mask, coordinates, 0, 0) > 0
                    mask &= ~organs
                if "ribs" in self.masks:
                    mask &= ~self._mask_at_display("ribs", coordinates)
            elif "lung" in name:
                # Lung envelopes may be hidden independently of internal vessels.
                mask &= (data < -400.) & (data > -960.)
            data[mask] = -1000.
        self.grid.point_data["HU"][:] = data
        self.grid.GetPointData().GetScalars().Modified()

    def set_quality(self, quality):
        if quality not in DISPLAY_LIMITS:
            raise ValueError("Unknown CT reconstruction quality.")
        if quality == self.quality:
            return
        self.quality = quality
        if self.volume is None:
            return
        self._build_grid()
        self.mapper.SetInputData(self.grid)
        self.mapper.SetSampleDistance(min(self.display_spacing) * .65)
        self._make_cutface()
        self.update(self._displacement)

    def _make_cutface(self):
        if self.cut_actor is not None:
            self.plotter.remove_actor(self.cut_actor, render=False)
        origin = self._cut_plane.GetOrigin()
        # Cut faces use the diagnostic source lattice, independently of the
        # ray caster's coarsened grid. A coarse 3D grid must not turn a CT cut
        # into blocky rectangles or hide small source-image vessels.
        self._plane = self.volume.slice_grid("coronal", origin, max_pixels=384)
        points = self._plane.world_grid()
        rows, cols = self._plane.shape
        lower = np.arange((rows - 1) * cols).reshape(rows - 1, cols)[:, :-1].ravel()
        faces = np.column_stack((np.full(len(lower), 4), lower, lower + 1,
                                 lower + cols + 1, lower + cols))
        self.cut_mesh = pv.PolyData(points.reshape(-1, 3), faces.ravel())
        self.cut_mesh.point_data["CT window"] = np.zeros((rows * cols, 4), dtype=np.uint8)
        self.cut_actor = self.plotter.add_mesh(self.cut_mesh, scalars="CT window", rgba=True,
                                               lighting=False, interpolate_before_map=False,
                                               name="ct_cutface", reset_camera=False,
                                               render=False, show_scalar_bar=False)
        self._update_cutface()
        self._apply_visibility()

    def _update_cutface(self):
        if self.cut_mesh is None:
            return
        if self.source is not None:
            plane, mask_planes = self.source.slice_plane(
                "coronal", self._cut_plane.GetOrigin(), self._displacement,
                max_pixels=384, overlays=True)
            hu = plane.image.ravel()
            lung_masks = [section.image.ravel().astype(bool)
                          for name, section in mask_planes.items() if "lung" in name]
        else:
            hu = self.volume.sample_world(self.cut_mesh.points)
            lung_masks = []
            for name, mask in self.masks.items():
                if "lung" in name:
                    mask_volume = Volume(np.asarray(mask, dtype=np.uint8),
                                         self.volume.spacing, self.volume.origin,
                                         self.volume.direction)
                    lung_masks.append(mask_volume.sample_world(
                        self.cut_mesh.points, interpolation=0, cval=0) > 0)
        rgba = ct_cutface_rgba(hu)
        if lung_masks:
            # Present a physical section through lung tissue, not an opaque
            # whole-body slab that conceals the reconstruction behind it.
            rgba[~np.logical_or.reduce(lung_masks), 3] = 0
        for name in self.suppressed_structures:
            if name in ("body", "ribs"):
                continue
            if self.source is not None:
                mask = mask_planes[name].image.ravel().astype(bool)
            else:
                mask_volume = Volume(np.asarray(self.masks[name], dtype=np.uint8),
                                     self.volume.spacing, self.volume.origin,
                                     self.volume.direction)
                mask = mask_volume.sample_world(
                    self.cut_mesh.points, interpolation=0, cval=0) > 0
            if "lung" in name:
                mask &= (hu < -400.) & (hu > -960.)
            rgba[mask, 3] = 0
        self.cut_mesh.point_data["CT window"] = rgba

    def set_cutaway(self, enabled, position=None):
        self.cutaway_enabled = bool(enabled)
        if position is not None:
            position = np.asarray(position, dtype=float)
            if position.shape != (3,) or not np.all(np.isfinite(position)):
                raise ValueError("CT cutaway position must be a finite xyz point.")
            self._cut_plane.SetOrigin(*position)
        if self.mapper is not None:
            self.mapper.RemoveAllClippingPlanes()
            if self.cutaway_enabled:
                self.mapper.AddClippingPlane(self._cut_plane)
            if position is not None:
                self._make_cutface()
        self._apply_visibility()

    def set_visible(self, visible):
        self.visible = bool(visible)
        self._apply_visibility()

    def _apply_visibility(self):
        if self.actor is not None:
            self.actor.SetVisibility(self.visible and self.opacity > 0)
        if self.cut_actor is not None:
            show_cut = (self.visible and self.cutaway_enabled
                        and self.style == "CT reconstruction" and self.opacity > 0)
            if show_cut and not self.cut_actor.GetVisibility():
                self._update_cutface()
            self.cut_actor.SetVisibility(show_cut)
            self.cut_actor.GetProperty().SetOpacity(self.opacity)

    def update(self, displacement=(0., 0., 0.), quality=None):
        if quality is not None:
            self.set_quality(quality)
        if self.volume is None:
            return False
        displacement = np.asarray(displacement, dtype=float)
        if displacement.shape != (3,) or not np.all(np.isfinite(displacement)):
            raise ValueError("CT displacement must be a finite xyz vector.")
        if self.anatomy is not None:
            displacement = self.anatomy._displacement(displacement)
        if self._last_displacement is not None and np.array_equal(displacement, self._last_displacement):
            return False
        started = perf_counter()
        self._displacement = displacement.copy()
        if self.source is not None:
            data = self._synthetic_data(displacement)
            self._raw_data = data.copy()
            self._apply_gates()
            self._display_volume.data = data.reshape(self._display_volume.shape)
            if self.visible and self.cutaway_enabled and self.style == "CT reconstruction":
                self._update_cutface()
        self._last_displacement = displacement.copy()
        self.frame_time_ms = (perf_counter() - started) * 1000
        return True


# ============================================================================
# interface / scene_viewer
# ============================================================================

"""Physical-coordinate anatomy and finite needle overlays for the workstation."""

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from vtkmodules.vtkCommonDataModel import vtkPlane

from motiontwin import mesh_from_mask
from motiontwin import prepare_display_meshes, attach_ct_scalars



COLORS = {"body": "#779da7", "left_lung": "#79b5bf", "right_lung": "#8ec6cc",
          "lungs": "#83bac5", "ribs": "#e0d4bf", "airways": "#b4edf0",
          "vessels": "#bc6861", "vascular_display": "#cb766e",
          "obstacles": "#d87570", "target": "#ffbd60"}
QUALITY = {"Interactive": (16000, 160, 12, 0),
           "Balanced": (40000, 360, 20, 4),
           "High": (100000, 720, 32, 16)}


def _point(value, label):
    value = np.asarray(value, dtype=float)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError(f"{label} must be a finite xyz position in millimetres.")
    return value


def _vector_data(points, displacements, limit):
    points, displacements = np.asarray(points, dtype=float), np.asarray(displacements, dtype=float)
    if points.size == 0 and displacements.size == 0:
        return np.empty((0, 3)), np.empty((0, 3)), np.empty(0)
    if (points.ndim != 2 or points.shape[1] != 3 or points.shape != displacements.shape
            or not np.all(np.isfinite(points)) or not np.all(np.isfinite(displacements))):
        raise ValueError("Motion vectors require matching finite N by 3 physical-coordinate arrays.")
    selected = np.linspace(0, len(points) - 1, min(len(points), limit), dtype=int)
    vectors = displacements[selected]
    return points[selected], vectors, np.linalg.norm(vectors, axis=1)


def _needle_parts(entry, endpoint, fraction, resolution):
    """Keep every rendered shaft and cone point within the finite insertion depth."""
    entry, endpoint = _point(entry, "Needle entry"), _point(endpoint, "Needle endpoint")
    if not np.isfinite(fraction):
        raise ValueError("Needle progress must be finite.")
    delta = endpoint - entry
    length = float(np.linalg.norm(delta))
    inserted = float(np.clip(fraction, 0, 1)) * length
    if inserted <= 1e-6 or length <= 1e-6:
        return None
    direction = delta / length
    tip = entry + direction * inserted
    head_length = min(3., inserted)
    head = pv.Cone(center=tip - direction * head_length / 2, direction=direction,
                   height=head_length, radius=min(.8, head_length * .4), resolution=resolution)
    # The cone's centre lies behind the physical tip, rather than overhanging it.
    shaft_end = tip - direction * head_length
    shaft = None
    if inserted > head_length + 1e-6:
        shaft = pv.Line(entry, shaft_end).tube(radius=.8, n_sides=resolution, capping=True)
    return shaft, head, tip


def _uncertainty_surface(plan, resolution):
    covariance = np.asarray(plan.covariance, dtype=float)
    if covariance.shape != (3, 3) or not np.all(np.isfinite(covariance)):
        return None
    covariance = (covariance + covariance.T) / 2
    values, axes = np.linalg.eigh(covariance)
    if np.min(values) < -1e-8 or np.max(values) <= 1e-12:
        return None
    quantile = float(getattr(plan, "uncertainty_quantile", 7.8147279))
    if not np.isfinite(quantile) or quantile <= 0:
        return None
    sphere = pv.Sphere(radius=1., theta_resolution=resolution, phi_resolution=resolution)
    transform = axes @ np.diag(np.sqrt(np.maximum(values, 0) * quantile))
    sphere.points = sphere.points @ transform.T + _point(plan.prediction, "Prediction")
    return sphere


class SceneViewer(QtInteractor):
    def __init__(self, parent=None):
        super().__init__(parent, auto_update=False)
        self.set_background("#020405", top="#080e12")
        self.add_axes(xlabel="L", ylabel="P", zlabel="S", color="#b4cbd6")
        self.meshes, self.base_points, self.structure_actors = {}, {}, {}
        self._source_meshes = {}
        self.dynamic = {}
        self.anatomy = None
        self.vector_actor = None
        self._vector_title = None
        self._vector_range_upper = 20.
        self._vector_source = None
        self._last_state = None
        self._last_plan_key = None
        self._visibility = {"body": False, "ribs": False, "airways": False}
        self._overlay_visibility = {}
        self._highlighted = None
        self.lung_opacity = .35
        self.quality = "Balanced"
        self.style = "CT reconstruction"
        self.reference_volume = None
        self.source_label = "NO CT LOADED"
        self.scan = ScanReconstruction(quality=self.quality)
        self.cutaway_enabled = False
        self._cut_plane = vtkPlane()
        self._cut_plane.SetNormal(0., 1., 0.)
        self._scale_actors = []
        self.remove_all_lights()
        self.add_light(pv.Light(light_type="headlight", intensity=.65))
        self.add_light(pv.Light(position=(-.6, -.5, 1.), light_type="camera light", intensity=.55))
        self.add_light(pv.Light(position=(.8, .4, .6), light_type="camera light", intensity=.28))
        self.add_text("LPS  /  millimetres", position="upper_left", font_size=9,
                      color="#a8bcc7", name="coordinates")
        self.add_text("AMBER actual  ·  CYAN prediction / route\n"
                      "SILVER inserted needle  ·  VIOLET uncertainty",
                      position="lower_left", font_size=8, color="#afc2cd", name="legend")
        self.set_quality("Balanced", render=False)

    def set_style(self, name, render=True):
        if name not in ("CT reconstruction", "Lung motion", "Anatomy surfaces"):
            raise ValueError("Unknown 3D reconstruction style.")
        changed = name != self.style
        self.style = name
        self.scan.set_style("Lung detail" if name == "Lung motion" else "CT reconstruction")
        self.scan.set_visible(name == "CT reconstruction")
        if changed and self._source_meshes:
            camera = self.camera_position
            self._build_structures()
            if self._last_state is not None:
                self.update_state(**self._last_state, render=False)
            self.camera_position = camera
        self.set_source_label(self.source_label,render=False)
        if render:
            self.render()

    def set_source_label(self, label, render=True):
        """Keep exported 3D images attributable without the surrounding window."""
        self.source_label = str(label)
        self.add_text("LPS / mm  ·  " + self.style.upper() + "\n" + self.source_label,
                      position="upper_left", font_size=8, color="#98abb5",
                      name="coordinates", render=False)
        if render:
            self.render()

    def set_quality(self, name, render=True):
        if name not in QUALITY:
            raise ValueError("Scene quality must be Interactive, Balanced or High.")
        changed = name != self.quality
        self.quality = name
        self.scan.set_quality(name)
        if QUALITY[name][3]:
            self.enable_depth_peeling(number_of_peels=QUALITY[name][3], occlusion_ratio=.08)
        else:
            self.disable_depth_peeling()
        self.enable_anti_aliasing("fxaa")
        if changed and self._source_meshes:
            camera = self.camera_position
            self._build_structures()
            for actor in self.dynamic.values():
                self.remove_actor(actor, render=False)
            self.dynamic.clear()
            self._last_plan_key = None
            vector_source = self._vector_source
            self._clear_vectors()
            if self._last_state is not None:
                self.update_state(**self._last_state, render=False)
            if vector_source is not None and vector_source[2] == "supplied":
                self.supplied_vectors(vector_source[0], vector_source[1], render=False)
            self.camera_position = camera
        if render:
            self.render()

    def _build_structures(self):
        for actor in self.structure_actors.values():
            self.remove_actor(actor, render=False)
        self.meshes.clear()
        self.base_points.clear()
        self.structure_actors.clear()
        max_cells = QUALITY[self.quality][0]
        for name, source in self._source_meshes.items():
            mesh = source.copy()
            if mesh.n_cells > max_cells:
                mesh = mesh.decimate(1 - max_cells / mesh.n_cells)
            self.meshes[name] = mesh
            self.base_points[name] = mesh.points.copy()
            opacity = (.025 if name == "body" else self.lung_opacity if "lung" in name
                       else .10 if name == "ribs" else .9 if name == "target"
                       else .26 if name == "airways" else .85)
            textured = self.style != "Anatomy surfaces" and ("lung" in name or name == "body")
            options = (dict(scalars="CT_RGB", rgb=True, show_scalar_bar=False)
                       if textured and "CT_RGB" in mesh.point_data else
                       dict(color=COLORS.get(name, "#8cb2c0")))
            actor = self.add_mesh(mesh, opacity=opacity, **options,
                                  smooth_shading=True, ambient=.28, diffuse=.66, specular=.16,
                                  specular_power=24, name=f"structure_{name}",
                                  reset_camera=False, render=False)
            actor.SetVisibility(self._visibility.get(name, True))
            self.structure_actors[name] = actor
        self._apply_cutaway()
        self.highlight(self._highlighted, render=False)

    def set_volume(self, volume, masks, anatomy=None, prebuilt_meshes=None):
        self.scan.detach()
        for actor in list(self.dynamic.values()) + self._scale_actors:
            self.remove_actor(actor, render=False)
        self.dynamic.clear()
        self._scale_actors.clear()
        self._clear_vectors()
        self._vector_range_upper = 20.
        self._source_meshes.clear()
        self._last_state = None
        self._last_plan_key = None
        self.anatomy = anatomy
        self.reference_volume = volume
        self.set_source_label("SYNTHETIC CT + ANATOMY" if anatomy is not None else "SUPPLIED CT",render=False)
        self.actors["legend"].SetVisibility(anatomy is not None or "target" in masks)
        prepared = (prepare_display_meshes(volume, masks, anatomy=anatomy, max_cells=100000)
                    if not prebuilt_meshes else prebuilt_meshes)
        for name, mask in masks.items():
            mesh = prepared[name].copy() if name in prepared else mesh_from_mask(mask, volume)
            if mesh.n_points and "CT_RGB" not in mesh.point_data:
                mesh = attach_ct_scalars(mesh, volume, inset_mm=min(volume.spacing)*.65 if "lung" in name else 0.)
            if mesh.n_points:
                self._source_meshes[name] = mesh
        self.anatomical_center = np.asarray(volume.center, dtype=float)
        lungs = [np.asarray(mesh.bounds).reshape(3,2) for name,mesh in self._source_meshes.items()
                 if "lung" in name]
        self._lung_bounds = (np.array([np.min(np.stack(lungs)[:,:,0],axis=0),
                                       np.max(np.stack(lungs)[:,:,1],axis=0)]) if lungs else volume.bounds)
        if lungs:
            self.anatomical_center = self._lung_bounds.mean(axis=0)
        self._cut_plane.SetOrigin(*self.anatomical_center)
        self.scan.attach(self, volume, anatomy, masks=masks)
        self.scan.set_opacity(self.lung_opacity)
        self.scan.set_style("Lung detail" if self.style == "Lung motion" else "CT reconstruction")
        self.scan.set_visible(self.style == "CT reconstruction")
        for name, visible in self._visibility.items():
            self.scan.set_structure_visibility(name, visible)
        self._build_structures()
        self._add_scale(volume)
        self.preset("Oblique")

    def _add_scale(self, volume):
        # A world-coordinate reference remains 50 mm under rotation and perspective.
        lower = self._lung_bounds[0]
        start = self.anatomical_center + [-25., 0., 0.]
        start[1], start[2] = lower[1] - 12, lower[2] - 22
        end = start + [50., 0., 0.]
        lines = [pv.Line(start, end), pv.Line(start - [0, 0, 2], start + [0, 0, 2]),
                 pv.Line(end - [0, 0, 2], end + [0, 0, 2])]
        self.scale_endpoints = np.array([start, end])
        for i, line in enumerate(lines):
            self._scale_actors.append(self.add_mesh(line, color="#92adbb", line_width=2,
                lighting=False, name=f"scale_{i}", reset_camera=False, render=False))
        self._scale_actors.append(self.add_point_labels([start + [25, 0, 7]], ["50 mm"],
            show_points=False, always_visible=True, shape=None, bold=False, text_color="#abc1cd",
            font_size=10, name="scale_label", reset_camera=False, render=False))

    def preset(self, name):
        center = np.asarray(getattr(self, "anatomical_center", [0, 0, 0]))
        positions = {"Oblique": [430, -650, 240], "Anterior": [0, -800, 0],
                     "Posterior": [0, 800, 0], "Left": [800, 0, 0], "Superior": [0, 0, 800]}
        offset = np.asarray(positions.get(name, positions["Oblique"]))
        self.camera_position = [center + offset, center, [0, 1, 0] if name == "Superior" else [0, 0, 1]]
        if self.reference_volume is not None:
            bounds = (self.reference_volume.bounds.copy() if any(self._visibility.get(key,False) for key in ("body","ribs"))
                      else self._lung_bounds.copy())
            bounds[0] -= [12,12,35]
            bounds[1] += [12,12,30]
            if hasattr(self,"scale_endpoints"):
                bounds[0] = np.minimum(bounds[0],self.scale_endpoints.min(axis=0)-8)
                bounds[1] = np.maximum(bounds[1],self.scale_endpoints.max(axis=0)+8)
            self.reset_camera(bounds=tuple(bounds.T.ravel()))
        else:
            self.reset_camera()
        self.camera.zoom(1.45 if not any(self._visibility.get(key,False) for key in ("body","ribs")) else 1.10)
        # Keep the actual displayed lung bounds and world ruler inside the
        # viewport after the closer framing, including a nonzero phase.
        visible_bounds=[np.asarray(mesh.bounds).reshape(3,2) for name,mesh in self.meshes.items()
                        if "lung" in name or (name in ("body","ribs") and self._visibility.get(name,False))]
        if visible_bounds:
            lower=np.min(np.stack(visible_bounds)[:,:,0],axis=0)
            upper=np.max(np.stack(visible_bounds)[:,:,1],axis=0)
            corners=np.array(np.meshgrid(*zip(lower,upper))).reshape(3,-1).T
            landmarks=np.vstack((corners,self.scale_endpoints))
            width,height=self.render_window.GetSize()
            if width>32 and height>32:
                for _ in range(4):
                    projected=[]
                    for point in landmarks:
                        self.renderer.SetWorldPoint(*point,1.)
                        self.renderer.WorldToDisplay()
                        projected.append(self.renderer.GetDisplayPoint()[:2])
                    ratio=np.max(np.abs(np.asarray(projected)-[width/2,height/2])/
                                 np.array([width/2-16,height/2-16]))
                    if ratio<=1:
                        break
                    self.camera.zoom(1/(ratio*1.02))
        self.render()

    def _apply_cutaway(self):
        for name, actor in self.structure_actors.items():
            actor.mapper.RemoveAllClippingPlanes()
            if self.cutaway_enabled and (name in ("body", "ribs") or "lung" in name):
                actor.mapper.AddClippingPlane(self._cut_plane)

    def set_cutaway(self, enabled, position=None, render=True):
        self.cutaway_enabled = bool(enabled)
        if position is not None:
            self._cut_plane.SetOrigin(*_point(position, "Cutaway position"))
        self._apply_cutaway()
        self.scan.set_cutaway(enabled, position)
        if self.cutaway_enabled:
            self.add_text("ANTERIOR CUTAWAY / display only", position="upper_right",
                          font_size=8, color="#9fb8c7", name="cutaway_label", render=False)
        else:
            self.remove_actor("cutaway_label", render=False)
        if render:
            self.render()

    def visibility(self, name, visible, render=True):
        self._visibility[name] = bool(visible)
        self.scan.set_structure_visibility(name, visible)
        if name in self.structure_actors:
            self.structure_actors[name].SetVisibility(visible)
        if name == "target":
            for key in ("actual", "defined_target"):
                if key in self.dynamic:
                    self.dynamic[key].SetVisibility(visible)
        if render:
            self.render()

    def overlay_visibility(self, name, visible, render=True):
        if name not in ("prediction", "uncertainty", "needle", "trajectory", "crosshair"):
            raise ValueError("Unknown planning overlay.")
        self._overlay_visibility[name] = bool(visible)
        for key, actor in self.dynamic.items():
            if self._overlay_group(key) == name:
                actor.SetVisibility(visible)
        if render:
            self.render()

    @staticmethod
    def _overlay_group(name):
        return {"predicted": "prediction", "planned_route": "trajectory", "entry": "trajectory",
                "needle_tip": "needle"}.get(name, name)

    def transparency(self, value, render=True):
        if not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Lung opacity must be between zero and one.")
        self.lung_opacity = float(value)
        self.scan.set_opacity(value)
        for name, actor in self.structure_actors.items():
            if "lung" in name:
                actor.GetProperty().SetOpacity(value)
        if render:
            self.render()

    def highlight(self, name, render=True):
        self._highlighted = name
        for key, actor in self.structure_actors.items():
            actor.GetProperty().SetAmbient(.48 if key == name else .18)
            actor.GetProperty().SetEdgeVisibility(key == name)
            actor.GetProperty().SetEdgeColor(.4, .9, .95)
        if render:
            self.render()

    def _dynamic_mesh(self, name, mesh, **kwargs):
        if name in self.dynamic:
            self.dynamic[name].mapper.dataset.copy_from(mesh)
        else:
            self.dynamic[name] = self.add_mesh(mesh, name=name, reset_camera=False, render=False, **kwargs)
        visible = (self._visibility.get("target", True) if name in ("actual", "defined_target")
                   else self._overlay_visibility.get(self._overlay_group(name), True))
        self.dynamic[name].SetVisibility(visible)
        return self.dynamic[name]

    def _marker(self, name, center, radius, **kwargs):
        center = _point(center, name)
        if not np.isfinite(radius) or radius <= 0:
            raise ValueError("Marker radius must be positive millimetres.")
        if name not in self.dynamic:
            resolution = QUALITY[self.quality][2]
            self._dynamic_mesh(name, pv.Sphere(radius=1., theta_resolution=resolution,
                                               phi_resolution=resolution), **kwargs)
        self.dynamic[name].position = center
        self.dynamic[name].scale = (radius,) * 3

    def _remove_dynamic(self, names):
        for name in names:
            if name in self.dynamic:
                self.remove_actor(self.dynamic.pop(name), render=False)

    def update_state(self, displacement, actual, plan=None, depth=0., crosshair=None,
                     vectors=False, target_radius=None, render=True, preserve_supplied_vectors=False):
        displacement = _point(displacement, "Displacement")
        self._last_state = dict(displacement=displacement.copy(), actual=actual, plan=plan, depth=depth,
                                crosshair=crosshair, vectors=vectors, target_radius=target_radius,
                                preserve_supplied_vectors=preserve_supplied_vectors)
        if self.anatomy is not None:
            for name, mesh in self.meshes.items():
                if name not in ("body", "ribs"):
                    mesh.points = self.anatomy.deform_points(self.base_points[name], displacement)
        if self.style == "CT reconstruction":
            self.scan.update(displacement)
        if actual is not None:
            self._marker("actual", actual, 2., color="#ffcb75", ambient=.4, specular=.3)
            if target_radius is not None:
                self._marker("defined_target", actual, target_radius, color="#ffbd60", opacity=.28)
        else:
            self._remove_dynamic(("actual", "defined_target"))
        if target_radius is None:
            self._remove_dynamic(("defined_target",))
        if crosshair is not None:
            crosshair = _point(crosshair, "Crosshair")
            points = np.concatenate([[crosshair - axis * 5, crosshair + axis * 5] for axis in np.eye(3)])
            mesh = pv.PolyData(points, lines=np.array([[2, 0, 1], [2, 2, 3], [2, 4, 5]]))
            self._dynamic_mesh("crosshair", mesh, color="#dbe4e9", line_width=1, lighting=False)
        else:
            self._remove_dynamic(("crosshair",))
        if plan is not None and not plan.abstained:
            entry, endpoint = _point(plan.entry, "Entry"), _point(plan.endpoint, "Endpoint")
            prediction = _point(plan.prediction, "Prediction")
            key = (tuple(entry), tuple(endpoint), tuple(prediction),
                   np.asarray(plan.covariance).tobytes(), float(getattr(plan, "uncertainty_quantile", 7.8147279)))
            resolution = QUALITY[self.quality][2]
            if key != self._last_plan_key:
                self._marker("predicted", prediction, 3.2, color="#54edf1", style="wireframe", line_width=1.5)
                if np.linalg.norm(endpoint - entry) > 1e-6:
                    self._dynamic_mesh("planned_route", pv.Line(entry, endpoint).tube(radius=.42, n_sides=resolution),
                                       color="#49dfed", ambient=.55)
                else:
                    self._remove_dynamic(("planned_route",))
                self._marker("entry", entry, 2., color="#daf4f6", ambient=.5)
                uncertainty = _uncertainty_surface(plan, resolution)
                if uncertainty is not None:
                    self._dynamic_mesh("uncertainty", uncertainty, color="#b59ae9", opacity=.18,
                                       ambient=.45, specular=.1)
                else:
                    self._remove_dynamic(("uncertainty",))
                self._last_plan_key = key
            needle = _needle_parts(entry, endpoint, depth, resolution)
            if needle is None:
                self._remove_dynamic(("needle", "needle_tip"))
            else:
                shaft, head, _ = needle
                if shaft is not None:
                    self._dynamic_mesh("needle", shaft, color="#e1e8ed", specular=.9, specular_power=40)
                else:
                    self._remove_dynamic(("needle",))
                self._dynamic_mesh("needle_tip", head, color="#ffffff", specular=.6)
        else:
            self._last_plan_key = None
            self._remove_dynamic(("predicted", "planned_route", "entry", "needle", "needle_tip", "uncertainty"))
        if vectors and self.anatomy is not None:
            sources = [self.base_points[name] for name in ("left_lung", "right_lung", "lungs")
                       if name in self.base_points]
            if sources:
                # Arrow tails are reference tissue points; tips coincide with current tissue.
                points = np.concatenate(sources)
                points, _, _ = _vector_data(points, np.zeros_like(points), QUALITY[self.quality][1])
                moved = self.anatomy.deform_points(points, displacement)
                self._draw_vectors(points, moved - points, "synthetic")
            else:
                self._clear_vectors()
        elif not (preserve_supplied_vectors and self._vector_source is not None
                  and self._vector_source[2] == "supplied"):
            self._clear_vectors()
        if render:
            self.render()

    def _clear_vectors(self):
        if self._vector_title in self.scalar_bars:
            self.remove_scalar_bar(self._vector_title, render=False)
        if self.vector_actor is not None:
            self.remove_actor(self.vector_actor, render=False)
        self.vector_actor = None
        self._vector_title = None
        self._vector_source = None
        self._vector_range_upper = 20.

    def _draw_vectors(self, points, displacements, source):
        points, vectors, magnitude = _vector_data(points, displacements, QUALITY[self.quality][1])
        if not len(points):
            self._clear_vectors()
            return
        title = "Reference to current (mm)" if source == "synthetic" else "Supplied displacement (mm)"
        if self._vector_title != title:
            self._clear_vectors()
        self._vector_source = (points.copy(), vectors.copy(), source)
        self._vector_range_upper = max(self._vector_range_upper, float(np.ceil(np.max(magnitude) / 10) * 10))
        cloud = pv.PolyData(points)
        cloud["displacement"] = vectors
        cloud["magnitude"] = magnitude
        arrow = pv.Arrow(tip_length=.22, tip_radius=.1, shaft_radius=.025,
                         shaft_resolution=6, tip_resolution=8)
        arrows = cloud.glyph(orient="displacement", scale="magnitude", factor=1., geom=arrow)
        if self.vector_actor is None:
            self.vector_actor = self.add_mesh(arrows, scalars="magnitude", cmap="turbo",
                clim=[0, self._vector_range_upper], ambient=.5, specular=.15, name="motion_vectors",
                scalar_bar_args={"title": title, "color": "#d9e7ee", "vertical": True,
                                 "position_x": .86, "position_y": .26, "width": .06, "height": .45,
                                 "title_font_size": 10, "label_font_size": 10, "n_labels": 5,
                                 "fmt": "%.0f", "outline": False},
                reset_camera=False, render=False)
            self._vector_title = title
        else:
            self.vector_actor.mapper.dataset.copy_from(arrows)
            self.vector_actor.mapper.scalar_range = (0, self._vector_range_upper)

    def supplied_vectors(self, points, displacements, render=True):
        self._draw_vectors(points, displacements, "supplied")
        if render:
            self.render()

    def focus_target(self, target):
        if target is not None:
            self.camera.focal_point = _point(target, "Target")
            self.camera.zoom(1.35)
            self.render()

    def inspect_trajectory(self, plan):
        if plan is None or plan.abstained:
            return
        entry, endpoint = _point(plan.entry, "Entry"), _point(plan.endpoint, "Endpoint")
        direction = endpoint - entry
        if np.linalg.norm(direction) <= 1e-6:
            return
        middle = (entry + endpoint) / 2
        normal = np.cross(direction, [0., 0., 1.])
        if np.linalg.norm(normal) <= 1e-6:
            normal = np.array([0., -1., 0.])
        normal /= np.linalg.norm(normal)
        self.camera_position = [middle + normal * max(180., np.linalg.norm(direction) * 3),
                                middle, [0, 0, 1]]
        self.camera.clipping_range = (.1, 2000.)
        self.render()


# ============================================================================
# interface / slice_viewer
# ============================================================================

import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel

from motiontwin import Volume



def physical_scale_ruler(plane, image_width, target_pixels=75.):
    """A readable physical length and its exact on-screen pixel width."""
    pixels_per_mm = float(image_width) / (plane.shape[1] * plane.spacing[0])
    desired = max(float(target_pixels) / pixels_per_mm, np.finfo(float).tiny)
    decade = 10. ** np.floor(np.log10(desired))
    length = max(value * decade for value in (0.1, 0.2, 0.5, 1., 2., 5., 10.)
                 if value * decade <= desired * (1 + 1e-12))
    return length, length * pixels_per_mm


class SliceCanvas(QWidget):
    selected = Signal(object)
    scrolled = Signal(int)

    def __init__(self, plane):
        super().__init__()
        self.plane_name = plane
        self.setMinimumSize(165,115)
        self.setMouseTracking(True)
        self.plane = None
        self.zoom = 1.
        self.window, self.level = 1500., -500.
        self.crosshair = np.zeros(3)
        self.target = None
        self.target_radius = 6.
        self.path = None
        self.needle_path = None
        self.overlays = []
        self.max_pixels = 384
        self._image_key = None
        self._image_buffer = None
        self._image = None
        self._overlay_images = []

    def set_quality(self, max_pixels):
        if isinstance(max_pixels, bool) or int(max_pixels) != max_pixels or max_pixels < 2:
            raise ValueError("Slice resolution must be an integer of at least 2 pixels.")
        changed = self.max_pixels != int(max_pixels)
        self.max_pixels = int(max_pixels)
        return changed

    def set_data(self, volume, crosshair, target=None, radius=6., plan=None, masks=None,
                 *, plane=None, mask_planes=None, needle_fraction=0.):
        self.crosshair = np.asarray(crosshair)
        self.plane = (volume.slice_plane(self.plane_name, crosshair, max_pixels=self.max_pixels)
                      if plane is None else plane)
        if self.plane.name != self.plane_name:
            raise ValueError("The supplied slice does not match the viewer orientation.")
        self.target, self.target_radius = target, radius
        self.path = None if plan is None or plan.abstained else np.array([plan.entry,plan.endpoint])
        fraction = float(np.clip(needle_fraction, 0, 1))
        self.needle_path = (None if self.path is None or fraction <= 0 else
                            np.array([self.path[0], self.path[0]+fraction*(self.path[1]-self.path[0])]))
        self.overlays = []
        for name, mask in ((mask_planes if mask_planes is not None else masks) or {}).items():
            if name == "body":
                continue
            if mask_planes is not None:
                if (mask.shape != self.plane.shape
                        or not np.allclose(mask.origin, self.plane.origin)
                        or not np.allclose(mask.spacing, self.plane.spacing)
                        or not np.allclose(mask.u, self.plane.u)
                        or not np.allclose(mask.v, self.plane.v)):
                    raise ValueError("A segmentation overlay must use the exact CT slice grid.")
                overlay = mask.image
            else:
                mask_volume = Volume(np.asarray(mask), volume.spacing,
                                     volume.origin, volume.direction)
                overlay = mask_volume.reslice_like(self.plane, interpolation=0, cval=0).image
            self.overlays.append((overlay,COLORS.get(name,"#8cb2c0")))
        self._image_key = None
        self._overlay_images = []
        for overlay, color in self.overlays:
            rgba = np.zeros((*overlay.shape, 4), dtype=np.uint8)
            c = QColor(color)
            rgba[overlay > 0] = [c.red(), c.green(), c.blue(), 65]
            rgba = np.ascontiguousarray(np.flipud(rgba))
            rows, cols = overlay.shape
            qimage = QImage(rgba.data, cols, rows, rgba.strides[0], QImage.Format.Format_RGBA8888)
            self._overlay_images.append((rgba, qimage))
        self.update()

    def image_rect(self):
        rows, cols = self.plane.shape
        aspect_width = cols * self.plane.spacing[0]
        aspect_height = rows * self.plane.spacing[1]
        scale = min(self.width()/aspect_width,max(1,self.height()-25)/aspect_height)*self.zoom
        width,height = aspect_width*scale,aspect_height*scale
        return QRectF((self.width()-width)/2,(self.height()-height)/2,width,height)

    def screen_point(self, world):
        pixels = self.plane.world_to_pixel(world)
        rect = self.image_rect()
        rows,cols = self.plane.shape
        # All anatomical panels show superior/posterior toward their labelled edge.
        return QPointF(rect.left()+(pixels[0]+.5)/cols*rect.width(),rect.bottom()-(pixels[1]+.5)/rows*rect.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(),QColor("#030609"))
        if self.plane is None:
            return
        key = (id(self.plane.image), self.window, self.level)
        if key != self._image_key:
            self._image_buffer = np.ascontiguousarray(np.flipud(np.clip(
                (self.plane.image-self.level+self.window/2)/max(self.window,1)*255,
                0,255).astype(np.uint8)))
            rows,cols = self._image_buffer.shape
            self._image = QImage(self._image_buffer.data, cols, rows,
                                 self._image_buffer.strides[0], QImage.Format.Format_Grayscale8)
            self._image_key = key
        rows, cols = self.plane.shape
        rect = self.image_rect()
        painter.drawImage(rect,self._image)
        # Grey-scale CT benefits from linear display interpolation. Binary
        # segmentations retain their exact nearest-neighbour label boundary.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False)
        for _, overlay_image in self._overlay_images:
            painter.drawImage(rect,overlay_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        point = self.screen_point(self.crosshair)
        painter.setPen(QPen(QColor("#6ddce8"),1,Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(rect.left(),point.y()),QPointF(rect.right(),point.y()))
        painter.drawLine(QPointF(point.x(),rect.top()),QPointF(point.x(),rect.bottom()))
        if self.target is not None:
            distance = abs(float(self.plane.distance_to_plane(self.target)))
            if distance <= self.target_radius:
                radius = np.sqrt(max(self.target_radius**2-distance**2,0))
                scale = rect.width()/(cols*self.plane.spacing[0])
                painter.setPen(QPen(QColor("#ffc36b"),2))
                painter.drawEllipse(self.screen_point(self.target),radius*scale,radius*scale)
        if self.path is not None:
            distances = self.plane.distance_to_plane(self.path)
            painter.setPen(QPen(QColor("#4ce1eb"),1.5,Qt.PenStyle.DotLine))
            painter.drawLine(self.screen_point(self.path[0]),self.screen_point(self.path[1]))
            if distances[0]*distances[1] <= 0 and abs(distances[0]-distances[1])>1e-8:
                fraction = distances[0]/(distances[0]-distances[1])
                intersection = self.path[0]+fraction*(self.path[1]-self.path[0])
                painter.setPen(QPen(QColor("#ffffff"),2))
                painter.drawEllipse(self.screen_point(intersection),4,4)
        if self.needle_path is not None:
            painter.setPen(QPen(QColor("#e2e7ed"),2,Qt.PenStyle.DashLine))
            painter.drawLine(self.screen_point(self.needle_path[0]),self.screen_point(self.needle_path[1]))
            distances = self.plane.distance_to_plane(self.needle_path)
            if distances[0]*distances[1] <= 0 and abs(distances[0]-distances[1]) > 1e-8:
                fraction = distances[0]/(distances[0]-distances[1])
                intersection = self.needle_path[0]+fraction*(self.needle_path[1]-self.needle_path[0])
                painter.setBrush(QColor("#e2e7ed"))
                painter.drawEllipse(self.screen_point(intersection),3,3)
                painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor("#b3c4d0"))
        painter.drawText(8,16,"CT / LPS")
        labels = {"axial":("R","L","P","A"),"coronal":("R","L","S","I"),"sagittal":("A","P","S","I")}[self.plane_name]
        painter.drawText(5,self.height()//2,labels[0])
        painter.drawText(self.width()-16,self.height()//2,labels[1])
        painter.drawText(self.width()//2,32,labels[2])
        painter.drawText(self.width()//2,self.height()-8,labels[3])
        length, width = physical_scale_ruler(self.plane, rect.width(),
                                             min(75., max(25., self.width() * .3)))
        left, bottom = 24., self.height() - 27.
        painter.setPen(QPen(QColor("#d5e5ef"), 1.5))
        painter.drawLine(QPointF(left,bottom),QPointF(left+width,bottom))
        for x in (left, left+width):
            painter.drawLine(QPointF(x,bottom-4),QPointF(x,bottom+4))
        painter.drawText(QRectF(left,bottom-21,width+12,17),
                         Qt.AlignmentFlag.AlignLeft,f"{length:g} mm")
        painter.drawText(QRectF(0,self.height()-22,self.width()-7,17),
                         Qt.AlignmentFlag.AlignRight,f"W {self.window:g}  L {self.level:g}")

    def mousePressEvent(self,event):
        if self.plane is None:
            return
        if event.button()==Qt.MouseButton.LeftButton:
            rect = self.image_rect()
            rows,cols = self.plane.shape
            position = event.position()
            if rect.contains(position):
                pixels = [(position.x()-rect.left())/rect.width()*cols-.5,(rect.bottom()-position.y())/rect.height()*rows-.5]
                self.selected.emit(self.plane.pixel_to_world(pixels))

    def wheelEvent(self,event):
        direction = 1 if event.angleDelta().y()>0 else -1
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom = float(np.clip(self.zoom*(1.12**direction),.5,5))
            self.update()
        else:
            self.scrolled.emit(direction)


class SliceViewer(QWidget):
    selected = Signal(object)

    def __init__(self, plane, parent=None):
        super().__init__(parent)
        self.plane_name = plane
        self.axis = {"axial":2,"coronal":1,"sagittal":0}[plane]
        self.setObjectName(f"{plane}Panel")
        accents={"axial":("#bd6269","#342026"),"coronal":("#6da187","#1b302a"),
                 "sagittal":("#b6a368","#322e20")}
        accent,background=accents[plane]
        self.setStyleSheet(f"""
            QWidget#{plane}Panel {{ background:#06090d; border:1px solid {accent}; }}
            QWidget#{plane}Header {{ background:{background}; border:0; border-top:2px solid {accent}; }}
            QWidget#{plane}Header QLabel {{ background:transparent; border:0; color:#e0e7ed; font-size:10px; }}
        """)
        self.canvas = SliceCanvas(plane)
        self.canvas.selected.connect(self.selected)
        self.canvas.scrolled.connect(lambda delta:self.slider.setValue(self.slider.value()+delta))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setToolTip("Move through this physical CT plane. Scroll the image to advance one slice; Ctrl+scroll to zoom.")
        self.slider.setFixedHeight(17)
        self.slider.valueChanged.connect(self._scroll)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1,1,1,1)
        layout.setSpacing(0)
        header=QWidget(self)
        header.setObjectName(f"{plane}Header")
        labels=QHBoxLayout(header)
        labels.setContentsMargins(8,4,8,4)
        title=QLabel({"axial":"AXIAL","coronal":"CORONAL","sagittal":"SAGITTAL"}[plane])
        title.setStyleSheet("font-weight:650")
        labels.addWidget(title)
        labels.addStretch()
        self.position_label=QLabel("— mm")
        labels.addWidget(self.position_label)
        layout.addWidget(header)
        layout.addWidget(self.canvas,1)
        layout.addWidget(self.slider)
        self.volume = None

    def set_quality(self, max_pixels):
        """Set the sampling cap; the workstation refreshes all views together."""
        return self.canvas.set_quality(max_pixels)

    def set_data(self,volume,crosshair,*args,**kwargs):
        self.volume = volume
        self.crosshair = np.array(crosshair)
        bounds = volume.bounds
        self.minimum = bounds[0,self.axis]
        self.step = min(volume.spacing)
        self.slider.blockSignals(True)
        self.slider.setRange(0,int(np.ceil((bounds[1,self.axis]-self.minimum)/self.step)))
        self.slider.setValue(int(round((crosshair[self.axis]-self.minimum)/self.step)))
        self.slider.blockSignals(False)
        self.canvas.set_data(volume,crosshair,*args,**kwargs)
        coordinate="XYZ"[self.axis]
        self.position_label.setText(f"{coordinate} {self.canvas.plane.position:+.1f} mm")

    def _scroll(self,value):
        if self.volume is not None:
            point = self.crosshair.copy()
            point[self.axis] = self.minimum+value*self.step
            self.selected.emit(point)


# ============================================================================
# interface / main_window
# ============================================================================

from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
import json
import traceback
from time import perf_counter

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QLabel, QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QSlider,
    QTabWidget, QSplitter, QCheckBox, QFileDialog, QMessageBox, QScrollArea,
    QPlainTextEdit, QGroupBox, QInputDialog, QGridLayout, QToolButton, QSizePolicy)

from motiontwin import load_config
from motiontwin import load_volume, save_volume
from motiontwin import SyntheticSliceSource
from motiontwin import load_mask, mesh_from_mask
from motiontwin import PhaseSequence



from motiontwin import Plan, plan_trajectory
from motiontwin import generate_anatomy
from motiontwin import RespiratoryModel
from motiontwin import VirtualPatient
from motiontwin import run_episode


class Worker(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.result.emit(self.function())
        except Exception:
            self.failed.emit(traceback.format_exc())


class TracePlot(QWidget):
    def __init__(self,title):
        super().__init__()
        self.title=title
        self.setMinimumHeight(125)
        self.time=np.array([])
        self.actual=np.array([])
        self.predicted=None

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#0b141e"))
        painter.setPen(QColor("#b6cbd8"))
        painter.drawText(10,20,self.title)
        if len(self.time)<2:
            painter.drawText(10,60,"Awaiting computed observations")
            return
        x0,x1=float(self.time.min()),float(self.time.max())
        if self.predicted is not None:
            x1=max(x1,self.predicted[0])
        values=self.actual
        low,high=float(np.min(values))-2,float(np.max(values))+2
        if self.predicted is not None:
            low=min(low,self.predicted[1]-2)
            high=max(high,self.predicted[1]+2)
        def point(x,y):
            return QPointF(34+(x-x0)/max(x1-x0,1)*max(self.width()-48,1),self.height()-24-(y-low)/max(high-low,1)*(self.height()-60))
        painter.setPen(QPen(QColor("#203746"),1))
        for fraction in (.0,.5,1.):
            y=low+fraction*(high-low)
            painter.drawLine(point(x0,y),point(x1,y))
        painter.setPen(QColor("#8199ac"))
        painter.drawText(3,42,f"{high:.0f}")
        painter.drawText(3,self.height()-24,f"{low:.0f}")
        painter.drawText(35,self.height()-5,f"{x0:.1f} s")
        painter.drawText(self.width()-55,self.height()-5,f"{x1:.1f} s")
        painter.setPen(QPen(QColor("#f7bc64"),1.8))
        for i in range(1,len(self.time)):
            painter.drawLine(point(self.time[i-1],values[i-1]),point(self.time[i],values[i]))
        if self.predicted is not None:
            painter.setPen(QPen(QColor("#58dde5"),2))
            painter.drawEllipse(point(*self.predicted),4,4)


def group(title,layout):
    box=QGroupBox(title)
    box.setLayout(layout)
    return box


class MainWindow(QMainWindow):
    def __init__(self, demo=False, initial_source="synthetic"):
        super().__init__()
        self.setWindowTitle("MotionTwin | Respiratory Motion Research Workstation")
        available=QApplication.primaryScreen().availableGeometry()
        width=min(1600,max(800,available.width()-48))
        height=min(980,max(600,available.height()-64))
        self.setMinimumSize(min(1050,width),min(680,height))
        self.resize(width,height)
        self.setStyleSheet(STYLE)
        self.patient=VirtualPatient(seed=17)
        self.motion=RespiratoryModel(self.patient)
        self.time=8.
        self.plan=None
        self.plan_time=8.
        self.execution_start=None
        self.anatomy=None
        self.volume=None
        self.synthetic_slices=None
        self.source_info=None
        self._mask_sources={}
        self._supplied_meshes={}
        self.masks={}
        self.phase_sequence=None
        self.phase_index=0
        self._displayed_phase_sequence=None
        self.mode="synthetic"
        self.real_target=None
        self.real_entry=None
        self.real_radius=6.
        self.checkpoint=str(Path("outputs/model/motion_predictor.pt"))
        self.worker=None
        self.last_result=None
        self.last_result_source=None
        self.revision=0
        self._last_tick=None
        self.display_frame_ms=0.
        self._ui()
        self.timer=QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        if initial_source == "public-example":
            self.study_metadata.setText("Opening public chest CT")
            self.badge.setText("PUBLIC CT EXAMPLE")
            self.workspace.setCurrentText("CT review")
            QTimer.singleShot(0,self.load_public_example)
        else:
            self.new_synthetic()
            QTimer.singleShot(100,self.replan)

    def _ui(self):
        central=QWidget()
        self.setCentralWidget(central)
        outer=QVBoxLayout(central)
        outer.setContentsMargins(8,0,8,6)
        outer.setSpacing(6)
        study_strip=QWidget()
        study_strip.setObjectName("studyStrip")
        header=QHBoxLayout(study_strip)
        header.setContentsMargins(12,9,12,9)
        brand=QLabel("MotionTwin")
        brand.setObjectName("brand")
        header.addWidget(brand)
        titles=QVBoxLayout()
        titles.setSpacing(2)
        subtitle=QLabel("PULMONARY IMAGING  /  4D MOTION & PLANNING")
        subtitle.setObjectName("studySubtitle")
        subtitle.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        titles.addWidget(subtitle)
        self.study_metadata=QLabel("Loading synthetic thoracic study")
        self.study_metadata.setObjectName("studyMetadata")
        self.study_metadata.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        titles.addWidget(self.study_metadata)
        header.addLayout(titles,1)
        self.badge=QLabel("SYNTHETIC ANATOMY")
        self.badge.setObjectName("badge")
        header.addWidget(self.badge)
        research_badge=QLabel("RESEARCH WORKSTATION")
        research_badge.setObjectName("researchBadge")
        header.addWidget(research_badge)
        outer.addWidget(study_strip)

        navigation=QWidget()
        navigation.setObjectName("navigationStrip")
        tools=QHBoxLayout(navigation)
        tools.setContentsMargins(8,5,8,5)
        tools.setSpacing(7)
        tools.addWidget(QLabel("WORKSPACE"))
        self.workspace=QComboBox()
        self.workspace.addItems(["3D planning","CT review","Research & analysis"])
        self.workspace.setFixedWidth(170)
        self.workspace.setToolTip("Rearrange the existing linked viewers; camera, CT zoom and physical state are retained.")
        tools.addWidget(self.workspace)
        tools.addWidget(QLabel("RENDER"))
        self.scene_style=QComboBox()
        self.scene_style.addItems(["CT reconstruction","Lung motion","Anatomy surfaces"])
        self.scene_style.setFixedWidth(165)
        self.scene_style.setToolTip("CT reconstruction: scan density and fine branches. Lung motion: tissue and displacement vectors. Anatomy surfaces: segmented structures.")
        tools.addWidget(self.scene_style)
        tools.addStretch()
        self.display_quality=QComboBox()
        self.display_quality.addItems(["Interactive","Balanced","High"])
        self.display_quality.setCurrentText("Balanced")
        self.display_quality.setFixedWidth(108)
        self.display_quality.setToolTip("Display detail only: CT density sampling, meshes and vectors. Physical planning inputs stay unchanged.")
        self.display_quality.currentTextChanged.connect(self.change_display_quality)
        tools.addWidget(QLabel("QUALITY"))
        tools.addWidget(self.display_quality)
        self.controls_toggle=QToolButton()
        self.controls_toggle.setText("Controls")
        self.controls_toggle.setFixedWidth(79)
        self.controls_toggle.setCheckable(True)
        self.controls_toggle.setChecked(True)
        tools.addWidget(self.controls_toggle)
        self.analysis_toggle=QToolButton()
        self.analysis_toggle.setText("Analysis")
        self.analysis_toggle.setFixedWidth(79)
        self.analysis_toggle.setCheckable(True)
        self.analysis_toggle.setToolTip("Show computed planning metrics and respiratory traces.")
        tools.addWidget(self.analysis_toggle)
        outer.addWidget(navigation)
        self.status=QLabel("Initialising synthetic scene…")
        self.status.setObjectName("statusLine")
        self.status.setWordWrap(True)
        self.status.setMaximumHeight(36)
        outer.addWidget(self.status)
        main=QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter=main
        main.setChildrenCollapsible(False)
        main.setHandleWidth(5)
        outer.addWidget(main,1)
        self.tabs=QTabWidget()
        self.tabs.setMinimumWidth(275)
        self.tabs.setMaximumWidth(335)
        self.tabs.setDocumentMode(True)
        main.addWidget(self.tabs)
        self._simulation_tab()
        self._imaging_tab()
        self._planning_tab()
        self._research_tab()

        # Every native viewport retains its original parent when the workspace
        # changes. Moving grid items avoids recreating a Windows OpenGL window.
        center=QWidget()
        self.imaging_workspace=center
        center_layout=QVBoxLayout(center)
        center_layout.setContentsMargins(0,0,0,0)
        center_layout.setSpacing(5)
        self.viewport_grid_parent=QWidget(center)
        self.viewport_grid=QGridLayout(self.viewport_grid_parent)
        self.viewport_grid.setContentsMargins(0,0,0,0)
        self.viewport_grid.setSpacing(5)
        center_layout.addWidget(self.viewport_grid_parent,1)
        main.addWidget(center)
        scene_panel=QWidget(self.viewport_grid_parent)
        self.scene_panel=scene_panel
        scene_panel.setObjectName("viewportPanel")
        scene_layout=QVBoxLayout(scene_panel)
        scene_layout.setContentsMargins(1,1,1,1)
        scene_layout.setSpacing(0)
        toolbar_panel=QWidget(scene_panel)
        toolbar_panel.setObjectName("viewportToolbar")
        toolbar=QHBoxLayout(toolbar_panel)
        toolbar.setContentsMargins(8,4,6,4)
        toolbar.setSpacing(5)
        self.camera=QComboBox()
        self.camera.addItems(["Oblique","Anterior","Posterior","Left","Superior"])
        self.camera.setFixedWidth(90)
        self.camera.currentTextChanged.connect(lambda text:self.scene.preset(text))
        self.scene_title=QLabel("3D · CT RECONSTRUCTION")
        self.scene_title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        toolbar.addWidget(self.scene_title,1)
        toolbar.addWidget(self.camera)
        reset=QToolButton()
        reset.setText("Fit")
        reset.setFixedWidth(42)
        reset.setToolTip("Fit the complete anatomical study in this viewport.")
        reset.clicked.connect(lambda:self.scene.preset(self.camera.currentText()))
        toolbar.addWidget(reset)
        focus=QToolButton()
        focus.setText("Target")
        focus.setFixedWidth(62)
        focus.setToolTip("Focus the current physical target.")
        focus.clicked.connect(lambda:self.scene.focus_target(self.actual_target()))
        toolbar.addWidget(focus)
        scene_layout.addWidget(toolbar_panel)
        self.scene=SceneViewer(scene_panel)
        scene_layout.addWidget(self.scene.interactor,1)
        self.slices=[]
        for plane in ("axial","coronal","sagittal"):
            view=SliceViewer(plane,self.viewport_grid_parent)
            view.selected.connect(self.set_crosshair)
            self.slices.append(view)
        phase_panel=QWidget(center)
        self.phase_panel=phase_panel
        phase_panel.setObjectName("phaseStrip")
        phase_layout=QHBoxLayout(phase_panel)
        phase_layout.setContentsMargins(8,4,8,4)
        phase_layout.setSpacing(8)
        for title,callback in (("Play",self.play),("Pause",self.pause)):
            transport=QToolButton()
            transport.setText(title)
            transport.clicked.connect(callback)
            phase_layout.addWidget(transport)
        phase_label=QLabel("4D PHASE")
        self.phase_label=phase_label
        phase_label.setStyleSheet("font-size:10px;color:#9cb2c5")
        phase_layout.addWidget(phase_label)
        phase_layout.addWidget(self.phase_slider,1)
        self.phase_readout=QLabel("0%")
        self.phase_readout.setMinimumWidth(82)
        self.phase_readout.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        phase_layout.addWidget(self.phase_readout)
        center_layout.addWidget(phase_panel)

        side=QWidget()
        side.setObjectName("analysisPanel")
        side.setMinimumWidth(220)
        side.setMaximumWidth(275)
        side_scroll=QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setMinimumWidth(230)
        side_scroll.setMaximumWidth(285)
        side_scroll.setWidget(side)
        self.analysis_panel=side_scroll
        main.addWidget(side_scroll)
        info=QVBoxLayout(side)
        info.setContentsMargins(10,0,8,4)
        info.setSpacing(2)
        analysis_title=QLabel("COMPUTED ANALYSIS")
        analysis_title.setObjectName("panelTitle")
        info.addWidget(analysis_title)
        self.metrics={}
        for key in ("Time / phase","Actual target (mm)","Predicted arrival (mm)","Trajectory length","Obstacle clearance","Prediction error","Targeting error","Obstacle violations","Needle depth","Planning latency","Uncertainty","Outcome"):
            label=QLabel(key)
            label.setObjectName("metricName")
            info.addWidget(label)
            value=QLabel("—")
            value.setObjectName("metric")
            value.setWordWrap(True)
            info.addWidget(value)
            self.metrics[key]=value
        self.trace_plot=TracePlot("Superior displacement (mm)")
        self.error_plot=TracePlot("Evaluated forecast error (mm)")
        info.addWidget(self.trace_plot)
        info.addWidget(self.error_plot)
        info.addStretch()
        main.setStretchFactor(0,0)
        main.setStretchFactor(1,1)
        main.setStretchFactor(2,0)
        main.setSizes([295,1000,240])
        self.controls_toggle.toggled.connect(self.tabs.setVisible)
        self.analysis_toggle.toggled.connect(side_scroll.setVisible)
        side_scroll.hide()
        self.workspace.currentTextChanged.connect(self.change_workspace)
        self.scene_style.currentTextChanged.connect(self.change_scene_style)
        self.change_workspace("3D planning")
        self.change_scene_style(self.scene_style.currentText())
        footer=QLabel("LPS · mm   |   CT: click to position · scroll to slice · Ctrl+scroll to zoom   |   Cyan route · silver inserted needle · amber target")
        footer.setStyleSheet("color:#7f97ad;font-size:10px")
        footer.setWordWrap(True)
        outer.addWidget(footer)
        self.display_info=QLabel("Balanced display · linked physical coordinates")
        self.display_info.setStyleSheet("color:#8099ae;font-size:10px")
        outer.addWidget(self.display_info)

    def change_workspace(self,name):
        """Rearrange a single set of viewer widgets without changing parents."""
        if name not in ("3D planning","CT review","Research & analysis"):
            raise ValueError("Unknown imaging workspace.")
        self.viewport_grid_parent.setUpdatesEnabled(False)
        try:
            while self.viewport_grid.count():
                self.viewport_grid.takeAt(0)
            for index in range(3):
                self.viewport_grid.setColumnStretch(index,0)
                self.viewport_grid.setColumnMinimumWidth(index,0)
            if name=="3D planning":
                self.viewport_grid.addWidget(self.scene_panel,0,0,1,3)
                for column,view in enumerate(self.slices):
                    self.viewport_grid.addWidget(view,1,column)
                    self.viewport_grid.setColumnStretch(column,1)
                self.viewport_grid.setRowStretch(0,7)
                self.viewport_grid.setRowStretch(1,3)
                self.tabs.setCurrentIndex(0 if self.mode=="synthetic" else 1)
                self.analysis_toggle.setChecked(False)
            else:
                self.viewport_grid.addWidget(self.slices[0],0,0)
                self.viewport_grid.addWidget(self.scene_panel,0,1)
                self.viewport_grid.addWidget(self.slices[1],1,0)
                self.viewport_grid.addWidget(self.slices[2],1,1)
                self.viewport_grid.setColumnStretch(0,1)
                self.viewport_grid.setColumnStretch(1,1)
                self.viewport_grid.setRowStretch(0,1)
                self.viewport_grid.setRowStretch(1,1)
                research=name=="Research & analysis"
                self.tabs.setCurrentIndex(3 if research else 1)
                self.analysis_toggle.setChecked(research)
        finally:
            self.viewport_grid_parent.setUpdatesEnabled(True)
        self._update_scene_title()
        QTimer.singleShot(0,self.scene.render)

    def change_scene_style(self,name):
        self.scene.set_style(name)
        self._update_scene_title()
        if name=="Lung motion" and self.mode=="synthetic":
            self.vectors.setChecked(True)
        elif name!="Lung motion":
            self.vectors.setChecked(False)

    def _update_scene_title(self):
        name=self.scene_style.currentText()
        long_titles={"CT reconstruction":"3D · CT RECONSTRUCTION",
            "Lung motion":"3D · LUNG MOTION","Anatomy surfaces":"3D · SEGMENTATIONS"}
        short_titles={"CT reconstruction":"3D · CT","Lung motion":"3D · MOTION",
            "Anatomy surfaces":"3D · SURFACES"}
        self.scene_title.setText((long_titles if self.workspace.currentText()=="3D planning"
                                 else short_titles)[name])

    def tab(self,title):
        content=QWidget()
        layout=QVBoxLayout(content)
        layout.setContentsMargins(10,10,10,10)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        self.tabs.addTab(scroll,title)
        return layout

    def spin(self,minimum,maximum,value,step=1,decimals=1):
        widget=QDoubleSpinBox()
        widget.setRange(minimum,maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setValue(value)
        return widget

    def button(self,text,callback,layout,primary=False):
        widget=QPushButton(text)
        widget.setMinimumWidth(0)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        widget.clicked.connect(callback)
        if primary:
            widget.setObjectName("primary")
        layout.addWidget(widget)
        return widget

    def _simulation_tab(self):
        layout=self.tab("Patient")
        form=QFormLayout()
        self.seed=QSpinBox()
        self.seed.setRange(0,999999)
        self.seed.setValue(17)
        form.addRow("Virtual patient",self.seed)
        self.pattern=QComboBox()
        self.pattern.addItems(["Regular","Mild irregularity","Strong irregularity","Stress test"])
        self.pattern.setCurrentIndex(1)
        form.addRow("Breathing",self.pattern)
        self.parameters={}
        for key,title,low,high,value,step in [
            ("amplitude","Amplitude (mm)",0,30,12,1),
            ("frequency","Breaths / minute",6,36,15,1),
            ("noise","Noise SD (mm)",0,4,.5,.1),
            ("delay","Execution delay (s)",0,6,1,.1),
            ("insertion_speed","Insertion (mm/s)",10,150,60,5),
            ("target_radius","Target radius (mm)",3,15,6,1)]:
            widget=self.spin(low,high,value,step)
            self.parameters[key]=widget
            form.addRow(title,widget)
        self.speed=self.spin(.1,4,1,.1)
        form.addRow("Simulation speed",self.speed)
        layout.addWidget(group("Virtual patient / respiration",form))
        self.button("Apply patient parameters",self.apply_parameters,layout,True)
        playback=QHBoxLayout()
        self.play_button=self.button("Play",self.play,playback)
        self.button("Pause",self.pause,playback)
        self.button("Reset",self.reset,playback)
        layout.addLayout(playback)
        phase_note=QLabel("Use the shared 4D phase strip below the imaging views to review respiration.")
        phase_note.setWordWrap(True)
        layout.addWidget(phase_note)
        self.phase_slider=QSlider(Qt.Orientation.Horizontal)
        self.phase_slider.setRange(0,1000)
        self.phase_slider.valueChanged.connect(self.seek_phase)
        layout.addWidget(QLabel("Needle insertion depth"))
        self.depth_slider=QSlider(Qt.Orientation.Horizontal)
        self.depth_slider.setRange(0,1000)
        self.depth_slider.valueChanged.connect(lambda value:self.refresh(True))
        layout.addWidget(self.depth_slider)
        self.button("Execute planned insertion",self.execute,layout,True)
        visibility=QVBoxLayout()
        self.visibility_layout=visibility
        self.visibility_controls={}
        for name,label in [("body","Chest wall"),("left_lung","Left lung"),("right_lung","Right lung"),("ribs","Rib overlay"),("airways","Central airway overlay"),("vessels","Vascular structures"),("target","Lesion")]:
            check=QCheckBox(label)
            check.setChecked(name not in ("body","ribs","airways"))
            check.toggled.connect(lambda checked,n=name:self.scene.visibility(n,checked))
            visibility.addWidget(check)
            self.visibility_controls[name]=check
        self.vectors=QCheckBox("Show displacement vectors (mm)")
        self.vectors.toggled.connect(lambda:self.refresh(False))
        visibility.addWidget(self.vectors)
        self.opacity=QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(5,90)
        self.opacity.setValue(35)
        self.opacity.valueChanged.connect(lambda value:self.scene.transparency(value/100))
        visibility.addWidget(QLabel("Lung tissue opacity"))
        visibility.addWidget(self.opacity)
        self.inspect_structure=QComboBox()
        self.inspect_structure.addItems(["No highlight","left_lung","right_lung","ribs","airways","vessels","target"])
        self.inspect_structure.currentTextChanged.connect(lambda name:self.scene.highlight(name))
        visibility.addWidget(QLabel("Inspect structure"))
        visibility.addWidget(self.inspect_structure)
        self.cutaway=QCheckBox("Anterior tissue cutaway")
        self.cutaway.setChecked(False)
        self.cutaway.setToolTip("Open the CT reconstruction and outer tissue in the same physical plane. Planning obstacles remain unchanged.")
        self.cutaway.toggled.connect(self.update_cutaway)
        visibility.addWidget(self.cutaway)
        self.cutaway_position=QSlider(Qt.Orientation.Horizontal)
        self.cutaway_position.setRange(-90,90)
        self.cutaway_position.setValue(-50)
        self.cutaway_position.setEnabled(False)
        self.cutaway_position.valueChanged.connect(self.update_cutaway)
        self.cutaway_label=QLabel("Cutaway depth · anterior to posterior")
        visibility.addWidget(self.cutaway_label)
        visibility.addWidget(self.cutaway_position)
        layout.addWidget(group("Anatomical visibility",visibility))
        overlays=QVBoxLayout()
        self.overlay_controls={}
        for name,label in [("trajectory","Planned route and entry"),("needle","Inserted needle and tip"),
                           ("prediction","Predicted arrival target"),("uncertainty","Prediction uncertainty"),
                           ("crosshair","Shared slice position")]:
            check=QCheckBox(label)
            check.setChecked(True)
            check.toggled.connect(lambda checked,n=name:self.scene.overlay_visibility(n,checked))
            overlays.addWidget(check)
            self.overlay_controls[name]=check
        layout.addWidget(group("3D planning overlays",overlays))
        layout.addStretch()

    def _imaging_tab(self):
        layout=self.tab("Imaging")
        self.button("Open public CT example",self.load_public_example,layout,True)
        self.button("Synthetic anatomy",self.new_synthetic,layout)
        ct_import=self.button("Import CT volume…",self.import_volume,layout,True)
        ct_import.setToolTip("Open a CT volume in NIfTI (.nii/.nii.gz) or MetaImage (.mha/.mhd) format.")
        self.button("Import DICOM series…",self.import_dicom,layout)
        self.button("Import 4D CT sequence…",self.import_phases,layout)
        self.phase_choice=QComboBox()
        self.phase_choice.currentIndexChanged.connect(self.select_phase)
        layout.addWidget(self.phase_choice)
        layout.addWidget(QLabel("Segmentation role"))
        self.mask_role=QComboBox()
        self.mask_role.addItems(["left_lung","right_lung","ribs","airways","vessels","target","obstacles","body"])
        layout.addWidget(self.mask_role)
        self.button("Load aligned mask…",self.import_mask,layout)
        self.segmentation_visible=QCheckBox("CT segmentation overlays")
        self.segmentation_visible.setChecked(False)
        self.segmentation_visible.toggled.connect(lambda:self.refresh(True))
        layout.addWidget(self.segmentation_visible)
        form=QFormLayout()
        self.ct_preset=QComboBox()
        self.ct_preset.addItems(["Lung","Soft tissue","Bone","Custom"])
        self.ct_preset.currentTextChanged.connect(self.apply_ct_preset)
        form.addRow("Window preset",self.ct_preset)
        self.window_control=self.spin(1,4000,1500,50,0)
        self.level_control=self.spin(-1500,2000,-500,50,0)
        self.window_control.valueChanged.connect(self.window_level)
        self.level_control.valueChanged.connect(self.window_level)
        form.addRow("Window (intensity)",self.window_control)
        form.addRow("Level (intensity)",self.level_control)
        layout.addWidget(group("CT display",form))
        self.follow_target=QCheckBox("Crosshair follows target")
        self.follow_target.setChecked(True)
        self.follow_target.toggled.connect(lambda:self.refresh(True))
        layout.addWidget(self.follow_target)
        self.button("Set target at crosshair",self.define_target,layout)
        self.button("Set entry at crosshair",self.define_entry,layout)
        self.button("Export displayed CT…",self.export_volume,layout)
        self.button("Export phase analysis…",self.export_phase_analysis,layout)
        self.imaging_info=QLabel("")
        self.imaging_info.setWordWrap(True)
        self.imaging_info.setMinimumWidth(0)
        self.imaging_info.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.imaging_info)
        layout.addStretch()

    def _planning_tab(self):
        layout=self.tab("Planning")
        form=QFormLayout()
        self.method=QComboBox()
        self.method.addItems(["Static image","Mathematical sinusoidal","Learned uncertainty-aware","Constant velocity"])
        self.method.setCurrentIndex(1)
        self.method.currentIndexChanged.connect(self.invalidate_plan)
        form.addRow("Method",self.method)
        self.risk=self.spin(.01,1,.2,.05,2)
        self.risk.valueChanged.connect(self.invalidate_plan)
        form.addRow("Allowed miss fraction",self.risk)
        layout.addWidget(group("Trajectory selection",form))
        self.button("Recalculate trajectory",self.replan,layout,True)
        self.button("Inspect planned trajectory",lambda:self.scene.inspect_trajectory(self.plan),layout)
        self.button("Load learned checkpoint",self.load_checkpoint,layout)
        self.model_label=QLabel("Checkpoint: outputs/model/motion_predictor.pt")
        self.model_label.setWordWrap(True)
        self.model_label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.model_label)
        self.plan_info=QPlainTextEdit()
        self.plan_info.setReadOnly(True)
        self.plan_info.setMinimumHeight(170)
        layout.addWidget(self.plan_info)
        self.button("Run evaluated simulation",self.evaluate_current,layout,True)
        self.button("Save current results",self.save_results,layout)
        note=QLabel("Rigid straight needle; fixed direction after insertion starts. Success means a target intersection with no modelled obstacle collision during the sampled insertion interval. Planning clearances are estimates; execution is evaluated separately.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def _research_tab(self):
        layout=self.tab("Research")
        research_scope=QLabel("SYNTHETIC RESEARCH\nThese experiments and predictor training use virtual patients, independently of the CT currently displayed.")
        research_scope.setWordWrap(True)
        layout.addWidget(research_scope)
        form=QFormLayout()
        self.experiment_patients=QSpinBox()
        self.experiment_patients.setRange(2,100)
        self.experiment_patients.setValue(4)
        form.addRow("Held-out patients",self.experiment_patients)
        self.research_config=QLabel("builtin:experiments")
        self.research_config.setWordWrap(True)
        self.research_config.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        form.addRow("Experiment config",self.research_config)
        layout.addLayout(form)
        self.button("Choose experiment configuration",self.choose_research_config,layout)
        self.button("Run synthetic experiments",self.run_research,layout,True)
        self.button("Train synthetic predictor",self.train,layout)
        self.button("View saved research figures",self.show_figures,layout)
        self.research_log=QPlainTextEdit()
        self.research_log.setReadOnly(True)
        self.research_log.setMinimumHeight(300)
        self.research_log.setPlainText("Experiments are not yet run in this session.\n\nAll plots and metrics use computed outcomes. Training and experiments run in a worker thread.\n\nCalibration and evaluation use synthetic data. No claim of clinical safety is made.")
        layout.addWidget(self.research_log)
        layout.addStretch()

    def current_method(self):
        return ["static","sinusoidal","learned","velocity"][self.method.currentIndex()]

    def change_display_quality(self,name):
        self.scene.set_quality(name)
        pixels={"Interactive":256,"Balanced":384,"High":768}[name]
        for view in self.slices:
            view.set_quality(pixels)
        if self.volume is not None:
            self.refresh(True)

    def update_cutaway(self,*args,render=True):
        enabled=self.cutaway.isChecked()
        self.cutaway_position.setEnabled(enabled)
        if self.volume is None:
            return
        bounds=self.volume.bounds[:,1]
        position=self.volume.center.copy()
        position[1]=float(bounds.mean()+self.cutaway_position.value()/100*(bounds[1]-bounds[0])/2)
        self.cutaway_label.setText(f"Cutaway depth · Y {position[1]:+.0f} mm")
        self.scene.set_cutaway(enabled,position=position,render=render)

    def apply_ct_preset(self,name):
        presets={"Lung":(1500,-500),"Soft tissue":(400,40),"Bone":(1800,400)}
        if name not in presets:
            return
        window,level=presets[name]
        for control,value in [(self.window_control,window),(self.level_control,level)]:
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        self.window_level()

    def invalidate_plan(self,*args,refresh=True):
        self.pause()
        self.revision+=1
        self.plan=None
        self.execution_start=None
        self.last_result=None
        self.last_result_source=None
        if hasattr(self,"error_plot"):
            self.error_plot.time=np.array([])
            self.error_plot.actual=np.array([])
            self.error_plot.update()
        if self.volume is not None and refresh:
            self.status.setText("Planning settings changed. Recalculate the trajectory.")
            self.refresh(True)

    def current_patient(self):
        values={key:widget.value() for key,widget in self.parameters.items()}
        values["frequency"]/=60
        return VirtualPatient(seed=self.seed.value(),irregularity=[0,.15,.65,1.][self.pattern.currentIndex()],**values)

    def new_synthetic(self):
        self.pause()
        self.invalidate_plan(refresh=False)
        self.mode="synthetic"
        self.method.setEnabled(True)
        self._supplied_meshes={}
        self.phase_sequence=None
        self.patient=self.current_patient()
        self.motion=RespiratoryModel(self.patient)
        self.time=8.
        self.plan=None
        self.execution_start=None
        baseline=generate_anatomy(seed=self.patient.seed,target_radius=self.patient.target_radius,spacing=4.)
        self.anatomy=generate_anatomy(seed=self.patient.seed,target_radius=self.patient.target_radius,
                                    spacing=2.,reference_target=baseline.target)
        self.synthetic_slices=SyntheticSliceSource(self.anatomy)
        self.source_info=None
        self._mask_sources={name:{"kind":"procedural synthetic anatomy"} for name in self.anatomy.masks}
        self.volume=self.anatomy.volume
        self.masks=self.anatomy.masks
        self.crosshair=self.anatomy.target.copy()
        self.scene.set_volume(self.volume,self.masks,self.anatomy)
        self.badge.setText("SYNTHETIC CT + ANATOMY")
        self.status.setText("Synthetic thoracic CT · 2 mm source sampling · linked reconstruction, masks and respiratory motion")
        self.phase_choice.blockSignals(True)
        self.phase_choice.clear()
        self.phase_choice.setEnabled(False)
        self.phase_choice.blockSignals(False)
        self._update_metadata()
        self.refresh(True)

    def apply_parameters(self):
        if self.mode!="synthetic":
            self.status.setText("Switch to synthetic anatomy to apply virtual-patient parameters.")
            return
        patient=self.current_patient()
        if (patient.seed!=self.patient.seed or patient.target_radius!=self.patient.target_radius
                or self.time < self.motion.last_change_time):
            self.new_synthetic()
        else:
            self.invalidate_plan(refresh=False)
            self.motion.change_patient(patient,self.time)
            self.patient=patient
            self.plan=None
            self.execution_start=None
            self.refresh(True)
        self.replan()

    def actual_target(self):
        if self.mode=="synthetic" and self.anatomy is not None:
            return self.anatomy.target+self.motion.displacement(self.time)
        return self.real_target

    def pause(self):
        if hasattr(self,"timer"):
            self.timer.stop()
        self._last_tick=None

    def play(self):
        if self.mode=="real":
            self.status.setText("Single CT volume: no respiratory motion annotations are available.")
        else:
            self.timer.setInterval(max(25,int(250/self.speed.value())) if self.mode=="phases" else 33)
            self._last_tick=perf_counter()
            self.timer.start()

    def reset(self):
        self.pause()
        self.invalidate_plan(refresh=False)
        self.time=8.
        if self.mode=="synthetic":
            self.motion=RespiratoryModel(self.patient)
        self.plan=None
        self.execution_start=None
        self.depth_slider.setValue(0)
        if self.mode=="phases":
            self.timer.setInterval(max(25,int(250/self.speed.value())))
            self.select_phase(0)
        self.refresh(True)

    def tick(self):
        if self.mode=="phases":
            self.phase_choice.setCurrentIndex((self.phase_index+1)%len(self.phase_sequence))
            return
        if self.mode!="synthetic":
            return
        now=perf_counter()
        elapsed=now-self._last_tick if self.timer.isActive() and self._last_tick is not None else self.timer.interval()/1000
        self._last_tick=now if self.timer.isActive() else None
        self.time+=elapsed*self.speed.value()
        if self.execution_start is not None and self.plan is not None and not self.plan.abstained:
            elapsed=max(0,self.time-self.execution_start-self.patient.delay)
            fraction=min(1,elapsed*self.patient.insertion_speed/self.plan.length)
            self.depth_slider.blockSignals(True)
            self.depth_slider.setValue(int(fraction*1000))
            self.depth_slider.blockSignals(False)
            if fraction>=1:
                self.time=self.execution_start+self.patient.delay+self.plan.length/self.patient.insertion_speed
                self.execution_start=None
                self.pause()
        self.refresh(True)

    def seek_phase(self,value):
        if self.mode=="phases":
            self.phase_choice.setCurrentIndex(min(len(self.phase_sequence)-1,int(value/1001*len(self.phase_sequence))))
        elif self.mode=="synthetic":
            self.pause()
            from scipy.optimize import brentq
            phase=float(self.motion.phase(self.time))
            cycle=np.floor(phase/(2*np.pi))
            target_phase=(cycle+min(value,999)/1000)*2*np.pi
            # Select the requested physical phase in the current or next cycle.
            if target_phase<float(self.motion.phase(8.)):
                target_phase+=2*np.pi
            upper=max(self.time+2/self.patient.frequency,12.)
            while float(self.motion.phase(upper))<target_phase:
                upper+=1/self.patient.frequency
            self.time=float(brentq(lambda t:float(self.motion.phase(t))-target_phase,8.,upper))
            self.execution_start=None
            self.refresh(True)

    def set_crosshair(self,point):
        self.follow_target.blockSignals(True)
        self.follow_target.setChecked(False)
        self.follow_target.blockSignals(False)
        self.crosshair=np.asarray(point)
        self.refresh(True)

    def refresh(self,images=True):
        if self.volume is None:
            return
        started=perf_counter()
        actual=self.actual_target()
        displacement=self.motion.displacement(self.time) if self.mode=="synthetic" else np.zeros(3)
        if self.follow_target.isChecked() and actual is not None:
            self.crosshair=actual.copy()
        self.scene.update_state(displacement,actual,self.plan,self.depth_slider.value()/1000,self.crosshair,self.vectors.isChecked() and self.mode=="synthetic",
            target_radius=self.real_radius if self.mode!="synthetic" and "target" not in self.masks else None,
            render=False,preserve_supplied_vectors=self.mode=="phases" and self.vectors.isChecked())
        if self.mode=="phases" and self.vectors.isChecked():
            points,vectors=self.phase_sequence.motion_vectors(self.phase_index)
            self.scene.supplied_vectors(points,vectors,render=False)
        self.scene.render()
        if images:
            overlays=self.masks if self.segmentation_visible.isChecked() else None
            for view in self.slices:
                kwargs=dict(needle_fraction=self.depth_slider.value()/1000)
                if self.mode=="synthetic":
                    plane,mask_planes=self.synthetic_slices.slice_plane(view.plane_name,self.crosshair,displacement,
                        max_pixels=view.canvas.max_pixels,overlays=overlays is not None)
                    kwargs.update(plane=plane,mask_planes=mask_planes)
                view.set_data(self.volume,self.crosshair,actual,self.patient.target_radius if self.mode=="synthetic" else self.real_radius,self.plan,overlays,**kwargs)
        phase=float(self.motion.phase(self.time)%(2*np.pi)/(2*np.pi)) if self.mode=="synthetic" else self.phase_index/max(1,len(self.phase_sequence)-1) if self.phase_sequence else 0
        self.phase_slider.blockSignals(True)
        self.phase_slider.setValue(int(phase*1000))
        self.phase_slider.blockSignals(False)
        self.phase_readout.setText(f"{phase*100:.0f}% · {self.time:.1f} s" if self.mode=="synthetic"
            else f"{self.phase_index+1}/{len(self.phase_sequence)}" if self.phase_sequence else "Single CT")
        self.metrics["Time / phase"].setText(f"{self.time:.2f} s  /  {phase*100:.0f}%" if self.mode=="synthetic" else self.phase_sequence.identifiers[self.phase_index] if self.phase_sequence else "Single CT")
        self.metrics["Actual target (mm)"].setText(self.point_text(actual))
        if self.plan is not None and not self.plan.abstained:
            p=self.plan
            self.metrics["Predicted arrival (mm)"].setText(self.point_text(p.prediction))
            self.metrics["Trajectory length"].setText(f"{p.length:.1f} mm")
            self.metrics["Obstacle clearance"].setText(f"{p.clearance:.1f} mm  (estimated)")
            self.metrics["Needle depth"].setText(f"{self.depth_slider.value()/1000*p.length:.1f} mm")
            self.metrics["Planning latency"].setText(f"{p.latency_ms:.1f} ms")
            self.metrics["Uncertainty"].setText(f"SD {np.sqrt(np.trace(p.covariance)):.1f} mm" if np.all(np.isfinite(p.covariance)) else "Not calibrated for baseline")
            if self.mode=="synthetic" and self.time>=self.plan_time+p.horizon:
                truth=self.anatomy.target+self.motion.displacement(self.plan_time+p.horizon)
                error=float(np.linalg.norm(truth-p.prediction))
                self.metrics["Prediction error"].setText(f"{error:.2f} mm  (evaluated)")
            else:
                self.metrics["Prediction error"].setText("Awaiting arrival time")
        elif self.plan is not None:
            self.metrics["Outcome"].setText("Planner abstained")
        if self.plan is None or self.plan.abstained:
            for key in ("Predicted arrival (mm)","Trajectory length","Obstacle clearance","Prediction error","Targeting error","Obstacle violations","Needle depth","Planning latency","Uncertainty"):
                self.metrics[key].setText("—")
            if self.plan is None:
                self.metrics["Outcome"].setText("No current plan")
        if self.mode=="synthetic":
            times=np.linspace(max(0,self.time-10),self.time,130)
            self.trace_plot.time=times
            self.trace_plot.actual=self.motion.displacement(times)[:,2]
            self.trace_plot.predicted=None if self.plan is None or self.plan.abstained else (self.plan_time+self.plan.horizon,self.plan.prediction[2]-self.anatomy.target[2])
            self.trace_plot.update()
        self.display_frame_ms=(perf_counter()-started)*1000
        self.display_info.setText(f"{self.display_quality.currentText()} display · {self.display_frame_ms:.0f} ms update · rulers in mm · CT and 3D share the current phase")

    @staticmethod
    def point_text(point):
        return "—" if point is None else "  ".join(f"{value:+.1f}" for value in point)

    def task(self,function,callback,label):
        if self.worker is not None:
            self.status.setText("A computation is already running; wait for its result.")
            return
        self.pause()
        self.tabs.setEnabled(False)
        self.phase_panel.setEnabled(False)
        self.status.setText(label)
        self.worker=Worker(function)
        revision=self.revision
        self.worker.result.connect(lambda result:self._task_result(callback,result,revision))
        self.worker.failed.connect(self._task_failed)
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _task_result(self,callback,result,revision):
        if revision!=self.revision:
            self.status.setText("Discarded a result from an earlier patient or plan state.")
            return
        try:
            callback(result)
        except Exception:
            self._task_failed(traceback.format_exc())

    def _task_failed(self,message):
        self.status.setText("Computation failed; details are shown in Research.")
        self.research_log.setPlainText(message)
        QMessageBox.warning(self,"MotionTwin computation",message[-1500:])

    def _task_finished(self):
        self.worker.deleteLater()
        self.worker=None
        self.tabs.setEnabled(True)
        self.phase_panel.setEnabled(self.mode!="real")

    def replan(self):
        if self.worker is not None:
            return
        self.pause()
        if self.mode!="synthetic":
            self.real_plan()
            return
        times=np.linspace(max(0,self.time-8),self.time,81)
        observations=self.motion.observe(times,self.anatomy.target)
        instant=self.time
        anatomy,patient,method=self.anatomy,self.patient,self.current_method()
        risk,checkpoint=self.risk.value(),self.checkpoint
        def accepted(plan):
            self.plan_time=instant
            self.accept_plan(plan)
        self.task(lambda:plan_trajectory(anatomy,times,observations,method,patient.delay,patient.insertion_speed,risk,checkpoint),accepted,"Calculating finite candidate trajectories…")

    def accept_plan(self,plan):
        self.plan=plan
        self.last_result=None
        self.last_result_source=None
        self.metrics["Targeting error"].setText("Awaiting evaluation")
        self.metrics["Obstacle violations"].setText("Awaiting evaluation")
        self.depth_slider.setValue(0)
        self.execution_start=None
        self.status.setText(plan.reason)
        self.metrics["Outcome"].setText("Abstained" if plan.abstained else "Ready for simulated insertion")
        details={"method":plan.method,"abstained":plan.abstained,"reason":plan.reason,
                 "entry_mm":None if plan.entry is None else plan.entry.tolist(),
                 "endpoint_mm":None if plan.endpoint is None else plan.endpoint.tolist(),
                 "path_length_mm":plan.length,"clearance_mm":plan.clearance,
                 "arrival_horizon_s":plan.horizon,"planning_latency_ms":plan.latency_ms}
        self.plan_info.setPlainText(json.dumps(details,indent=2))
        self.refresh(True)

    def execute(self):
        if self.plan is None or self.plan.abstained:
            self.status.setText("Calculate an accepted trajectory before insertion.")
            return
        if self.mode!="synthetic":
            self.depth_slider.setValue(1000)
            return
        self.time=self.plan_time
        self.execution_start=self.time
        self.depth_slider.blockSignals(True)
        self.depth_slider.setValue(0)
        self.depth_slider.blockSignals(False)
        self.refresh(True)
        self.play()

    def evaluate_current(self):
        if self.mode!="synthetic":
            self.status.setText("Research episode evaluation requires synthetic ground truth.")
            return
        if self.plan is None:
            self.status.setText("Calculate a trajectory before evaluating the displayed plan.")
            return
        import copy
        patient,method,checkpoint,risk=self.patient,self.current_method(),self.checkpoint,self.risk.value()
        plan,anatomy,motion,instant=copy.deepcopy(self.plan),self.anatomy,copy.deepcopy(self.motion),self.plan_time
        self.task(lambda:run_episode(patient,method,checkpoint,risk,planning_time=instant,
            anatomy=anatomy,planned_trajectory=plan,motion_model=motion),self.accept_result,"Evaluating the displayed plan against moving target and obstacle interactions…")

    def accept_result(self,result):
        self.last_result=result
        self.last_result_source={"kind":"synthetic episode","patient_seed":self.patient.seed,
                                 "planning_time_s":self.plan_time}
        scalar={key:value for key,value in result.items() if key!="trace"}
        self.research_log.setPlainText(json.dumps(scalar,indent=2))
        if result["abstained"]:
            self.metrics["Outcome"].setText("Abstained")
        else:
            self.metrics["Outcome"].setText("Simulated hit" if result["hit"] else "Simulated miss / violation")
            self.metrics["Prediction error"].setText(f"{result['forecast_error']:.2f} mm")
            self.metrics["Targeting error"].setText(f"{result['targeting_error']:.2f} mm")
            self.metrics["Obstacle violations"].setText("Yes" if result["obstacle_violation"] else "None at evaluated steps")
            trace=result.get("trace",{})
            if trace:
                actual=np.asarray(trace["actual"])
                predicted=np.asarray(trace["predicted"])
                self.error_plot.time=np.asarray(trace["time"])
                self.error_plot.actual=np.linalg.norm(actual-predicted,axis=1)
                self.error_plot.update()
        self.status.setText("Episode evaluated. Save results or run paired research experiments.")

    def load_checkpoint(self):
        path,_=QFileDialog.getOpenFileName(self,"Load MotionTwin checkpoint","outputs","PyTorch checkpoint (*.pt *.pth)")
        if path:
            self.checkpoint=path
            self.model_label.setText(f"Checkpoint: {path}")
            self.invalidate_plan()

    def import_volume(self):
        path,_=QFileDialog.getOpenFileName(self,"Import CT volume","","Volumes (*.nii *.nii.gz *.mha *.mhd)")
        if path:
            self.task(lambda:load_volume(path),self.accept_volume,"Reading CT with physical-coordinate metadata…")

    def load_public_example(self):
        """Load an attributed real CT example without inventing planning data."""
        from motiontwin import load_public_sample
        from motiontwin import prepare_display_meshes

        def prepare():
            volume,masks,provenance=load_public_sample(cache_dir="data/public-example")
            meshes=prepare_display_meshes(volume,masks,max_cells=100000)
            return volume,masks,meshes,provenance

        def accepted(result):
            volume,masks,meshes,provenance=result
            self.accept_volume(volume,masks=masks,prebuilt_meshes=meshes,source_info=provenance)
            self.badge.setText("PUBLIC CT EXAMPLE · DERIVED DISPLAY MASKS")
            self.status.setText("Public CT example · static imaging study · threshold-derived display masks; target and planning annotations are not supplied.")

        self.task(prepare,accepted,"Opening the public CT example and preparing display reconstructions…")

    def import_dicom(self):
        path=QFileDialog.getExistingDirectory(self,"Select one DICOM series directory")
        if path:
            self.task(lambda:load_volume(path),self.accept_volume,"Reading a single DICOM series…")

    def accept_volume(self,volume,*,masks=None,prebuilt_meshes=None,source_info=None):
        self.pause()
        self.invalidate_plan(refresh=False)
        self.mode="real"
        self.method.setCurrentIndex(0)
        self.method.setEnabled(False)
        self.anatomy=None
        self.synthetic_slices=None
        self.source_info=None if source_info is None else dict(source_info)
        self._supplied_meshes={} if prebuilt_meshes is None else dict(prebuilt_meshes)
        self.phase_sequence=None
        self.phase_choice.blockSignals(True)
        self.phase_choice.clear()
        self.phase_choice.setEnabled(False)
        self.phase_choice.blockSignals(False)
        self.volume=volume
        self.masks={} if masks is None else dict(masks)
        self._mask_sources={name:{"kind":"derived display mask" if source_info else "supplied segmentation"}
                            for name in self.masks}
        self.plan=None
        self.real_target=None
        self.real_entry=None
        self.crosshair=volume.center
        self.scene.set_volume(volume,self.masks,prebuilt_meshes=self._supplied_meshes)
        self.badge.setText("SUPPLIED CT · NO SEGMENTATIONS")
        self.status.setText("CT imported. Load aligned masks to reconstruct anatomy; define a target and entry for geometric planning.")
        self._update_metadata()
        self.refresh(True)

    def import_mask(self):
        if self.mode=="synthetic":
            self.status.setText("Import a CT volume before adding patient segmentation masks.")
            return
        if self.mode=="phases":
            self.status.setText("Supply phase-specific masks in the phase manifest so their provenance and phase mapping remain explicit.")
            return
        path,_=QFileDialog.getOpenFileName(self,"Load aligned label image","","Volumes (*.nii *.nii.gz *.mha *.mhd)")
        if not path:
            return
        label,ok=QInputDialog.getInt(self,"Segmentation label","Label number (0 means all nonzero labels)",0,0,65535)
        if not ok:
            return
        role=self.mask_role.currentText()
        reference=self.volume
        def prepare():
            mask=load_mask(path,reference,label=label if label else None)
            return mask,mesh_from_mask(mask,reference)
        self.task(prepare,lambda result:self.accept_mask(role,*result,source_path=path),"Validating segmentation and reconstructing its surface…")

    def accept_mask(self,role,mask,mesh=None,*,source_path=None):
        if not np.any(mask):
            self.status.setText(f"The selected {role} label is empty; the existing structure was retained.")
            return
        self.invalidate_plan(refresh=False)
        self.masks[role]=mask
        self._mask_sources[role]={"kind":"user-loaded segmentation","source_path":source_path}
        self._supplied_meshes[role]=mesh if mesh is not None else mesh_from_mask(mask,self.volume)
        self.plan=None
        if role=="target" and np.any(mask):
            self.real_target=self.volume.index_to_world(np.argwhere(mask).mean(axis=0)[::-1])
            points=self.volume.index_to_world(np.argwhere(mask)[:,::-1])
            self.real_radius=float(np.max(np.linalg.norm(points-self.real_target,axis=1)))
        self.scene.set_volume(self.volume,self.masks,prebuilt_meshes=self._supplied_meshes)
        self.badge.setText("PUBLIC CT · DERIVED + LOADED MASKS" if self.source_info else "SUPPLIED CT + SEGMENTATIONS")
        self.status.setText(f"Loaded {role} segmentation in the CT's physical coordinates.")
        self._update_metadata()
        self.refresh(True)

    def import_phases(self):
        path,_=QFileDialog.getOpenFileName(self,"Open ordered 4D CT manifest","","Phase manifest (*.json *.yaml *.yml)")
        if path:
            def load():
                sequence=PhaseSequence.from_manifest(path)
                return sequence,sequence.get(0),sequence.meshes(0)
            self.task(load,self.accept_phases,"Reading ordered respiratory phases…")

    def accept_phases(self,result):
        sequence,frame=result[:2]
        self.pause()
        self.phase_sequence=sequence
        self.mode="phases"
        self.anatomy=None
        self.synthetic_slices=None
        self.source_info=None
        self._displayed_phase_sequence=None
        self._supplied_meshes={}
        self.plan=None
        self.real_entry=None
        self.phase_choice.blockSignals(True)
        self.phase_choice.clear()
        self.phase_choice.addItems(sequence.identifiers)
        self.phase_choice.setEnabled(True)
        self.phase_choice.blockSignals(False)
        self.apply_phase(0,frame,result[2] if len(result)>2 else None)

    def select_phase(self,index):
        if self.phase_sequence is None or index<0:
            return
        if self.worker is not None:
            return
        playing=self.timer.isActive()
        sequence=self.phase_sequence
        def loaded(result):
            frame,meshes=result
            self.apply_phase(index,frame,meshes)
            if playing:
                self.play()
        self.task(lambda:(sequence.get(index),sequence.meshes(index)),loaded,"Loading respiratory phase and cached surfaces…")

    def apply_phase(self,index,frame,meshes=None):
        self.invalidate_plan(refresh=False)
        self.method.setCurrentIndex(0)
        self.method.setEnabled(False)
        previous_camera=self.scene.camera_position
        preserve_camera=self._displayed_phase_sequence is self.phase_sequence
        self.phase_index=index
        self.real_entry=None
        self.volume,self.masks=frame.volume,frame.masks
        self._mask_sources={name:{"kind":"supplied phase segmentation","phase_identifier":frame.identifier}
                            for name in self.masks}
        self.real_target=self.phase_sequence.target_at(index)
        if np.any(self.masks.get("target",False)):
            points=self.volume.index_to_world(np.argwhere(self.masks["target"])[:,::-1])
            self.real_radius=float(np.max(np.linalg.norm(points-self.real_target,axis=1)))
        else:
            self.real_radius=float(self.phase_sequence.phases[index].get("target_radius",self.parameters["target_radius"].value()))
        self.plan=None
        self.crosshair=self.real_target.copy() if self.real_target is not None else self.volume.center
        self.scene.set_volume(self.volume,self.masks,prebuilt_meshes=meshes)
        self._displayed_phase_sequence=self.phase_sequence
        if preserve_camera:
            self.scene.camera_position=previous_camera
        self.badge.setText("SUPPLIED 4D CT · DISCRETE PHASES")
        self.status.setText(f"Phase {frame.identifier} · {'marked registered by supplied manifest' if frame.registered else 'registration not assumed'} · discrete playback")
        self._update_metadata()
        self.refresh(True)

    def define_target(self):
        if self.mode=="synthetic":
            self.status.setText("Synthetic target location is defined by the virtual patient.")
            return
        if self.mode=="phases":
            self.status.setText("Supply phase-specific target annotations or target masks in the phase manifest.")
            return
        self.invalidate_plan(refresh=False)
        self.real_target=self.crosshair.copy()
        self.real_radius=self.parameters["target_radius"].value()
        if "target" in self.masks:
            self.masks.pop("target")
            self._mask_sources.pop("target",None)
            self._supplied_meshes.pop("target",None)
            self.scene.set_volume(self.volume,self.masks,prebuilt_meshes=self._supplied_meshes)
            self._update_metadata()
        self.plan=None
        self.status.setText("User-defined spherical target at crosshair; radius from the target-radius control.")
        self.refresh(True)

    def define_entry(self):
        if self.mode=="synthetic":
            self.status.setText("Synthetic entries are selected from the designated thoracic surface.")
            return
        self.invalidate_plan(refresh=False)
        self.real_entry=self.crosshair.copy()
        self.refresh(True)
        self.status.setText("User-defined entry at crosshair. Supply obstacle masks before planning.")

    def real_plan(self):
        from scipy.ndimage import distance_transform_edt, map_coordinates
        from time import perf_counter
        if self.real_entry is None or self.real_target is None:
            self.status.setText("Define a target and entry in CT views before geometric planning.")
            return
        obstacles=[mask for name,mask in self.masks.items() if name in ("ribs","vessels","airways","obstacles")]
        if not obstacles:
            self.status.setText("Load an obstacle segmentation to evaluate this patient-derived route.")
            return
        started=perf_counter()
        entry,target=self.real_entry.copy(),self.real_target.copy()
        length=float(np.linalg.norm(target-entry))
        if length<1e-6:
            self.status.setText("Entry and target must be different physical points.")
            return
        points=np.linspace(entry,target,max(2,int(np.ceil(length/.5))+1))
        indices=self.volume.world_to_index(points)
        if np.any(indices<0) or np.any(indices>np.array(self.volume.shape[::-1])-1):
            self.status.setText("Route leaves the CT field of view; obstacle status is unknown.")
            return
        distances=distance_transform_edt(~np.logical_or.reduce(obstacles),sampling=self.volume.spacing[::-1])
        # EDT gives voxel-centre distances; cover voxel extent and path sampling.
        clearance=float(np.min(map_coordinates(distances,indices[:,::-1].T,order=1))-.8-.5*np.linalg.norm(self.volume.spacing)-.25)
        plan=Plan(entry=entry,endpoint=target,prediction=target.copy(),length=length,clearance=clearance,
                  horizon=0.,latency_ms=(perf_counter()-started)*1000,abstained=bool(clearance<1),
                  reason="Static supplied-volume route; conservative voxel-distance estimate, sampled every ≤0.5 mm" if clearance>=1 else "Route violates supplied obstacle clearance",method="static supplied CT")
        self.plan_time=self.time
        self.accept_plan(plan)

    def _update_metadata(self):
        if self.mode!="synthetic":
            for plot in (self.trace_plot,self.error_plot):
                plot.time=np.array([])
                plot.actual=np.array([])
                plot.predicted=None
                plot.update()
        source=f"VP-{self.patient.seed:04d}" if self.mode=="synthetic" else "4D CT sequence" if self.mode=="phases" else "Supplied CT"
        spacing=" × ".join(f"{value:g}" for value in self.volume.spacing)
        self.study_metadata.setText(f"{source}   /   {self.volume.shape[0]} slices   /   {spacing} mm   /   LPS")
        self.study_metadata.setToolTip(self.volume.name)
        self.phase_slider.setEnabled(self.mode!="real")
        self.phase_panel.setEnabled(self.mode!="real" and self.worker is None)
        self.phase_label.setText("STATIC CT" if self.mode=="real" else "4D PHASE")
        self.phase_choice.setEnabled(self.mode=="phases")
        self.scene_style.model().item(1).setEnabled(self.mode!="real")
        self.vectors.setEnabled(self.mode!="real")
        if self.mode=="real":
            if self.scene_style.currentText()=="Lung motion":
                self.scene_style.setCurrentText("CT reconstruction")
            self.vectors.setChecked(False)
        loaded_masks=[name for name,source in self._mask_sources.items()
                      if source.get("kind")=="user-loaded segmentation"]
        source_label=("SYNTHETIC CT + ANATOMY" if self.mode=="synthetic" else
            "PUBLIC CT · STATIC · DERIVED + LOADED MASKS" if self.source_info and loaded_masks else
            "PUBLIC CT · STATIC · DERIVED DISPLAY MASKS" if self.source_info else
            "SUPPLIED 4D CT · "+self.phase_sequence.identifiers[self.phase_index] if self.phase_sequence else
            "SUPPLIED CT · STATIC")
        self.scene.set_source_label(source_label,render=False)
        segmentation_source=("Procedural anatomical masks" if self.mode=="synthetic" else
            "Derived display masks + loaded segmentations" if self.source_info and loaded_masks else
            "Derived display masks" if self.source_info else "Supplied masks" if self.masks else "No segmentations loaded")
        self.imaging_info.setText(f"{self.volume.name}\nArray z,y,x: {self.volume.shape}\nSpacing x,y,z: {self.volume.spacing} mm\nOrigin LPS: {self.volume.origin}\nWorld coordinate system: LPS\n{segmentation_source}\nRegistration is not assumed.")
        if self.source_info:
            source_name=self.source_info.get("name",self.volume.name)
            self.study_metadata.setText(f"{source_name}   /   {self.volume.shape[0]} slices   /   {spacing} mm")
            attribution="\n\nPublic sample provenance\n"+"\n".join(
                f"{key.replace('_',' ').title()}: {value}" for key,value in self.source_info.items()
                if key in ("name","source_url","license","sha256","checksum"))
            self.imaging_info.setText(self.imaging_info.text()+attribution+
                "\nDisplay masks are derived for visualisation. They are not supplied clinical segmentations or planning obstacle annotations.")
            if loaded_masks:
                self.imaging_info.setText(self.imaging_info.text()+
                    "\nSeparately loaded segmentation roles: "+", ".join(loaded_masks))
        labels=self.source_info.get("display_labels",{}) if self.source_info else {}
        virtual_body=(self.mode!="synthetic" and "body" not in self.masks
                      and any("lung" in name for name in self.masks))
        for name in self.scene.structure_actors:
            if name not in self.visibility_controls:
                check=QCheckBox(labels.get(name,name.replace('_',' ').title()))
                check.setChecked(True)
                check.toggled.connect(lambda checked,n=name:self.scene.visibility(n,checked))
                self.visibility_layout.insertWidget(0,check)
                self.visibility_controls[name]=check
        for name,check in self.visibility_controls.items():
            if name=="body":
                check.setText("CT context outside lung masks" if virtual_body else "Thoracic context")
                check.setToolTip("Show source CT density outside the known lung masks. This changes display context only.")
            elif name in loaded_masks:
                check.setText(name.replace('_',' ').title()+" (loaded)")
            elif name in labels:
                check.setText(labels[name])
            elif check.text().endswith((" (loaded)"," (derived)")):
                check.setText(name.replace('_',' ').title())
            check.setVisible(name in self.scene.structure_actors or (name=="body" and virtual_body))
            self.scene.visibility(name,check.isChecked(),render=False)
        previous=self.inspect_structure.currentText()
        self.inspect_structure.blockSignals(True)
        self.inspect_structure.clear()
        self.inspect_structure.addItems(["No highlight",*self.scene.structure_actors])
        self.inspect_structure.setCurrentText(previous if previous in self.scene.structure_actors else "No highlight")
        self.inspect_structure.blockSignals(False)
        self.scene.transparency(self.opacity.value()/100,render=False)
        self.update_cutaway(render=False)

    def export_phase_analysis(self):
        if self.phase_sequence is None:
            self.status.setText("Load an ordered phase sequence before analysing annotations.")
            return
        from motiontwin import analyse_phases
        sequence=self.phase_sequence
        destination=Path("outputs/phase_analysis")
        self.task(lambda:analyse_phases(sequence,destination),lambda result:self.accept_phase_analysis(result),"Analysing supplied phase target annotations…")

    def accept_phase_analysis(self,result):
        self.research_log.setPlainText(json.dumps(result,indent=2))
        self.status.setText("Phase annotation coordinates and available displacement summaries exported to outputs/phase_analysis.")

    def window_level(self):
        values=(self.window_control.value(),self.level_control.value())
        name=next((name for name,preset in {"Lung":(1500,-500),"Soft tissue":(400,40),"Bone":(1800,400)}.items()
                   if preset==values),"Custom")
        self.ct_preset.blockSignals(True)
        self.ct_preset.setCurrentText(name)
        self.ct_preset.blockSignals(False)
        for view in getattr(self,"slices",[]):
            view.canvas.window=self.window_control.value()
            view.canvas.level=self.level_control.value()
            view.canvas.update()

    def export_volume(self):
        path,_=QFileDialog.getSaveFileName(self,"Export displayed CT","outputs/displayed_ct.mha","MetaImage (*.mha);;NIfTI (*.nii.gz)")
        if path:
            anatomy=self.anatomy
            displacement=self.motion.displacement(self.time) if self.mode=="synthetic" else None
            volume=self.volume
            def export():
                displayed=anatomy.volume_at(displacement) if displacement is not None else volume
                save_volume(displayed,path)
                return path
            self.task(export,lambda saved:self.status.setText(f"Exported displayed CT: {saved}"),"Writing the CT at the displayed phase…")

    def save_results(self):
        destination=Path("outputs/sessions")/datetime.now().strftime("%Y%m%d_%H%M%S")
        destination.mkdir(parents=True,exist_ok=True)
        def clean(value):
            if isinstance(value,np.ndarray): return clean(value.tolist())
            if isinstance(value,np.generic): return clean(value.item())
            if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
            if isinstance(value,list): return [clean(v) for v in value]
            if isinstance(value,float) and not np.isfinite(value): return None
            return value
        volume_metadata=(None if self.volume is None else dict(name=self.volume.name,
            shape_zyx=self.volume.shape,spacing_xyz_mm=self.volume.spacing,
            origin_lps_mm=self.volume.origin,direction=self.volume.direction,
            coordinate_system="LPS millimetres"))
        payload=dict(mode=self.mode,patient=asdict(self.patient) if self.mode=="synthetic" else None,
            time=self.time if self.mode=="synthetic" else None,
            source_info=self.source_info,volume=volume_metadata,mask_sources=self._mask_sources,
            phase_identifier=self.phase_sequence.identifiers[self.phase_index] if self.phase_sequence else None,
            phase_index=self.phase_index if self.phase_sequence else None,
            target_lps_mm=self.actual_target(),entry_lps_mm=self.real_entry if self.mode!="synthetic" else None,
            target_radius_mm=(self.patient.target_radius if self.mode=="synthetic" else self.real_radius)
                if self.actual_target() is not None else None,
            plan=asdict(self.plan) if self.plan else None,
            latest_result=self.last_result if self.last_result_source is not None else None,
            latest_result_source=self.last_result_source)
        (destination/"session.json").write_text(json.dumps(clean(payload),indent=2,allow_nan=False),encoding="utf-8")
        QApplication.primaryScreen().grabWindow(self.winId()).save(str(destination/"workstation.png"))
        self.scene.screenshot(str(destination/"anatomy.png"))
        self.status.setText(f"Saved computed state and workstation images: {destination}")

    def choose_research_config(self):
        path,_=QFileDialog.getOpenFileName(self,"Experiment settings","configs","YAML (*.yaml *.yml)")
        if path:
            self.research_config.setText(path)

    def run_research(self):
        from motiontwin import run_experiments
        try:
            config=load_config(self.research_config.text())
        except Exception as exc:
            self.status.setText(f"Experiment configuration could not be loaded: {exc}")
            return
        settings=config
        if isinstance(config.get("research"),dict):
            settings=config["research"]
        elif isinstance(config.get("experiments"),dict):
            settings=config["experiments"]
        settings["patients"]=self.experiment_patients.value()
        checkpoint=self.checkpoint if Path(self.checkpoint).is_file() else None
        self.task(lambda:run_experiments(config,checkpoint=checkpoint),self.accept_research,"Running configured paired patient experiments in the background…")

    def accept_research(self,result):
        self.last_result=result
        self.last_result_source={"kind":"synthetic experiments","config":self.research_config.text(),
                                 "displayed_ct_used":False}
        lines=[f"Completed: {', '.join(result['completed_experiments'])}",
               f"{result['patient_count']} held-out patients; {result['outcome_count']} paired episode outcomes",
               f"Exports: {result['output_dir']}",
               "Intervals resample whole virtual patients.",
               "Hit rate includes abstention; targeting error uses executed plans.", ""]
        def number(value,percent=False):
            if value is None:
                return "unavailable"
            return f"{value*100:.1f}%" if percent else f"{value:.2f}"
        for group in result["summary"]:
            metrics=group["metrics"]
            lines.extend([f"{group['experiment']} / {group['condition']} / {group['method']} / {group['variant']}",
                          f"  MAE {number(metrics['targeting_mae_mm'])} mm; hit {number(metrics['hit_rate'],True)}; abstain {number(metrics['abstention_rate'],True)}",
                          f"  Violation/executed {number(metrics['obstacle_violation_rate'],True)}; mean latency {number(metrics['mean_planning_latency_ms'])} ms"])
        lines.extend(["", "Limitations:", *result.get("limitations",[])])
        self.research_log.setPlainText("\n".join(lines))
        self.status.setText(f"Research complete. Computed results exported to {result.get('output_dir','outputs/experiments')}.")

    def train(self):
        from motiontwin import train_model
        config=load_config("builtin:default")
        self.task(lambda:train_model(config),self.accept_training,"Training and calibrating a synthetic respiratory predictor…")

    def accept_training(self,result):
        self.last_result=result
        self.last_result_source={"kind":"synthetic predictor training","config":"configs/default.yaml",
                                 "displayed_ct_used":False}
        self.research_log.setPlainText(json.dumps(result,indent=2,default=str))
        checkpoint=result.get("checkpoint") or result.get("checkpoint_path")
        if checkpoint:
            self.checkpoint=str(checkpoint)
            self.model_label.setText(f"Checkpoint: {checkpoint}")
        self.status.setText("Training complete; held-out metrics are available in Research.")

    def show_figures(self):
        from PySide6.QtWidgets import QDialog
        from PySide6.QtGui import QPixmap
        paths=list(Path("outputs/experiments").rglob("*.png"))
        if not paths:
            self.status.setText("No research figures exist yet. Run experiments first.")
            return
        dialog=QDialog(self)
        dialog.setWindowTitle("MotionTwin | Computed research figures")
        dialog.resize(1080,760)
        layout=QVBoxLayout(dialog)
        choice=QComboBox()
        choice.addItems([path.name for path in paths])
        layout.addWidget(choice)
        image=QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image,1)
        def show(index):
            image.setPixmap(QPixmap(str(paths[index])).scaled(1030,660,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        choice.currentIndexChanged.connect(show)
        show(0)
        dialog.exec()

    def closeEvent(self,event):
        self.pause()
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("A background computation is still running. Close the workstation after it finishes.")
            event.ignore()
            return
        self.scene.close()
        event.accept()


def launch(demo=False):
    import sys
    from motiontwin import cached_public_sample_available
    app=QApplication.instance() or QApplication(sys.argv[:1])
    initial_source="public-example" if not demo and cached_public_sample_available() else "synthetic"
    window=MainWindow(demo=demo,initial_source=initial_source)
    window.show()
    return app.exec()


# Command-line entrypoint
import argparse
from pathlib import Path
import json

from motiontwin import load_config


def main(argv=None):
    import os
    os.chdir(Path(__file__).resolve().parent)
    parser=argparse.ArgumentParser(prog="motiontwin",description="Respiratory motion research workstation")
    commands=parser.add_subparsers(dest="command",required=False)
    commands.add_parser("gui",help="Launch the desktop workstation")
    commands.add_parser("demo",help="Launch self-contained synthetic anatomy and CT")
    training=commands.add_parser("train",help="Train and calibrate the PyTorch predictor")
    training.add_argument("--config",default="builtin:default")
    training.add_argument("--output",default="outputs/model")
    evaluation=commands.add_parser("evaluate",help="Run paired virtual-patient experiments")
    evaluation.add_argument("--config",default="builtin:experiments")
    evaluation.add_argument("--output",default="outputs/experiments")
    evaluation.add_argument("--checkpoint",default=None)
    args=parser.parse_args(argv)
    if args.command is None:
        args.command="gui"
    if args.command in ("gui","demo"):
        pass  # Desktop launch is defined above.
        return launch(demo=args.command=="demo")
    if args.command=="train":
        from motiontwin import train_model
        result=train_model(load_config(args.config),args.output)
    else:
        from motiontwin import run_experiments
        checkpoint=args.checkpoint
        if checkpoint is None and Path("outputs/model/motion_predictor.pt").is_file():
            checkpoint="outputs/model/motion_predictor.pt"
        result=run_experiments(load_config(args.config),args.output,checkpoint)
    print(json.dumps(result,indent=2,default=str))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
