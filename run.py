from __future__ import annotations

# select the local interpreter before importing any GUI/scientific dependencies.
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
QMainWindow, QWidget { background:#303234; color:#e0e1e3; font-family:'Segoe UI'; font-size:12px; }
QWidget#studyStrip { background:#292b2d; border-bottom:1px solid #494c50; }
QLabel#brand { font-size:17px; font-weight:650; color:#f1f2f3; background:transparent; }
QLabel#studyMetadata { color:#c0c3c7; font-size:11px; background:transparent; }
QLabel#badge { color:#d5dfe3; background:#3b4248; border:1px solid #59626a; border-radius:2px; padding:3px 6px; font-size:9px; font-weight:600; }
QLabel#statusLine { color:#c1c5ca; font-size:10px; background:transparent; }
QWidget#viewportPanel { background:#070809; border:1px solid #8687ab; }
QWidget#viewportToolbar { background:#9294ba; border:0; }
QWidget#viewportToolbar QLabel { background:transparent; font-size:10px; color:#171a21; font-weight:650; }
QWidget#viewportToolbar QComboBox, QWidget#viewportToolbar QToolButton { padding:1px 4px; font-size:10px; }
QToolBar { background:#343638; border:0; border-bottom:1px solid #515458; spacing:5px; padding:3px 6px; }
QToolBar::separator { background:#56595d; width:1px; margin:3px 6px; }
QToolButton { background:#424548; border:1px solid #606469; padding:4px 8px; border-radius:2px; }
QToolButton:hover { background:#53585e; border-color:#8c939c; }
QToolButton:pressed, QToolButton:checked { background:#303e4a; border-color:#86a3ba; }
QToolButton:disabled { color:#777d84; background:#35383b; border-color:#464a4e; }
QMenuBar, QMenu { background:#2b2d2f; color:#e0e1e3; }
QMenuBar::item:selected, QMenu::item:selected { background:#4a5663; }
QMenu::item:disabled { color:#777d84; }
QComboBox, QDoubleSpinBox, QSpinBox { background:#242628; border:1px solid #5a5e64; padding:4px; border-radius:2px; selection-background-color:#46677e; }
QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover { border-color:#8a949f; }
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled { color:#777d84; border-color:#44484d; }
QTabWidget::pane { border:0; }
QTabBar::tab { background:#383b3f; border:1px solid #4a4e53; padding:7px 18px; color:#c3c6ca; }
QTabBar::tab:selected { background:#484d53; color:#ffffff; border-bottom:2px solid #9fb4c6; }
QTabBar::tab:disabled { color:#757b82; }
QComboBox::drop-down { width:18px; background:#9da7b2; border-left:1px solid #616a74; }
QComboBox::down-arrow { image:url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png); width:10px; height:10px; }
QComboBox::drop-down:disabled { background:#555d66; }
QComboBox QAbstractItemView { background:#2d3136; selection-background-color:#46677e; }
QDoubleSpinBox, QSpinBox { padding-right:20px; }
QDoubleSpinBox::up-button, QSpinBox::up-button { subcontrol-origin:border; subcontrol-position:top right; width:16px; background:#9da7b2; border-left:1px solid #616a74; }
QDoubleSpinBox::down-button, QSpinBox::down-button { subcontrol-origin:border; subcontrol-position:bottom right; width:16px; background:#9da7b2; border-left:1px solid #616a74; border-top:1px solid #616a74; }
QDoubleSpinBox::up-arrow, QSpinBox::up-arrow { image:url(:/qt-project.org/styles/commonstyle/images/arrow-up-16.png); width:9px; height:9px; }
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow { image:url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png); width:9px; height:9px; }
QDoubleSpinBox::up-button:disabled, QDoubleSpinBox::down-button:disabled, QSpinBox::up-button:disabled, QSpinBox::down-button:disabled { background:#555d66; }
QGroupBox { border:1px solid #53585e; border-radius:2px; margin-top:10px; padding-top:12px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; color:#d6d8db; }
QCheckBox { spacing:7px; padding:2px 0; }
QCheckBox::indicator { width:13px; height:13px; border:1px solid #939ba4; border-radius:2px; background:#25282c; }
QCheckBox::indicator:checked { background:#92b3c8; border:1px solid #c2d4df; image:none; }
QCheckBox::indicator:disabled { background:#363a3f; border-color:#555b62; }
QSlider::groove:horizontal { height:3px; background:#555d66; border-radius:1px; }
QSlider::sub-page:horizontal { background:#7d9eb8; }
QSlider::handle:horizontal { width:9px; margin:-5px 0; border:1px solid #d3dae1; border-radius:2px; background:#a8bbcc; }
QSlider::handle:horizontal:disabled { background:#606870; border-color:#737a82; }
QScrollArea { border:0; background:#303234; }
QScrollBar:vertical { width:8px; background:#292c2f; margin:0; }
QScrollBar::handle:vertical { min-height:28px; background:#656d76; border-radius:2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSplitter::handle { background:#4a4e53; }
QSplitter::handle:hover { background:#8395a8; }
QStatusBar { background:#26282b; border-top:1px solid #4a4e53; }
QStatusBar::item { border:0; }
QToolTip { background:#454c54; color:#f0f2f5; border:1px solid #87939f; padding:4px; }
QTreeWidget { background:#242628; border:1px solid #53585e; alternate-background-color:#2c2f32; }
QTreeWidget::item { height:25px; }
QTreeWidget::item:selected { background:#46677e; color:#ffffff; }
QHeaderView::section { background:#41464b; color:#e0e1e3; border:0; border-right:1px solid #5a6067; padding:4px; }
QLineEdit { background:#242628; color:#e0e1e3; border:1px solid #5a5e64; padding:4px; }
"""

import argparse
import csv
import os
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction, vtkVolume, vtkVolumeProperty
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkOpenGLGPUVolumeRayCastMapper
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPalette, QIcon, QPixmap, QPolygonF
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QLabel, QComboBox, QDoubleSpinBox, QSlider,
    QSplitter, QCheckBox, QFileDialog, QMessageBox, QScrollArea,
    QGroupBox, QGridLayout, QToolButton, QSizePolicy, QTabWidget, QSpinBox,
    QToolBar, QStyle, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit,
    QColorDialog, QDialog, QDialogButtonBox, QProgressDialog)

from motiontwin import (Volume, load_volume, mesh_from_mask,
    prepare_display_meshes, attach_ct_scalars, load_public_sample,
    cached_public_sample_available, DISPLAY_MAX_CELLS, BREATHING_PATTERNS,
    BreathingSettings, RespiratoryModel, LungDeformation, respiratory_slice, PackedMasks,
    StructureStyle, load_segmentation, LOBE_SEGMENTS, load_lobe_cache,
    load_lobe_segmentation, build_lobe_cache, generate_lobe_segmentation,
    AIRWAY_KEY, AIRWAY_STYLE, AIRWAY_SEED_HU_RANGE, load_airway_cache, load_airway_segmentation,
    build_airway_cache, extract_airways, load_ct_sequence, LandmarkSeries, load_landmarks,
    create_research_target, target_slice_contour, ObservationSettings,
    generate_target_observations, respiratory_model_id,
    ensure_respiratory_example, cached_respiratory_example_available,
    BASELINE_METHODS, ForecastSettings, fit_baseline, select_validation_origins,
    evaluate_baselines, check_export_destination)

COLORS = {"left_lung": "#79b5bf", "right_lung": "#8ec6cc",
          "lungs": "#83bac5", "vascular_display": "#cb766e"}
STATIC_DISPLAY_LIMITS = {"Interactive": 1_200_000, "Balanced": 3_000_000, "High": 8_000_000}

def default_structure_style(key, name=None):
    lung="lung" in key
    names={"left_lung":"Left lung","right_lung":"Right lung",
           "vascular_display":"High-density lung detail (derived)"}
    return StructureStyle(name or names.get(key,key.replace("_"," ")),
                          COLORS.get(key,"#8cb2c0"),.35 if lung else .85,
                          ct_coloring=lung,kind="lung" if lung else "other")

def static_display_strides(shape, spacing, quality):
    """balance XYZ sampling strides under a fixed memory cap.

    decimate thin in-plane pixels before thick source slices to avoid
    widening a 2.5 mm source gap to 10 mm with a uniform index stride.
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

    def __init__(self):
        self.quality = "Balanced"
        self.plotter = self.volume = None
        self.actor = self.mapper = self.grid = None
        self.opacity = .35
        self.masks = {}
        self.structure_styles = {}
        self._gate_key = None
        self._has_context = True
        self._cropped_to_lungs = False

    def attach(self, plotter, volume, masks=None):
        self.detach()
        self.plotter, self.volume = plotter, volume
        self.masks = masks or {}
        self.structure_styles = {key:default_structure_style(key) for key in self.masks}
        self._gate_key = None
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
        # opacity is defined per 4 mm, independent of the display grid stride.
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
            self.actor.SetVisibility(value > 0 and self._has_context)

    def set_structures(self, masks, styles):
        if self.volume is not None and any(np.asarray(mask).shape != self.volume.shape for mask in masks.values()):
            raise ValueError("Segmentation masks must match the CT geometry.")
        self.masks,self.structure_styles=masks,dict(styles)
        self._apply_gates()

    def _apply_gates(self):
        if self.grid is None:
            return
        key=tuple((name,id(mask),self.structure_styles.get(name,default_structure_style(name)).visible,
                   self.structure_styles.get(name,default_structure_style(name)).opacity>0,
                   self.structure_styles.get(name,default_structure_style(name)).ct_coloring,
                   self.structure_styles.get(name,default_structure_style(name)).kind)
                  for name,mask in self.masks.items())
        if key==self._gate_key:
            return
        self._gate_key=key
        data = self._raw_data.copy()
        keep=np.zeros(data.shape,dtype=bool)
        for name,mask in self.masks.items():
            style=self.structure_styles.get(name,default_structure_style(name))
            if style.visible and style.opacity>0 and style.ct_coloring:
                keep |= np.asarray(mask)[self._display_slices].ravel().astype(bool)
        self._cropped_to_lungs=any(style.kind=="lung" for style in self.structure_styles.values())
        self._has_context=not self._cropped_to_lungs or bool(keep.any())
        if self._cropped_to_lungs:
            data[~keep]=-1000.
        self.grid.point_data["HU"][:] = data
        self.grid.GetPointData().GetScalars().Modified()
        if self.actor is not None:
            self.actor.SetVisibility(self.opacity>0 and self._has_context)


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
        # low lung opacity keeps internal detail visible through the surface.
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
        self.set_background("#8b8da8", top="#4b4f68")
        self.add_axes(xlabel="L", ylabel="P", zlabel="S", color="#eef1f5")
        self.meshes, self.structure_actors = {}, {}
        self._source_meshes = {}
        self.structure_styles = {}
        self.style = "CT reconstruction"
        self.reference_volume = None
        self.source_label = "NO CT LOADED"
        self.scan = ScanReconstruction()
        self._visibility = {}
        self._scale_actors = []
        self.motion_matrix = vtkMatrix4x4()
        self.motion_matrix.Identity()
        self.simulated = False
        self.landmark_point = None
        self.landmark_segments = ()
        self._landmark_key = None
        self.target = None
        self.target_actor = None
        self.forecast_point = None
        self._forecast_mesh = None
        self.remove_all_lights()
        self.add_light(pv.Light(light_type="headlight", intensity=.65))
        self.add_light(pv.Light(position=(-.6, -.5, 1.), light_type="camera light", intensity=.55))
        self.add_light(pv.Light(position=(.8, .4, .6), light_type="camera light", intensity=.28))
        self.add_text("LPS  /  millimetres", position="upper_left", font_size=9,
                      color="#a8bcc7", name="coordinates")
        self.enable_depth_peeling(number_of_peels=4, occlusion_ratio=.08)
        self.enable_anti_aliasing("fxaa")


    def set_source_label(self, label, render=True):
        self.source_label = str(label)
        mode = "SIMULATED MOTION / NOT MEASURED 4D CT\n" if self.simulated else ""
        self.add_text(mode + "LPS / mm  ·  " + self.style.upper() + "\n" + self.source_label,
                      position="upper_left", font_size=8, color="#f0f1f4",
                      name="coordinates", render=False)
        if render:
            self.render()


    def _build_structures(self):
        for actor in self.structure_actors.values():
            self.remove_actor(actor, render=False)
        self.meshes.clear()
        self.structure_actors.clear()
        for name, source in self._source_meshes.items():
            self._add_structure_actor(name,source)

    def _add_structure_actor(self,name,source):
        mesh=source.copy()
        self.meshes[name]=mesh
        options=(dict(scalars="CT_RGB",rgb=True,show_scalar_bar=False)
                 if "CT_RGB" in mesh.point_data else dict(color=self.structure_styles[name].color))
        actor=self.add_mesh(mesh,**options,smooth_shading=True,ambient=.18,diffuse=.66,
            specular=.16,specular_power=24,name=f"structure_{name}",reset_camera=False,render=False)
        actor.SetUserMatrix(self.motion_matrix)
        self.structure_actors[name]=actor
        self._apply_structure_style(name)

    def _apply_structure_style(self,name):
        style=self.structure_styles[name]
        actor=self.structure_actors[name]
        colour=QColor(style.color)
        actor.GetProperty().SetColor(colour.redF(),colour.greenF(),colour.blueF())
        actor.GetProperty().SetOpacity(style.opacity)
        actor.GetMapper().SetScalarVisibility(style.ct_coloring and "CT_RGB" in self.meshes[name].point_data)
        actor.SetVisibility(style.visible and style.opacity>0)

    def set_structures(self,styles):
        self.structure_styles=dict(styles)
        self._visibility={key:value.visible and value.opacity>0 for key,value in styles.items()}
        for name in self.structure_actors:
            self._apply_structure_style(name)
        self.scan.set_structures(self.scan.masks,styles)

    def _update_bounds(self):
        lungs=[np.asarray(mesh.bounds).reshape(3,2) for name,mesh in self._source_meshes.items()
               if self.structure_styles[name].kind=="lung"]
        self._lung_bounds=(np.array([np.min(np.stack(lungs)[:,:,0],axis=0),
                                    np.max(np.stack(lungs)[:,:,1],axis=0)]) if lungs else self.reference_volume.bounds)
        self.anatomical_center=self._lung_bounds.mean(axis=0)

    def add_structure(self,key,mask,mesh,styles):
        self.add_structures({key:mask},{key:mesh},styles)

    def add_structures(self,masks,meshes,styles):
        for key,mask in masks.items():
            if np.asarray(mask).shape!=self.reference_volume.shape:
                raise ValueError("Segmentation masks must match the CT geometry.")
            mesh=meshes.get(key)
            if mesh is None or not mesh.n_points or mesh.n_cells>DISPLAY_MAX_CELLS:
                raise ValueError("The segmentation requires a nonempty, bounded surface.")
            if key not in styles:
                raise ValueError("Each segmentation requires display settings.")
        prepared={key:meshes[key].copy() for key in masks}
        self._source_meshes.update(prepared)
        self.structure_styles=dict(styles)
        for key,mesh in prepared.items():
            self._add_structure_actor(key,mesh)
        self.scan.set_structures({**self.scan.masks,**masks},styles)
        self.set_structures(styles)
        self._update_bounds()

    def set_motion(self, matrix, *, simulated=False):
        for row in range(4):
            for column in range(4):
                self.motion_matrix.SetElement(row, column, float(matrix[row,column]))
        if self.simulated != simulated:
            self.simulated = simulated
            self.set_source_label(self.source_label, render=False)

    def transformed_points(self, points):
        matrix = np.array([[self.motion_matrix.GetElement(i,j) for j in range(4)] for i in range(4)])
        return np.asarray(points)@matrix[:3,:3].T+matrix[:3,3]

    def set_crosshair(self, point):
        if hasattr(self,"_crosshair_position") and np.array_equal(point,self._crosshair_position):
            return
        self._crosshair_position=np.asarray(point).copy()
        offsets=np.array([[-5,0,0],[5,0,0],[0,-5,0],[0,5,0],[0,0,-5],[0,0,5]])
        points=offsets+point
        if not hasattr(self,"_crosshair_mesh"):
            self._crosshair_mesh=pv.line_segments_from_points(points)
            self.add_mesh(self._crosshair_mesh,color="#6ddce8",line_width=1,lighting=False,
                          name="world_crosshair",reset_camera=False,render=False)
        else:
            self._crosshair_mesh.points=points

    def set_landmarks(self, series, index):
        points={} if series is None else series.points
        reference=None if series is None else series.reference_index
        key=(id(series),index,reference,tuple((i,tuple(p)) for i,p in sorted(points.items())))
        if key==self._landmark_key:
            return
        self._landmark_key=key
        for name in ("landmark_current","landmark_reference","landmark_path"):
            self.remove_actor(name,render=False)
        self.landmark_point=None if index not in points else points[index].copy()
        self.landmark_segments=tuple(np.array([points[i-1],points[i]]) for i in sorted(points) if i-1 in points)
        if self.landmark_segments:
            path=pv.line_segments_from_points(np.concatenate(self.landmark_segments))
            self.add_mesh(path,color="#e6bb63",line_width=2,lighting=False,
                          name="landmark_path",reset_camera=False,render=False)
        for name,point,color,size in (
            ("landmark_reference",points.get(reference),"#8cbcf0",14),
            ("landmark_current",self.landmark_point,"#ffd071",10)):
            if point is not None:
                self.add_points(np.asarray([point]),color=color,point_size=size,
                    render_points_as_spheres=True,lighting=False,name=name,
                    reset_camera=False,render=False)

    def set_target(self,target):
        if target is self.target:
            return
        self.remove_actor("research_target",render=False)
        self.target=target
        self.target_actor=None
        if target is not None:
            mesh=pv.Sphere(radius=target.radius_mm,center=target.center_lps_mm,
                           theta_resolution=40,phi_resolution=32)
            self.target_actor=self.add_mesh(mesh,color="#ffc465",ambient=.35,diffuse=.65,
                specular=.25,smooth_shading=True,name="research_target",reset_camera=False,render=False)
            self.target_actor.SetUserMatrix(self.motion_matrix)

    def set_forecast(self,point):
        if point is None:
            if self.forecast_point is not None:
                self.remove_actor("target_forecast",render=False)
            self.forecast_point=self._forecast_mesh=None
            return
        point=np.asarray(point,dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all():
            raise ValueError("A forecast marker requires a finite LPS position.")
        if self.forecast_point is not None and np.array_equal(point,self.forecast_point):
            return
        self.forecast_point=point.copy()
        if self._forecast_mesh is None:
            self._forecast_mesh=pv.PolyData(point[None,:])
            self.add_mesh(self._forecast_mesh,color="#49dcf4",point_size=13,
                render_points_as_spheres=True,lighting=False,name="target_forecast",
                reset_camera=False,render=False)
        else:
            self._forecast_mesh.points=point[None,:]


    def set_volume(self, volume, masks, prebuilt_meshes=None,styles=None):
        if any(np.asarray(mask).shape != volume.shape for mask in masks.values()):
            raise ValueError("Lung masks must match the CT geometry.")
        prepared = (prepare_display_meshes(volume, masks)
                    if prebuilt_meshes is None else prebuilt_meshes)
        if any(mesh.n_cells > DISPLAY_MAX_CELLS for mesh in prepared.values()):
            raise ValueError("Display meshes exceed the fixed viewer resolution.")
        self.set_target(None)
        self.set_forecast(None)
        self.scan.detach()
        for actor in self._scale_actors:
            self.remove_actor(actor, render=False)
        self._scale_actors.clear()
        self._source_meshes.clear()
        self.structure_styles=(dict(styles) if styles is not None else
                               {key:default_structure_style(key) for key in masks})
        self._visibility={key:style.visible and style.opacity>0 for key,style in self.structure_styles.items()}
        self.reference_volume = volume
        self.set_source_label("SUPPLIED CT", render=False)
        for name, mask in masks.items():
            mesh = prepared[name].copy() if name in prepared else mesh_from_mask(mask, volume)
            if mesh.n_points and "CT_RGB" not in mesh.point_data:
                mesh = attach_ct_scalars(mesh, volume, inset_mm=min(volume.spacing)*.65 if "lung" in name else 0.)
            if mesh.n_points:
                self._source_meshes[name] = mesh
        self._update_bounds()
        self.scan.attach(self, volume, masks=masks)
        self.scan.actor.SetUserMatrix(self.motion_matrix)
        self.scan.set_structures(masks,self.structure_styles)
        self._build_structures()
        self._add_scale(volume)


    def _add_scale(self, volume):
        # a world-coordinate reference remains 50 mm under rotation and perspective.
        lower = self._lung_bounds[0]
        start = self.anatomical_center + [-25., 0., 0.]
        start[1], start[2] = lower[1] - 12, lower[2] - 22
        end = start + [50., 0., 0.]
        lines = [pv.Line(start, end), pv.Line(start - [0, 0, 2], start + [0, 0, 2]),
                 pv.Line(end - [0, 0, 2], end + [0, 0, 2])]
        self.scale_endpoints = np.array([start, end])
        for i, line in enumerate(lines):
            self._scale_actors.append(self.add_mesh(line, color="#edf0f4", line_width=2,
                lighting=False, name=f"scale_{i}", reset_camera=False, render=False))
        self._scale_actors.append(self.add_point_labels([start + [25, 0, 7]], ["50 mm"],
            show_points=False, always_visible=True, shape=None, bold=False, text_color="#f4f5f7",
            font_size=10, name="scale_label", reset_camera=False, render=False))


    def preset(self, name):
        center = self.transformed_points(getattr(self, "anatomical_center", [0, 0, 0]))
        positions = {"Oblique": [430, -650, 240], "Anterior": [0, -800, 0],
                     "Posterior": [0, 800, 0], "Left": [800, 0, 0], "Superior": [0, 0, 800]}
        offset = np.asarray(positions.get(name, positions["Oblique"]))
        self.camera_position = [center + offset, center, [0, 1, 0] if name == "Superior" else [0, 0, 1]]
        if self.reference_volume is not None:
            visible=[np.asarray(mesh.bounds).reshape(3,2) for key,mesh in self.meshes.items() if self._visibility.get(key,True)]
            if not self.scan._cropped_to_lungs and self.scan.opacity>0:
                visible.append(self.reference_volume.bounds.T)
            bounds=(np.array([np.min(np.stack(visible)[:,:,0],axis=0),np.max(np.stack(visible)[:,:,1],axis=0)])
                    if visible else self._lung_bounds.copy())
            corners = self.transformed_points(np.array(np.meshgrid(*zip(*bounds))).reshape(3,-1).T)
            bounds = np.array([corners.min(axis=0),corners.max(axis=0)])
            bounds[0] -= [12,12,35]
            bounds[1] += [12,12,30]
            if hasattr(self,"scale_endpoints"):
                bounds[0] = np.minimum(bounds[0],self.scale_endpoints.min(axis=0)-8)
                bounds[1] = np.maximum(bounds[1],self.scale_endpoints.max(axis=0)+8)
            self.reset_camera(bounds=tuple(bounds.T.ravel()))
        else:
            self.reset_camera()
        self.camera.zoom(1.45 if not any(self._visibility.get(key,False) for key in ("body","ribs")) else 1.10)
        # fit lung bounds and the world ruler after zooming.
        visible_bounds=[np.asarray(mesh.bounds).reshape(3,2) for name,mesh in self.meshes.items()
                        if self._visibility.get(name,True)]
        if self.reference_volume is not None and not self.scan._cropped_to_lungs and self.scan.opacity>0:
            visible_bounds.append(self.reference_volume.bounds.T)
        if visible_bounds:
            lower=np.min(np.stack(visible_bounds)[:,:,0],axis=0)
            upper=np.max(np.stack(visible_bounds)[:,:,1],axis=0)
            corners=np.array(np.meshgrid(*zip(lower,upper))).reshape(3,-1).T
            landmarks=np.vstack((self.transformed_points(corners),self.scale_endpoints))
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



def physical_scale_ruler(plane, image_width, target_pixels=75.):
    """return a readable physical length and its on-screen width in pixels."""
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
        self._ct_key = None
        self._mask_images = {}
        self._mask_sources = {}
        self._overlay_key = None
        self.landmark_point = None
        self.landmark_tolerance_mm = 0.
        self.target_contour = None
        self.forecast_point = None
        self.forecast_tolerance_mm = 0.

    def set_target(self,target,matrix):
        self.target_contour=(target_slice_contour(target,self.plane,matrix)
                             if target is not None and self.plane is not None else None)
        self.update()

    def set_forecast(self,point,tolerance_mm):
        self.forecast_point=None if point is None else np.asarray(point,dtype=float).copy()
        self.forecast_tolerance_mm=float(tolerance_mm)
        self.update()

    @property
    def forecast_on_plane(self):
        return (self.plane is not None and self.forecast_point is not None
                and abs(float(self.plane.distance_to_plane(self.forecast_point)))<=self.forecast_tolerance_mm+1e-6)

    def set_landmark(self, point, tolerance_mm):
        self.landmark_point=None if point is None else np.asarray(point,dtype=float).copy()
        self.landmark_tolerance_mm=float(tolerance_mm)
        self.update()

    @property
    def landmark_on_plane(self):
        return (self.plane is not None and self.landmark_point is not None
                and abs(float(self.plane.distance_to_plane(self.landmark_point)))<=self.landmark_tolerance_mm+1e-6)


    def set_quality(self, max_pixels):
        if isinstance(max_pixels, bool) or int(max_pixels) != max_pixels or max_pixels < 2:
            raise ValueError("Slice resolution must be an integer of at least 2 pixels.")
        changed = self.max_pixels != int(max_pixels)
        self.max_pixels = int(max_pixels)
        return changed


    def set_data(self, volume, crosshair, masks=None,
                 *, plane=None, mask_planes=None, structures=None, packed_masks=None):
        self.crosshair = np.asarray(crosshair)
        axis = {"axial":2, "coronal":1, "sagittal":0}[self.plane_name]
        ct_key=(id(volume),float(self.crosshair[axis]),self.max_pixels,id(plane))
        ct_changed=ct_key!=self._ct_key
        if ct_changed:
            self.plane = (volume.slice_plane(self.plane_name, crosshair, max_pixels=self.max_pixels)
                          if plane is None else plane)
            self._ct_key=ct_key
            self._image_key=None
        if self.plane.name != self.plane_name:
            raise ValueError("The supplied slice does not match the viewer orientation.")
        supplied=(mask_planes if mask_planes is not None else masks) or {}
        images={name:image for name,image in self._mask_images.items()
                if not ct_changed and name in supplied and self._mask_sources.get(name) is supplied[name]}
        missing={name:mask for name,mask in supplied.items() if name not in images
                 and (structures is None or structures[name].visible and structures[name].opacity>0)}
        if packed_masks is not None and mask_planes is None:
            images.update(packed_masks.sample(lambda data:Volume(data,volume.spacing,volume.origin,volume.direction)
                                              .reslice_like(self.plane,interpolation=0,cval=0).image,missing))
        else:
            for name, mask in missing.items():
                if mask_planes is not None:
                    if (mask.shape != self.plane.shape
                            or not np.allclose(mask.origin, self.plane.origin)
                            or not np.allclose(mask.spacing, self.plane.spacing)
                            or not np.allclose(mask.u, self.plane.u)
                            or not np.allclose(mask.v, self.plane.v)):
                        raise ValueError("A segmentation overlay must use the exact CT slice grid.")
                    overlay = mask.image
                else:
                    mask_volume = Volume(np.asarray(mask), volume.spacing,volume.origin, volume.direction)
                    overlay = mask_volume.reslice_like(self.plane, interpolation=0, cval=0).image
                images[name]=overlay
        self._mask_images={name:images[name] for name in supplied if name in images}
        self._mask_sources=dict(supplied)
        overlay_key=tuple((name,id(image),structures.get(name) if structures else None)
                          for name,image in self._mask_images.items())
        if overlay_key==self._overlay_key:
            self.update()
            return
        self._overlay_key=overlay_key
        self.overlays = []
        self._overlay_images = []
        for name,overlay in self._mask_images.items():
            style=structures.get(name) if structures else None
            if style is not None and (not style.visible or style.opacity==0):
                continue
            color=style.color if style else COLORS.get(name,"#8cb2c0")
            alpha=round(255*style.opacity) if style else 65
            self.overlays.append((overlay,color))
            rgba = np.zeros((*overlay.shape, 4), dtype=np.uint8)
            c = QColor(color)
            rgba[overlay > 0] = [c.red(), c.green(), c.blue(), alpha]
            rgba = self.display_rows(rgba)
            rows, cols = overlay.shape
            qimage = QImage(rgba.data, cols, rows, rgba.strides[0], QImage.Format.Format_RGBA8888)
            self._overlay_images.append((rgba, qimage))
        self.update()


    def display_rows(self, image):
        # axial: anterior at the top. Coronal/sagittal: superior at the top.
        return np.ascontiguousarray(image if self.plane_name == "axial" else np.flipud(image))


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
        row = (pixels[1]+.5)/rows
        y = rect.top()+row*rect.height() if self.plane_name == "axial" else rect.bottom()-row*rect.height()
        return QPointF(rect.left()+(pixels[0]+.5)/cols*rect.width(), y)


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(),QColor("#050505"))
        if self.plane is None:
            return
        key = (id(self.plane.image), self.window, self.level)
        if key != self._image_key:
            self._image_buffer = self.display_rows(np.clip(
                (self.plane.image-self.level+self.window/2)/max(self.window,1)*255,
                0,255).astype(np.uint8))
            rows,cols = self._image_buffer.shape
            self._image = QImage(self._image_buffer.data, cols, rows,
                                 self._image_buffer.strides[0], QImage.Format.Format_Grayscale8)
            self._image_key = key
        rows, cols = self.plane.shape
        rect = self.image_rect()
        painter.drawImage(rect,self._image)
        # grey-scale CT benefits from linear display interpolation. Binary
        # segmentations retain their exact nearest-neighbour label boundary.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False)
        for _, overlay_image in self._overlay_images:
            painter.drawImage(rect,overlay_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        point = self.screen_point(self.crosshair)
        painter.setPen(QPen(QColor("#6ddce8"),1,Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(rect.left(),point.y()),QPointF(rect.right(),point.y()))
        painter.drawLine(QPointF(point.x(),rect.top()),QPointF(point.x(),rect.bottom()))
        if self.landmark_on_plane:
            marker=self.screen_point(self.landmark_point)
            painter.setPen(QPen(QColor("#ffd071"),2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(marker,6,6)
            painter.drawText(marker+QPointF(9,-8),"Landmark")
        if self.target_contour is not None:
            painter.setPen(QPen(QColor("#ffc465"),2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF([self.screen_point(p) for p in self.target_contour]))
        if self.forecast_on_plane:
            marker=self.screen_point(self.forecast_point)
            painter.setPen(QPen(QColor("#49dcf4"),2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([marker+QPointF(0,-6),marker+QPointF(6,0),
                                           marker+QPointF(0,6),marker+QPointF(-6,0)]))
            painter.drawText(marker+QPointF(9,17),"Predicted")
        painter.setPen(QColor("#b3c4d0"))
        painter.drawText(8,16,"SIMULATED CT / LPS" if getattr(self,"simulated",False) else "CT / LPS")
        labels = {"axial":("R","L","A","P"),"coronal":("R","L","S","I"),"sagittal":("A","P","S","I")}[self.plane_name]
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
                row = ((position.y()-rect.top()) if self.plane_name == "axial"
                       else (rect.bottom()-position.y()))/rect.height()
                pixels = [(position.x()-rect.left())/rect.width()*cols-.5, row*rows-.5]
                self.selected.emit(self.plane.pixel_to_world(pixels))


    def wheelEvent(self,event):
        if self.plane is None or event.angleDelta().y() == 0:
            return
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
        accent={"axial":"#dc7065","coronal":"#a2c77c","sagittal":"#e2c969"}[plane]
        self.setStyleSheet(f"""
            QWidget#{plane}Panel {{ background:#050505; border:1px solid {accent}; }}
            QWidget#{plane}Header {{ background:{accent}; border:0; }}
            QWidget#{plane}Header QLabel {{ background:transparent; border:0; color:#171b20; font-size:10px; }}
            QWidget#{plane}Header QSlider {{ background:transparent; }}
            QWidget#{plane}Header QSlider::groove:horizontal {{ background:#53606a; height:3px; }}
            QWidget#{plane}Header QSlider::sub-page:horizontal {{ background:#4887b1; }}
            QWidget#{plane}Header QSlider::handle:horizontal {{ background:#e5ebef; border:1px solid #3f4d59; }}
        """)
        self.canvas = SliceCanvas(plane)
        self.canvas.selected.connect(self.selected)
        self.canvas.scrolled.connect(lambda delta:self.slider.setValue(self.slider.value()+delta))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setToolTip("Move through this physical CT plane. Scroll the image to advance one slice; Ctrl+scroll to zoom.")
        self.slider.setFixedHeight(17)
        self.slider.setMinimumWidth(55)
        self.slider.valueChanged.connect(self._scroll)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1,1,1,1)
        layout.setSpacing(0)
        header=self.header=QWidget(self)
        header.setObjectName(f"{plane}Header")
        header.setFixedHeight(28)
        labels=QHBoxLayout(header)
        labels.setContentsMargins(6,2,6,2)
        labels.setSpacing(6)
        title=self.title_label=QLabel(plane.upper())
        title.setStyleSheet("font-weight:650")
        title.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred)
        title.setMinimumWidth(54)
        labels.addWidget(title)
        labels.addWidget(self.slider,1)
        self.position_label=QLabel("— mm")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        labels.addWidget(self.position_label)
        layout.addWidget(header)
        layout.addWidget(self.canvas,1)
        self.volume = None
        self.slider.setEnabled(False)

    def set_quality(self, max_pixels):
        return self.canvas.set_quality(max_pixels)

    def set_data(self,volume,crosshair,*args,**kwargs):
        self.volume = volume
        self.crosshair = np.array(crosshair)
        bounds = kwargs.pop("bounds",None)
        bounds = volume.bounds if bounds is None else np.asarray(bounds)
        self.minimum = bounds[0,self.axis]
        self.maximum = bounds[1,self.axis]
        self.step = 1./np.linalg.norm(volume.direction[self.axis]/volume.spacing)
        self.slider.setEnabled(True)
        self.slider.blockSignals(True)
        self.slider.setRange(0,int(np.ceil((bounds[1,self.axis]-self.minimum)/self.step)))
        value = (self.slider.maximum() if np.isclose(crosshair[self.axis], self.maximum)
                 else int(round((crosshair[self.axis]-self.minimum)/self.step)))
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.canvas.set_data(volume,crosshair,*args,**kwargs)
        coordinate="XYZ"[self.axis]
        self.position_label.setText(f"{coordinate} {self.canvas.plane.position:+.1f} mm")

    def _scroll(self,value):
        if self.volume is not None:
            point = self.crosshair.copy()
            point[self.axis] = min(self.maximum,self.minimum+value*self.step)
            self.selected.emit(point)



class ObservationPlot(QWidget):
    def __init__(self):
        super().__init__()
        self.data=None
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)

    def set_data(self,data):
        self.data=data
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor("#242628"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#d5d8dc"))
        painter.drawText(8,16,"Target SI displacement (mm; + superior)")
        if self.data is None:
            painter.setPen(QColor("#aeb5bd"))
            painter.drawText(QRectF(12,38,self.width()-24,self.height()-48),
                Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                "Generate observations to inspect the simulated target history.")
            return
        data=self.data
        origin=data.target.center_lps_mm[2]
        truth=data.evaluation_ground_truth_lps_mm[:,2]-origin
        observed=data.observed_lps_mm[:,2]-origin
        lower=min(0.,float(truth.min()),float(observed.min()))
        upper=max(0.,float(truth.max()),float(observed.max()))
        margin=max(.5,(upper-lower)*.1)
        lower,upper=lower-margin,upper+margin
        rect=QRectF(40,29,max(1,self.width()-50),self.height()-76)
        duration=max(.1,data.through_s)
        def points(values):
            return QPolygonF([QPointF(rect.left()+t/duration*rect.width(),
                rect.bottom()-(y-lower)/(upper-lower)*rect.height())
                for t,y in zip(data.times_s,values)])
        painter.setPen(QPen(QColor("#58616a"),1))
        painter.drawRect(rect)
        zero=rect.bottom()-(-lower)/(upper-lower)*rect.height()
        painter.drawLine(QPointF(rect.left(),zero),QPointF(rect.right(),zero))
        painter.setPen(QColor("#c2c7cd"))
        painter.drawText(QRectF(0,rect.top()-7,36,18),Qt.AlignmentFlag.AlignRight,f"{upper:.1f}")
        painter.drawText(QRectF(0,rect.bottom()-9,36,18),Qt.AlignmentFlag.AlignRight,f"{lower:.1f}")
        painter.drawText(QPointF(rect.left(),rect.bottom()+17),"0 s")
        painter.drawText(QRectF(rect.right()-70,rect.bottom()+2,70,18),
                         Qt.AlignmentFlag.AlignRight,f"{data.through_s:g} s")
        painter.setPen(QPen(QColor("#ffc465"),1.5))
        painter.drawPolyline(points(truth))
        painter.setPen(QPen(QColor("#93cbe0"),3))
        painter.drawPoints(points(observed))
        painter.setPen(QColor("#ffc465"))
        painter.drawText(8,self.height()-7,"Simulated truth")
        painter.setPen(QColor("#93cbe0"))
        painter.drawText(132,self.height()-7,"Noisy observations")


class ForecastPlot(QWidget):
    def __init__(self):
        super().__init__()
        self.data=None
        self.method=None
        self.setMinimumHeight(195)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)

    def set_data(self,data,method=None):
        self.data,self.method=data,method
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor("#242628"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#d5d8dc"))
        painter.drawText(8,16,"Target SI displacement (mm)")
        data=self.data
        fit=None if data is None else data["fits"].get(self.method)
        if fit is None:
            text="Compute baselines from recorded observations."
            if data is not None:
                text=data["unavailable"].get(self.method,"No forecast available.")
            painter.setPen(QColor("#b5bdc5"))
            painter.drawText(QRectF(12,35,self.width()-24,self.height()-45),
                Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,text)
            return
        origin=data["origin_s"]
        start=max(float(data["history_times_s"][0]),origin-min(5.,data["settings"].history_window_s))
        past=data["history_times_s"]>=start-1e-10
        times=data["history_times_s"][past]
        reference=data["target"].center_lps_mm[2]
        observed=data["history_observed_lps_mm"][past,2]-reference
        future_times=data["forecast_times_s"]
        forecast=fit.predict(future_times)[:,2]-reference
        truth=data["truth_curve_lps_mm"][:,2]-reference
        values=np.concatenate((observed,forecast,truth))
        lower,upper=float(values.min()),float(values.max())
        margin=max(.5,(upper-lower)*.1)
        lower,upper=lower-margin,upper+margin
        rect=QRectF(40,28,max(1,self.width()-50),self.height()-77)
        end=origin+data["horizon_s"]
        width=max(.1,end-start)
        def points(t,y):
            return QPolygonF([QPointF(rect.left()+(x-start)/width*rect.width(),
                rect.bottom()-(value-lower)/(upper-lower)*rect.height()) for x,value in zip(t,y)])
        painter.setPen(QPen(QColor("#58616a"),1))
        painter.drawRect(rect)
        painter.setPen(QColor("#c2c7cd"))
        painter.drawText(QRectF(0,rect.top()-7,36,18),Qt.AlignmentFlag.AlignRight,f"{upper:.1f}")
        painter.drawText(QRectF(0,rect.bottom()-9,36,18),Qt.AlignmentFlag.AlignRight,f"{lower:.1f}")
        painter.drawText(QPointF(rect.left(),rect.bottom()+17),f"{start:g} s")
        painter.drawText(QRectF(rect.right()-75,rect.bottom()+2,75,18),Qt.AlignmentFlag.AlignRight,f"{end:g} s")
        x=rect.left()+(origin-start)/width*rect.width()
        painter.setPen(QPen(QColor("#8e969e"),1,Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(x,rect.top()),QPointF(x,rect.bottom()))
        painter.setPen(QPen(QColor("#93cbe0"),3))
        painter.drawPoints(points(times,observed))
        if len(truth):
            painter.setPen(QPen(QColor("#ffc465"),2))
            painter.drawPolyline(points(data["truth_times_s"],truth))
        painter.setPen(QPen(QColor("#49dcf4"),2,Qt.PenStyle.DashLine))
        curve=points(future_times,forecast)
        painter.drawPolyline(curve)
        painter.setBrush(QColor("#49dcf4"))
        painter.drawEllipse(curve[-1],3,3)
        painter.setPen(QColor("#93cbe0"))
        painter.drawText(8,self.height()-7,"Past observations")
        painter.setPen(QColor("#49dcf4"))
        painter.drawText(145,self.height()-7,"Forecast")
        if len(truth):
            painter.setPen(QColor("#ffc465"))
            painter.drawText(8,self.height()-23,"Amber: simulated evaluation truth")


class Worker(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(str)
    download_progress = Signal(int,int)
    cancelled = Signal()

    def __init__(self, function, *, progress=False):
        super().__init__()
        self.function = function
        self.report_progress = progress

    def run(self):
        try:
            self.result.emit(self.function(self.progress.emit) if self.report_progress else self.function())
        except InterruptedError as error:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.failed.emit(str(error))
        except Exception as error:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.failed.emit(str(error))



def group(title,layout):
    box=QGroupBox(title)
    box.setLayout(layout)
    return box


class SegmentationDialog(QDialog):
    def __init__(self,path,labels,structures,parent=None,*,protected_keys=()):
        super().__init__(parent)
        self.setWindowTitle("Import segmentation")
        self.setMinimumWidth(380)
        self.structures=structures
        self.protected_keys=frozenset(protected_keys)
        layout=QVBoxLayout(self)
        source=QLabel(Path(path).name)
        source.setWordWrap(True)
        layout.addWidget(source)
        form=QFormLayout()
        self.label=QComboBox()
        for value in labels:
            self.label.addItem(f"Label {value}",str(value))
        if len(labels)>1:
            self.label.addItem("All nonzero labels",None)
        form.addRow("Region",self.label)
        self.name=QComboBox()
        self.name.setEditable(True)
        self.name.lineEdit().setMaxLength(80)
        self.name.addItems([style.name for style in structures.values()])
        default=Path(path).name.removesuffix(".gz").rsplit(".",1)[0].replace("_"," ")[:80]
        self.name.setEditText(default)
        form.addRow("Name",self.name)
        self.kind=QComboBox()
        self.kind.addItems(["Lung tissue","Other structure"])
        self.kind.setCurrentIndex(0 if any(word in default.lower() for word in ("lung","lobe")) else 1)
        self.kind.setToolTip("Lung tissue defines lung coverage and the respiratory preview reference.")
        form.addRow("Type",self.kind)
        layout.addLayout(form)
        self.message=QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.name.currentTextChanged.connect(self._validate)
        self.kind.currentIndexChanged.connect(self._validate)
        self._validate()

    def _validate(self,*args):
        name=self.name.currentText().strip()
        self.existing_key=next((key for key,style in self.structures.items() if style.name.casefold()==name.casefold()),None)
        self.kind.blockSignals(True)
        if self.existing_key is not None:
            self.kind.setCurrentIndex(0 if self.structures[self.existing_key].kind=="lung" else 1)
        self.kind.setEnabled(self.existing_key is None)
        self.kind.blockSignals(False)
        button=self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self.existing_key in self.protected_keys:
            self.message.setText("Use File > Airways > Import aligned airway mask to replace the recorded airway result."
                                 if self.existing_key==AIRWAY_KEY else
                                 "Use File > Lung lobes > Import five-lobe labels to replace the complete lobe segmentation.")
            button.setEnabled(False)
            return
        try:
            StructureStyle(name,"#8cb2c0",kind="lung" if self.kind.currentIndex()==0 else "other")
        except ValueError as error:
            self.message.setText(str(error))
            button.setEnabled(False)
            return
        button.setEnabled(True)
        button.setText("Replace" if self.existing_key is not None else "Add")
        self.message.setText("Replace this structure's mask and preserve its display settings." if self.existing_key is not None
                             else "Add the selected region in the CT's physical coordinates.")

    def selection(self):
        label=self.label.currentData()
        return (self.existing_key,self.name.currentText().strip(),
                "lung" if self.kind.currentIndex()==0 else "other",None if label is None else int(label))



class AirwaySeedDialog(QDialog):
    def __init__(self,volume,seed,parent=None):
        super().__init__(parent)
        self.volume=volume
        self.setWindowTitle("Extract central airways")
        self.setMinimumWidth(390)
        layout=QVBoxLayout(self)
        note=QLabel("Place the crosshair inside the tracheal air column in Imaging, then use that point as the seed. "
                    "Extraction stops before rapid spread into the lung air spaces.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form=QFormLayout()
        self.coordinates=[]
        bounds=volume.bounds
        for axis,name in enumerate(("LPS X","LPS Y","LPS Z")):
            control=QDoubleSpinBox()
            control.setDecimals(2)
            control.setRange(float(bounds[0,axis]),float(bounds[1,axis]))
            control.setSingleStep(.5)
            control.setSuffix(" mm")
            control.setValue(float(seed[axis]))
            self.coordinates.append(control)
            form.addRow(name,control)
        layout.addLayout(form)
        self.message=QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Extract")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for control in self.coordinates:
            control.valueChanged.connect(self._validate)
        self._validate()

    def seed(self):
        return np.array([control.value() for control in self.coordinates])

    def _validate(self,*args):
        continuous=self.volume.world_to_index(self.seed())
        index=np.rint(continuous).astype(int)
        inside=bool(np.all(continuous>=0) and np.all(continuous<=np.array(self.volume.shape[::-1])-1))
        hu=float(self.volume.data[tuple(index[::-1])]) if inside else None
        valid=inside and AIRWAY_SEED_HU_RANGE[0]<=hu<=AIRWAY_SEED_HU_RANGE[1]
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
        self.message.setText((f"Seed voxel: {hu:g} HU. The point must be inside the trachea, not the surrounding lung."
                              if valid else f"Seed voxel: {hu:g} HU. Choose a point inside the dark tracheal lumen in Imaging."
                              if inside else "This point is outside the scan's voxel grid."))


class LandmarkPlot(QWidget):
    clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.rows=[]
        self.index=0
        self.setMinimumHeight(132)
        self.setToolTip("Displacement from the reference in millimetres. Click a phase to view its CT. Missing observations break the line.")

    def set_data(self,rows,index):
        self.rows=rows
        self.index=index
        self.update()

    def _plot_rect(self):
        return QRectF(36,22,max(1,self.width()-52),max(1,self.height()-48))

    def _x(self,percent):
        low,high=self.rows[0]["phase_percent"],self.rows[-1]["phase_percent"]
        return self._plot_rect().left()+(percent-low)/max(high-low,1)*self._plot_rect().width()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#242628"))
        p.setPen(QColor("#c1c5ca"))
        p.drawText(8,14,"Displacement (mm)")
        if not self.rows:
            return
        rect=self._plot_rect()
        maximum=max([row["distance_mm"] or 0. for row in self.rows]+[1.])*1.15
        p.setPen(QPen(QColor("#636a72"),1))
        p.drawLine(rect.bottomLeft(),rect.bottomRight())
        p.drawLine(rect.topLeft(),rect.bottomLeft())
        p.drawText(QRectF(0,rect.top()-6,31,15),Qt.AlignmentFlag.AlignRight,f"{maximum:.1f}")
        p.drawText(QRectF(0,rect.bottom()-8,31,15),Qt.AlignmentFlag.AlignRight,"0")
        previous=None
        for i,row in enumerate(self.rows):
            x=self._x(row["phase_percent"])
            distance=row["distance_mm"]
            if i==self.index:
                p.setPen(QPen(QColor("#738795"),1,Qt.PenStyle.DashLine))
                p.drawLine(QPointF(x,rect.top()),QPointF(x,rect.bottom()))
            if distance is not None:
                point=QPointF(x,rect.bottom()-distance/maximum*rect.height())
                p.setPen(QPen(QColor("#e6bb63"),1.8))
                if previous is not None:
                    p.drawLine(previous,point)
                p.setBrush(QColor("#ffd071"))
                p.drawEllipse(point,3.5,3.5)
                previous=point
            else:
                p.setPen(QPen(QColor("#6f7983"),1))
                p.drawLine(QPointF(x,rect.bottom()-3),QPointF(x,rect.bottom()+3))
                previous=None
            if len(self.rows)<=6 or i in (0,len(self.rows)-1):
                p.setPen(QColor("#c1c5ca"))
                p.drawText(QRectF(x-21,rect.bottom()+5,42,17),Qt.AlignmentFlag.AlignCenter,f"{row['phase_percent']:g}%")

    def mousePressEvent(self,event):
        if self.rows and event.button()==Qt.MouseButton.LeftButton:
            index=min(range(len(self.rows)),key=lambda i:abs(self._x(self.rows[i]["phase_percent"])-event.position().x()))
            self.clicked.emit(index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app.style().objectName().lower() != "fusion":
            app.setStyle("Fusion")
        palette=app.palette()
        for role,colour in ((QPalette.ColorRole.Window,"#303234"),(QPalette.ColorRole.Base,"#242628"),
                            (QPalette.ColorRole.Button,"#424548"),(QPalette.ColorRole.ButtonText,"#e0e1e3"),
                            (QPalette.ColorRole.Text,"#e0e1e3"),(QPalette.ColorRole.WindowText,"#e0e1e3"),
                            (QPalette.ColorRole.Highlight,"#46677e"),(QPalette.ColorRole.HighlightedText,"#ffffff")):
            palette.setColor(role,QColor(colour))
        for role in (QPalette.ColorRole.ButtonText,QPalette.ColorRole.Text,QPalette.ColorRole.WindowText):
            palette.setColor(QPalette.ColorGroup.Disabled,role,QColor("#777d84"))
        app.setPalette(palette)
        self.setWindowTitle("MotionTwin | Pulmonary CT and Motion Preview")
        available = QApplication.primaryScreen().availableGeometry()
        width = min(1600, max(800, available.width()-48))
        height = min(980, max(600, available.height()-64))
        self.setMinimumSize(min(1050, width), min(680, height))
        self.resize(width, height)
        self.setStyleSheet(STYLE)
        self.volume = None
        self.masks = {}
        self.structures = {}
        self._pending_segmentation = None
        self._motion_sections = {}
        self._packed_masks = None
        self.source_info = None
        self.lobe_info = None
        self.airway_info = None
        self.imported_masks = False
        self._supplied_meshes = {}
        self.crosshair = np.zeros(3)
        self.worker = None
        self.ct_sequence = None
        self.phase_index = None
        self._phase_styles = {}
        self.landmarks = None
        self._landmarks_invalid = False
        self._landmark_table_key = None
        self.phase_playing = False
        self.phase_timer = QTimer(self)
        self.phase_timer.setSingleShot(True)
        self.phase_timer.timeout.connect(self._phase_tick)
        self._phase_generation = 0
        self._phase_work_kind = None
        self._phase_pending_manual = None
        self._phase_prepared_sequence = None
        self._phase_start_at_first = False
        self._phase_next_deadline = 0.
        self._respiratory_example_generation = 0
        self._respiratory_example_progress = None
        self._initial_camera_fitted = False
        self.motion_model = None
        self.deformation = None
        self.motion_time = 0.
        self.target = None
        self.target_observations = None
        self.forecast_result = None
        self._forecast_generation = 0
        self._target_mask_key = None
        self._target_mask = None
        self._study_source_paths = set()
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(67)
        self.motion_timer.timeout.connect(self._motion_tick)
        self._ui()
        if cached_public_sample_available():
            QTimer.singleShot(0, self.load_public_example)



    def showEvent(self,event):
        super().showEvent(event)
        if not self._initial_camera_fitted:
            self._initial_camera_fitted=True
            # native viewport sizes are final only after the first layout.
            QTimer.singleShot(0,lambda:self.scene.preset(self.camera.currentText())
                if self.scene.reference_volume is not None else None)


    def _ui(self):
        self.file_menu=self.menuBar().addMenu("File")
        self.open_ct_action=self.file_menu.addAction("Open CT…",self.import_volume)
        self.dicom_action=self.file_menu.addAction("Open DICOM series…",self.import_dicom)
        self.sequence_action=self.file_menu.addAction("Open 4D CT sequence…",self.import_sequence)
        self.import_mask_action=self.file_menu.addAction("Import segmentation…",self.import_mask)
        self.import_mask_action.setEnabled(False)
        self.lobes_menu=self.file_menu.addMenu("Lung lobes")
        self.generate_lobes_action=self.lobes_menu.addAction("Generate from current CT",self.generate_lobes)
        self.import_lobes_action=self.lobes_menu.addAction("Import five-lobe labels…",self.import_lobes)
        self.lobes_menu.setEnabled(False)
        self.airways_menu=self.file_menu.addMenu("Airways")
        self.extract_airways_action=self.airways_menu.addAction("Extract from tracheal seed…",self.extract_airways)
        self.extract_airways_action.setToolTip("Use a tracheal seed in the original static CT in Imaging.")
        self.import_airways_action=self.airways_menu.addAction("Import aligned airway mask…",self.import_airways)
        self.airways_menu.setEnabled(False)
        self.file_menu.addSeparator()
        self.example_action=self.file_menu.addAction("Open example CT",self.load_public_example)
        self.respiratory_example_path=Path(__file__).resolve().parent/"data"/"respiratory-example"/"sequence.json"
        self.respiratory_example_action=self.file_menu.addAction("Open respiratory CT example",self.load_respiratory_example)
        self.file_toolbar=QToolBar("Study files",self)
        self.file_toolbar.setObjectName("studyFiles")
        self.file_toolbar.setMovable(False)
        self.file_toolbar.setFloatable(False)
        self.file_toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.file_toolbar.setIconSize(QSize(16,16))
        self.file_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea,self.file_toolbar)
        for action,label,icon,tip in (
            (self.open_ct_action,"Open CT",QStyle.StandardPixmap.SP_DialogOpenButton,"Open a NIfTI, NRRD or MetaImage CT volume."),
            (self.dicom_action,"DICOM",QStyle.StandardPixmap.SP_DirOpenIcon,"Open a directory containing one DICOM series."),
            (self.sequence_action,"Import 4D CT",QStyle.StandardPixmap.SP_FileDialogListView,"Import your own respiratory CT sequence manifest and matching segmentations."),
            (self.import_mask_action,"Segmentation",QStyle.StandardPixmap.SP_FileDialogDetailedView,"Import an aligned label image as a named structure."),
            (self.example_action,"Example CT",QStyle.StandardPixmap.SP_FileIcon,"Open the public Slicer chest CT example."),
            (self.respiratory_example_action,"Respiratory example",QStyle.StandardPixmap.SP_MediaPlay,
             "Open the preset ten-phase respiratory CT with landmarks. Downloads once when needed; later openings use local data.")):
            action.setIcon(self.style().standardIcon(icon))
            action.setIconText(label)
            action.setToolTip(tip)
            if action is self.example_action:
                self.file_toolbar.addSeparator()
            self.file_toolbar.addAction(action)
        central=QWidget()
        self.setCentralWidget(central)
        outer=QVBoxLayout(central)
        outer.setContentsMargins(5,0,5,4)
        outer.setSpacing(4)
        study_strip=QWidget()
        study_strip.setObjectName("studyStrip")
        header=QHBoxLayout(study_strip)
        header.setContentsMargins(10,6,8,6)
        header.setSpacing(12)
        brand=QLabel("MotionTwin")
        brand.setObjectName("brand")
        header.addWidget(brand)
        self.study_metadata=QLabel("Open a CT study to begin")
        self.study_metadata.setObjectName("studyMetadata")
        self.study_metadata.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        header.addWidget(self.study_metadata,1)
        self.badge=QLabel("CT VIEWER")
        self.badge.setObjectName("badge")
        header.addWidget(self.badge)
        outer.addWidget(study_strip)
        self._phase_transport_controls(outer)

        self.status=QLabel("CT imaging and lung reconstruction")
        self.status.setObjectName("statusLine")
        self.status.setWordWrap(True)
        self.status.setMaximumHeight(36)
        self.statusBar().addWidget(self.status,1)
        main=QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter=main
        main.setChildrenCollapsible(False)
        main.setHandleWidth(5)
        outer.addWidget(main,1)
        self.controls=QTabWidget()
        self.controls.setMinimumWidth(270)
        for name,build in (("Imaging",self._imaging_controls),("Motion",self._motion_controls),("Landmarks",self._landmark_controls)):
            scroll=QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            content=QWidget()
            controls_layout=QVBoxLayout(content)
            controls_layout.setContentsMargins(10,8,10,8)
            controls_layout.setSpacing(8)
            build(controls_layout)
            scroll.setWidget(content)
            self.controls.addTab(scroll,name)
        self.controls.setTabEnabled(1,False)
        self.controls.setTabEnabled(2,False)
        self.controls.setTabToolTip(2,"Open a respiratory CT sequence to record phase-specific landmark positions.")
        self.controls.currentChanged.connect(self._workspace_changed)
        main.addWidget(self.controls)

        # keep native viewport parents fixed for the four-view layout.
        center=QWidget()
        center.setMinimumWidth(600)
        self.imaging_workspace=center
        center_layout=QVBoxLayout(center)
        center_layout.setContentsMargins(0,0,0,0)
        center_layout.setSpacing(3)
        self.viewport_grid_parent=QWidget(center)
        self.viewport_grid=QGridLayout(self.viewport_grid_parent)
        self.viewport_grid.setContentsMargins(0,0,0,0)
        self.viewport_grid.setSpacing(3)
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
        toolbar_panel.setFixedHeight(28)
        toolbar=QHBoxLayout(toolbar_panel)
        toolbar.setContentsMargins(6,2,6,2)
        toolbar.setSpacing(5)
        self.camera=QComboBox()
        self.camera.addItems(["Oblique","Anterior","Posterior","Left","Superior"])
        self.camera.setFixedWidth(94)
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
        sidebar_width=max(300,min(440,round(self.width()*.30)))
        main.setSizes([sidebar_width,max(600,self.width()-sidebar_width)])
        self.display_info=QLabel("Static CT · linked physical coordinates")
        self.display_info.setStyleSheet("color:#bec3c9;font-size:10px")
        self.display_info.setToolTip("Coordinates: LPS millimetres. Click a CT view to position; scroll to slice; Ctrl+scroll to zoom.")
        self.display_info.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        outer.addWidget(self.display_info)


    def spin(self,minimum,maximum,value,step=1,decimals=1):
        widget=QDoubleSpinBox()
        widget.setRange(minimum,maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setValue(value)
        widget.setKeyboardTracking(False)
        return widget


    def _imaging_controls(self,layout):
        self._phase_controls(layout)
        self._structure_controls(layout)
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
        texture=QVBoxLayout()
        self.opacity=QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0,90)
        self.opacity.setValue(35)
        self.opacity.setToolTip("Opacity of the reconstructed CT texture; zero hides the texture.")
        self.opacity.valueChanged.connect(self._texture_opacity_changed)
        texture.addWidget(self.opacity)
        self.ct_texture_group=group("3D CT texture opacity",texture)
        self.ct_texture_group.setEnabled(False)
        layout.addWidget(self.ct_texture_group)
        self.imaging_info=QLabel("")
        self.imaging_info.setWordWrap(True)
        self.imaging_info.setMinimumWidth(0)
        self.imaging_info.setMinimumHeight(70)
        self.imaging_info.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.imaging_info)
        layout.addStretch()

    def _phase_controls(self,layout):
        controls=QVBoxLayout()
        self.phase_selector=QComboBox()
        self.phase_selector.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.phase_selector.currentIndexChanged.connect(self.request_phase)
        controls.addWidget(self.phase_selector)
        navigation=QHBoxLayout()
        self.phase_previous=QToolButton()
        self.phase_previous.setText("Previous")
        self.phase_previous.clicked.connect(lambda:self.request_phase(self.phase_index-1))
        self.phase_slider=QSlider(Qt.Orientation.Horizontal)
        self.phase_slider.setTracking(False)
        self.phase_slider.setToolTip("Select a supplied respiratory phase; percentage is separate from elapsed time.")
        self.phase_slider.valueChanged.connect(self.request_phase)
        self.phase_next=QToolButton()
        self.phase_next.setText("Next")
        self.phase_next.clicked.connect(lambda:self.request_phase(self.phase_index+1))
        navigation.addWidget(self.phase_previous)
        navigation.addWidget(self.phase_slider,1)
        navigation.addWidget(self.phase_next)
        controls.addLayout(navigation)
        self.phase_readout=QLabel()
        self.phase_readout.setWordWrap(True)
        controls.addWidget(self.phase_readout)
        self.phase_group=group("Respiratory phases",controls)
        self.phase_group.hide()
        layout.addWidget(self.phase_group)

    def _phase_transport_controls(self,layout):
        self.phase_transport=QWidget()
        self.phase_transport.setObjectName("studyStrip")
        self.phase_transport.setToolTip("Discrete preview of supplied respiratory phases at a chosen display rate. Acquisition timestamps, when available, remain unchanged.")
        row=QHBoxLayout(self.phase_transport)
        row.setContentsMargins(8,4,8,4)
        row.setSpacing(8)
        self.phase_play=QToolButton()
        self.phase_play.setText("Play")
        self.phase_play.setToolTip("Play the supplied CT phases as a discrete preview. Pause holds the displayed phase.")
        self.phase_play.clicked.connect(self.toggle_phase_playback)
        row.addWidget(self.phase_play)
        self.phase_reset=QToolButton()
        self.phase_reset.setText("Reset")
        self.phase_reset.setToolTip("Stop playback and return to the first supplied phase.")
        self.phase_reset.clicked.connect(self.reset_phase_playback)
        row.addWidget(self.phase_reset)
        self.phase_loop=QCheckBox("Loop")
        self.phase_loop.setChecked(True)
        row.addWidget(self.phase_loop)
        row.addWidget(QLabel("Preview rate"))
        self.phase_rate=self.spin(.25,2.,1.,.25,2)
        self.phase_rate.setSuffix(" phases/s")
        self.phase_rate.setToolTip("Requested display pacing. Loading can slow the preview; this is separate from CT acquisition timing and breathing rate.")
        self.phase_rate.valueChanged.connect(self._phase_rate_changed)
        row.addWidget(self.phase_rate)
        self.phase_position=QLabel()
        row.addWidget(self.phase_position)
        self.phase_pacing=QLabel("Discrete preview · source timing not supplied")
        self.phase_pacing.setWordWrap(True)
        self.phase_pacing.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        row.addWidget(self.phase_pacing,1)
        self.phase_transport.hide()
        layout.addWidget(self.phase_transport)

    def _update_phase_transport(self):
        sequence=self.ct_sequence
        if sequence is None:
            self.phase_transport.hide()
            return
        self.phase_transport.show()
        self.phase_play.setText("Pause" if self.phase_playing else "Play")
        self.phase_play.setEnabled(self.phase_playing or self.worker is None)
        self.phase_reset.setEnabled(self.worker is None or self._phase_work_kind in ("auto","prepare"))
        phase=sequence.phases[self.phase_index]
        self.phase_position.setText(f"{self.phase_index+1} / {len(sequence.phases)} · {phase.percent:g}%")
        self.phase_pacing.setText("Discrete preview · "+("supplied timestamps shown separately" if phase.time_s is not None
                                   else "source timing not supplied"))

    def pause_phase_playback(self):
        was_playing=self.phase_playing
        self.phase_playing=False
        self.phase_timer.stop()
        self._phase_generation+=1
        self._phase_start_at_first=False
        self._phase_pending_manual=None
        if self.worker is not None and self._phase_work_kind=="prepare":
            self.worker.requestInterruption()
        if hasattr(self,"phase_play"):
            self._update_phase_transport()
        if was_playing:
            self.status.setText("Respiratory phase preview paused.")

    def toggle_phase_playback(self):
        if self.phase_playing:
            self.pause_phase_playback()
            return
        if self.ct_sequence is None or self.worker is not None or not self._update_landmarks():
            return
        self.pause_motion()
        self.phase_playing=True
        self._phase_generation+=1
        self._phase_start_at_first=self.phase_index==len(self.ct_sequence.phases)-1 and not self.phase_loop.isChecked()
        if self._phase_prepared_sequence is not self.ct_sequence:
            sequence=self.ct_sequence
            generation=self._phase_generation
            def read(report):
                def progress(completed,total):
                    if QThread.currentThread().isInterruptionRequested():
                        raise InterruptedError("Phase preparation cancelled.")
                    report(f"Preparing respiratory phase surfaces · {completed} / {total}")
                sequence.prepare_surfaces(progress)
                return sequence
            def accepted(prepared):
                if self.phase_playing and generation==self._phase_generation and prepared is self.ct_sequence:
                    self._phase_prepared_sequence=prepared
                    self.status.setText("Respiratory phases ready for discrete preview.")
            self.task(read,accepted,"Preparing respiratory phases for preview…",phase_kind="prepare",progress=True)
        else:
            self._start_phase_timer()
            self.status.setText("Playing supplied respiratory phases at the selected preview rate.")
        self._update_phase_transport()

    def _start_phase_timer(self):
        if not self.phase_playing or self.worker is not None:
            return
        if self._phase_start_at_first:
            self._phase_start_at_first=False
            self._phase_next_deadline=perf_counter()+1/self.phase_rate.value()
            self.request_phase(0,automatic=True)
            return
        self._phase_next_deadline=perf_counter()+1/self.phase_rate.value()
        self._arm_phase_timer()

    def _arm_phase_timer(self):
        if self.phase_playing and self.worker is None:
            remaining=max(.001,self._phase_next_deadline-perf_counter())
            self.phase_timer.start(max(1,round(1000*remaining)))

    def _phase_rate_changed(self,*args):
        if self.phase_playing:
            self._phase_next_deadline=perf_counter()+1/self.phase_rate.value()
            if self.worker is None:
                self._arm_phase_timer()

    def _phase_tick(self):
        if not self.phase_playing or self.ct_sequence is None or self.worker is not None:
            return
        index=self.phase_index+1
        if index==len(self.ct_sequence.phases):
            if not self.phase_loop.isChecked():
                self.pause_phase_playback()
                self.status.setText("End of the supplied respiratory sequence.")
                return
            index=0
        self._phase_next_deadline=perf_counter()+1/self.phase_rate.value()
        self.request_phase(index,automatic=True)

    def reset_phase_playback(self):
        self.request_phase(0)

    def _structure_controls(self,layout):
        self.structure_tree=QTreeWidget()
        self.structure_tree.setColumnCount(3)
        self.structure_tree.setHeaderLabels(["Structure","Show","Colour"])
        self.structure_tree.setMinimumHeight(176)
        self.structure_tree.setMaximumHeight(240)
        self.structure_tree.setAlternatingRowColors(True)
        self.structure_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.structure_tree.header().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for column in (1,2):
            self.structure_tree.header().setSectionResizeMode(column,QHeaderView.ResizeMode.Fixed)
            self.structure_tree.setColumnWidth(column,48)
        self.structure_tree.setToolTip("Show applies to 3D surfaces and enabled CT overlays. Double-click a colour swatch to edit it.")
        self.structure_tree.currentItemChanged.connect(self._structure_selected)
        self.structure_tree.itemChanged.connect(self._structure_item_changed)
        self.structure_tree.itemDoubleClicked.connect(lambda item,column:self.choose_structure_color() if column==2 else None)
        layout.addWidget(self.structure_tree)
        self.structure_items={}
        self._selected_key=None
        form=QFormLayout()
        self.structure_name=QLineEdit()
        self.structure_name.setMaxLength(80)
        self.structure_name.editingFinished.connect(self._rename_structure)
        form.addRow("Name",self.structure_name)
        self.structure_color=QToolButton()
        self.structure_color.clicked.connect(self.choose_structure_color)
        form.addRow("Colour",self.structure_color)
        opacity_row=QHBoxLayout()
        self.structure_opacity=QSlider(Qt.Orientation.Horizontal)
        self.structure_opacity.setRange(0,100)
        self.structure_opacity.valueChanged.connect(self._structure_opacity_changed)
        self.structure_opacity_label=QLabel("35%")
        self.structure_opacity_label.setFixedWidth(36)
        opacity_row.addWidget(self.structure_opacity,1)
        opacity_row.addWidget(self.structure_opacity_label)
        form.addRow("Surface / overlay",opacity_row)
        self.structure_ct_colors=QCheckBox("CT-coloured surface")
        self.structure_ct_colors.setToolTip("Use sampled CT colours on this 3D surface. Choosing a segment colour turns this off.")
        self.structure_ct_colors.toggled.connect(self._structure_ct_colors_changed)
        form.addRow(self.structure_ct_colors)
        self.structure_properties=group("Selected structure",form)
        self.structure_properties.setEnabled(False)
        layout.addWidget(self.structure_properties)

    def _landmark_controls(self,layout):
        instruction=QLabel("Select the same feature in each phase's CT, then confirm its crosshair position. Positions are never tracked automatically.")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        form=QFormLayout()
        self.landmark_name=QLineEdit("Landmark 1")
        self.landmark_name.setMaxLength(80)
        self.landmark_name.textEdited.connect(lambda:self.pause_phase_playback())
        self.landmark_name.editingFinished.connect(self._rename_landmark)
        form.addRow("Landmark",self.landmark_name)
        self.landmark_reference=QComboBox()
        self.landmark_reference.currentIndexChanged.connect(self._reference_landmark_changed)
        form.addRow("Reference phase",self.landmark_reference)
        layout.addLayout(form)
        self.landmark_mark=QToolButton()
        self.landmark_mark.setText("Confirm crosshair position")
        self.landmark_mark.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.landmark_mark.clicked.connect(self.record_landmark)
        layout.addWidget(self.landmark_mark)
        buttons=QHBoxLayout()
        for field,label,callback in (("landmark_go","Go to point",self.go_to_landmark),
                                      ("landmark_remove","Remove phase point",self.remove_landmark)):
            button=QToolButton()
            button.setText(label)
            button.clicked.connect(callback)
            setattr(self,field,button)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.landmark_readout=QLabel()
        self.landmark_readout.setMinimumHeight(96)
        self.landmark_readout.setWordWrap(True)
        layout.addWidget(self.landmark_readout)
        self.landmark_plot=LandmarkPlot()
        self.landmark_plot.clicked.connect(self.request_phase)
        layout.addWidget(self.landmark_plot)
        self.landmark_table=QTreeWidget()
        self.landmark_table.setColumnCount(3)
        self.landmark_table.setHeaderLabels(["Phase","|Δr| mm","Source"])
        self.landmark_table.setRootIsDecorated(False)
        self.landmark_table.setAlternatingRowColors(True)
        self.landmark_table.setMinimumHeight(120)
        self.landmark_table.setMaximumHeight(185)
        self.landmark_table.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.landmark_table.currentItemChanged.connect(self._landmark_phase_selected)
        layout.addWidget(self.landmark_table)
        files=QHBoxLayout()
        for field,label,callback in (("landmark_import","Import points…",self.import_landmarks),
                                     ("landmark_export","Export CSV…",self.export_landmarks)):
            button=QToolButton()
            button.setText(label)
            button.clicked.connect(callback)
            setattr(self,field,button)
            files.addWidget(button)
        layout.addLayout(files)
        note=QLabel("LPS mm: +L left · +P posterior · +S superior\nGold: current point · blue: reference\nLines join observations in adjacent supplied phases.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#b8bec6;font-size:10px")
        layout.addWidget(note)
        layout.addStretch()

    def _rename_landmark(self):
        if self.landmarks is None:
            return
        try:
            self.landmarks.name=self.landmark_name.text()
        except ValueError as error:
            self.landmark_name.setText(self.landmarks.name)
            self.status.setText(str(error))

    def _reference_landmark_changed(self,index):
        if self.landmarks is not None and index>=0:
            self.pause_phase_playback()
            if not self._update_landmarks():
                self.landmark_reference.blockSignals(True)
                self.landmark_reference.setCurrentIndex(self.landmarks.reference_index)
                self.landmark_reference.blockSignals(False)
                return
            self.landmarks.reference_index=index
            self._update_landmarks()
            self.scene.render()

    def _landmark_phase_selected(self,item,previous):
        if item is not None:
            self.request_phase(item.data(0,Qt.ItemDataRole.UserRole))

    def record_landmark(self):
        if self.landmarks is None or self.worker is not None:
            return
        self.pause_phase_playback()
        if not self._update_landmarks():
            return
        try:
            self.landmarks.set_point(self.phase_index,self.crosshair,source="manual")
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.refresh()
        self.status.setText("Confirmed this phase's landmark position. Inspect the same feature in the next supplied phase.")

    def remove_landmark(self):
        if self.landmarks is None or self.worker is not None:
            return
        self.pause_phase_playback()
        if not self._update_landmarks():
            return
        try:
            self.landmarks.remove_point(self.phase_index)
        except ValueError as error:
            self._invalidate_landmarks(str(error))
            return
        self.refresh()

    def go_to_landmark(self):
        if self.landmarks is None or self.worker is not None:
            return
        self.pause_phase_playback()
        if not self._update_landmarks():
            return
        point=self.landmarks.points.get(self.phase_index)
        if point is not None:
            self.set_crosshair(point)

    def accept_landmarks(self,series):
        if not isinstance(series,LandmarkSeries) or series.sequence is not self.ct_sequence:
            raise ValueError("Landmarks must belong to the open respiratory CT sequence.")
        series.measurements()
        self.landmarks=series
        self._landmarks_invalid=False
        self._landmark_table_key=None
        self.refresh()

    def import_landmarks(self):
        if self.ct_sequence is None or self.worker is not None:
            return
        self.pause_phase_playback()
        if not self._update_landmarks():
            return
        path,_=QFileDialog.getOpenFileName(self,"Import phase landmark positions",str(self.ct_sequence._manifest.parent),"Landmark coordinates (*.csv)")
        if path:
            try:
                series=load_landmarks(path,self.ct_sequence)
                self.accept_landmarks(series)
                self.status.setText("Imported landmark coordinates for this CT sequence.")
            except (ValueError,OSError) as error:
                QMessageBox.warning(self,"Cannot import landmark coordinates",str(error))

    def export_landmarks(self):
        if self.landmarks is None or self.worker is not None:
            return
        self.pause_phase_playback()
        if not self._update_landmarks():
            return
        path,_=QFileDialog.getSaveFileName(self,"Export phase landmark positions","landmark-motion.csv","Landmark coordinates (*.csv)")
        if path:
            try:
                self.landmarks.export_csv(path)
                self.status.setText("Exported physical coordinates, reference displacement and missing-phase rows.")
            except (ValueError,OSError) as error:
                QMessageBox.warning(self,"Cannot export landmark coordinates",str(error))

    def _invalidate_landmarks(self,message):
        self.pause_phase_playback()
        self._landmarks_invalid=True
        self.scene.set_landmarks(None,self.phase_index)
        for view in self.slices:
            view.canvas.set_landmark(None,0.)
        self.landmark_plot.set_data([],0)
        self.landmark_table.clear()
        self._landmark_table_key=None
        self.landmark_readout.setText("CT sources changed or are unavailable. Reopen the sequence before measuring or exporting.\n"+message)
        for control in (self.landmark_mark,self.landmark_go,self.landmark_remove,self.landmark_export,self.landmark_reference):
            control.setEnabled(False)
        self.status.setText("CT sources changed or are unavailable. Reopen the respiratory sequence.")
        self.scene.render()

    def _update_landmarks(self,*,validate=True):
        series=self.landmarks
        if self._landmarks_invalid and series is not None:
            return False
        key=(id(series),series.reference_index,tuple((i,tuple(p),series.sources[i]) for i,p in sorted(series.points.items()))) if series is not None else None
        if series is not None and (validate or key!=getattr(self,"_landmark_rows_key",None)):
            try:
                self._landmark_rows=series.measurements()
                self._landmark_rows_key=key
            except ValueError as error:
                self._invalidate_landmarks(str(error))
                return False
        self.scene.set_landmarks(series,self.phase_index)
        point=None if series is None else series.points.get(self.phase_index)
        for view in self.slices:
            tolerance=(0.5/np.linalg.norm(self.volume.direction[view.axis]/self.volume.spacing)
                       if self.volume is not None else 0.)
            view.canvas.set_landmark(point,tolerance)
        if series is None:
            if self._landmark_table_key is not None:
                self.landmark_plot.set_data([],0)
                self.landmark_table.clear()
            self._landmark_table_key=None
            return True
        rows=self._landmark_rows
        index=self.phase_index
        row=rows[index]
        self.landmark_name.setText(series.name)
        self.landmark_reference.blockSignals(True)
        self.landmark_reference.setCurrentIndex(series.reference_index)
        self.landmark_reference.blockSignals(False)
        self.landmark_reference.setEnabled(True)
        self.landmark_go.setEnabled(point is not None)
        self.landmark_remove.setEnabled(point is not None)
        self.landmark_export.setEnabled(bool(series.points))
        voxel=self.volume.world_to_index(self.crosshair)
        self.landmark_mark.setEnabled(bool(np.all(voxel>=-1e-8) and np.all(voxel<=np.array(self.volume.shape[::-1])-1+1e-8)))
        self.landmark_mark.setText("Replace phase position" if point is not None else "Confirm crosshair position")
        text=f"Phase {self.ct_sequence.phases[index].percent:g}% · {len(series.points)} / {len(rows)} recorded\n"
        if point is None:
            text+="No point recorded in this phase.\nDisplacement unavailable."
        else:
            text+="L / P / S: "+" / ".join(f"{value:.2f}" for value in point)+" mm\n"
            text+=(f"ΔL {row['dx_mm']:+.2f} · ΔP {row['dy_mm']:+.2f} · ΔS {row['dz_mm']:+.2f} mm\n"
                   f"3D displacement: {row['distance_mm']:.2f} mm" if row["distance_mm"] is not None
                   else "Record the reference phase to measure displacement.")
        if series.provenance:
            text+="\n"+(series.provenance if len(series.provenance)<=100 else series.provenance[:97]+"…")
        self.landmark_readout.setText(text)
        self.landmark_readout.setToolTip(series.provenance)
        self.landmark_plot.set_data(rows,index)
        self.landmark_table.blockSignals(True)
        if key!=self._landmark_table_key:
            self.landmark_table.clear()
            for i,item in enumerate(rows):
                entry=QTreeWidgetItem([f"{item['phase_percent']:g}%",
                    "—" if item["distance_mm"] is None else f"{item['distance_mm']:.2f}",
                    item["source"] or "Missing"])
                entry.setData(0,Qt.ItemDataRole.UserRole,i)
                self.landmark_table.addTopLevelItem(entry)
            self._landmark_table_key=key
        self.landmark_table.setCurrentItem(self.landmark_table.topLevelItem(index))
        self.landmark_table.blockSignals(False)
        return True

    def _rebuild_structure_tree(self,selected=None):
        self.structure_tree.blockSignals(True)
        self.structure_tree.clear()
        self.structure_items={}
        if self.volume is not None:
            source=QTreeWidgetItem([self.volume.name])
            source.setToolTip(0,self.volume.name)
            source.setIcon(0,self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
            self.structure_tree.addTopLevelItem(source)
            if self.structures:
                root=QTreeWidgetItem(["Segmentations"])
                root.setIcon(0,self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
                self.structure_tree.addTopLevelItem(root)
                lobe_keys=[key for _,key,_,_ in LOBE_SEGMENTS if key in self.structures]
                ordered=lobe_keys+([AIRWAY_KEY] if AIRWAY_KEY in self.structures else [])
                for key in ordered+[key for key in self.structures if key not in ordered]:
                    style=self.structures[key]
                    item=QTreeWidgetItem(root)
                    item.setData(0,Qt.ItemDataRole.UserRole,key)
                    item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
                    self.structure_items[key]=item
                    self._update_structure_item(key)
                root.setExpanded(True)
        key=selected if selected in self.structures else next(iter(self.structures),None)
        if key is not None:
            self.structure_tree.setCurrentItem(self.structure_items[key])
        self.structure_tree.blockSignals(False)
        self._structure_selected(self.structure_tree.currentItem(),None)

    def _update_structure_item(self,key):
        item=self.structure_items[key]
        style=self.structures[key]
        blocked=self.structure_tree.blockSignals(True)
        item.setText(0,style.name)
        item.setToolTip(0,style.name+"\n"+("Lung tissue" if style.kind=="lung" else "Other structure"))
        if self.lobe_info is not None and key in {entry[1] for entry in LOBE_SEGMENTS}:
            item.setToolTip(0,item.toolTip(0)+"\n"+self.lobe_info["model"]+" · not expert reviewed")
        if self.airway_info is not None and key==AIRWAY_KEY:
            item.setToolTip(0,item.toolTip(0)+"\n"+self.airway_info["method"]+" · not expert reviewed\nCentral airway lumen; distal branches may be incomplete.")
        item.setCheckState(1,Qt.CheckState.Checked if style.visible else Qt.CheckState.Unchecked)
        swatch=QPixmap(16,16)
        swatch.fill(QColor(style.color))
        item.setIcon(2,QIcon(swatch))
        item.setToolTip(2,style.color+" · double-click to change")
        self.structure_tree.blockSignals(blocked)

    def _structure_selected(self,item,previous=None):
        key=item.data(0,Qt.ItemDataRole.UserRole) if item is not None else None
        self._selected_key=key if key in self.structures else None
        self.structure_properties.setEnabled(self._selected_key is not None)
        if self._selected_key is None:
            self.structure_name.clear()
            self.structure_color.setText("—")
            self.structure_color.setIcon(QIcon())
            self.structure_opacity_label.setText("—")
            return
        style=self.structures[key]
        self.structure_name.setText(style.name)
        self.structure_color.setText(style.color)
        self.structure_color.setIcon(item.icon(2))
        for control,value in ((self.structure_opacity,round(style.opacity*100)),(self.structure_ct_colors,style.ct_coloring)):
            control.blockSignals(True)
            control.setValue(value) if control is self.structure_opacity else control.setChecked(value)
            control.blockSignals(False)
        self.structure_opacity_label.setText(f"{round(style.opacity*100)}%")

    def update_structure(self,key,**changes):
        style=replace(self.structures[key],**changes)
        available=self._phase_styles if self.ct_sequence is not None else self.structures
        if any(other!=key and value.name.casefold()==style.name.casefold() for other,value in available.items()):
            raise ValueError("A structure with that name already exists.")
        self.structures={**self.structures,key:style}
        if self.ct_sequence is not None:
            self._phase_styles={**self._phase_styles,key:style}
        self.scene.set_structures(self.structures)
        self.ct_texture_group.setEnabled(self.scene.scan._has_context)
        self._update_structure_item(key)
        if key==self._selected_key:
            self._structure_selected(self.structure_items[key])
        self.refresh()

    def _structure_item_changed(self,item,column):
        key=item.data(0,Qt.ItemDataRole.UserRole)
        if key in self.structures and column==1:
            self.update_structure(key,visible=item.checkState(1)==Qt.CheckState.Checked)

    def _rename_structure(self):
        if self._selected_key is None:
            return
        if self.structure_name.text()==self.structures[self._selected_key].name:
            return
        try:
            self.update_structure(self._selected_key,name=self.structure_name.text())
            self.status.setText("Structure name updated.")
        except ValueError as error:
            self.status.setText(str(error))
            self.structure_name.setText(self.structures[self._selected_key].name)

    def choose_structure_color(self):
        key=self._selected_key
        if key is None:
            return
        color=QColorDialog.getColor(QColor(self.structures[key].color),self,"Structure colour")
        if color.isValid():
            self.update_structure(key,color=color.name(),ct_coloring=False)

    def _structure_opacity_changed(self,value):
        if self._selected_key is not None:
            self.update_structure(self._selected_key,opacity=value/100)

    def _structure_ct_colors_changed(self,checked):
        if self._selected_key is not None:
            self.update_structure(self._selected_key,ct_coloring=checked)

    def _texture_opacity_changed(self,value):
        self.scene.scan.set_opacity(value/100)
        self.scene.render()


    def _motion_controls(self,layout):
        note=QLabel("SIMULATED MOTION\nA mathematical preview of this scan, not measured 4D CT. The original scan is in Imaging.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#c2d5e3; padding:3px 0")
        layout.addWidget(note)
        self._target_controls(layout)
        form=QFormLayout()
        self.breathing_pattern=QComboBox()
        self.breathing_pattern.addItems(BREATHING_PATTERNS)
        self.motion_amplitude=self.spin(0,30,8,.5)
        self.motion_amplitude.setSuffix(" mm")
        self.motion_amplitude.setToolTip("Reference superior–inferior amplitude at the lung base; the apex stays fixed.")
        self.breathing_rate=self.spin(6,36,15,1)
        self.breathing_rate.setSuffix(" /min")
        self.motion_seed=QSpinBox()
        self.motion_seed.setRange(0,999999)
        self.motion_seed.setValue(17)
        self.motion_seed.setKeyboardTracking(False)
        self.motion_seed.setToolTip("Reproduces the irregular pattern. Regular breathing does not use randomness.")
        for label,control in (("Pattern",self.breathing_pattern),("Base amplitude",self.motion_amplitude),
                              ("Breathing rate",self.breathing_rate),("Pattern seed",self.motion_seed)):
            form.addRow(label,control)
        self.breathing_group=group("Breathing",form)
        layout.addWidget(self.breathing_group)
        self.breathing_pattern.currentTextChanged.connect(self._motion_settings_changed)
        for control in (self.motion_amplitude,self.breathing_rate,self.motion_seed):
            control.valueChanged.connect(self._motion_settings_changed)
        playback=QVBoxLayout()
        buttons=QHBoxLayout()
        self.play_button=QToolButton()
        self.play_button.setText("Play")
        self.play_button.clicked.connect(self.toggle_motion)
        self.reset_motion_button=QToolButton()
        self.reset_motion_button.setText("Reset")
        self.reset_motion_button.clicked.connect(self.reset_motion)
        buttons.addWidget(self.play_button,1)
        buttons.addWidget(self.reset_motion_button,1)
        playback.addLayout(buttons)
        self.motion_seek=QSlider(Qt.Orientation.Horizontal)
        self.motion_seek.setRange(0,6000)
        self.motion_seek.setTracking(False)
        self.motion_seek.setToolTip("Pause and seek within the 60-second preview. Release the handle to update.")
        self.motion_seek.sliderPressed.connect(self.pause_motion)
        self.motion_seek.valueChanged.connect(self.seek_motion)
        playback.addWidget(self.motion_seek)
        self.motion_readout=QLabel("0.00 / 60 s")
        self.motion_readout.setWordWrap(True)
        self.motion_readout.setToolTip("Base superior–inferior displacement and velocity in LPS coordinates: positive is superior. Phase is the fraction of a breathing cycle.")
        playback.addWidget(self.motion_readout)
        layout.addWidget(group("Preview playback",playback))
        self._observation_controls(layout)
        explanation=QLabel("Settings blend over 1 second of simulation time without resetting phase.\n\n"
            "Motion varies smoothly from apex to base. CT, masks and surfaces share the same field. "
            "This simple deformation does not model tissue mechanics.\n\n"
            "Crosshairs mark a fixed position in the displayed world, not a tracked lesion.")
        explanation.setWordWrap(True)
        explanation.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(explanation)
        layout.addStretch()

    def _target_controls(self,layout):
        body=QVBoxLayout()
        note=QLabel("User-defined sphere in lung tissue. This is a simulated research target, not a detected lesion.")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(note)
        form=QFormLayout()
        self.target_radius=self.spin(.5,20,3,.5)
        self.target_radius.setSuffix(" mm")
        self.target_radius.setToolTip("Radius in the reference CT; the entire sphere must fit inside the lung masks and scan.")
        form.addRow("Reference radius",self.target_radius)
        body.addLayout(form)
        buttons=QHBoxLayout()
        for field,label,callback in (("target_set","Set at crosshair",self.set_target_at_crosshair),
                                     ("target_go","Go to target",self.go_to_target),
                                     ("target_clear","Clear",self.clear_target)):
            button=QToolButton()
            button.setText(label)
            button.setEnabled(False)
            button.clicked.connect(callback)
            setattr(self,field,button)
            buttons.addWidget(button,1)
        body.addLayout(buttons)
        self.target_readout=QLabel("No target defined.")
        self.target_readout.setWordWrap(True)
        self.target_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.target_readout)
        layout.addWidget(group("Simulated research target",body))
        self.target_radius.valueChanged.connect(self._target_radius_changed)

    def _observation_controls(self,layout):
        body=QVBoxLayout()
        form=QFormLayout()
        self.observation_rate=self.spin(.1,100,10,.5)
        self.observation_rate.setSuffix(" Hz")
        self.observation_noise=self.spin(0,20,.5,.1,decimals=2)
        self.observation_noise.setSuffix(" mm / axis")
        self.observation_noise.setToolTip("Independent Gaussian observation noise in each LPS axis. It does not change the target or scan.")
        self.observation_seed=QSpinBox()
        self.observation_seed.setRange(0,999999)
        self.observation_seed.setValue(17)
        self.observation_seed.setKeyboardTracking(False)
        for label,control in (("Sampling rate",self.observation_rate),("Noise SD",self.observation_noise),
                              ("Noise seed",self.observation_seed)):
            form.addRow(label,control)
            control.valueChanged.connect(self._invalidate_observations)
        body.addLayout(form)
        note=QLabel("Samples use simulation seconds, independent of display frames. Seek to a time, then record the history from 0 to that time.")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(note)
        self.observation_generate=QToolButton()
        self.observation_generate.setText("Record history to current time")
        self.observation_generate.clicked.connect(self.generate_observations)
        self.observation_generate.setEnabled(False)
        body.addWidget(self.observation_generate)
        self.observation_readout=QLabel("No observations recorded.")
        self.observation_readout.setWordWrap(True)
        self.observation_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.observation_readout)
        self.observation_plot=ObservationPlot()
        body.addWidget(self.observation_plot)
        for field,label,truth in (("observation_export","Export observations CSV…",False),
                                  ("evaluation_export","Export evaluation CSV (with truth)…",True)):
            button=QToolButton()
            button.setText(label)
            button.setEnabled(False)
            button.clicked.connect(lambda checked=False,include_truth=truth:self.export_observations(include_truth))
            setattr(self,field,button)
            body.addWidget(button)
        layout.addWidget(group("Timed target observations",body))

    def _lung_target_mask(self):
        key=(id(self.volume),tuple((name,id(mask)) for name,mask in self.masks.items()
                                  if self.structures[name].kind=="lung"))
        if key!=self._target_mask_key:
            mask=np.zeros(self.volume.shape,dtype=bool)
            for name,_ in key[1]:
                np.logical_or(mask,self.masks[name],out=mask)
            self._target_mask,self._target_mask_key=mask,key
        return self._target_mask

    def _motion_matrix(self):
        return (self.deformation.matrix(self.motion_model.position(self.motion_time))
                if self.motion_active else np.eye(4))

    def _display_bounds(self,matrix=None):
        if not self.motion_active or self.target is None:
            return self.volume.bounds
        matrix=self._motion_matrix() if matrix is None else matrix
        corners=self.volume.index_to_world(np.array(np.meshgrid(
            *[(0,size-1) for size in self.volume.shape[::-1]])).reshape(3,-1).T)
        points=corners@matrix[:3,:3].T+matrix[:3,3]
        return np.array([points.min(axis=0),points.max(axis=0)])

    def set_target_at_crosshair(self):
        if self.volume is None or self.ct_sequence is not None or self.worker is not None:
            return
        self.pause_motion()
        center=self.crosshair
        if self.motion_active:
            center=self.deformation.inverse(center,self.motion_model.position(self.motion_time))
        try:
            target=create_research_target(self.volume,self._lung_target_mask(),center,self.target_radius.value())
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.target=target
        self.scene.set_target(target)
        self._motion_sections.clear()
        self._invalidate_observations()
        self.refresh()
        self.status.setText("Simulated target defined in reference lung tissue · amber outlines follow the same motion as the CT.")

    def _target_radius_changed(self,*args):
        if self.target is None:
            return
        self.pause_motion()
        try:
            target=create_research_target(self.volume,self._lung_target_mask(),
                                          self.target.center_lps_mm,self.target_radius.value())
        except ValueError as error:
            self.target_radius.blockSignals(True)
            self.target_radius.setValue(self.target.radius_mm)
            self.target_radius.blockSignals(False)
            self.status.setText(str(error))
            return
        self.target=target
        self.scene.set_target(target)
        self._invalidate_observations()
        self.refresh()

    def go_to_target(self):
        if self.target is None or self.worker is not None:
            return
        self.pause_motion()
        matrix=self._motion_matrix()
        center=np.asarray(self.target.center_lps_mm)
        self.set_crosshair(matrix[:3,:3]@center+matrix[:3,3])

    def clear_target(self):
        self.target=None
        self.scene.set_target(None)
        self._motion_sections.clear()
        self._invalidate_observations()
        if self.volume is not None:
            self.crosshair=np.clip(self.crosshair,*self._display_bounds())
            self.refresh()

    def _revalidate_target(self):
        if self.target is None:
            return
        try:
            create_research_target(self.volume,self._lung_target_mask(),
                                   self.target.center_lps_mm,self.target.radius_mm)
        except ValueError:
            self.clear_target()
            self.status.setText("Target cleared: its full reference sphere is no longer contained in the current lung masks.")

    def _observation_settings(self):
        return ObservationSettings(self.observation_rate.value(),self.observation_noise.value(),
                                   self.observation_seed.value())

    def _invalidate_observations(self,*args):
        self.target_observations=None
        if hasattr(self,"observation_plot"):
            self.observation_plot.set_data(None)
            self.observation_readout.setText("No observations recorded.")
            self.observation_export.setEnabled(False)
            self.evaluation_export.setEnabled(False)

    def _update_target_controls(self):
        available=self.volume is not None and self.ct_sequence is None and self.deformation is not None
        self.target_set.setEnabled(available)
        self.target_go.setEnabled(available and self.target is not None)
        self.target_clear.setEnabled(self.target is not None)
        self.observation_generate.setEnabled(self.motion_active and self.target is not None)
        if self.target is None:
            self.target_readout.setText("No target defined.")
        else:
            center=np.asarray(self.target.center_lps_mm)
            matrix=self._motion_matrix()
            current=matrix[:3,:3]@center+matrix[:3,3]
            coords=lambda p:", ".join(f"{x:+.1f}" for x in p)
            self.target_readout.setText(f"Reference LPS: {coords(center)} mm\n"
                f"Displayed LPS: {coords(current)} mm\nReference radius: {self.target.radius_mm:g} mm · simulated")

    def generate_observations(self):
        if not self.motion_active or self.target is None or self.worker is not None:
            return
        self.pause_motion()
        target,model,volume=self.target,self.motion_model,self.volume
        deformation,settings,through=self.deformation,self._observation_settings(),self.motion_time
        def accepted(data):
            if (self.target is not target or self.motion_model is not model or self.volume is not volume
                    or self.ct_sequence is not None or settings!=self._observation_settings()
                    or data.model_id!=respiratory_model_id(model)):
                return
            self.target_observations=data
            self.observation_plot.set_data(data)
            self.observation_readout.setText(f"{len(data.times_s)} samples · history 0–{data.through_s:g} s\n"
                f"Last sample {data.times_s[-1]:g} s · {settings.rate_hz:g} Hz\n"
                f"Simulated · noise SD {settings.noise_std_mm:g} mm/axis · seed {settings.seed}")
            self.observation_export.setEnabled(True)
            self.evaluation_export.setEnabled(True)
            self.status.setText("Reproducible simulated target observations recorded. Evaluation truth is exported only when explicitly selected.")
        self.task(lambda:generate_target_observations(target,model,deformation,settings,through_s=through),
                  accepted,"Recording timed simulated target observations…")

    def export_observations(self,include_truth=False):
        data=self.target_observations
        if data is None or self.worker is not None:
            return
        if (self.target is not data.target or self.motion_model is None
                or data.model_id!=respiratory_model_id(self.motion_model)
                or data.settings!=self._observation_settings()):
            self._invalidate_observations()
            self.status.setText("The scenario changed. Record its observations again before exporting.")
            return
        label="evaluation" if include_truth else "observations"
        path,_=QFileDialog.getSaveFileName(self,f"Export target {label}",f"target-{label}.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        try:
            protected=set(self._study_source_paths)
            for metadata in (self.source_info,self.lobe_info,self.airway_info):
                if metadata and metadata.get("source_path"):
                    protected.add(Path(metadata["source_path"]))
            protected.update(Path(__file__).resolve().parent/name for name in (
                "run.py","motiontwin.py","README.md","requirements.txt","pyproject.toml",
                ".gitignore","THIRD_PARTY_LICENSES.txt"))
            data.export_csv(path,include_truth=include_truth,protected_paths=protected)
        except (ValueError,OSError) as error:
            self.status.setText(str(error))
            return
        self.status.setText(f"Exported simulated target {label}: {path}")

    def _motion_settings(self):
        return BreathingSettings(self.motion_amplitude.value(),self.breathing_rate.value(),
                                 self.breathing_pattern.currentText(),self.motion_seed.value())

    def _show_motion_settings(self,settings):
        for control,value in ((self.motion_amplitude,settings.amplitude),(self.breathing_rate,settings.rate_bpm),
                              (self.breathing_pattern,settings.pattern),(self.motion_seed,settings.seed)):
            control.blockSignals(True)
            if control is self.breathing_pattern:
                control.setCurrentText(value)
            else:
                control.setValue(value)
            control.blockSignals(False)
        self.motion_seed.setEnabled(settings.pattern != "Regular")

    @property
    def motion_active(self):
        return self.ct_sequence is None and self.controls.currentIndex()==1 and self.motion_model is not None

    def _workspace_changed(self,index):
        self.pause_phase_playback()
        self.pause_motion()
        self.extract_airways_action.setEnabled(index==0 and self.volume is not None and self.ct_sequence is None)
        if self.ct_sequence is not None:
            if index==1:
                self.controls.blockSignals(True)
                self.controls.setCurrentIndex(0)
                self.controls.blockSignals(False)
            self.refresh()
            return
        if index==1 and self.deformation is not None:
            if self.motion_model is None:
                self.reset_motion()
            else:
                self.refresh()
            self.status.setText("Simulated motion preview · same reference CT and anatomy · not measured respiratory phases.")
        else:
            if self.volume is not None:
                self.crosshair=np.clip(self.crosshair,*self.volume.bounds)
            self.refresh()
            if self.volume is not None:
                self.status.setText("Original static CT · linked physical coordinates.")

    def reset_motion(self):
        self.pause_motion()
        if self.deformation is None:
            return
        self.motion_model=RespiratoryModel(self._motion_settings())
        self._invalidate_observations()
        self.motion_time=0.
        self._show_motion_settings(self.motion_model.settings_at(0.))
        self.refresh()

    def pause_motion(self):
        self.motion_timer.stop()
        self.play_button.setText("Play")

    def toggle_motion(self):
        if not self.motion_active or self.worker is not None:
            return
        if self.motion_timer.isActive():
            self.pause_motion()
        elif self.motion_time < self.motion_model.duration:
            self._motion_anchor=perf_counter()-self.motion_time
            self.motion_timer.start()
            self.play_button.setText("Pause")

    def _motion_tick(self):
        if not self.motion_active or not self.motion_timer.isActive():
            return
        self.motion_time=min(self.motion_model.duration,perf_counter()-self._motion_anchor)
        self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
        if self.motion_time>=self.motion_model.duration:
            self.pause_motion()
        self.refresh()

    def seek_motion(self,value):
        self.pause_motion()
        if self.motion_model is not None:
            self.motion_time=value/100.
            self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
            self.refresh()

    def _motion_settings_changed(self,*args):
        self.motion_seed.setEnabled(self.breathing_pattern.currentText() != "Regular")
        if self.motion_model is not None and self.motion_time<self.motion_model.duration:
            self.motion_model.configure(self.motion_time,self._motion_settings())
            self._invalidate_observations()
            self.refresh()

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
        self.pause_phase_playback()
        self.pause_motion()
        path,_=QFileDialog.getOpenFileName(self,"Import CT volume","","Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if path:
            self.task(lambda:self._read_study(path),lambda result:self.accept_volume(result[0],lobe_bundle=result[1],airway_bundle=result[2],source_path=path),
                      "Reading CT with physical-coordinate metadata…")

    def import_sequence(self):
        if self.worker is not None:
            return
        self.pause_phase_playback()
        path,_=QFileDialog.getOpenFileName(self,"Open respiratory CT sequence","","CT sequence (*.json)")
        if not path:
            return
        def read():
            sequence=load_ct_sequence(path,surface_cache_dir=Path(__file__).resolve().parent/"data"/"phase-surfaces")
            return sequence,sequence.phase(0)
        self.task(read,lambda result:self.accept_sequence(*result),
                  "Validating respiratory phase headers and opening the first CT…")

    def accept_sequence(self,sequence,data=None):
        if data is None:
            data=sequence.phase(0)
        self._accept_phase(0,data,sequence=sequence)

    def load_respiratory_example(self):
        if self.worker is not None:
            return
        self._respiratory_example_generation+=1
        generation=self._respiratory_example_generation
        reference,previous_sequence=self.volume,self.ct_sequence
        cache_dir=self.respiratory_example_path.parent
        if not cached_respiratory_example_available(cache_dir):
            self._show_respiratory_example_progress()
        def read(report):
            thread=QThread.currentThread()
            def progress(done,total):
                if thread.isInterruptionRequested():
                    raise InterruptedError("Respiratory example setup cancelled.")
                thread.download_progress.emit(done,total)
            path=ensure_respiratory_example(cache_dir,progress=progress,
                                            cancelled=thread.isInterruptionRequested)
            if thread.isInterruptionRequested():
                raise InterruptedError("Respiratory example setup cancelled.")
            report("Opening the respiratory example and preparing its first CT view…")
            sequence=load_ct_sequence(path,max_cached_phases=6,surface_cache_dir=cache_dir/"surfaces")
            data=sequence.phase(0)
            landmarks=load_landmarks(path.with_name("published-landmark-39.csv"),sequence)
            if (landmarks.reference_index!=1 or set(landmarks.points)!=set(range(len(sequence.phases)))
                    or any(source!="dataset" for source in landmarks.sources.values())):
                raise ValueError("The respiratory example requires its published landmark in every supplied phase.")
            if thread.isInterruptionRequested():
                raise InterruptedError("Respiratory example setup cancelled.")
            return sequence,data,landmarks
        def accepted(result):
            if (generation!=self._respiratory_example_generation or self.volume is not reference
                    or self.ct_sequence is not previous_sequence):
                return
            sequence,data,landmarks=result
            self.accept_sequence(sequence,data)
            self.accept_landmarks(landmarks)
            self.set_crosshair(landmarks.points[0])
            self.controls.setCurrentIndex(2)
            self.status.setText(f"POPI real respiratory CT · {len(sequence.phases)} supplied phases · published landmark 39 loaded for comparison.")
        self.task(read,accepted,"Preparing the preset respiratory CT example…",phase_kind="example",progress=True)

    def _show_respiratory_example_progress(self):
        if self._respiratory_example_progress is not None:
            return
        dialog=QProgressDialog("Preparing the respiratory example. First use downloads about 700 MiB; later openings use the local cache.",
                               "Cancel",0,1000,self)
        dialog.setWindowTitle("Respiratory CT example")
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setMinimumWidth(430)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.canceled.connect(self.cancel_respiratory_example)
        self._respiratory_example_progress=dialog
        dialog.setValue(0)
        dialog.show()

    def _respiratory_example_download_progress(self,done,total):
        if self.worker is None or self._phase_work_kind!="example" or self.worker.isInterruptionRequested():
            return
        if done<total:
            self._show_respiratory_example_progress()
        dialog=self._respiratory_example_progress
        text=f"Preparing respiratory example · {done/(1024*1024):.1f} / {total/(1024*1024):.1f} MiB"
        self.status.setText(text)
        if dialog is not None:
            dialog.setLabelText(text+"\nVerified phases are kept locally for later openings. Cancel preserves your current study.")
            dialog.setValue(min(1000,round(1000*done/max(1,total))))

    def cancel_respiratory_example(self):
        if self.worker is not None and self._phase_work_kind=="example":
            self._respiratory_example_generation+=1
            self.worker.requestInterruption()
            self.status.setText("Stopping respiratory example setup. The current study will be kept.")

    def _respiratory_example_message(self,message):
        if self.worker is None or self._phase_work_kind!="example" or self.worker.isInterruptionRequested():
            return
        self.status.setText(message)
        if self._respiratory_example_progress is not None:
            self._respiratory_example_progress.setLabelText(message)

    def request_phase(self,index,*,automatic=False):
        sequence=self.ct_sequence
        if sequence is None:
            return
        if not automatic:
            pending=self.worker is not None and self._phase_work_kind in ("auto","prepare")
            self.pause_phase_playback()
        else:
            pending=False
            if not self.phase_playing:
                return
        self._update_phase_controls()
        if not self._update_landmarks():
            return
        if (isinstance(index,bool) or not isinstance(index,(int,np.integer))
                or not 0<=index<len(sequence.phases)):
            return
        index=int(index)
        if self.worker is not None:
            if pending and index!=self.phase_index:
                self._phase_pending_manual=index
            return
        if index==self.phase_index:
            return
        generation=self._phase_generation
        landmarks=self.landmarks
        def read():
            if landmarks is not None:
                landmarks.validate_sources()
            return sequence.phase(index)
        def accepted(data):
            if self.ct_sequence is sequence and (not automatic or self.phase_playing and generation==self._phase_generation):
                self._accept_phase(index,data)
        self.task(read,accepted,f"Loading respiratory phase {sequence.phases[index].percent:g}%…",
                  phase_kind="auto" if automatic else "manual")

    def _accept_phase(self,index,data,*,sequence=None):
        sequence=self.ct_sequence if sequence is None else sequence
        if sequence is None or not 0<=index<len(sequence.phases):
            raise ValueError("Select a phase from the open CT sequence.")
        if (not isinstance(data.volume,Volume) or set(data.masks)!=set(data.meshes)
                or set(data.masks)!=set(data.styles)
                or any(mask.dtype!=bool or mask.shape!=data.volume.shape for mask in data.masks.values())):
            raise ValueError("A respiratory phase requires its own aligned CT, masks and surfaces.")
        initial=sequence is not self.ct_sequence
        if initial:
            self.pause_phase_playback()
            self._phase_prepared_sequence=None
        landmarks=LandmarkSeries(sequence) if initial else self.landmarks
        registry=dict(sequence.styles) if initial else dict(self._phase_styles)
        structures={key:registry.get(key,style) for key,style in data.styles.items()}
        if len({style.name.casefold() for style in structures.values()})!=len(structures):
            raise ValueError("Phase structure names must be unique.")
        camera=self.scene.camera.copy()
        crosshair=data.volume.center.copy() if initial else self.crosshair.copy()
        selected=getattr(self,"_selected_key",None)
        self.scene.set_volume(data.volume,data.masks,prebuilt_meshes=data.meshes,styles=structures)
        self.target=None
        self._target_mask=self._target_mask_key=None
        self._invalidate_observations()
        self.pause_motion()
        self.ct_sequence=sequence
        self.phase_index=index
        self._phase_styles=registry
        self.landmarks=landmarks
        self._landmarks_invalid=False
        self.volume=data.volume
        self.masks=dict(data.masks)
        self.structures=structures
        self._supplied_meshes=dict(self.scene._source_meshes)
        self.source_info=self.lobe_info=self.airway_info=None
        self.imported_masks=bool(data.masks)
        self.motion_model=self.deformation=None
        self.motion_time=0.
        self._motion_sections.clear()
        self._packed_masks=None
        self.scene.set_motion(np.eye(4))
        self.crosshair=np.clip(crosshair,*self.volume.bounds)
        self.controls.blockSignals(True)
        if initial or self.controls.currentIndex()==1:
            self.controls.setCurrentIndex(0)
        self.controls.blockSignals(False)
        if initial:
            self.landmark_reference.blockSignals(True)
            self.landmark_reference.clear()
            self.landmark_reference.addItems([f"{phase.percent:g}%" for phase in sequence.phases])
            self.landmark_reference.blockSignals(False)
            for view in self.slices:
                view.canvas.zoom=1.
            self.phase_selector.blockSignals(True)
            self.phase_selector.clear()
            self.phase_selector.addItems([f"{i+1} / {len(sequence.phases)} · {phase.percent:g}%"
                                          for i,phase in enumerate(sequence.phases)])
            self.phase_selector.blockSignals(False)
            self.phase_slider.blockSignals(True)
            self.phase_slider.setRange(0,len(sequence.phases)-1)
            self.phase_slider.blockSignals(False)
            self.segmentation_visible.blockSignals(True)
            self.segmentation_visible.setChecked(bool(self.masks))
            self.segmentation_visible.blockSignals(False)
        else:
            self.scene.camera.DeepCopy(camera)
        self.phase_group.show()
        self._rebuild_structure_tree(selected)
        self._update_metadata()
        self._update_phase_controls()
        self._update_phase_transport()
        self.refresh()
        if initial:
            self.scene.preset(self.camera.currentText())
        self.status.setText(f"Respiratory phase {index+1} / {len(sequence.phases)} · "
                            +("matching supplied segmentations." if self.masks else "CT volume; no segmented structures for this phase."))

    def _update_phase_controls(self):
        if self.ct_sequence is None:
            self.phase_group.hide()
            self._update_phase_transport()
            return
        index=self.phase_index
        for control in (self.phase_selector,self.phase_slider):
            control.blockSignals(True)
            control.setCurrentIndex(index) if control is self.phase_selector else control.setValue(index)
            control.blockSignals(False)
        self.phase_previous.setEnabled(index>0)
        self.phase_next.setEnabled(index<len(self.ct_sequence.phases)-1)
        phase=self.ct_sequence.phases[index]
        timing=f"Supplied time: {phase.time_s:g} s" if phase.time_s is not None else "Timing not supplied · discrete phases"
        self.phase_readout.setText(f"Phase {index+1} / {len(self.ct_sequence.phases)} · {phase.percent:g}%\n{timing}")
        self._update_phase_transport()

    def _read_study(self,path):
        volume=load_volume(path)
        return volume,load_lobe_cache(volume),load_airway_cache(volume)


    def load_public_example(self):
        if self.source_info is not None:
            return
        self.pause_phase_playback()
        def accepted(result):
            (volume,masks,meshes,provenance),lobes,airways=result
            self.accept_volume(volume,masks=masks,prebuilt_meshes=meshes,source_info=provenance,
                               lobe_bundle=lobes,airway_bundle=airways)
            if lobes is None and airways is None:
                self.status.setText("Public CT example · static imaging study · threshold-derived display masks; display reconstruction only.")
        def read():
            study=load_public_sample()
            return study,load_lobe_cache(study[0]),load_airway_cache(study[0])
        self.task(read,accepted,"Opening the public CT example and its lung reconstruction…")


    def import_dicom(self):
        self.pause_phase_playback()
        self.pause_motion()
        path=QFileDialog.getExistingDirectory(self,"Select one DICOM series directory")
        if path:
            self.task(lambda:self._read_study(path),lambda result:self.accept_volume(result[0],lobe_bundle=result[1],airway_bundle=result[2],source_path=path),
                      "Reading a single DICOM series…")

    def generate_lobes(self):
        if self.ct_sequence is not None:
            return
        if self.volume is None or self.worker is not None:
            return
        if not self._lobe_names_available():
            return
        reference=self.volume
        self.task(lambda:generate_lobe_segmentation(reference),self.accept_lobes,
                  "Generating five lobe masks from this CT · one-time CPU processing can take several minutes…")

    def _airway_name_available(self):
        name=self.structures.get(AIRWAY_KEY,AIRWAY_STYLE).name.casefold()
        if any(key!=AIRWAY_KEY and style.name.casefold()==name for key,style in self.structures.items()):
            self.status.setText("The airway name conflicts with an existing structure. Rename that structure first.")
            return False
        return True

    def extract_airways(self):
        if self.ct_sequence is not None:
            return
        self.pause_motion()
        if self.volume is None or self.worker is not None:
            return
        if self.motion_active:
            self.status.setText("Place the tracheal seed on the original static CT in Imaging.")
            return
        if not self._airway_name_available():
            return
        dialog=AirwaySeedDialog(self.volume,self.crosshair,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:
            self.status.setText("Airway extraction cancelled.")
            return
        reference,seed=self.volume,dialog.seed()
        def prepare():
            mask,metadata=extract_airways(reference,seed)
            return build_airway_cache(reference,mask,metadata)
        self.task(prepare,self.accept_airways,"Extracting connected central airways from the tracheal seed and checking for lung leakage…")

    def import_airways(self):
        if self.ct_sequence is not None:
            return
        self.pause_motion()
        if self.volume is None or self.worker is not None or not self._airway_name_available():
            return
        path,_=QFileDialog.getOpenFileName(self,"Import aligned connected airway mask","",
                                         "Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if not path:
            return
        reference=self.volume
        def prepare():
            mask=load_airway_segmentation(path,reference)
            return build_airway_cache(reference,mask,dict(method="supplied airway segmentation",model="supplied label image",
                                     model_version="not specified",source_kind="supplied",source_path=str(path)))
        self.task(prepare,self.accept_airways,"Validating and reconstructing the aligned airway mask…")

    def accept_airways(self,bundle,*,refresh=True):
        if self.ct_sequence is not None:
            raise ValueError("Supply phase-specific segmentations through the CT sequence manifest.")
        masks,meshes,styles,metadata=bundle
        if set(masks)!={AIRWAY_KEY} or set(meshes)!={AIRWAY_KEY} or set(styles)!={AIRWAY_KEY}:
            raise ValueError("The airway result must contain one connected airway mask and surface.")
        if not isinstance(metadata,dict) or any(not isinstance(metadata.get(key),str) or not metadata[key].strip()
                                              for key in ("method","model","model_version")):
            raise ValueError("Airway masks require their source metadata.")
        mask=np.asarray(masks[AIRWAY_KEY])
        if mask.dtype!=bool or mask.shape!=self.volume.shape or not np.any(mask):
            raise ValueError("The airway mask must be nonempty and match the CT grid.")
        style=replace(self.structures.get(AIRWAY_KEY,styles[AIRWAY_KEY]),kind="other")
        if any(key!=AIRWAY_KEY and value.name.casefold()==style.name.casefold() for key,value in self.structures.items()):
            raise ValueError("The airway name conflicts with an existing structure. Rename that structure first.")
        structures={**self.structures,AIRWAY_KEY:style}
        camera=self.scene.camera_position
        self.scene.add_structures(masks,meshes,structures)
        self.scene.camera_position=camera
        self.masks={**self.masks,**masks}
        self._supplied_meshes={**self._supplied_meshes,**meshes}
        self.structures=structures
        self.airway_info=metadata
        if metadata.get("source_path"):
            self._study_source_paths.add(Path(metadata["source_path"]))
        self.segmentation_visible.blockSignals(True)
        self.segmentation_visible.setChecked(True)
        self.segmentation_visible.blockSignals(False)
        self._rebuild_structure_tree(AIRWAY_KEY)
        self._update_metadata()
        if refresh:
            self.refresh()
        self.status.setText("Central airway mask loaded · inspect the trachea and supported bronchial branches on the CT.")

    def import_lobes(self):
        if self.ct_sequence is not None:
            return
        self.pause_motion()
        if self.volume is None:
            return
        if not self._lobe_names_available():
            return
        path,_=QFileDialog.getOpenFileName(self,"Import five-lobe labels (1: LUL, 2: LLL, 3: RUL, 4: RML, 5: RLL)",
                                         "","Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if not path:
            return
        reference=self.volume
        def read():
            masks,_=load_lobe_segmentation(path,reference)
            labels=np.zeros(reference.shape,dtype=np.uint8)
            for label,key,_,_ in LOBE_SEGMENTS:
                labels[masks[key]]=label
            return build_lobe_cache(reference,labels,dict(method="supplied segmentation",model="supplied label image",
                                    model_version="not specified",source_path=str(path)))
        self.task(read,self.accept_lobes,"Validating and reconstructing all five aligned lobe labels…")

    def _lobe_names_available(self):
        lobe_names={key:self.structures[key].name if key in self.structures else name
                    for _,key,name,_ in LOBE_SEGMENTS}
        names=[style.name.casefold() for key,style in self.structures.items() if key not in lobe_names]
        names.extend(name.casefold() for name in lobe_names.values())
        if len(names)!=len(set(names)):
            self.status.setText("Lobe names conflict with existing structures. Rename those structures before importing or generating lobes.")
            return False
        return True

    def accept_lobes(self,bundle,*,refresh=True):
        if self.ct_sequence is not None:
            raise ValueError("Supply phase-specific segmentations through the CT sequence manifest.")
        masks,meshes,styles,metadata=bundle
        keys={key for _,key,_,_ in LOBE_SEGMENTS}
        if not isinstance(metadata,dict) or not isinstance(metadata.get("model"),str) or not metadata["model"].strip():
            raise ValueError("Lobe masks require their source metadata.")
        if set(masks)!=keys or set(meshes)!=keys or set(styles)!=keys:
            raise ValueError("The lobe result must contain all five reconstructed lung lobes.")
        if any(np.asarray(mask).shape!=self.volume.shape or not np.any(mask) for mask in masks.values()):
            raise ValueError("All lobe masks must be nonempty and match the CT grid.")
        structures={**self.structures,**{key:self.structures.get(key,style) for key,style in styles.items()}}
        if len({style.name.casefold() for style in structures.values()})!=len(structures):
            raise ValueError("Lobe names conflict with existing structure names. Rename those structures before importing.")
        if self.lobe_info is None:
            for key in ("left_lung","right_lung","vascular_display"):
                if key in structures:
                    structures[key]=replace(structures[key],visible=False)
        camera=self.scene.camera_position
        self.scene.add_structures(masks,meshes,structures)
        self.scene.camera_position=camera
        self.masks={**self.masks,**masks}
        self._supplied_meshes={**self._supplied_meshes,**meshes}
        self.structures=structures
        self.lobe_info=metadata
        if metadata.get("source_path"):
            self._study_source_paths.add(Path(metadata["source_path"]))
        self.segmentation_visible.blockSignals(True)
        self.segmentation_visible.setChecked(True)
        self.segmentation_visible.blockSignals(False)
        self._rebuild_structure_tree(next(iter(styles)))
        self._update_metadata()
        self._revalidate_target()
        if refresh:
            self.refresh()
        self.status.setText("Five aligned lobe masks loaded · "+metadata["model"]+" · inspect boundaries on the CT; not expert reviewed.")


    def import_mask(self):
        if self.ct_sequence is not None:
            return
        self.pause_motion()
        if self.volume is None:
            self.status.setText("Open a CT volume before importing a segmentation.")
            return
        path,_=QFileDialog.getOpenFileName(self,"Load aligned label image","","Volumes (*.nii *.nii.gz *.nrrd *.mha *.mhd)")
        if not path:
            return
        reference=self.volume
        def read():
            image=load_segmentation(path,reference)
            return image,tuple(int(value) for value in np.unique(image.data) if value>0)
        def ready(result):
            image,labels=result
            if not labels:
                self.status.setText("The segmentation is empty; the current structures are unchanged.")
                return
            self._pending_segmentation=(image,labels,path)
        self.task(read,ready,"Reading segmentation labels and validating their physical coordinates…")

    def _choose_segmentation(self,image,labels,path):
        protected={key for _,key,_,_ in LOBE_SEGMENTS} if self.lobe_info else set()
        if self.airway_info is not None:
            protected.add(AIRWAY_KEY)
        dialog=SegmentationDialog(path,labels,self.structures,self,protected_keys=protected)
        if dialog.exec()!=QDialog.DialogCode.Accepted:
            self.status.setText("Segmentation import cancelled.")
            return
        key,name,kind,label=dialog.selection()
        if key is None:
            index=1
            prefix="lung_segment" if kind=="lung" else "segment"
            while f"{prefix}_{index}" in self.structures:
                index+=1
            key=f"{prefix}_{index}"
            palette=("#d6a77a","#98bd8d","#d2c477","#81b6cd","#c493b7")
            style=StructureStyle(name,palette[len(self.structures)%len(palette)],.35 if kind=="lung" else .85,
                                 ct_coloring=False,kind=kind)
        else:
            style=replace(self.structures[key],name=name)
        reference=self.volume
        def prepare():
            mask=np.asarray(image.data>0 if label is None else image.data==label,dtype=bool)
            return mask,prepare_display_meshes(reference,{key:mask}).get(key)
        self.task(prepare,lambda result:self.accept_mask(key,*result,source_path=path,style=style),
                  "Reconstructing the selected segmentation surface…")


    def accept_mask(self,role,mask,mesh=None,*,source_path=None,style=None):
        if self.ct_sequence is not None:
            raise ValueError("Supply phase-specific segmentations through the CT sequence manifest.")
        if role==AIRWAY_KEY and self.airway_info is not None:
            raise ValueError("Replace the recorded airway result using File > Airways > Import aligned airway mask.")
        if self.lobe_info is not None and role in {key for _,key,_,_ in LOBE_SEGMENTS}:
            raise ValueError("Replace lobe masks together using File > Lung lobes > Import five-lobe labels.")
        if np.asarray(mask).shape!=self.volume.shape:
            raise ValueError("Segmentation masks must match the CT geometry.")
        if not np.any(mask):
            self.status.setText(f"The selected {role} label is empty; the existing structure was retained.")
            return
        if mesh is None:
            mesh=prepare_display_meshes(self.volume,{role:mask})[role]
        style=style or self.structures.get(role,default_structure_style(role))
        if any(key!=role and value.name.casefold()==style.name.casefold() for key,value in self.structures.items()):
            raise ValueError("A structure with that name already exists.")
        structures={**self.structures,role:style}
        masks={**self.masks,role:mask}
        meshes={**self._supplied_meshes,role:mesh}
        camera=self.scene.camera_position
        self.scene.add_structure(role,mask,mesh,structures)
        self.scene.camera_position=camera
        self.masks,self._supplied_meshes=masks,meshes
        self.structures=structures
        self.imported_masks=True
        if source_path:
            self._study_source_paths.add(Path(source_path))
        self.badge.setText("PUBLIC CT · DERIVED + LOADED MASKS" if self.source_info else "SUPPLIED CT + SEGMENTATIONS")
        self.status.setText(f"Loaded {style.name} in the CT's physical coordinates.")
        self._rebuild_structure_tree(role)
        self._update_metadata()
        self._revalidate_target()
        self.refresh()
        self.scene.render()



    def accept_volume(self,volume,*,masks=None,prebuilt_meshes=None,source_info=None,lobe_bundle=None,airway_bundle=None,source_path=None):
        self.pause_phase_playback()
        self._phase_prepared_sequence=None
        structures={key:default_structure_style(key,(source_info or {}).get("display_labels",{}).get(key))
                    for key in (masks or {})}
        self.scene.set_volume(volume,masks or {},prebuilt_meshes=prebuilt_meshes,styles=structures)
        self.target=None
        self._target_mask=self._target_mask_key=None
        self._invalidate_observations()
        self._study_source_paths={Path(p) for p in (source_path,(source_info or {}).get("source_path")) if p}
        self.ct_sequence=None
        self.phase_index=None
        self._phase_styles={}
        self.landmarks=None
        self._landmarks_invalid=False
        self.phase_group.hide()
        self.phase_transport.hide()
        self.pause_motion()
        self.controls.blockSignals(True)
        self.controls.setCurrentIndex(0)
        self.controls.blockSignals(False)
        self.motion_model=self.deformation=None
        self._motion_sections.clear()
        self._packed_masks=None
        self.motion_time=0.
        self.scene.set_motion(np.eye(4))
        self.volume=volume
        self.masks={} if masks is None else dict(masks)
        self.structures=structures
        self.source_info=source_info
        self.lobe_info=None
        self.airway_info=None
        self.imported_masks=False
        self._supplied_meshes=dict(self.scene._source_meshes)
        self.crosshair=volume.center.copy()
        for view in self.slices:
            view.canvas.zoom=1.
        self.scene.set_source_label("PUBLIC STATIC CT / DERIVED DISPLAY MASKS" if source_info else "SUPPLIED STATIC CT",render=False)
        self.badge.setText("PUBLIC CT EXAMPLE" if source_info else "SUPPLIED CT")
        self.status.setText("CT loaded. Click or scroll the linked CT views; drag the lung view to rotate.")
        self._rebuild_structure_tree()
        self._update_metadata()
        if lobe_bundle is not None:
            self.accept_lobes(lobe_bundle,refresh=False)
        if airway_bundle is not None:
            self.accept_airways(airway_bundle,refresh=False)
        self.refresh()
        self.scene.preset(self.camera.currentText())

    def _update_source_label(self):
        if self.ct_sequence is not None:
            phase=self.ct_sequence.phases[self.phase_index]
            self.scene.set_source_label(f"SUPPLIED CT SEQUENCE / PHASE {phase.percent:g}%\n"
                                       +("MATCHING PHASE SEGMENTATIONS" if self.masks else "NO SEGMENTED STRUCTURES IN THIS PHASE"),render=False)
            return
        base="PUBLIC STATIC CT" if self.source_info else "SUPPLIED STATIC CT"
        details=[]
        if self.lobe_info is not None:
            details.append("FIVE LOBES")
        if self.airway_info is not None:
            details.append("CENTRAL AIRWAYS")
        if details:
            label=base+" / "+" + ".join(details)+"\nMASKS NOT EXPERT REVIEWED"
        else:
            label=base+(" / LOADED SEGMENTATIONS" if self.imported_masks else
                        " / DERIVED DISPLAY MASKS" if self.source_info else "")
        self.scene.set_source_label(label,render=False)

    def _update_metadata(self):
        if self.volume is None:
            return
        if self.ct_sequence is not None:
            self._update_phase_metadata()
            return
        volume=self.volume
        self.study_metadata.setText(f"{volume.name} · {volume.shape[2]} × {volume.shape[1]} × {volume.shape[0]} · static CT")
        self.study_metadata.setToolTip(self.study_metadata.text())
        self.imaging_info.setText("Spacing (mm): " + " × ".join(f"{value:.3f}" for value in volume.spacing)
            + "\nCoordinates: LPS millimetres\n"
            + ("Public CT: derived display layers and imported segmentations." if self.imported_masks and self.source_info
               else "Public example: threshold-derived lung/detail display masks." if self.source_info
               else "Imported CT. Lung surfaces require aligned lung masks."))
        if self.masks and not self.source_info:
            self.imaging_info.setText(self.imaging_info.text().split("\n")[0]+"\nCoordinates: LPS millimetres\nImported, aligned segmentations.")
        if self.lobe_info is not None:
            self.imaging_info.setText(self.imaging_info.text()+"\nFive lobe masks · not expert reviewed.")
        if self.airway_info is not None:
            self.imaging_info.setText(self.imaging_info.text()+"\nCentral airway lumen · distal branches may be incomplete.")
        self._update_source_label()
        has_lungs=any(style.kind=="lung" and key in self.scene.meshes for key,style in self.structures.items())
        self.scene_title.setText("3D · LOBES + AIRWAYS" if self.lobe_info is not None and self.airway_info is not None else
                                "3D · LUNG LOBES" if self.lobe_info is not None else
                                "3D · CENTRAL AIRWAYS" if self.airway_info is not None else
                                "3D · LUNG RECONSTRUCTION" if has_lungs else "3D · STRUCTURES" if self.masks else "3D · CT VOLUME")
        self.controls.setTabEnabled(1,has_lungs)
        self.controls.setTabEnabled(2,False)
        self.controls.setTabToolTip(2,"Open a respiratory CT sequence to record phase-specific landmark positions.")
        self.controls.setTabToolTip(1,"Preview simulated breathing using the loaded lung anatomy." if has_lungs
                                  else "Load a CT and an aligned lung mask to enable motion.")
        if has_lungs and self.deformation is None:
            self.deformation=LungDeformation(self.scene._lung_bounds[0,2],self.scene._lung_bounds[1,2])
            maximum=min(30.,self.deformation.height*.20/1.8)
            self.motion_amplitude.blockSignals(True)
            self.motion_amplitude.setMaximum(np.floor(maximum*10)/10)
            self.motion_amplitude.setValue(min(8.,self.motion_amplitude.maximum()))
            self.motion_amplitude.blockSignals(False)
        self.import_mask_action.setEnabled(True)
        self.import_mask_action.setToolTip("Import an aligned label image as a named structure.")
        self.lobes_menu.setEnabled(True)
        self.generate_lobes_action.setEnabled(self.lobe_info is None)
        self.airways_menu.setEnabled(True)
        self.extract_airways_action.setEnabled(not self.motion_active)
        self.example_action.setEnabled(self.source_info is None)
        self.segmentation_visible.setEnabled(bool(self.masks))
        self.ct_display_group.setEnabled(True)
        self.ct_texture_group.setEnabled(self.scene.scan._has_context)
        self.camera.setEnabled(True)
        self.fit_button.setEnabled(True)

    def _update_phase_metadata(self):
        volume=self.volume
        phase=self.ct_sequence.phases[self.phase_index]
        self.study_metadata.setText(f"{self.ct_sequence.name} · {volume.shape[2]} × {volume.shape[1]} × {volume.shape[0]} · phase {phase.percent:g}%")
        self.study_metadata.setToolTip(self.study_metadata.text())
        self.imaging_info.setText("Spacing (mm): "+" × ".join(f"{value:.3f}" for value in volume.spacing)
            +"\nCoordinates: LPS millimetres\nSupplied respiratory CT phases · discrete navigation.\n"
            +("Segmentations belong to the selected phase; inspect against its CT." if self.masks else
              "No segmented structures for this phase; the 3D view shows its CT volume."))
        self._update_source_label()
        self.controls.setTabEnabled(1,False)
        self.controls.setTabEnabled(2,True)
        self.controls.setTabToolTip(2,"Record one matching feature across the supplied CT phases and measure its physical displacement.")
        self.controls.setTabToolTip(1,"This sequence uses supplied CT phases. Open a static CT with lung masks for simulated breathing.")
        self.import_mask_action.setEnabled(False)
        self.import_mask_action.setToolTip("List each phase's segmentation in the sequence JSON file.")
        self.lobes_menu.setEnabled(False)
        self.airways_menu.setEnabled(False)
        self.extract_airways_action.setEnabled(False)
        self.example_action.setEnabled(True)
        self.segmentation_visible.setEnabled(bool(self.masks))
        self.ct_display_group.setEnabled(True)
        self.ct_texture_group.setEnabled(self.scene.scan._has_context)
        self.camera.setEnabled(True)
        self.fit_button.setEnabled(True)

    def set_crosshair(self,point):
        if self.volume is None:
            return
        point=np.asarray(point,dtype=float)
        if point.shape != (3,) or not np.isfinite(point).all():
            raise ValueError("Crosshair must be a finite physical xyz position.")
        self.crosshair=np.clip(point,*self._display_bounds())
        self.refresh()

    def refresh(self):
        if self.volume is None:
            return
        masks=self.masks if self.segmentation_visible.isChecked() else None
        shown={name:mask for name,mask in (masks or {}).items()
               if self.structures[name].visible and self.structures[name].opacity>0}
        if self._packed_masks is None or not self._packed_masks.matches(shown):
            self._packed_masks=PackedMasks(shown)
        simulated=self.motion_active
        matrix=np.eye(4)
        if simulated:
            displacement,velocity,phase=self.motion_model.evaluate(self.motion_time)
            matrix=self.deformation.matrix(displacement)
            self.scene.set_motion(matrix,simulated=True)
            self.motion_seek.blockSignals(True)
            self.motion_seek.setValue(round(self.motion_time*100))
            self.motion_seek.blockSignals(False)
            self.motion_readout.setText(f"{self.motion_time:.2f} / 60 s  ·  phase {(phase/(2*np.pi)%1)*100:.1f}%\n"
                f"Base SI: {displacement[2]:+.2f} mm\nBase SI speed: {velocity[2]:+.2f} mm/s")
            self.breathing_group.setEnabled(self.motion_time<self.motion_model.duration)
            self.play_button.setEnabled(self.motion_time<self.motion_model.duration)
        else:
            self.scene.set_motion(np.eye(4))
        self.badge.setText("SIMULATED MOTION · REFERENCE CT" if simulated else
            "CT + LOBES + AIRWAYS · ESTIMATED MASKS" if self.lobe_info is not None and self.airway_info is not None else
            "CT + CENTRAL AIRWAYS · ESTIMATED MASK" if self.airway_info is not None else
            "CT + FIVE LOBES · NOT EXPERT REVIEWED" if self.lobe_info is not None else
            "PUBLIC CT · DERIVED + LOADED MASKS" if self.source_info and self.imported_masks else
            "PUBLIC CT EXAMPLE · DERIVED DISPLAY MASKS" if self.source_info else
            "SUPPLIED CT + SEGMENTATIONS" if self.masks else "SUPPLIED CT")
        self.scene_title.setText("3D · SIMULATED MOTION" if simulated else
                                "3D · LOBES + AIRWAYS" if self.lobe_info is not None and self.airway_info is not None else
                                "3D · CENTRAL AIRWAYS" if self.airway_info is not None and self.lobe_info is None else
                                "3D · LUNG LOBES" if self.lobe_info is not None else
                                "3D · LUNG RECONSTRUCTION" if any(style.kind=="lung" for style in self.structures.values())
                                else "3D · STRUCTURES" if self.masks else "3D · CT VOLUME")
        self.display_info.setText("Simulated deformation of one reference scan · not measured 4D CT · fixed world crosshair" if simulated
                                  else "Static CT · linked physical coordinates")
        phase=self.ct_sequence.phases[self.phase_index] if self.ct_sequence is not None else None
        slice_bounds=None
        if simulated and self.target is not None:
            moved=self._display_bounds(matrix)
            reference=self.volume.bounds
            slice_bounds=np.array([np.minimum(reference[0],moved[0]),np.maximum(reference[1],moved[1])])
        if phase is not None:
            self.badge.setText(f"4D CT · PHASE {phase.percent:g}%")
            self.scene_title.setText(f"3D · PHASE {phase.percent:g}% · "+("STRUCTURES" if self.masks else "CT VOLUME"))
            self.display_info.setText(f"Supplied CT sequence · phase {phase.percent:g}% · linked physical coordinates")
        for view in self.slices:
            view.canvas.simulated=simulated
            view.title_label.setText(view.plane_name.upper()+(f" · {phase.percent:g}%" if phase is not None else " · SIMULATED" if simulated else ""))
            view.title_label.setMinimumWidth(view.title_label.fontMetrics().horizontalAdvance(view.title_label.text())+2)
            if simulated:
                key=(id(self.volume),id(self.deformation),self.motion_time,float(self.crosshair[view.axis]),
                     tuple((name,id(mask)) for name,mask in (masks or {}).items()),
                     None if slice_bounds is None else tuple(slice_bounds.ravel()))
                cached=self._motion_sections.get(view.plane_name)
                if cached is None or cached[0]!=key:
                    plane,overlays=respiratory_slice(self.volume,view.plane_name,self.crosshair,self.deformation,
                                                    displacement,masks=shown,max_pixels=256,packed_masks=self._packed_masks,bounds=slice_bounds)
                    self._motion_sections[view.plane_name]=(key,plane,overlays)
                else:
                    _,plane,overlays=cached
                    missing={name:mask for name,mask in shown.items() if name not in overlays}
                    if missing:
                        _,additional=respiratory_slice(self.volume,view.plane_name,self.crosshair,self.deformation,
                                                      displacement,masks=missing,max_pixels=256,packed_masks=self._packed_masks,bounds=slice_bounds)
                        overlays.update(additional)
                bounds=self.volume.bounds if slice_bounds is None else slice_bounds
                # keep a fixed world crosshair reachable while the scan moves.
                bounds=np.array([np.minimum(bounds[0],self.crosshair),np.maximum(bounds[1],self.crosshair)])
                view.set_data(self.volume,self.crosshair,plane=plane,mask_planes=overlays,structures=self.structures,bounds=bounds)
            else:
                view.set_data(self.volume,self.crosshair,masks=masks,structures=self.structures,packed_masks=self._packed_masks)
            view.canvas.set_target(self.target,matrix)
        self.scene.set_crosshair(self.crosshair)
        self._update_target_controls()
        self._update_landmarks(validate=False)
        self.scene.reset_camera_clipping_range()
        self.scene.render()

    def task(self,function,callback,label,*,phase_kind=None,progress=False):
        if self.worker is not None:
            return
        if phase_kind not in ("auto","prepare"):
            self.pause_phase_playback()
        self.pause_motion()
        self.controls.setEnabled(False)
        self.file_menu.setEnabled(False)
        self.file_toolbar.setEnabled(False)
        self.status.setText(label)
        self._phase_work_kind=phase_kind
        self.worker=Worker(function,progress=progress)
        sequence=self.ct_sequence
        generation=self._phase_generation
        self.worker.result.connect(lambda result:self._task_result(callback,result))
        def failed(message):
            if phase_kind in ("auto","prepare") and (generation!=self._phase_generation or sequence is not self.ct_sequence):
                return
            self._task_failed(message)
        self.worker.failed.connect(failed)
        if phase_kind=="example":
            self.worker.download_progress.connect(self._respiratory_example_download_progress)
            self.worker.progress.connect(self._respiratory_example_message)
        else:
            self.worker.progress.connect(lambda message:self.status.setText(message)
                if phase_kind!="prepare" or self.phase_playing and generation==self._phase_generation else None)
        self.worker.cancelled.connect(lambda:self.status.setText(
            "Respiratory example setup cancelled. The current study was kept." if phase_kind=="example"
            else "Respiratory phase preparation stopped."))
        self.worker.finished.connect(self._task_finished)
        self._update_phase_transport()
        self.worker.start()

    def _task_result(self,callback,result):
        try:
            callback(result)
        except Exception as error:
            self._task_failed(str(error))

    def _task_failed(self,message):
        self.pause_phase_playback()
        self.status.setText("CT operation failed. The details are shown below.")
        QMessageBox.warning(self,"MotionTwin CT viewer",message[-1500:])

    def _task_finished(self):
        kind=self._phase_work_kind
        if kind=="example" and self._respiratory_example_progress is not None:
            dialog=self._respiratory_example_progress
            self._respiratory_example_progress=None
            dialog.blockSignals(True)
            dialog.close()
            dialog.deleteLater()
        self.worker.deleteLater()
        self.worker=None
        self._phase_work_kind=None
        self.controls.setEnabled(True)
        self.file_menu.setEnabled(True)
        self.file_toolbar.setEnabled(True)
        self._update_phase_transport()
        pending=self._phase_pending_manual
        self._phase_pending_manual=None
        if pending is not None:
            sequence=self.ct_sequence
            generation=self._phase_generation
            def select_pending(index=pending,source=sequence,token=generation):
                if source is self.ct_sequence and token==self._phase_generation:
                    self.request_phase(index)
            QTimer.singleShot(0,select_pending)
        elif self.phase_playing:
            if kind=="prepare":
                self._start_phase_timer()
            else:
                self._arm_phase_timer()
        if self._pending_segmentation is not None:
            pending=self._pending_segmentation
            self._pending_segmentation=None
            self._choose_segmentation(*pending)

    def closeEvent(self,event):
        self.pause_phase_playback()
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish loading the CT before closing the viewer.")
            event.ignore()
            return
        self.motion_timer.stop()
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
    parser=argparse.ArgumentParser(prog="motiontwin",description="CT and lung viewer with a simulated respiratory preview")
    parser.add_argument("command",nargs="?",choices=["gui"],default="gui",help="Open the CT viewer")
    parser.parse_args(argv)
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
