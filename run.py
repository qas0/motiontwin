"""Run MotionTwin, including VS Code's Run Python File action.

This file contains the desktop interface, linked CT/3D renderers and CLI.
The CT loading and display geometry are in motiontwin.py.
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


STYLE = """
QMainWindow, QWidget { background:#10151d; color:#d9e1e9; font-family:'Segoe UI'; font-size:12px; }
QWidget#studyStrip { background:#142136; border-bottom:1px solid #2b3f59; }
QLabel#brand { font-size:22px; font-weight:650; color:#f0f6fb; background:transparent; }
QLabel#studySubtitle { font-size:10px; color:#9bb0c6; background:transparent; }
QLabel#studyMetadata { color:#aebfd0; font-size:11px; background:transparent; }
QLabel#badge { color:#76dde2; background:#173b46; border:1px solid #285464; border-radius:3px; padding:5px 8px; font-size:10px; font-weight:650; }
QLabel#statusLine { color:#a7b8c9; font-size:11px; padding:1px 2px; }
QWidget#viewportPanel { background:#05080d; border:1px solid #364555; }
QWidget#viewportToolbar { background:#1d2a3d; border-bottom:2px solid #7091b7; }
QWidget#viewportToolbar QLabel { background:transparent; font-size:10px; color:#c9d8e8; font-weight:600; }
QToolButton { background:#26354a; border:1px solid #3c4e66; padding:6px 9px; border-radius:3px; }
QToolButton:hover { background:#354c65; border-color:#6888a6; }
QToolButton:pressed { background:#182e42; }
QToolButton:disabled { color:#64778d; background:#1a2533; }
QMenuBar, QMenu { background:#151d28; color:#d9e1e9; }
QMenuBar::item:selected, QMenu::item:selected { background:#2e526c; }
QMenu::item:disabled { color:#64778d; }
QComboBox, QDoubleSpinBox { background:#0d141f; border:1px solid #354359; padding:5px; border-radius:3px; selection-background-color:#285a75; }
QComboBox:hover, QDoubleSpinBox:hover { border-color:#5f7b97; }
QComboBox::drop-down { width:18px; border:0; }
QComboBox QAbstractItemView { background:#172334; selection-background-color:#2e526c; }
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

import argparse
from pathlib import Path
import traceback

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction, vtkVolume, vtkVolumeProperty
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkOpenGLGPUVolumeRayCastMapper
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QLabel, QComboBox, QDoubleSpinBox, QSlider,
    QSplitter, QCheckBox, QFileDialog, QMessageBox, QScrollArea,
    QGroupBox, QInputDialog, QGridLayout, QToolButton, QSizePolicy)

from motiontwin import (Volume, load_volume, load_mask, mesh_from_mask,
    prepare_display_meshes, attach_ct_scalars, load_public_sample,
    cached_public_sample_available)

COLORS = {"left_lung": "#79b5bf", "right_lung": "#8ec6cc",
          "lungs": "#83bac5", "vascular_display": "#cb766e"}
STATIC_DISPLAY_LIMITS = {"Interactive": 1_200_000, "Balanced": 3_000_000, "High": 8_000_000}

def static_display_strides(shape, spacing, quality):
    """XYZ strides balance physical resolution under a static-image memory cap.

    Thin in-plane CT pixels must be decimated before thick source slices. A
    uniform index stride would turn a 2.5 mm slice gap into 10 mm while still
    oversampling the transverse plane. The existing static CT sampling limits
    are retained for the lung viewer.
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



class ScanReconstruction:
    """Retained static CT ray caster; source HU and geometry are unchanged."""

    def __init__(self):
        self.quality = "Balanced"
        self.plotter = self.volume = None
        self.actor = self.mapper = self.grid = None
        self.opacity = .35
        self.masks = {}
        self._structure_visibility = {}

    def attach(self, plotter, volume, masks=None):
        self.detach()
        self.plotter, self.volume = plotter, volume
        self.masks = masks or {}
        if any(np.asarray(mask).shape != volume.shape for mask in self.masks.values()):
            raise ValueError("CT reconstruction masks must match the source image geometry.")
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
        return self

    def detach(self):
        if self.plotter is not None and self.actor is not None:
            self.plotter.remove_actor(self.actor, render=False)
        self.actor = self.mapper = self.grid = None
        self.plotter = self.volume = None
        self.masks = {}

    def _build_grid(self):
        self.stride_xyz = static_display_strides(self.volume.shape, self.volume.spacing, self.quality)
        self._display_slices = tuple(slice(None, None, stride) for stride in self.stride_xyz[::-1])
        data = np.asarray(self.volume.data[self._display_slices], dtype=np.float32).copy()
        self.display_spacing = tuple(np.asarray(self.volume.spacing) * self.stride_xyz)
        self.grid = pv.ImageData(dimensions=data.shape[::-1], spacing=self.display_spacing,
                                 origin=self.volume.origin, direction_matrix=self.volume.direction)
        self.grid.point_data["HU"] = data.ravel()
        self.grid.set_active_scalars("HU")
        self._raw_data = data.ravel().copy()
        self._apply_gates()

    def set_opacity(self, value):
        if not np.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("CT opacity must be between zero and one.")
        self.opacity = float(value)
        self._apply_style()
        if self.actor is not None:
            self.actor.SetVisibility(value > 0)

    def set_structure_visibility(self, name, visible):
        self._structure_visibility[name] = bool(visible)
        self._apply_gates()

    def _apply_gates(self):
        if self.grid is None:
            return
        data = self._raw_data.copy()
        lungs = [name for name in self.masks if "lung" in name]
        if lungs:
            keep = np.logical_or.reduce([np.asarray(self.masks[name])[self._display_slices].ravel()
                                         for name in lungs])
            data[~keep] = -1000.
        for name, visible in self._structure_visibility.items():
            if visible or name not in self.masks:
                continue
            mask = np.asarray(self.masks[name])[self._display_slices].ravel().astype(bool)
            if "lung" in name:
                mask &= (data < -400.) & (data > -960.)
            data[mask] = -1000.
        self.grid.point_data["HU"][:] = data
        self.grid.GetPointData().GetScalars().Modified()


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
        lung = .018
        tissue = .0018
        bone = .004
        for hu, value in ((-1000, 0), (-960, 0), (-900, lung * .2),
                          (-840, lung), (-740, lung * .65), (-450, .001),
                          (-150, .0004), (0, tissue), (55, tissue * 1.8),
                          (95, .15), (180, .25), (300, .018), (650, bone),
                          (1100, bone * 1.8)):
            opacity.AddPoint(float(hu), float(value * self.opacity))
        self.actor.GetProperty().SetColor(colours)
        self.actor.GetProperty().SetScalarOpacity(opacity)



class SceneViewer(QtInteractor):
    def __init__(self, parent=None):
        super().__init__(parent, auto_update=False)
        self.set_background("#020405", top="#080e12")
        self.add_axes(xlabel="L", ylabel="P", zlabel="S", color="#b4cbd6")
        self.meshes, self.structure_actors = {}, {}
        self._source_meshes = {}
        self.lung_opacity = .35
        self.style = "CT reconstruction"
        self.reference_volume = None
        self.source_label = "NO CT LOADED"
        self.scan = ScanReconstruction()
        self._visibility = {}
        self._scale_actors = []
        self.remove_all_lights()
        self.add_light(pv.Light(light_type="headlight", intensity=.65))
        self.add_light(pv.Light(position=(-.6, -.5, 1.), light_type="camera light", intensity=.55))
        self.add_light(pv.Light(position=(.8, .4, .6), light_type="camera light", intensity=.28))
        self.add_text("LPS  /  millimetres", position="upper_left", font_size=9,
                      color="#a8bcc7", name="coordinates")
        self.enable_depth_peeling(number_of_peels=4, occlusion_ratio=.08)
        self.enable_anti_aliasing("fxaa")


    def set_source_label(self, label, render=True):
        """Show the active CT source inside the lung viewport."""
        self.source_label = str(label)
        self.add_text("LPS / mm  ·  " + self.style.upper() + "\n" + self.source_label,
                      position="upper_left", font_size=8, color="#98abb5",
                      name="coordinates", render=False)
        if render:
            self.render()


    def _build_structures(self):
        for actor in self.structure_actors.values():
            self.remove_actor(actor, render=False)
        self.meshes.clear()
        self.structure_actors.clear()
        max_cells = 40000
        for name, source in self._source_meshes.items():
            mesh = source.copy()
            if mesh.n_cells > max_cells:
                mesh = mesh.decimate(1 - max_cells / mesh.n_cells)
            self.meshes[name] = mesh
            opacity = self.lung_opacity if "lung" in name else .85
            textured = "lung" in name
            options = (dict(scalars="CT_RGB", rgb=True, show_scalar_bar=False)
                       if textured and "CT_RGB" in mesh.point_data else
                       dict(color=COLORS.get(name, "#8cb2c0")))
            actor = self.add_mesh(mesh, opacity=opacity, **options,
                                  smooth_shading=True, ambient=.18, diffuse=.66, specular=.16,
                                  specular_power=24, name=f"structure_{name}",
                                  reset_camera=False, render=False)
            actor.SetVisibility(self._visibility.get(name, True))
            self.structure_actors[name] = actor


    def set_volume(self, volume, masks, prebuilt_meshes=None):
        self.scan.detach()
        for actor in self._scale_actors:
            self.remove_actor(actor, render=False)
        self._scale_actors.clear()
        self._source_meshes.clear()
        self.reference_volume = volume
        self.set_source_label("SUPPLIED CT", render=False)
        prepared = (prepare_display_meshes(volume, masks, max_cells=100000)
                    if prebuilt_meshes is None else prebuilt_meshes)
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
        self.scan.attach(self, volume, masks=masks)
        self.scan.set_opacity(self.lung_opacity)
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
        # viewport after the closer framing.
        visible_bounds=[np.asarray(mesh.bounds).reshape(3,2) for name,mesh in self.meshes.items()
                        if "lung" in name or (name in ("body","ribs") and self._visibility.get(name,False))]
        if visible_bounds:
            lower=np.min(np.stack(visible_bounds)[:,:,0],axis=0)
            upper=np.max(np.stack(visible_bounds)[:,:,1],axis=0)
            corners=np.array(np.meshgrid(*zip(lower,upper))).reshape(3,-1).T
            landmarks=np.vstack((corners,self.scale_endpoints))
            width,height=self.render_window.GetSize()
            if self.isVisible() and width>32 and height>32:
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


    def visibility(self, name, visible, render=True):
        self._visibility[name] = bool(visible)
        self.scan.set_structure_visibility(name, visible)
        if name in self.structure_actors:
            self.structure_actors[name].SetVisibility(visible)
        if render:
            self.render()


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


    def set_data(self, volume, crosshair, masks=None,
                 *, plane=None, mask_planes=None):
        self.crosshair = np.asarray(crosshair)
        self.plane = (volume.slice_plane(self.plane_name, crosshair, max_pixels=self.max_pixels)
                      if plane is None else plane)
        if self.plane.name != self.plane_name:
            raise ValueError("The supplied slice does not match the viewer orientation.")
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



def group(title,layout):
    box=QGroupBox(title)
    box.setLayout(layout)
    return box



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app.style().objectName().lower() != "fusion":
            app.setStyle("Fusion")
        self.setWindowTitle("MotionTwin | CT and Lung Viewer")
        available = QApplication.primaryScreen().availableGeometry()
        width = min(1600, max(800, available.width()-48))
        height = min(980, max(600, available.height()-64))
        self.setMinimumSize(min(1050, width), min(680, height))
        self.resize(width, height)
        self.setStyleSheet(STYLE)
        self.volume = None
        self.masks = {}
        self.source_info = None
        self._supplied_meshes = {}
        self.crosshair = np.zeros(3)
        self.worker = None
        self._initial_camera_fitted = False
        self._ui()
        if cached_public_sample_available():
            QTimer.singleShot(0, self.load_public_example)



    def showEvent(self,event):
        super().showEvent(event)
        if not self._initial_camera_fitted:
            self._initial_camera_fitted=True
            # Native viewport sizes are final only after the first layout.
            QTimer.singleShot(0,lambda:self.scene.preset(self.camera.currentText())
                if self.scene.reference_volume is not None else None)


    def _ui(self):
        self.file_menu=self.menuBar().addMenu("File")
        self.file_menu.addAction("Open CT…",self.import_volume)
        self.file_menu.addAction("Open DICOM series…",self.import_dicom)
        self.import_mask_action=self.file_menu.addAction("Load lung mask…",self.import_mask)
        self.import_mask_action.setEnabled(False)
        self.file_menu.addSeparator()
        self.example_action=self.file_menu.addAction("Open example CT",self.load_public_example)
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
        subtitle=QLabel("PULMONARY CT IMAGING")
        subtitle.setObjectName("studySubtitle")
        subtitle.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        titles.addWidget(subtitle)
        self.study_metadata=QLabel("Open a CT study to begin")
        self.study_metadata.setObjectName("studyMetadata")
        self.study_metadata.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        titles.addWidget(self.study_metadata)
        header.addLayout(titles,1)
        self.badge=QLabel("CT VIEWER")
        self.badge.setObjectName("badge")
        header.addWidget(self.badge)
        outer.addWidget(study_strip)

        self.status=QLabel("CT imaging and lung reconstruction")
        self.status.setObjectName("statusLine")
        self.status.setWordWrap(True)
        self.status.setMaximumHeight(36)
        outer.addWidget(self.status)
        main=QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter=main
        main.setChildrenCollapsible(False)
        main.setHandleWidth(5)
        outer.addWidget(main,1)
        self.controls=QScrollArea()
        self.controls.setWidgetResizable(True)
        self.controls.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controls.setMinimumWidth(275)
        self.controls.setMaximumWidth(335)
        content=QWidget()
        controls_layout=QVBoxLayout(content)
        controls_layout.setContentsMargins(10,10,10,10)
        controls_layout.addWidget(QLabel("IMAGING"))
        self._imaging_controls(controls_layout)
        self.controls.setWidget(content)
        main.addWidget(self.controls)

        # Retain the existing CT review layout and native viewport parents.
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
        self.camera.setEnabled(False)
        self.camera.currentTextChanged.connect(lambda text:self.scene.preset(text))
        self.scene_title=QLabel("3D · CT RECONSTRUCTION")
        self.scene_title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        toolbar.addWidget(self.scene_title,1)
        toolbar.addWidget(self.camera)
        self.fit_button=QToolButton()
        self.fit_button.setText("Fit")
        self.fit_button.setFixedWidth(42)
        self.fit_button.setToolTip("Fit the complete anatomical study in this viewport.")
        self.fit_button.setEnabled(False)
        self.fit_button.clicked.connect(lambda:self.scene.preset(self.camera.currentText()))
        toolbar.addWidget(self.fit_button)
        scene_layout.addWidget(toolbar_panel)
        self.scene=SceneViewer(scene_panel)
        scene_layout.addWidget(self.scene.interactor,1)
        self.slices=[]
        for plane in ("axial","coronal","sagittal"):
            view=SliceViewer(plane,self.viewport_grid_parent)
            view.selected.connect(self.set_crosshair)
            self.slices.append(view)
        self.viewport_grid.addWidget(self.slices[0],0,0)
        self.viewport_grid.addWidget(self.scene_panel,0,1)
        self.viewport_grid.addWidget(self.slices[1],1,0)
        self.viewport_grid.addWidget(self.slices[2],1,1)
        for index in range(2):
            self.viewport_grid.setColumnStretch(index,1)
            self.viewport_grid.setRowStretch(index,1)
        main.setStretchFactor(0,0)
        main.setStretchFactor(1,1)
        main.setSizes([295,1000])
        footer=QLabel("LPS · mm   |   CT: click to position · scroll to slice · Ctrl+scroll to zoom")
        footer.setStyleSheet("color:#7f97ad;font-size:10px")
        footer.setWordWrap(True)
        outer.addWidget(footer)
        self.display_info=QLabel("Static CT · linked physical coordinates")
        self.display_info.setStyleSheet("color:#8099ae;font-size:10px")
        outer.addWidget(self.display_info)


    def spin(self,minimum,maximum,value,step=1,decimals=1):
        widget=QDoubleSpinBox()
        widget.setRange(minimum,maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setValue(value)
        return widget


    def _imaging_controls(self,layout):
        self.segmentation_visible=QCheckBox("CT segmentation overlays")
        self.segmentation_visible.setChecked(False)
        self.segmentation_visible.setEnabled(False)
        self.segmentation_visible.toggled.connect(self.refresh)
        layout.addWidget(self.segmentation_visible)
        form=QFormLayout()
        self.ct_preset=QComboBox()
        self.ct_preset.addItems(["Lung","Soft tissue","Bone"])
        self.ct_preset.setPlaceholderText("Custom")
        self.ct_preset.currentTextChanged.connect(self.apply_ct_preset)
        form.addRow("Window preset",self.ct_preset)
        self.window_control=self.spin(1,4000,1500,50,0)
        self.level_control=self.spin(-1500,2000,-500,50,0)
        self.window_control.valueChanged.connect(self.window_level)
        self.level_control.valueChanged.connect(self.window_level)
        form.addRow("Window (HU)",self.window_control)
        form.addRow("Level (HU)",self.level_control)
        self.ct_display_group=group("CT display",form)
        self.ct_display_group.setEnabled(False)
        layout.addWidget(self.ct_display_group)
        visibility=QVBoxLayout()
        self.visibility_controls={}
        for name,label in [("left_lung","Left lung"),("right_lung","Right lung"),
                           ("vascular_display","High-density lung detail (derived)")]:
            check=QCheckBox(label)
            check.setChecked(True)
            check.setEnabled(False)
            check.toggled.connect(lambda checked,n=name:self.scene.visibility(n,checked))
            visibility.addWidget(check)
            self.visibility_controls[name]=check
        self.opacity=QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(5,90)
        self.opacity.setValue(35)
        self.opacity.valueChanged.connect(lambda value:self.scene.transparency(value/100))
        visibility.addWidget(QLabel("Lung tissue opacity"))
        visibility.addWidget(self.opacity)
        self.lung_display_group=group("Lung display",visibility)
        self.lung_display_group.setEnabled(False)
        layout.addWidget(self.lung_display_group)
        self.imaging_info=QLabel("")
        self.imaging_info.setWordWrap(True)
        self.imaging_info.setMinimumWidth(0)
        self.imaging_info.setMinimumHeight(70)
        self.imaging_info.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.imaging_info)
        layout.addStretch()


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


    def window_level(self):
        values=(self.window_control.value(),self.level_control.value())
        name=next((name for name,preset in {"Lung":(1500,-500),"Soft tissue":(400,40),"Bone":(1800,400)}.items()
                   if preset==values),"Custom")
        self.ct_preset.blockSignals(True)
        self.ct_preset.setCurrentIndex(self.ct_preset.findText(name))
        self.ct_preset.blockSignals(False)
        for view in getattr(self,"slices",[]):
            view.canvas.window=self.window_control.value()
            view.canvas.level=self.level_control.value()
            view.canvas.update()


    def import_volume(self):
        path,_=QFileDialog.getOpenFileName(self,"Import CT volume","","Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if path:
            self.task(lambda:load_volume(path),self.accept_volume,"Reading CT with physical-coordinate metadata…")


    def load_public_example(self):
        """Load an attributed real CT example with its existing lung display masks."""
        if self.source_info is not None:
            return
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
            self.status.setText("Public CT example · static imaging study · threshold-derived display masks; display reconstruction only.")

        self.task(prepare,accepted,"Opening the public CT example and preparing display reconstructions…")


    def import_dicom(self):
        path=QFileDialog.getExistingDirectory(self,"Select one DICOM series directory")
        if path:
            self.task(lambda:load_volume(path),self.accept_volume,"Reading a single DICOM series…")


    def import_mask(self):
        if self.volume is None:
            self.status.setText("Import a CT volume before adding lung masks.")
            return
        path,_=QFileDialog.getOpenFileName(self,"Load aligned label image","","Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if not path:
            return
        label,ok=QInputDialog.getInt(self,"Segmentation label","Label number (0 means all nonzero labels)",0,0,65535)
        if not ok:
            return
        side,ok=QInputDialog.getItem(self,"Lung mask","Which lung does this mask contain?",
                                   ["Left lung","Right lung"],0,False)
        if not ok:
            return
        role={"Left lung":"left_lung","Right lung":"right_lung"}[side]
        reference=self.volume
        def prepare():
            mask=load_mask(path,reference,label=label if label else None)
            return mask,mesh_from_mask(mask,reference)
        self.task(prepare,lambda result:self.accept_mask(role,*result,source_path=path),"Validating segmentation and reconstructing its surface…")


    def accept_mask(self,role,mask,mesh=None,*,source_path=None):
        if not np.any(mask):
            self.status.setText(f"The selected {role} label is empty; the existing structure was retained.")
            return
        self.masks[role]=mask
        self._supplied_meshes[role]=mesh if mesh is not None else mesh_from_mask(mask,self.volume)
        self.scene.set_volume(self.volume,self.masks,prebuilt_meshes=self._supplied_meshes)
        self.badge.setText("PUBLIC CT · DERIVED + LOADED MASKS" if self.source_info else "SUPPLIED CT + SEGMENTATIONS")
        self.status.setText(f"Loaded {role} segmentation in the CT's physical coordinates.")
        self._update_metadata()
        self.refresh()



    def accept_volume(self,volume,*,masks=None,prebuilt_meshes=None,source_info=None):
        self.scene.set_volume(volume,masks or {},prebuilt_meshes=prebuilt_meshes)
        self.volume=volume
        self.masks={} if masks is None else dict(masks)
        self.source_info=source_info
        self._supplied_meshes={} if prebuilt_meshes is None else dict(prebuilt_meshes)
        self.crosshair=volume.center.copy()
        self.scene.set_source_label("PUBLIC STATIC CT / DERIVED DISPLAY MASKS" if source_info else "SUPPLIED STATIC CT")
        self.badge.setText("PUBLIC CT EXAMPLE" if source_info else "SUPPLIED CT")
        self.status.setText("CT loaded. Click or scroll the linked CT views; drag the lung view to rotate.")
        self._update_metadata()
        self.refresh()

    def _update_metadata(self):
        if self.volume is None:
            return
        volume=self.volume
        self.study_metadata.setText(f"{volume.name} · {volume.shape[2]} × {volume.shape[1]} × {volume.shape[0]} · static CT")
        self.imaging_info.setText("Spacing (mm): " + " × ".join(f"{value:.3f}" for value in volume.spacing)
            + "\nCoordinates: LPS millimetres\n"
            + ("Public example: threshold-derived lung/detail display masks." if self.source_info
               else "Imported CT. Lung surfaces require aligned lung masks."))
        self.import_mask_action.setEnabled(True)
        self.example_action.setEnabled(self.source_info is None)
        self.segmentation_visible.setEnabled(bool(self.masks))
        self.ct_display_group.setEnabled(True)
        self.lung_display_group.setEnabled(any("lung" in name for name in self.masks))
        self.camera.setEnabled(True)
        self.fit_button.setEnabled(True)
        for name,check in self.visibility_controls.items():
            check.setEnabled(name in self.masks)
            self.scene.visibility(name,check.isChecked(),render=False)

    def set_crosshair(self,point):
        if self.volume is None:
            return
        self.crosshair=np.clip(np.asarray(point,dtype=float),*self.volume.bounds)
        self.refresh()

    def refresh(self):
        if self.volume is None:
            return
        masks=self.masks if self.segmentation_visible.isChecked() else None
        for view in self.slices:
            view.set_data(self.volume,self.crosshair,masks=masks)

    def task(self,function,callback,label):
        if self.worker is not None:
            return
        self.controls.setEnabled(False)
        self.file_menu.setEnabled(False)
        self.status.setText(label)
        self.worker=Worker(function)
        self.worker.result.connect(lambda result:self._task_result(callback,result))
        self.worker.failed.connect(self._task_failed)
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _task_result(self,callback,result):
        try:
            callback(result)
        except Exception:
            self._task_failed(traceback.format_exc())

    def _task_failed(self,message):
        self.status.setText("CT operation failed. The details are shown below.")
        QMessageBox.warning(self,"MotionTwin CT viewer",message[-1500:])

    def _task_finished(self):
        self.worker.deleteLater()
        self.worker=None
        self.controls.setEnabled(True)
        self.file_menu.setEnabled(True)

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish loading the CT before closing the viewer.")
            event.ignore()
            return
        self.scene.close()
        event.accept()


def launch():
    import sys
    app=QApplication.instance() or QApplication(sys.argv[:1])
    window=MainWindow()
    window.show()
    return app.exec()


def main(argv=None):
    import os
    os.chdir(Path(__file__).resolve().parent)
    parser=argparse.ArgumentParser(prog="motiontwin",description="CT and lung viewer")
    parser.add_argument("command",nargs="?",choices=["gui"],default="gui",help="Open the CT viewer")
    parser.parse_args(argv)
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
