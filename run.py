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
QTabBar::tab { background:#383b3f; border:1px solid #4a4e53; padding:7px 10px; color:#c3c6ca; }
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
import json
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
from vtkmodules.vtkRenderingCore import (vtkColorTransferFunction,vtkVolume,vtkVolumeProperty,
    vtkActor2D,vtkCoordinate,vtkPolyDataMapper2D)
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkOpenGLGPUVolumeRayCastMapper
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPalette, QIcon, QPixmap, QPolygonF
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QLabel, QComboBox, QDoubleSpinBox, QSlider,
    QSplitter, QCheckBox, QFileDialog, QMessageBox, QScrollArea,
    QGroupBox, QGridLayout, QToolButton, QSizePolicy, QTabWidget, QSpinBox,
    QToolBar, QStyle, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit,
    QColorDialog, QDialog, QDialogButtonBox, QProgressDialog, QProgressBar)

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
    evaluate_baselines, check_export_destination,
    NeedleSettings, validate_needle_entry, create_needle_plan, evaluate_needle,
    evaluate_needle_state, clip_segment_to_slice,ResearchTarget,
    RouteSettings,create_exclusion_region,select_geometric_route,evaluate_needle_constraints,
    select_forecast_route,create_forecast_needle_plan,
    PlanningBenchmarkSettings,planning_benchmark_cases,run_planning_benchmark,EXCLUSION_POLICIES,
    UncertaintySettings,calibrate_forecast_region,evaluate_forecast_region,
    ForecastStudySettings,run_forecast_study)

from motiontwin_charts import ObservationPlot, ForecastPlot, ForecastCoveragePlot, LandmarkPlot
from motiontwin_results import NeedleResultsDialog

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
        self.forecast_region_point = None
        self.forecast_region_radius_mm = None
        self._forecast_region_actor = None
        self.needle_plan = None
        self.needle_depth_mm = 0.
        self.needle_tip_lps_mm = None
        self.exclusion_regions = ()
        self.needle_arrival_point = None
        self._needle_arrival_mesh = None
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
            self.set_forecast_region(None,None)
            if self.target_actor is not None:
                self.target_actor.GetProperty().SetOpacity(1.)
            if self.forecast_point is not None:
                self.remove_actor("target_forecast",render=False)
                self.remove_actor("forecast_label-labels",render=False)
            self.forecast_point=self._forecast_mesh=None
            return
        point=np.asarray(point,dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all():
            raise ValueError("A forecast marker requires a finite LPS position.")
        if self.target_actor is not None:
            # keep the predicted centre visible when it lies inside the current target sphere.
            self.target_actor.GetProperty().SetOpacity(.4)
        if self.forecast_point is not None and np.array_equal(point,self.forecast_point):
            return
        self.forecast_point=point.copy()
        if self._forecast_mesh is None:
            self._forecast_mesh=pv.PolyData(point[None,:])
            self._forecast_mesh["forecast_text"]=["Predicted"]
            self.add_mesh(self._forecast_mesh,color="#49dcf4",point_size=13,
                render_points_as_spheres=True,lighting=False,name="target_forecast",
                reset_camera=False,render=False)
            self.add_point_labels(self._forecast_mesh,"forecast_text",show_points=False,
                always_visible=True,font_size=11,text_color="#49dcf4",shape=None,
                name="forecast_label",render=False)
        else:
            self._forecast_mesh.points=point[None,:]

    def set_forecast_region(self,point,radius_mm):
        if point is None or radius_mm is None:
            self.forecast_region_point=self.forecast_region_radius_mm=None
            if self._forecast_region_actor is not None:
                self._forecast_region_actor.SetVisibility(False)
            return
        point=np.asarray(point,dtype=float)
        radius=float(radius_mm)
        if point.shape!=(3,) or not np.isfinite(point).all() or not np.isfinite(radius) or radius<0:
            raise ValueError("An observation-error region requires a finite LPS centre and nonnegative radius.")
        self.forecast_region_point=point.copy()
        self.forecast_region_radius_mm=radius
        if self._forecast_region_actor is None and radius>1e-9:
            self._forecast_region_actor=self.add_mesh(pv.Sphere(radius=1.,theta_resolution=32,phi_resolution=24),
                style="wireframe",color="#49dcf4",opacity=.6,line_width=1,lighting=False,
                name="forecast_region",reset_camera=False,render=False)
        if self._forecast_region_actor is not None:
            self._forecast_region_actor.SetPosition(*point)
            self._forecast_region_actor.SetScale(radius,radius,radius)
            self._forecast_region_actor.SetVisibility(radius>1e-9)


    def set_needle_arrival(self,point):
        if point is None:
            if self.needle_arrival_point is not None:
                self.remove_actor("needle_arrival",render=False)
                self.remove_actor("needle_arrival_label-labels",render=False)
            self.needle_arrival_point=self._needle_arrival_mesh=None
            if self.needle_plan is not None:
                self._needle_tip_label.SetVisibility(self.needle_depth_mm>1e-8)
            return
        point=np.asarray(point,dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all():
            raise ValueError("A planned arrival marker requires a finite LPS position.")
        if self._needle_arrival_mesh is None:
            self._needle_arrival_mesh=pv.PolyData(point[None,:])
            self._needle_arrival_mesh["arrival_text"]=["Planned arrival"]
            self.add_mesh(self._needle_arrival_mesh,color="#49dcf4",point_size=11,
                render_points_as_spheres=True,lighting=False,name="needle_arrival",reset_camera=False,render=False)
            self.add_point_labels(self._needle_arrival_mesh,"arrival_text",show_points=False,always_visible=True,
                font_size=10,text_color="#49dcf4",shape=None,name="needle_arrival_label",render=False)
        else:
            self._needle_arrival_mesh.points=point[None,:]
        self.needle_arrival_point=point.copy()
        if self.needle_plan is not None:
            self._needle_tip_label.SetVisibility(bool(self.needle_depth_mm>1e-8 and np.linalg.norm(self.needle_tip_lps_mm-point)>1e-6))

    def set_exclusions(self,regions):
        regions=tuple(regions)
        if regions==self.exclusion_regions:
            return
        for index in range(len(self.exclusion_regions)):
            self.remove_actor(f"exclusion_{index}",render=False)
        self.exclusion_regions=regions
        for index,region in enumerate(regions):
            mesh=pv.Sphere(center=region.center_lps_mm,radius=region.radius_mm,
                           theta_resolution=32,phi_resolution=24)
            actor=self.add_mesh(mesh,color="#e88a8a",style="wireframe",opacity=.65,
                line_width=1,name=f"exclusion_{index}",reset_camera=False,render=False)
            actor.SetUserMatrix(self.motion_matrix)

    def set_needle(self,plan,depth=0.):
        if plan is None:
            self.set_needle_arrival(None)
            if self.target_actor is not None:
                self.target_actor.GetProperty().SetOpacity(.4 if self.forecast_point is not None else 1.)
            if self.needle_plan is not None:
                for name in ("needle_shaft","needle_tip","needle_path","needle_entry","needle_entry_label-labels",
                             "needle_path_guide","needle_inserted_guide","needle_tip_label-labels"):
                    self.remove_actor(name,render=False)
            self.needle_plan=None
            self.needle_depth_mm=0.
            self.needle_tip_lps_mm=None
            return
        tip=plan.tip_at_depth(depth)
        if plan is not self.needle_plan:
            self.set_needle(None)
            self.needle_plan=plan
            radius=plan.settings.radius_mm
            shaft=pv.Cylinder(center=(0,0,.5),direction=(0,0,1),radius=radius,height=1,resolution=24)
            cone=pv.Cone(center=(0,0,.5),direction=(0,0,1),radius=radius,height=1,resolution=24)
            self._needle_shaft_actor=self.add_mesh(shaft,color="#c5d0dc",smooth_shading=True,
                specular=.8,specular_power=35,name="needle_shaft",reset_camera=False,render=False)
            self._needle_tip_actor=self.add_mesh(cone,color="#ecf2f7",smooth_shading=True,
                specular=.8,specular_power=35,name="needle_tip",reset_camera=False,render=False)
            self.add_mesh(pv.Line(plan.entry_lps_mm,plan.endpoint_lps_mm),color="#e9dcb6",
                line_width=1,opacity=.65,name="needle_path",reset_camera=False,render=False)
            # world-coordinate centreline annotations remain readable through opaque CT layers.
            self._needle_inserted_line=pv.Line(plan.entry_lps_mm,plan.entry_lps_mm)
            for mesh,name,color,width in ((pv.Line(plan.entry_lps_mm,plan.endpoint_lps_mm),"needle_path_guide","#e9dcb6",1),
                                          (self._needle_inserted_line,"needle_inserted_guide","#e7f0fa",2)):
                coordinate=vtkCoordinate()
                coordinate.SetCoordinateSystemToWorld()
                mapper=vtkPolyDataMapper2D()
                mapper.SetInputData(mesh)
                mapper.ScalarVisibilityOff()
                mapper.SetTransformCoordinate(coordinate)
                actor=vtkActor2D()
                actor.SetMapper(mapper)
                c=QColor(color)
                actor.GetProperty().SetColor(c.redF(),c.greenF(),c.blueF())
                actor.GetProperty().SetLineWidth(width)
                self.add_actor(actor,name=name,reset_camera=False,pickable=False,render=False)
            self._needle_tip_point=pv.PolyData(tip[None,:])
            self._needle_tip_point["tip_text"]=["Tip"]
            self._needle_tip_label=self.add_point_labels(self._needle_tip_point,"tip_text",show_points=False,
                always_visible=True,text_color="#e7f0fa",font_size=10,shape=None,name="needle_tip_label",render=False)
            entry=pv.PolyData(np.asarray(plan.entry_lps_mm)[None,:])
            entry["entry_text"]=["Entry"]
            self.add_mesh(entry,color="#a6d7ff",point_size=8,render_points_as_spheres=True,
                lighting=False,name="needle_entry",reset_camera=False,render=False)
            self.add_point_labels(entry,"entry_text",show_points=False,always_visible=True,
                text_color="#a6d7ff",font_size=10,shape=None,justification_horizontal="right",
                justification_vertical="top",name="needle_entry_label",render=False)
            direction=plan.direction
            helper=np.eye(3)[np.argmin(np.abs(direction))]
            u=np.cross(helper,direction)
            u/=np.linalg.norm(u)
            self._needle_basis=np.column_stack((u,np.cross(direction,u),direction))
            self._needle_matrices=[vtkMatrix4x4(),vtkMatrix4x4()]
            self._needle_shaft_actor.SetUserMatrix(self._needle_matrices[0])
            self._needle_tip_actor.SetUserMatrix(self._needle_matrices[1])
        if self.target_actor is not None:
            self.target_actor.GetProperty().SetOpacity(.4)
        self.needle_depth_mm=float(depth)
        self.needle_tip_lps_mm=tip.copy()
        self._needle_inserted_line.points=np.stack((plan.entry_lps_mm,tip))
        self._needle_tip_point.points=tip[None,:]
        self._needle_tip_label.SetVisibility(float(depth)>1e-8)
        tip_length=min(float(depth),3*plan.settings.radius_mm,3.,.15*plan.length_mm)
        shaft_length=max(0.,float(depth)-tip_length)
        for actor,matrix,start,length in (
            (self._needle_shaft_actor,self._needle_matrices[0],np.asarray(plan.entry_lps_mm),shaft_length),
            (self._needle_tip_actor,self._needle_matrices[1],np.asarray(plan.entry_lps_mm)+plan.direction*shaft_length,tip_length)):
            transform=np.eye(4)
            transform[:3,:3]=self._needle_basis@np.diag((1.,1.,max(length,1e-9)))
            transform[:3,3]=start
            for row in range(4):
                for column in range(4):
                    matrix.SetElement(row,column,float(transform[row,column]))
            actor.SetVisibility(length>1e-8)

    def set_volume(self, volume, masks, prebuilt_meshes=None,styles=None):
        if any(np.asarray(mask).shape != volume.shape for mask in masks.values()):
            raise ValueError("Lung masks must match the CT geometry.")
        prepared = (prepare_display_meshes(volume, masks)
                    if prebuilt_meshes is None else prebuilt_meshes)
        if any(mesh.n_cells > DISPLAY_MAX_CELLS for mesh in prepared.values()):
            raise ValueError("Display meshes exceed the fixed viewer resolution.")
        self.set_target(None)
        self.set_forecast(None)
        self.set_needle(None)
        self.set_exclusions(())
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
        self.forecast_region_point = None
        self.forecast_region_radius_mm = None
        self.needle_overlay = {}
        self.exclusion_contours = []
        self.needle_arrival_point = None
        self.needle_arrival_tolerance_mm = 0.

    def set_target(self,target,matrix):
        self.target_contour=(target_slice_contour(target,self.plane,matrix)
                             if target is not None and self.plane is not None else None)
        self.update()

    def set_forecast(self,point,tolerance_mm):
        self.forecast_point=None if point is None else np.asarray(point,dtype=float).copy()
        self.forecast_tolerance_mm=float(tolerance_mm)
        if point is None:
            self.set_forecast_region(None,None)
        self.update()

    def set_forecast_region(self,point,radius_mm):
        if point is None or radius_mm is None:
            self.forecast_region_point=self.forecast_region_radius_mm=None
        else:
            point=np.asarray(point,dtype=float)
            radius=float(radius_mm)
            if point.shape!=(3,) or not np.isfinite(point).all() or not np.isfinite(radius) or radius<0:
                raise ValueError("An observation-error region requires a finite LPS centre and nonnegative radius.")
            self.forecast_region_point=point.copy()
            self.forecast_region_radius_mm=radius
        self.update()

    @property
    def forecast_region_contour(self):
        if self.plane is None or self.forecast_region_point is None or self.forecast_region_radius_mm is None:
            return None
        distance=float(self.plane.distance_to_plane(self.forecast_region_point))
        radius=self.forecast_region_radius_mm
        if abs(distance)>radius+1e-9:
            return None
        centre=self.forecast_region_point-distance*self.plane.normal
        section=np.sqrt(max(0.,radius*radius-distance*distance))
        angle=np.linspace(0.,2*np.pi,65)
        return centre+section*(np.cos(angle)[:,None]*self.plane.u+np.sin(angle)[:,None]*self.plane.v)

    def set_needle_arrival(self,point,tolerance_mm):
        self.needle_arrival_point=None if point is None else np.asarray(point,dtype=float).copy()
        self.needle_arrival_tolerance_mm=float(tolerance_mm)
        self.update()

    @property
    def needle_arrival_on_plane(self):
        return (self.plane is not None and self.needle_arrival_point is not None
                and abs(float(self.plane.distance_to_plane(self.needle_arrival_point)))<=self.needle_arrival_tolerance_mm+1e-6)

    def set_exclusions(self,regions,matrix):
        self.exclusion_contours=[]
        if self.plane is not None:
            for region in regions:
                sphere=ResearchTarget(region.name,region.center_lps_mm,region.radius_mm,region.study_id)
                contour=target_slice_contour(sphere,self.plane,matrix)
                if contour is not None:
                    self.exclusion_contours.append((region.name,contour))
        self.update()

    def set_needle(self,plan,depth,half_thickness_mm):
        self.needle_overlay={}
        if plan is not None and self.plane is not None:
            tip=plan.tip_at_depth(depth)
            on_plane=lambda p:abs(float(self.plane.distance_to_plane(p)))<=half_thickness_mm+1e-6
            self.needle_overlay=dict(
                planned=clip_segment_to_slice(plan.entry_lps_mm,plan.endpoint_lps_mm,self.plane,half_thickness_mm),
                inserted=clip_segment_to_slice(plan.entry_lps_mm,tip,self.plane,half_thickness_mm),
                entry=np.asarray(plan.entry_lps_mm) if on_plane(plan.entry_lps_mm) else None,
                tip=tip if on_plane(tip) else None)
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
        for name,contour in self.exclusion_contours:
            painter.setPen(QPen(QColor("#e88a8a"),2,Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF([self.screen_point(p) for p in contour]))
            painter.drawText(self.screen_point(contour[0])+QPointF(5,-5),name)
        region_contour=self.forecast_region_contour
        if region_contour is not None:
            painter.setPen(QPen(QColor("#49dcf4"),1,Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF([self.screen_point(p) for p in region_contour]))
        if self.forecast_on_plane:
            marker=self.screen_point(self.forecast_point)
            painter.setPen(QPen(QColor("#49dcf4"),2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([marker+QPointF(0,-6),marker+QPointF(6,0),
                                           marker+QPointF(0,6),marker+QPointF(-6,0)]))
            painter.drawText(marker+QPointF(9,17),"Predicted")
        if self.needle_overlay:
            for field,color,width,style in (("planned","#e9dcb6",1,Qt.PenStyle.DashLine),
                                             ("inserted","#e7f0fa",3,Qt.PenStyle.SolidLine)):
                points=self.needle_overlay[field]
                if len(points):
                    painter.setPen(QPen(QColor(color),width,style))
                    painter.drawLine(self.screen_point(points[0]),self.screen_point(points[-1]))
            for field,color,text in (("entry","#a6d7ff","Entry"),("tip","#e7f0fa","Tip")):
                position=self.needle_overlay[field]
                if position is not None:
                    marker=self.screen_point(position)
                    painter.setPen(QPen(QColor(color),2))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(marker,4,4)
                    if field!="tip" or self.needle_arrival_point is None or np.linalg.norm(position-self.needle_arrival_point)>1e-6:
                        painter.drawText(marker+QPointF(7,-7),text)
        if self.needle_arrival_on_plane:
            marker=self.screen_point(self.needle_arrival_point)
            painter.setPen(QPen(QColor("#49dcf4"),2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([marker+QPointF(0,-6),marker+QPointF(6,0),marker+QPointF(0,6),marker+QPointF(-6,0)]))
            painter.drawText(marker+QPointF(9,17),"Planned arrival")
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


class PlanningBenchmarkDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self._context=owner._planning_benchmark_context()
        self.benchmark_result=None
        self._worker=None
        self._cancel_requested=False
        self.setWindowTitle("Simulated planning comparison")
        self.resize(940,680)
        self.setMinimumSize(760,540)
        layout=QVBoxLayout(self)
        note=QLabel("Compare three methods on identical controlled cases using this CT, target, manual entry patch and exclusions. "
                    "These are correlated simulated scenarios on one anatomy, not independent patients.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form=QFormLayout()
        self.preset=QComboBox()
        for name,count in (("Quick",32),("Extended",128)):
            self.preset.addItem(f"{name} · {count} cases / {count*3} trials",name)
        self.seed=QSpinBox()
        self.seed.setRange(0,999999)
        self.seed.setValue(17)
        form.addRow("Protocol",self.preset)
        form.addRow("Comparison seed",self.seed)
        self.compare_exclusions=QCheckBox("Compare current and predicted exclusion motion")
        self.compare_exclusions.setChecked(bool(self._context["exclusions"]))
        self.compare_exclusions.setEnabled(bool(self._context["exclusions"]))
        self.compare_exclusions.setToolTip("Runs both screening policies within each method and case, using identical observations. Add declared exclusions to enable this comparison.")
        form.addRow(self.compare_exclusions)
        self.assess_uncertainty=QCheckBox("Assess empirical observation-error regions")
        form.addRow(self.assess_uncertainty)
        self.uncertainty_horizon=owner.spin(.1,5,.5,.1,decimals=2)
        self.uncertainty_horizon.setSuffix(" s")
        self.uncertainty_horizon.setEnabled(False)
        self.uncertainty_coverage=QComboBox()
        for coverage in (.8,.9,.95):
            self.uncertainty_coverage.addItem(f"{coverage:.0%}",coverage)
        self.uncertainty_coverage.setCurrentIndex(1)
        self.uncertainty_coverage.setEnabled(False)
        audit_parameters=QHBoxLayout()
        audit_parameters.addWidget(QLabel("Look ahead"))
        audit_parameters.addWidget(self.uncertainty_horizon,1)
        audit_parameters.addWidget(QLabel("Nominal coverage"))
        audit_parameters.addWidget(self.uncertainty_coverage,1)
        form.addRow("Forecast regions",audit_parameters)
        layout.addLayout(form)
        self.protocol_note=QLabel()
        self.protocol_note.setWordWrap(True)
        layout.addWidget(self.protocol_note)
        self.preset.currentIndexChanged.connect(self._protocol_changed)
        self.seed.valueChanged.connect(self._protocol_changed)
        self.compare_exclusions.toggled.connect(self._protocol_changed)
        self.assess_uncertainty.toggled.connect(self._protocol_changed)
        self.uncertainty_horizon.valueChanged.connect(self._protocol_changed)
        self.uncertainty_coverage.currentIndexChanged.connect(self._protocol_changed)
        buttons=QHBoxLayout()
        self.run_button=QToolButton()
        self.run_button.setText("Run comparison")
        self.run_button.clicked.connect(self.run_benchmark)
        self.cancel_button=QToolButton()
        self.cancel_button.setText("Cancel run")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_run)
        self.export_button=QToolButton()
        self.export_button.setText("Export evaluation CSV…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        for button in (self.run_button,self.cancel_button,self.export_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.progress=QProgressBar()
        self.progress.setRange(0,96)
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m trials")
        layout.addWidget(self.progress)
        self.readout=QLabel("No comparison run. Existing observations and insertion plans are kept.")
        self.readout.setWordWrap(True)
        layout.addWidget(self.readout)
        tabs=QTabWidget()
        summary=QWidget()
        body=QVBoxLayout(summary)
        self.summary_group=QComboBox()
        self.summary_group.addItems(["All cases",*BREATHING_PATTERNS])
        self.summary_group.currentTextChanged.connect(self._show_results)
        body.addWidget(self.summary_group)
        self.summary_table=QTreeWidget()
        self.summary_table.setHeaderLabels(["Method","Executed / cases","Mean / p95 mm","Arrival contacts / cases","Violations / assessed","Exclusions"])
        self.summary_table.setRootIsDecorated(False)
        self.summary_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.summary_table.header().setStretchLastSection(True)
        body.addWidget(self.summary_table)
        self.paired_table=QTreeWidget()
        self.paired_table.setHeaderLabels(["Versus constant position","Paired / cases","Mean Δ mm","Better / tied / worse","Exclusions"])
        self.paired_table.setRootIsDecorated(False)
        self.paired_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.paired_table.header().setStretchLastSection(True)
        body.addWidget(self.paired_table)
        definitions=QLabel("Errors use evaluated insertions only. Arrival contacts / cases includes unavailable fits, abstentions and evaluation failures in the denominator. "
                           "Paired differences use mutually evaluated cases; negative Δ favours the named method. "
                           "Obstacle violations are unassessed without declared exclusions. Fit acceptance is not calibrated uncertainty.")
        definitions.setWordWrap(True)
        body.addWidget(definitions)
        tabs.addTab(summary,"Summary")
        self.trials_table=QTreeWidget()
        self.trials_table.setHeaderLabels(["Case / method","Pattern","Noise mm","Delay / speed","Status","Arrival mm","Exclusions"])
        self.trials_table.setRootIsDecorated(False)
        self.trials_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.trials_table.header().setStretchLastSection(True)
        tabs.addTab(self.trials_table,"Every trial")
        policy_page=QWidget()
        policy_body=QVBoxLayout(policy_page)
        self.policy_group=QComboBox()
        self.policy_group.addItems(["All cases",*BREATHING_PATTERNS])
        self.policy_group.currentIndexChanged.connect(self.summary_group.setCurrentIndex)
        self.summary_group.currentIndexChanged.connect(self.policy_group.setCurrentIndex)
        policy_body.addWidget(self.policy_group)
        self.policy_table=QTreeWidget()
        self.policy_table.setHeaderLabels(["Method","Executed current → predicted","Abstained current → predicted",
            "Contact + clear / cases","Violations / assessed","Paired / cases"])
        self.policy_table.setRootIsDecorated(False)
        self.policy_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.policy_table.header().setStretchLastSection(True)
        policy_body.addWidget(self.policy_table,1)
        policy_note=QLabel("Compare screening policies within the same method and case. Contact + clear requires arrival contact and no numerically detected exclusion violation; its denominator includes every attempted case. "
            "Extra abstention does not count as a successful insertion. Predicted screening assumes anchored shared affine motion; actual outcomes remain a separate simulation evaluation.")
        policy_note.setWordWrap(True)
        policy_body.addWidget(policy_note)
        tabs.addTab(policy_page,"Screening trade-off")
        tabs.setTabEnabled(2,bool(self._context["exclusions"]))
        tabs.setTabToolTip(2,"Declare exclusions and compare both policies to assess this trade-off.")
        region_page=QWidget()
        region_body=QVBoxLayout(region_page)
        self.uncertainty_group=QComboBox()
        self.uncertainty_group.addItems(["All cases",*BREATHING_PATTERNS])
        self.uncertainty_group.currentIndexChanged.connect(self.summary_group.setCurrentIndex)
        self.summary_group.currentIndexChanged.connect(self.uncertainty_group.setCurrentIndex)
        region_body.addWidget(self.uncertainty_group)
        self.uncertainty_table=QTreeWidget()
        self.uncertainty_table.setHeaderLabels(["Method","Available / cases","Observation covered / assessed","True centre covered / assessed","Mean radius mm"])
        self.uncertainty_table.setRootIsDecorated(False)
        self.uncertainty_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.uncertainty_table.header().setStretchLastSection(True)
        region_body.addWidget(self.uncertainty_table,1)
        region_note=QLabel("Calibrate from completed past noisy-observation errors, then evaluate at a later observation-grid probe. "
            "Availability counts attempted cases; coverage and radius summaries count each distinct forecast probe once across repeated delays, speeds and policies. "
            "Observation and simulated true-centre coverage are separate. "
            "Regions are empirical under dependent histories, not guaranteed latent-target probabilities. These diagnostics do not change route selection.")
        region_note.setWordWrap(True)
        region_body.addWidget(region_note)
        tabs.addTab(region_page,"Forecast regions")
        layout.addWidget(tabs,1)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self._protocol_changed()

    def _settings(self):
        context=self._context
        return PlanningBenchmarkSettings(preset=self.preset.currentData(),seed=self.seed.value(),
            amplitude_mm=context["amplitude_mm"],rate_bpm=context["rate_bpm"],
            observation_rate_hz=context["observation_rate_hz"],forecast_settings=context["forecast_settings"],
            compare_exclusion_policies=self.compare_exclusions.isChecked(),
            assess_forecast_uncertainty=self.assess_uncertainty.isChecked(),
            uncertainty_settings=UncertaintySettings(nominal_coverage=self.uncertainty_coverage.currentData()),
            uncertainty_horizon_s=self.uncertainty_horizon.value())

    def _protocol_changed(self,*args):
        if self._worker is not None:
            return
        self.benchmark_result=None
        self.summary_table.clear()
        self.paired_table.clear()
        self.trials_table.clear()
        self.policy_table.clear()
        self.uncertainty_table.clear()
        self.export_button.setEnabled(False)
        settings=self._settings()
        cases=planning_benchmark_cases(settings)
        count=len(cases)
        policies=2 if settings.compare_exclusion_policies and self._context["exclusions"] else 1
        for index,name,count_cases in ((0,"Quick",32),(1,"Extended",128)):
            self.preset.setItemText(index,f"{name} · {count_cases} cases / {count_cases*len(BASELINE_METHODS)*policies} trials")
        self.progress.setRange(0,count*len(BASELINE_METHODS)*policies)
        self.progress.setValue(0)
        self.uncertainty_horizon.setEnabled(settings.assess_forecast_uncertainty)
        self.uncertainty_coverage.setEnabled(settings.assess_forecast_uncertainty)
        context=self._context
        origins="31.15 s" if settings.preset=="Quick" else "31.15 / 42.65 s, two seeded replicates per pattern"
        self.protocol_note.setText(f"{count} cases / {count*len(BASELINE_METHODS)*policies} trials · {policies} exclusion screening {'policies' if policies==2 else 'policy'} · four breathing patterns · noise 0 / 1 mm per axis · delay 0 / 1.5 s · speed 15 / 30 mm/s.\n"
            f"Origins: {origins}. Base amplitude {settings.amplitude_mm:g} mm · rate {settings.rate_bpm:g}/min · sampling {settings.observation_rate_hz:g} Hz · fit history {settings.forecast_settings.history_window_s:g} s.\n"
            f"Target radius {context['target'].radius_mm:g} mm · needle radius {context['needle_radius_mm']:g} mm · entry patch {context['route_settings'].patch_radius_mm:g} mm · {len(context['exclusions'])} exclusions.")
        if settings.assess_forecast_uncertainty:
            self.protocol_note.setText(self.protocol_note.text()+f"\nForecast-region audit: nominal {settings.uncertainty_settings.nominal_coverage:.0%}, first observed sample at/after {settings.uncertainty_horizon_s:g} s look ahead; separate from needle arrival.")
        self.readout.setText("Protocol selected. Every method receives the same past noisy observations for each case.")
        self.run_button.setEnabled(self.owner._planning_benchmark_context_matches(context))

    def run_benchmark(self):
        if self._worker is not None or self.owner.worker is not None:
            return
        if not self.owner._planning_benchmark_context_matches(self._context):
            self._discard_stale()
            return
        self._protocol_changed()
        self._cancel_requested=False
        context,settings=self._context,self._settings()
        self.preset.setEnabled(False)
        self.seed.setEnabled(False)
        self.compare_exclusions.setEnabled(False)
        self.assess_uncertainty.setEnabled(False)
        self.uncertainty_horizon.setEnabled(False)
        self.uncertainty_coverage.setEnabled(False)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.readout.setText("Running paired cases. No partial result will be published if cancelled.")
        def compute(report):
            thread=QThread.currentThread()
            def progress(done,total):
                thread.download_progress.emit(done,total)
                report(f"Planning comparison · {done} / {total} trials")
            return run_planning_benchmark(context["volume"],context["mask"],context["target"],
                context["entry_reference"],context["deformation"],settings=settings,
                needle_radius_mm=context["needle_radius_mm"],route_settings=context["route_settings"],
                exclusions=context["exclusions"],progress=progress,cancelled=thread.isInterruptionRequested)
        def accepted(result):
            if self._cancel_requested:
                return
            if not self.owner._planning_benchmark_context_matches(context) or self._settings()!=settings:
                self._discard_stale()
                return
            self.benchmark_result=result
            self._show_results()
            self.readout.setText(f"Completed {len(result.rows)} trials · result {result.result_id[:12]}. "
                "Inspect failures and per-pattern results before interpreting pooled errors. Evaluation exports include scenario seeds.")
            self.export_button.setEnabled(True)
        def connect_worker(worker):
            self._worker=worker
            worker.download_progress.connect(self._show_progress)
            worker.cancelled.connect(self._cancelled)
            worker.failed.connect(lambda message:self.readout.setText("Comparison failed: "+message))
            worker.finished.connect(self._finished)
        self.owner.task(compute,accepted,"Running the controlled planning comparison…",phase_kind="benchmark",progress=True,
                        before_start=connect_worker)

    def _show_progress(self,done,total):
        self.progress.setRange(0,total)
        self.progress.setValue(done)

    def _cancelled(self):
        self.benchmark_result=None
        self.readout.setText("Comparison cancelled. No partial result was published; existing study and plans were kept.")

    def cancel_run(self):
        if self._worker is not None:
            self._cancel_requested=True
            self._worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.readout.setText("Cancelling after the current numerical operation…")

    def _finished(self):
        self._worker=None
        self.preset.setEnabled(True)
        self.seed.setEnabled(True)
        self.compare_exclusions.setEnabled(bool(self._context["exclusions"]))
        self.assess_uncertainty.setEnabled(True)
        self.uncertainty_horizon.setEnabled(self.assess_uncertainty.isChecked())
        self.uncertainty_coverage.setEnabled(self.assess_uncertainty.isChecked())
        self.cancel_button.setEnabled(False)
        valid=self.owner._planning_benchmark_context_matches(self._context)
        self.run_button.setEnabled(valid)
        self.export_button.setEnabled(valid and self.benchmark_result is not None)
        if not valid:
            self._discard_stale()
        if self._cancel_requested:
            self._cancelled()

    def _discard_stale(self):
        self.benchmark_result=None
        self.summary_table.clear()
        self.paired_table.clear()
        self.trials_table.clear()
        self.policy_table.clear()
        self.uncertainty_table.clear()
        self.export_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.readout.setText("The study or comparison inputs changed. Close this window and open a new comparison.")

    def _show_results(self,*args):
        result=self.benchmark_result
        self.summary_table.clear()
        self.paired_table.clear()
        self.policy_table.clear()
        self.uncertainty_table.clear()
        if result is None:
            return
        pattern=self.summary_group.currentText()
        summaries=result.summaries if pattern=="All cases" else [row for row in result.pattern_summaries if row["pattern"]==pattern]
        paired=result.paired_summaries if pattern=="All cases" else [row for row in result.pattern_paired_summaries if row["pattern"]==pattern]
        policies=result.policy_summaries if pattern=="All cases" else [row for row in result.pattern_policy_summaries if row["pattern"]==pattern]
        uncertainty=result.uncertainty_summaries if pattern=="All cases" else [row for row in result.pattern_uncertainty_summaries if row["pattern"]==pattern]
        number=lambda value:"—" if value is None else f"{value:.3f}"
        screening=lambda row:"Predicted" if row["exclusion_policy"]=="Predicted motion" else "Current"
        for row in summaries:
            item=QTreeWidgetItem([row["method"],f"{row['executed_count']} / {row['case_count']}",
                f"{number(row['mean_arrival_error_mm'])} / {number(row['p95_arrival_error_mm'])}",
                f"{row['arrival_hit_count']} / {row['case_count']}",
                f"{row['obstacle_violation_count']} / {row['obstacle_assessed_count']}" if row["obstacle_assessed_count"] else "Unassessed",
                screening(row)])
            tip=(f"Fit unavailable: {row['fit_unavailable_count']} · route abstained: {row['abstained_count']} · evaluation failed: {row['execution_failed_count']}\n"
                f"Median arrival error: {number(row['median_arrival_error_mm'])} mm · errors from {row['arrival_error_count']} evaluated cases.\n"
                f"Tip contact during insertion: {row['tip_contact_count']} · finite-centreline contact: {row['shaft_contact_count']}")
            tip+="\nExclusion screening: "+row["exclusion_policy"]
            for column in range(6):
                item.setToolTip(column,tip)
            self.summary_table.addTopLevelItem(item)
        for row in paired:
            item=QTreeWidgetItem([row["method"],f"{row['paired_count']} / {row['paired_count']+row['excluded_count']}",
                number(row["mean_error_delta_mm"]),f"{row['wins']} / {row['ties']} / {row['losses']}",screening(row)])
            item.setToolTip(0,f"Median paired difference: {number(row['median_error_delta_mm'])} mm. {row['excluded_count']} cases excluded because both methods did not execute.")
            self.paired_table.addTopLevelItem(item)
        for row in policies:
            current_hit=row["current_arrival_hit_clear_count"]
            predicted_hit=row["predicted_arrival_hit_clear_count"]
            current_violation=(f"{row['current_obstacle_violation_count']} / {row['current_obstacle_assessed_count']}"
                               if row["current_obstacle_assessed_count"] else "Unassessed")
            predicted_violation=(f"{row['predicted_obstacle_violation_count']} / {row['predicted_obstacle_assessed_count']}"
                                 if row["predicted_obstacle_assessed_count"] else "Unassessed")
            item=QTreeWidgetItem([row["method"],f"{row['current_executed_count']} → {row['predicted_executed_count']}",
                f"{row['current_abstained_count']} → {row['predicted_abstained_count']}",
                f"{current_hit} / {row['case_count']} → {predicted_hit} / {row['case_count']}",
                f"{current_violation} → {predicted_violation}",
                f"{row['paired_executed_count']} / {row['case_count']}"])
            tip=(f"Mean paired arrival-error change (predicted − current): {number(row['paired_error_delta_mm'])} mm.\n"
                f"Different entries on shared evaluated cases: {row['samecase_different_entry_count']}.\n"
                f"Unavailable fits current/predicted: {row['current_fit_unavailable_count']} / {row['predicted_fit_unavailable_count']}; "
                f"evaluation failures: {row['current_execution_failed_count']} / {row['predicted_execution_failed_count']}.")
            for column in range(6):
                item.setToolTip(column,tip)
            self.policy_table.addTopLevelItem(item)
        for row in uncertainty:
            item=QTreeWidgetItem([row["method"],f"{row['available_count']} / {row['case_count']}",
                f"{row['observed_covered_count']} / {row['observation_assessed_count']}" if row["observation_assessed_count"] else "Unassessed",
                f"{row['true_covered_count']} / {row['truth_assessed_count']}" if row["truth_assessed_count"] else "Unassessed",
                number(row["mean_radius_mm"])])
            tip=(f"Nominal observation coverage: {row['nominal_coverage']:.0%}. {row['unavailable_count']} cases unavailable.\n"
                f"Distinct forecast probes: {row['available_probe_count']} available / {row['distinct_probe_count']} attempted; repeated execution settings and policies add no coverage evidence.\n"
                f"Median / p95 radius: {number(row['median_radius_mm'])} / {number(row['p95_radius_mm'])} mm.\n"
                "Empirical noisy-observation residuals; no formal time-series coverage guarantee.")
            for column in range(5):
                item.setToolTip(column,tip)
            self.uncertainty_table.addTopLevelItem(item)
        if not self.trials_table.topLevelItemCount():
            for row in result.rows:
                item=QTreeWidgetItem([f"{row['case_id']} / {row['method']}",row["pattern"],f"{row['noise_std_mm']:g}",
                    f"{row['delay_s']:g} s / {row['speed_mm_s']:g} mm/s",row["status"].replace("_"," "),number(row["arrival_tip_error_mm"]),screening(row)])
                for column in range(7):
                    item.setToolTip(column,row["reason"])
                self.trials_table.addTopLevelItem(item)

    def export_results(self):
        result=self.benchmark_result
        if result is None or self._worker is not None:
            return
        if not self.owner._planning_benchmark_context_matches(self._context):
            self._discard_stale()
            return
        path,_=QFileDialog.getSaveFileName(self,"Export simulated planning comparison","planning-comparison.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        temporary=None
        def check_current():
            if (self.benchmark_result is not result or result.settings!=self._settings()
                    or not self.owner._planning_benchmark_context_matches(self._context)):
                self._discard_stale()
                raise ValueError("Comparison inputs changed during export. Open a new comparison before exporting.")
        try:
            check_current()
            protected=self.owner._protected_export_paths()
            path=check_export_destination(path,protected)
            records=[dict(record_kind="protocol_manifest",manifest_json=json.dumps(result.manifest,sort_keys=True,separators=(",",":"),allow_nan=False))]
            for kind,rows in (("method_summary",result.summaries),("paired_summary",result.paired_summaries),
                              ("pattern_summary",result.pattern_summaries),("pattern_paired_summary",result.pattern_paired_summaries),
                              ("policy_summary",result.policy_summaries),("pattern_policy_summary",result.pattern_policy_summaries),
                              ("uncertainty_summary",result.uncertainty_summaries),("pattern_uncertainty_summary",result.pattern_uncertainty_summaries),
                              ("trial",result.rows)):
                for row in rows:
                    records.append(dict(row,record_kind=kind))
            fields=["format_version","result_id","record_kind","manifest_json",*sorted(set().union(*(set(row) for row in records))
                -{"format_version","result_id","record_kind","manifest_json"})]
            identity=result.result_id
            temporary=path.with_name(f".{path.name}.{uuid4().hex}.part")
            with temporary.open("x",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                for row in records:
                    values={key:json.dumps(value,separators=(",",":"),allow_nan=False) if isinstance(value,(list,tuple,dict)) else value
                            for key,value in row.items()}
                    writer.writerow(dict(values,format_version=3,result_id=identity))
            check_export_destination(path,protected)
            check_current()
            os.replace(temporary,path)
        except (ValueError,OSError) as error:
            self.readout.setText(str(error))
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.readout.setText(f"Exported complete simulated evaluation, case definitions, seeds and outcomes: {path}")

    def reject(self):
        if self._worker is not None:
            self.cancel_run()
            return
        super().reject()

    def closeEvent(self,event):
        if self._worker is not None:
            self.cancel_run()
            event.ignore()
            return
        super().closeEvent(event)


class ForecastStudyDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self._context=owner._forecast_study_context()
        self.study_result=None
        self._worker=None
        self._cancel_requested=False
        self.setWindowTitle("Held-out synthetic forecast study")
        self.resize(1000,720)
        self.setMinimumSize(780,620)
        layout=QVBoxLayout(self)
        note=QLabel("Calibrate on one synthetic subject group, freeze its forecast-error regions, then evaluate a separate group. "
            "Both use this reference target and affine geometry. The study generates its own observations.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form=QFormLayout()
        parameters=QHBoxLayout()
        self.preset=QComboBox()
        self.preset.addItem("Quick · 32 calibration + 32 evaluation", "Quick")
        self.preset.addItem("Extended · 64 calibration + 64 evaluation", "Extended")
        self.seed=QSpinBox()
        self.seed.setRange(0,999999)
        self.seed.setValue(17)
        self.coverage=QComboBox()
        for value in (.8,.9,.95):
            self.coverage.addItem(f"{value:.0%}",value)
        self.coverage.setCurrentIndex(1)
        parameters.addWidget(self.preset,2)
        parameters.addWidget(QLabel("Seed"))
        parameters.addWidget(self.seed,1)
        parameters.addWidget(QLabel("Nominal coverage"))
        parameters.addWidget(self.coverage,1)
        form.addRow("Protocol",parameters)
        layout.addLayout(form)
        self.protocol_note=QLabel()
        self.protocol_note.setWordWrap(True)
        layout.addWidget(self.protocol_note)
        buttons=QHBoxLayout()
        self.run_button=QToolButton()
        self.run_button.setText("Run held-out study")
        self.run_button.clicked.connect(self.run_study)
        self.cancel_button=QToolButton()
        self.cancel_button.setText("Cancel run")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_run)
        self.export_button=QToolButton()
        self.export_button.setText("Export study evaluation CSV…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        for button in (self.run_button,self.cancel_button,self.export_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.progress=QProgressBar()
        self.progress.setFormat("%v / %m subjects")
        layout.addWidget(self.progress)
        self.readout=QLabel("No study run. Calibration and evaluation subjects have disjoint identities and random streams.")
        self.readout.setWordWrap(True)
        layout.addWidget(self.readout)
        tabs=QTabWidget()
        summary=QWidget()
        body=QVBoxLayout(summary)
        filters=QHBoxLayout()
        self.error_kind=QComboBox()
        self.error_kind.addItem("Simulated true-centre errors","true")
        self.error_kind.addItem("Noisy-observation errors","observed")
        self.pattern=QComboBox()
        self.pattern.addItems(["All cases",*BREATHING_PATTERNS])
        for widget in (self.error_kind,self.pattern):
            widget.currentIndexChanged.connect(self._show_results)
            filters.addWidget(widget)
        body.addLayout(filters)
        self.coverage_plot=ForecastCoveragePlot()
        self.coverage_plot.compact=True
        self.coverage_plot.setMinimumHeight(180)
        self.coverage_plot.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.summary_table=QTreeWidget()
        self.summary_table.setHeaderLabels(["Method","Ahead s","Calibration n","Assessed / subjects","Covered / assessed","Radius mm","Mean / RMSE mm"])
        self.summary_table.setRootIsDecorated(False)
        self.summary_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.summary_table.header().setStretchLastSection(True)
        self.analysis_splitter=QSplitter(Qt.Orientation.Vertical)
        self.analysis_splitter.setChildrenCollapsible(False)
        self.analysis_splitter.setHandleWidth(5)
        self.analysis_splitter.addWidget(self.coverage_plot)
        self.analysis_splitter.addWidget(self.summary_table)
        self.analysis_splitter.setSizes([200,200])
        body.addWidget(self.analysis_splitter,1)
        definitions=QLabel("Coverage uses assessed evaluation subjects; unavailable fits and regions remain in attempted counts. "
            "Radii are pooled across the declared synthetic mixture. Pattern filters use those frozen pooled radii. "
            "Observed and true-centre errors are separate label populations; empirical results describe this simulator.")
        definitions.setWordWrap(True)
        body.addWidget(definitions)
        tabs.addTab(summary,"Held-out evaluation")
        self.calibration_table=QTreeWidget()
        self.calibration_table.setHeaderLabels(["Method","Ahead s","Error labels","Scores / required","Rank","Radius mm","Status"])
        self.calibration_table.setRootIsDecorated(False)
        self.calibration_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tabs.addTab(self.calibration_table,"Frozen calibration")
        self.trials_table=QTreeWidget()
        self.trials_table.setHeaderLabels(["Split / subject","Method","Ahead s","Pattern","Status","Observed mm","True centre mm"])
        self.trials_table.setRootIsDecorated(False)
        self.trials_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tabs.addTab(self.trials_table,"Every forecast")
        layout.addWidget(tabs,1)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        for signal in (self.preset.currentIndexChanged,self.seed.valueChanged,self.coverage.currentIndexChanged):
            signal.connect(self._protocol_changed)
        self._protocol_changed()

    def _settings(self):
        return ForecastStudySettings(preset=self.preset.currentData(),seed=self.seed.value(),
            nominal_coverage=self.coverage.currentData(),forecast_settings=self._context["forecast_settings"])

    def _protocol_changed(self,*args):
        self.study_result=None
        self.summary_table.clear()
        self.calibration_table.clear()
        self.trials_table.clear()
        self.coverage_plot.set_data((),self.coverage.currentData())
        self.export_button.setEnabled(False)
        settings=self._settings()
        total=2*settings.subjects_per_split
        if self._worker is None:
            self.progress.setRange(0,total)
            self.progress.setValue(0)
        self.protocol_note.setText(f"{settings.subjects_per_split} calibration + {settings.subjects_per_split} evaluation subjects · 10 Hz · horizons 0.5, 1, 2, 3, 5 s. "
            f"Amplitude 4–16 mm; rate 8–24 /min; noise SD 0–1.5 mm/axis; four breathing patterns; origin 30–45 s. "
            f"Fit history {settings.forecast_settings.history_window_s:g} s. One origin per subject; reference geometry is fixed.")
        self.readout.setText("Protocol changed. Run a new held-out study.")
        self.run_button.setEnabled(self._worker is None and self.owner._forecast_study_context_matches(self._context))

    def run_study(self):
        if self._worker is not None or self.owner.worker is not None:
            return
        if not self.owner._forecast_study_context_matches(self._context):
            self._discard_stale()
            return
        self._protocol_changed()
        self._cancel_requested=False
        settings=self._settings()
        for widget in (self.preset,self.seed,self.coverage,self.run_button):
            widget.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.readout.setText("Calibrating first, then evaluating separate subjects. Cancelling publishes no partial result.")
        def compute(report):
            thread=QThread.currentThread()
            def progress(done,total):
                thread.download_progress.emit(done,total)
                report(f"Held-out forecast study · {done} / {total} subjects")
            return run_forecast_study(self._context["target"],self._context["deformation"],settings=settings,
                progress=progress,cancelled=thread.isInterruptionRequested)
        def accepted(result):
            if self._cancel_requested:
                return
            if not self.owner._forecast_study_context_matches(self._context):
                self._discard_stale()
                return
            if self._settings()!=settings:
                self._protocol_changed()
                return
            self.study_result=result
            self._show_results()
            self.readout.setText(f"Completed {len(result.rows)} forecasts · result {result.result_id[:12]}. "
                "Inspect availability and denominators alongside coverage. Simulated subjects are not clinical cases.")
            self.export_button.setEnabled(True)
        def connect_worker(worker):
            self._worker=worker
            worker.download_progress.connect(lambda done,total:(self.progress.setRange(0,total),self.progress.setValue(done)))
            worker.cancelled.connect(self._cancelled)
            worker.failed.connect(lambda message:self.readout.setText("Study failed: "+message))
            worker.finished.connect(self._finished)
        self.owner.task(compute,accepted,"Running held-out synthetic forecast calibration and evaluation…",
            phase_kind="forecast-study",progress=True,before_start=connect_worker)

    def cancel_run(self):
        if self._worker is not None:
            self._cancel_requested=True
            self._worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.readout.setText("Cancelling after the current numerical operation…")

    def _cancelled(self):
        self.study_result=None
        self.readout.setText("Study cancelled. No partial result was published.")
        self.export_button.setEnabled(False)

    def _finished(self):
        self._worker=None
        for widget in (self.preset,self.seed,self.coverage):
            widget.setEnabled(True)
        self.cancel_button.setEnabled(False)
        valid=self.owner._forecast_study_context_matches(self._context)
        self.run_button.setEnabled(valid)
        self.export_button.setEnabled(valid and self.study_result is not None)
        if not valid:
            self._discard_stale()
        elif self._cancel_requested:
            self._cancelled()

    def _discard_stale(self):
        self.study_result=None
        for table in (self.summary_table,self.calibration_table,self.trials_table):
            table.clear()
        self.coverage_plot.set_data(())
        self.run_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.readout.setText("The reference target, geometry or forecast settings changed. Open a new study.")

    def _show_results(self,*args):
        result=self.study_result
        if result is None:
            return
        if not self.owner._forecast_study_context_matches(self._context):
            self._discard_stale()
            return
        pattern=self.pattern.currentText()
        summaries=result.summaries if pattern=="All cases" else [row for row in result.pattern_summaries if row["pattern"]==pattern]
        summaries=[row for row in summaries if row["error_kind"]==self.error_kind.currentData()]
        self.coverage_plot.set_data(summaries,result.settings.nominal_coverage)
        self.summary_table.clear()
        number=lambda value:"—" if value is None else f"{value:.3f}"
        for row in summaries:
            item=QTreeWidgetItem([row["method"],f"{row['horizon_s']:g}",str(row["calibration_count"]),
                f"{row['assessed_count']} / {row['attempted_count']}",
                f"{row['covered_count']} / {row['assessed_count']}" if row["assessed_count"] else "Unassessed",
                number(row["radius_mm"]),f"{number(row['mean_error_mm'])} / {number(row['rmse_mm'])} (n={row['error_assessed_count']})"])
            tip=(f"{row['fit_unavailable_count']} unavailable fits; {row['outcome_unavailable_count']} missing evaluation outcomes; "
                f"{row['region_unavailable_count']} forecasts without an available calibration region. "
                "Mean/RMSE use available forecasts; coverage uses available regions and forecasts. Calibration uses a separate subject group.")
            for column in range(7):
                item.setToolTip(column,tip)
            self.summary_table.addTopLevelItem(item)
        if not self.calibration_table.topLevelItemCount():
            for row in result.calibrations:
                item=QTreeWidgetItem([row["method"],f"{row['horizon_s']:g}",row["error_kind"],
                    f"{row['calibration_count']} / {row['required_count']}",str(row["rank"]),number(row["radius_mm"]),row["status"]])
                for column in range(7):
                    item.setToolTip(column,row["reason"])
                self.calibration_table.addTopLevelItem(item)
        if not self.trials_table.topLevelItemCount():
            for row in result.rows:
                item=QTreeWidgetItem([f"{row['split']} / {row['subject_id']}",row["method"],f"{row['horizon_s']:g}",
                    row["pattern"],row["status"].replace("_"," "),number(row["observed_error_mm"]),number(row["true_error_mm"])])
                for column in range(7):
                    item.setToolTip(column,row["reason"])
                self.trials_table.addTopLevelItem(item)

    def export_results(self):
        result=self.study_result
        if result is None or self._worker is not None:
            return
        if not self.owner._forecast_study_context_matches(self._context):
            self._discard_stale()
            return
        path,_=QFileDialog.getSaveFileName(self,"Export held-out synthetic forecast study","held-out-forecast-study.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        temporary=None
        def check_current():
            if not self.owner._forecast_study_context_matches(self._context):
                self._discard_stale()
                raise ValueError("Study inputs changed during export. Run a new study before exporting.")
            if self.study_result is not result or result.settings!=self._settings():
                self._protocol_changed()
                raise ValueError("The study protocol changed during export. Run it again before exporting.")
        try:
            check_current()
            protected=self.owner._protected_export_paths()
            path=check_export_destination(path,protected)
            records=[dict(record_kind="protocol_manifest",manifest_json=json.dumps(result.manifest,sort_keys=True,separators=(",",":"),allow_nan=False))]
            for kind,rows in (("calibration",result.calibrations),("evaluation_summary",result.summaries),
                              ("pattern_evaluation_summary",result.pattern_summaries),("forecast_trial",result.rows)):
                records.extend(dict(row,record_kind=kind) for row in rows)
            fields=["format_version","result_id","record_kind","manifest_json",*sorted(set().union(*(set(row) for row in records))
                -{"format_version","result_id","record_kind","manifest_json"})]
            identity=result.result_id
            temporary=path.with_name(f".{path.name}.{uuid4().hex}.part")
            with temporary.open("x",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                for row in records:
                    values={key:json.dumps(value,separators=(",",":"),allow_nan=False) if isinstance(value,(list,tuple,dict)) else value
                        for key,value in row.items()}
                    writer.writerow(dict(values,format_version=1,result_id=identity))
            check_export_destination(path,protected)
            check_current()
            os.replace(temporary,path)
        except (ValueError,OSError) as error:
            self.readout.setText(str(error))
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.readout.setText(f"Exported held-out simulated calibration, evaluation, subject definitions and outcomes: {path}")

    def reject(self):
        if self._worker is not None:
            self.cancel_run()
            return
        super().reject()

    def closeEvent(self,event):
        if self._worker is not None:
            self.cancel_run()
            event.ignore()
            return
        super().closeEvent(event)


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
        self.needle_entry_reference = None
        self._needle_entry_volume = None
        self.needle_plan = None
        self.needle_evaluation = None
        self._needle_results_dialog = None
        self._needle_generation = 0
        self._needle_plan_volume = None
        self._needle_plan_mask_key = None
        self.needle_exclusions = ()
        self._needle_exclusions_volume = None
        self.needle_route_selection = None
        self.needle_constraint_evaluation = None
        self._needle_route_context = None
        self._needle_plan_constraint_key = None
        self._needle_prediction_error = None
        self._planning_benchmark_dialog = None
        self._target_mask_key = None
        self._target_mask = None
        self._study_source_paths = set()
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(67)
        self.motion_timer.timeout.connect(self._motion_tick)
        self.needle_timer = QTimer(self)
        self.needle_timer.setInterval(67)
        self.needle_timer.timeout.connect(self._needle_tick)
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
        for name,build in (("Imaging",self._imaging_controls),("Motion",self._motion_controls),
                           ("Landmarks",self._landmark_controls),("Needle",self._needle_controls)):
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
        self.controls.setTabEnabled(3,False)
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
        self._forecast_controls(layout)
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

    def _forecast_controls(self,layout):
        body=QVBoxLayout()
        form=QFormLayout()
        self.forecast_method=QComboBox()
        self.forecast_method.addItems(BASELINE_METHODS)
        self.forecast_method.currentTextChanged.connect(self._forecast_method_changed)
        self.forecast_horizon=self.spin(.1,5,.5,.1,decimals=2)
        self.forecast_horizon.setSuffix(" s")
        self.forecast_history=self.spin(4,40,20,1)
        self.forecast_history.setSuffix(" s")
        self.forecast_history.setToolTip("Maximum sinusoidal history. At least 20 sampled seconds are needed to identify two cycles at 6 breaths/min. Velocity uses the latest 1 second.")
        for label,control in (("Display method",self.forecast_method),("Look ahead",self.forecast_horizon),
                              ("Fit history",self.forecast_history)):
            form.addRow(label,control)
        self.forecast_horizon.valueChanged.connect(self._invalidate_forecasts)
        self.forecast_history.valueChanged.connect(self._invalidate_forecasts)
        self.forecast_uncertainty=QCheckBox("Estimate observation-error region")
        self.forecast_uncertainty.setToolTip("Uses completed past forecast errors against noisy observations. This is empirical coverage, not a calibrated latent-target probability.")
        self.forecast_uncertainty.toggled.connect(self._invalidate_forecasts)
        form.addRow(self.forecast_uncertainty)
        self.forecast_coverage=QComboBox()
        for value in (.8,.9,.95):
            self.forecast_coverage.addItem(f"{value:.0%}",value)
        self.forecast_coverage.setCurrentIndex(1)
        self.forecast_coverage.setEnabled(False)
        self.forecast_coverage.currentIndexChanged.connect(self._invalidate_forecasts)
        form.addRow("Nominal coverage",self.forecast_coverage)
        body.addLayout(form)
        self.forecast_compute=QToolButton()
        self.forecast_compute.setText("Compute mathematical baselines")
        self.forecast_compute.setEnabled(False)
        self.forecast_compute.clicked.connect(self.compute_forecasts)
        body.addWidget(self.forecast_compute)
        self.forecast_readout=QLabel("Record target observations before forecasting.")
        self.forecast_readout.setWordWrap(True)
        self.forecast_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.forecast_readout)
        self.forecast_uncertainty_readout=QLabel("Observation-error regions are off.")
        self.forecast_uncertainty_readout.setWordWrap(True)
        self.forecast_uncertainty_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.forecast_uncertainty_readout)
        self.forecast_plot=ForecastPlot()
        body.addWidget(self.forecast_plot)
        self.forecast_table=QTreeWidget()
        self.forecast_table.setColumnCount(3)
        self.forecast_table.setHeaderLabels(["Method","Mean 3D","RMSE"])
        self.forecast_table.setRootIsDecorated(False)
        self.forecast_table.setAlternatingRowColors(True)
        self.forecast_table.setFixedHeight(120)
        self.forecast_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.forecast_table.header().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for column in (1,2):
            self.forecast_table.header().setSectionResizeMode(column,QHeaderView.ResizeMode.Fixed)
            self.forecast_table.setColumnWidth(column,61)
        self.forecast_table.setToolTip("Historical paired validation, millimetres. Mean 3D error is the mean Euclidean position error; RMSE is the square root of the mean squared 3D error.")
        body.addWidget(self.forecast_table)
        self.forecast_validation_readout=QLabel("Historical validation requires completed forecast outcomes.")
        self.forecast_validation_readout.setWordWrap(True)
        self.forecast_validation_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.forecast_validation_readout)
        for field,label,truth in (("forecast_export","Export forecasts CSV…",False),
                                  ("forecast_evaluation_export","Export forecast evaluation CSV…",True)):
            button=QToolButton()
            button.setText(label)
            button.setEnabled(False)
            button.clicked.connect(lambda checked=False,include_truth=truth:self.export_forecasts(include_truth))
            setattr(self,field,button)
            body.addWidget(button)
        note=QLabel("Cyan: predicted future centre · amber: actual target now. Fits use past noisy observations only. Errors use separate simulated truth, not patient outcomes.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#b8bec6;font-size:10px")
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(note)
        self.forecast_study=QToolButton()
        self.forecast_study.setText("Validate on held-out scenarios…")
        self.forecast_study.setToolTip("Calibrate and evaluate the three mathematical forecasts on separate synthetic subject groups. Uses a fixed 10 Hz study protocol; no existing recording is required.")
        self.forecast_study.setEnabled(False)
        self.forecast_study.clicked.connect(self.open_forecast_study)
        body.addWidget(self.forecast_study)
        layout.addWidget(group("Mathematical forecasts",body))

    def _forecast_study_context(self):
        if self.ct_sequence is not None or self.target is None or self.deformation is None:
            raise ValueError("Define a simulated target in Motion before opening a forecast study.")
        return dict(volume=self.volume,target=self.target,deformation=self.deformation,forecast_settings=self._forecast_settings())

    def _forecast_study_context_matches(self,context):
        return (self.ct_sequence is None and self.volume is context["volume"] and self.target is context["target"]
            and self.deformation==context["deformation"] and self._forecast_settings()==context["forecast_settings"])

    def open_forecast_study(self):
        if not self.motion_active or self.target is None or self.deformation is None or self.worker is not None:
            return
        self.pause_motion()
        dialog=ForecastStudyDialog(self)
        self._forecast_study_dialog=dialog
        dialog.exec()
        self._forecast_study_dialog=None
        dialog.deleteLater()

    def _forecast_settings(self):
        return ForecastSettings(history_window_s=self.forecast_history.value())

    def _uncertainty_settings(self):
        return UncertaintySettings(nominal_coverage=self.forecast_coverage.currentData())

    def _invalidate_forecasts(self,*args):
        had_forecast=self.forecast_result is not None
        self._forecast_generation+=1
        self.forecast_result=None
        if hasattr(self,"forecast_plot"):
            self.forecast_plot.set_data(None)
            self.forecast_table.clear()
            self.forecast_readout.setText("Compute baselines at the current simulation time.")
            self.forecast_validation_readout.setText("Historical validation requires completed forecast outcomes.")
            enabled=self.forecast_uncertainty.isChecked()
            self.forecast_coverage.setEnabled(enabled)
            self.forecast_uncertainty_readout.setText("Compute baselines to assess the observation-error region." if enabled else "Observation-error regions are off.")
            self.forecast_export.setEnabled(False)
            self.forecast_evaluation_export.setEnabled(False)
        if hasattr(self,"scene"):
            self.scene.set_forecast(None)
            for view in self.slices:
                view.canvas.set_forecast(None,0.)
            if had_forecast:
                self.scene.render()
        self._update_forecast_controls()

    def _update_forecast_controls(self):
        if not hasattr(self,"forecast_compute"):
            return
        data=self.target_observations
        ready=(self.motion_active and data is not None and self.target is data.target
               and self.motion_time<=data.through_s+1e-10)
        self.forecast_compute.setEnabled(ready)
        self.forecast_study.setEnabled(self.motion_active and self.target is not None and self.deformation is not None
            and self.ct_sequence is None)
        self.forecast_compute.setToolTip("Fit all three baselines from observations up to the displayed time." if ready
            else "In Motion, define a target and record observations through the displayed simulation time.")

    def _forecast_context_matches(self,result):
        return (self.motion_active and self.target is result["target"]
                and self.target_observations is result["observations"]
                and self.motion_time==result["origin_s"]
                and self._forecast_settings()==result["settings"]
                and self.forecast_horizon.value()==result["horizon_s"]
                and self.forecast_uncertainty.isChecked()==result["uncertainty_enabled"]
                and (not result["uncertainty_enabled"] or self._uncertainty_settings()==result["uncertainty_settings"])
                and self.deformation==result["observations"].deformation
                and self._observation_settings()==result["observations"].settings
                and respiratory_model_id(self.motion_model)==result["observations"].model_id)

    def compute_forecasts(self):
        data=self.target_observations
        if not self.motion_active or data is None or self.target is None or self.worker is not None:
            return
        self.pause_motion()
        if (self.target is not data.target or data.model_id!=respiratory_model_id(self.motion_model)
                or data.deformation!=self.deformation or data.settings!=self._observation_settings()):
            self._invalidate_observations()
            self.status.setText("The scenario changed. Record its observations again before forecasting.")
            return
        if self.motion_time>data.through_s+1e-10:
            self.status.setText("Record observations through the displayed time before forecasting.")
            return
        origin,horizon=self.motion_time,self.forecast_horizon.value()
        settings=self._forecast_settings()
        uncertainty_enabled=self.forecast_uncertainty.isChecked()
        uncertainty_settings=self._uncertainty_settings()
        generation=self._forecast_generation
        target,model,volume=self.target,self.motion_model,self.volume
        times,positions=data.observations_through(origin)
        def compute():
            fits,predictions,unavailable,regions,region_evaluations,region_unavailable={},{},{},{},{},{}
            for method in BASELINE_METHODS:
                try:
                    fit=fit_baseline(times,positions,method,origin_s=origin,settings=settings)
                    predictions[method]=fit.predict(origin+horizon)
                    fits[method]=fit
                    if uncertainty_enabled:
                        try:
                            regions[method]=calibrate_forecast_region(times,positions,method,origin_s=origin,horizon_s=horizon,
                                settings=uncertainty_settings,forecast_settings=settings,cancelled=QThread.currentThread().isInterruptionRequested)
                        except ValueError as error:
                            region_unavailable[method]=str(error)
                except ValueError as error:
                    unavailable[method]=str(error)
            origins=select_validation_origins(times,through_s=origin,horizon_s=horizon,settings=settings)
            # evaluation labels follow the shared deformation; the fitting functions never receive them.
            weight=(data.deformation.apex_z-target.center_lps_mm[2])/data.deformation.height
            def truth_at(query):
                return np.asarray(target.center_lps_mm)+weight*model.position(query)
            labels=truth_at(origins+horizon) if len(origins) else np.empty((0,3))
            validation=evaluate_baselines(times,positions,origins,labels,horizon_s=horizon,
                settings=settings,methods=tuple(fits) or None)
            future_times=np.linspace(origin,origin+horizon,51)
            covered=origin+horizon<=min(data.through_s,model.duration)
            truth_times=future_times if covered else np.empty(0)
            truth_curve=truth_at(truth_times) if covered else np.empty((0,3))
            observed_outcome=None
            if uncertainty_enabled:
                query=origin+horizon
                full_times=data.times_s
                matches=np.flatnonzero(np.isclose(full_times,query,rtol=0,atol=1e-9))
                observed_outcome=data.observed_lps_mm[int(matches[0])] if len(matches) else None
                for method,region in regions.items():
                    region_evaluations[method]=evaluate_forecast_region(region,observed_lps_mm=observed_outcome,
                        true_lps_mm=truth_curve[-1] if covered else None)
            return dict(target=target,observations=data,origin_s=origin,horizon_s=horizon,
                settings=settings,fits=fits,predictions=predictions,unavailable=unavailable,
                uncertainty_enabled=uncertainty_enabled,uncertainty_settings=uncertainty_settings,
                regions=regions,region_evaluations=region_evaluations,
                region_unavailable=region_unavailable,region_observed_position=observed_outcome,
                validation=validation,history_times_s=times,history_observed_lps_mm=positions,
                forecast_times_s=future_times,truth_times_s=truth_times,truth_curve_lps_mm=truth_curve,
                truth_position=truth_curve[-1].copy() if covered else None)
        def accepted(result):
            if (generation!=self._forecast_generation or self.volume is not volume
                    or self.motion_model is not model or not self._forecast_context_matches(result)):
                return
            self.forecast_result=result
            self._update_forecast_display()
            self.scene.render()
            self.status.setText(f"Computed {len(result['fits'])} / 3 mathematical baselines from past noisy observations.")
        self.task(compute,accepted,"Fitting mathematical baselines and checking historical forecasts…")

    def _forecast_method_changed(self,*args):
        if not hasattr(self,"scene"):
            return
        self._update_forecast_display()
        self.scene.render()

    def _update_forecast_display(self):
        result=self.forecast_result
        if result is not None and not self._forecast_context_matches(result):
            self._invalidate_forecasts()
            return
        method=self.forecast_method.currentText()
        point=None if result is None else result["predictions"].get(method)
        self.scene.set_forecast(point)
        region=None if result is None else result.get("regions",{}).get(method)
        radius=region.radius_mm if region is not None and region.available else None
        self.scene.set_forecast_region(point,radius)
        for view in self.slices:
            tolerance=(.5/np.linalg.norm(self.volume.direction[view.axis]/self.volume.spacing)
                       if self.volume is not None else 0.)
            view.canvas.set_forecast(point,tolerance)
            view.canvas.set_forecast_region(point,radius)
        self.forecast_plot.set_data(result,method)
        if result is None:
            return
        fit=result["fits"].get(method)
        text=f"Origin {result['origin_s']:g} s → {result['origin_s']+result['horizon_s']:g} s\n"
        if fit is None:
            text+=result["unavailable"].get(method,"Forecast unavailable.")
        else:
            text+="Predicted LPS: "+", ".join(f"{value:+.2f}" for value in point)+" mm\n"
            text+=f"{fit.n_samples} fit samples · last observation {fit.last_observation_s:g} s\n"
            if fit.frequency_hz is not None:
                text+=f"Fitted rate {fit.frequency_hz*60:.2f} /min\n"
            text+=fit.note
            if result["truth_position"] is not None:
                error=np.linalg.norm(point-result["truth_position"])
                text+=f"\nSimulated query error: {error:.3f} mm"
            else:
                text+="\nQuery truth unavailable beyond the recorded cutoff."
        self.forecast_readout.setText(text)
        if result["uncertainty_enabled"]:
            if region is None:
                note="Observation-error region unavailable: "+result["region_unavailable"].get(method,result["unavailable"].get(method,"No fit is available."))
            else:
                note=(f"EMPIRICAL OBSERVATION-ERROR REGION · nominal {region.settings.nominal_coverage:.0%}\n"
                    f"{region.n_scores} completed calibration scores · {region.required_score_count} required · {region.excluded_count} excluded fits.\n")
                if region.available:
                    note+=f"Joint 3D radius: {region.radius_mm:.3f} mm at {region.query_s:g} s.\n"
                    assessed=result["region_evaluations"][method]
                    show=lambda value:"Unavailable" if value is None else "Inside" if value else "Outside"
                    note+=f"Later recorded observation: {show(assessed['observed_covered'])}\nSeparate simulated true centre: {show(assessed['true_covered'])}\n"
                else:
                    note+=region.reason+"\n"
                note+="Noisy-observation errors; dependent histories. No guaranteed true-target coverage or change to needle selection."
            self.forecast_uncertainty_readout.setText(note)
        else:
            self.forecast_uncertainty_readout.setText("Observation-error regions are off.")
        self.forecast_export.setEnabled(True)
        validation=result["validation"]
        self.forecast_evaluation_export.setEnabled(bool(validation.rows) or result["truth_position"] is not None and bool(result["fits"]))
        self.forecast_table.clear()
        summaries={row["method"]:row for row in validation.summaries}
        for name in BASELINE_METHODS:
            summary=summaries.get(name)
            scored=summary is not None and summary["count"]>0
            row=QTreeWidgetItem([name,f"{summary['mean_error_mm']:.3f}" if scored else "—",
                                    f"{summary['rmse_mm']:.3f}" if scored else "—"])
            tip=name+"\n"+result["unavailable"].get(name,"Historical paired errors in mm." if scored else "No completed historical validation origins.")
            for column in range(3):
                row.setToolTip(column,tip)
            self.forecast_table.addTopLevelItem(row)
        excluded=validation.candidate_count-validation.paired_count
        note=f"Historical validation · {validation.paired_count} / {validation.candidate_count} paired origins · errors in mm."
        if excluded:
            note+=f"\n{excluded} origins excluded for every compared method when any fit was unavailable."
        if not validation.paired_count:
            note+="\nRecord more history to evaluate completed outcomes."
        self.forecast_validation_readout.setText(note)
        self.forecast_validation_readout.setToolTip("\n".join(dict.fromkeys(row["reason"] for row in validation.unavailable)))

    def _needle_controls(self,layout):
        note=QLabel("SIMULATED STRAIGHT NEEDLE\nDefine a target in Motion, then select a chest-wall entry in the CT views. Entry is selected manually; skin is not detected automatically.")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(note)
        buttons=QHBoxLayout()
        for field,label,callback in (("needle_entry_set","Set entry at crosshair",self.set_needle_entry),
                                     ("needle_entry_go","Go to entry",self.go_to_needle_entry),
                                     ("needle_entry_clear","Clear",self.clear_needle_entry)):
            button=QToolButton()
            button.setText(label)
            button.setEnabled(False)
            button.clicked.connect(callback)
            setattr(self,field,button)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.needle_entry_readout=QLabel("No entry selected.")
        self.needle_entry_readout.setWordWrap(True)
        self.needle_entry_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.needle_entry_readout)
        form=QFormLayout()
        self.needle_targeting_method=QComboBox()
        self.needle_targeting_method.addItems(["Displayed centre",*BASELINE_METHODS])
        self.needle_targeting_method.setToolTip("Displayed centre uses geometric reference anatomy. Constant position uses the last noisy observation; the other methods forecast from past observations.")
        self.needle_targeting_method.currentTextChanged.connect(self._needle_parameters_changed)
        form.addRow("Targeting method",self.needle_targeting_method)
        self.needle_prediction_history=self.spin(4,40,20,1)
        self.needle_prediction_history.setSuffix(" s")
        self.needle_prediction_history.setEnabled(False)
        self.needle_prediction_history.setToolTip("History for the sinusoidal fit. Constant velocity uses the latest second; constant position uses the last available sample.")
        self.needle_prediction_history.valueChanged.connect(self._needle_parameters_changed)
        form.addRow("Prediction history",self.needle_prediction_history)
        self.needle_prediction_readout=QLabel()
        self.needle_prediction_readout.setWordWrap(True)
        self.needle_prediction_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        form.addRow(self.needle_prediction_readout)
        self.needle_radius=self.spin(.2,2,.7,.1,decimals=2)
        self.needle_radius.setSuffix(" mm")
        self.needle_speed=self.spin(1,100,30,1)
        self.needle_speed.setSuffix(" mm/s")
        self.needle_delay=self.spin(0,5,.5,.1,decimals=2)
        self.needle_delay.setSuffix(" s")
        for label,control in (("Shaft radius",self.needle_radius),("Insertion speed",self.needle_speed),
                              ("Execution delay",self.needle_delay)):
            form.addRow(label,control)
            control.valueChanged.connect(self._needle_parameters_changed)
        layout.addLayout(form)
        self.needle_build=QToolButton()
        self.needle_build.setText("Build path to displayed target centre")
        self.needle_build.setEnabled(False)
        self.needle_build.clicked.connect(self.build_needle_plan)
        layout.addWidget(self.needle_build)
        self.needle_plan_readout=QLabel("No path built.")
        self.needle_plan_readout.setWordWrap(True)
        self.needle_plan_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.needle_plan_readout)
        transport=QVBoxLayout()
        buttons=QHBoxLayout()
        for field,label,callback in (("needle_play","Play insertion",self.toggle_needle_preview),
                                     ("needle_reset","Restart",self.restart_needle_preview)):
            button=QToolButton()
            button.setText(label)
            button.clicked.connect(callback)
            button.setEnabled(False)
            setattr(self,field,button)
            buttons.addWidget(button,1)
        transport.addLayout(buttons)
        self.needle_depth=QSlider(Qt.Orientation.Horizontal)
        self.needle_depth.setRange(0,1000)
        self.needle_depth.setTracking(False)
        self.needle_depth.setEnabled(False)
        self.needle_depth.setToolTip("Advance or retract along the fixed path. Releasing the slider seeks to the corresponding insertion time.")
        self.needle_depth.sliderPressed.connect(self.pause_motion)
        self.needle_depth.valueChanged.connect(self._needle_depth_changed)
        transport.addWidget(self.needle_depth)
        self.needle_readout=QLabel("Build a path to preview insertion.")
        self.needle_readout.setWordWrap(True)
        self.needle_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        transport.addWidget(self.needle_readout)
        layout.addWidget(group("Timed insertion preview",transport))
        self.needle_results=QToolButton()
        self.needle_results.setText("Inspect insertion results…")
        self.needle_results.setToolTip("Inspect the computed distance, contact and exclusion timelines alongside the existing animation.")
        self.needle_results.setEnabled(False)
        self.needle_results.clicked.connect(self.open_needle_results)
        layout.addWidget(self.needle_results)
        self.needle_result_readout=QLabel("No insertion evaluated.")
        self.needle_result_readout.setWordWrap(True)
        self.needle_result_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.needle_result_readout)
        self.needle_export=QToolButton()
        self.needle_export.setText("Export insertion evaluation CSV…")
        self.needle_export.setEnabled(False)
        self.needle_export.clicked.connect(self.export_needle_evaluation)
        layout.addWidget(self.needle_export)
        self.needle_benchmark=QToolButton()
        self.needle_benchmark.setText("Compare planning methods…")
        self.needle_benchmark.setEnabled(False)
        self.needle_benchmark.setToolTip("Run reproducible simulated scenarios on this target and entry patch. Existing observations and insertion plans are kept.")
        self.needle_benchmark.clicked.connect(self.open_planning_benchmark)
        layout.addWidget(self.needle_benchmark)
        self._needle_constraint_controls(layout)
        note=QLabel("The rigid path stays fixed while anatomy moves. Target outcomes use the tip centre and finite inserted centreline. Declared exclusion constraints include needle radius. Clinical safety and skin detection are not assessed.")
        self.needle_scope_note=note
        note.setWordWrap(True)
        note.setStyleSheet("color:#b8bec6;font-size:10px")
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(note)
        layout.addStretch()

    def _needle_settings(self):
        return NeedleSettings(radius_mm=self.needle_radius.value(),speed_mm_s=self.needle_speed.value(),
                              delay_s=self.needle_delay.value())

    def _needle_result_is_current(self,result):
        return (result is not None and result is self.needle_evaluation and result.plan is self.needle_plan
            and self._needle_context_matches(result.plan))

    def _sync_needle_results(self):
        dialog=self._needle_results_dialog
        if dialog is None:
            return
        result=self.needle_evaluation
        if not self._needle_result_is_current(result):
            dialog.invalidate()
            return
        dialog.set_results(result,self.needle_constraint_evaluation,
            getattr(self.needle_route_selection,"predicted_constraint_evaluation",None),
            time_s=self.motion_time,can_navigate=self.motion_active and self.worker is None)

    def open_needle_results(self):
        if self.worker is not None or not self._needle_result_is_current(self.needle_evaluation):
            return
        dialog=self._needle_results_dialog
        if dialog is None:
            dialog=NeedleResultsDialog(self)
            self._needle_results_dialog=dialog
            def closed(*args):
                if self._needle_results_dialog is dialog:
                    self._needle_results_dialog=None
            dialog.finished.connect(closed)
        self._sync_needle_results()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def seek_needle_result(self,time_s,result):
        if (self.worker is not None or not self.motion_active or not self._needle_result_is_current(result)
                or isinstance(time_s,(bool,np.bool_)) or not isinstance(time_s,(int,float,np.integer,np.floating))
                or not np.isfinite(time_s) or not result.plan.planning_time_s<=time_s<=result.plan.arrival_s):
            return False
        self.pause_motion()
        self._invalidate_forecasts()
        self.motion_time=float(time_s)
        self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
        self.refresh()
        return True

    def _needle_forecast_settings(self):
        return ForecastSettings(history_window_s=self.needle_prediction_history.value())

    def _needle_exclusion_policy(self):
        return (self.needle_exclusion_policy.currentText()
                if self.needle_targeting_method.currentText()!="Displayed centre" and self.needle_exclusions else "Current geometry")

    def _planning_benchmark_context(self):
        if not self.motion_active or self.target is None or self.needle_entry_reference is None:
            raise ValueError("Define a simulated target and manual entry before comparing planning methods.")
        return dict(volume=self.volume,target=self.target,entry_reference=self.needle_entry_reference,
            mask=self._lung_target_mask(),mask_key=self._needle_lung_key(),deformation=self.deformation,
            exclusions=self.needle_exclusions,route_settings=self._needle_route_settings(),
            needle_radius_mm=self.needle_radius.value(),amplitude_mm=self.motion_amplitude.value(),
            rate_bpm=self.breathing_rate.value(),observation_rate_hz=self.observation_rate.value(),
            forecast_settings=self._needle_forecast_settings())

    def _planning_benchmark_context_matches(self,context):
        return (self.ct_sequence is None and self.volume is context["volume"] and self.target is context["target"]
            and self.needle_entry_reference==context["entry_reference"] and self._needle_lung_key()==context["mask_key"]
            and self.deformation==context["deformation"] and self.needle_exclusions==context["exclusions"]
            and self._needle_route_settings()==context["route_settings"] and self.needle_radius.value()==context["needle_radius_mm"]
            and self.motion_amplitude.value()==context["amplitude_mm"] and self.breathing_rate.value()==context["rate_bpm"]
            and self.observation_rate.value()==context["observation_rate_hz"]
            and self._needle_forecast_settings()==context["forecast_settings"])

    def open_planning_benchmark(self):
        if (not self.motion_active or self.target is None or self.needle_entry_reference is None
                or self.worker is not None):
            return
        self.pause_motion()
        dialog=PlanningBenchmarkDialog(self)
        self._planning_benchmark_dialog=dialog
        dialog.exec()
        self._planning_benchmark_dialog=None
        dialog.deleteLater()

    def _needle_prediction_ready(self):
        method=self.needle_targeting_method.currentText()
        if method=="Displayed centre":
            return True,"Current displayed centre · geometric reference route."
        data=self.target_observations
        if data is None:
            return False,"Record target observations in Motion before using this method."
        if (data.target is not self.target or self.motion_model is None or data.deformation!=self.deformation
                or data.model_id!=respiratory_model_id(self.motion_model) or data.settings!=self._observation_settings()):
            return False,"The recording belongs to a different scenario. Record its observations again."
        if self.motion_time>data.through_s+1e-10:
            return False,"Record observations through the displayed time before building a new forecast route."
        times=data.times_s
        count=int(np.searchsorted(times,self.motion_time,side="right"))
        if not count:
            return False,"No observations are available at the displayed planning time."
        if method=="Constant velocity" and count<2:
            return False,"Constant velocity needs at least two distinct observed timestamps."
        if method=="Sinusoidal fit":
            if self.needle_prediction_history.value()<20 or times[count-1]-times[0]<20-1e-8 or count<12:
                return False,"Sinusoidal fit needs at least 20 sampled seconds and 12 observations; set prediction history to at least 20 s."
            if .6/data.settings.rate_hz>=.5:
                return False,"Sampling is too sparse for the 6–36 breaths/min sinusoidal search."
        key=(id(data),self.motion_time,method,self.needle_prediction_history.value())
        if self._needle_prediction_error is not None and self._needle_prediction_error[0]==key:
            return False,self._needle_prediction_error[1]
        return True,(f"{count} past samples · last {times[count-1]:g} s. "
                     "Arrival is solved from delay, speed and predicted path length, within 5 s.")

    def _update_needle_prediction_controls(self):
        if not hasattr(self,"needle_prediction_readout"):
            return
        can_predict=self.needle_targeting_method.currentText()!="Displayed centre" and bool(self.needle_exclusions)
        self.needle_exclusion_policy.setEnabled(can_predict)
        if not can_predict and self.needle_exclusion_policy.currentText()!="Current geometry":
            self.needle_exclusion_policy.blockSignals(True)
            self.needle_exclusion_policy.setCurrentText("Current geometry")
            self.needle_exclusion_policy.blockSignals(False)
        ready,text=self._needle_prediction_ready()
        self.needle_prediction_readout.setText(text)
        self.needle_build.setText("Build path to displayed target centre" if self.needle_targeting_method.currentText()=="Displayed centre"
                                  else "Build path to predicted arrival centre")
        self.needle_prediction_history.setEnabled(self.needle_targeting_method.currentText()=="Sinusoidal fit")
        available=self.motion_active and self.target is not None and self.needle_entry_reference is not None and ready
        self.needle_build.setEnabled(available)
        self.needle_search.setEnabled(available)

    def _needle_constraint_controls(self,layout):
        body=QVBoxLayout()
        note=QLabel("User-defined exclusion regions are simulated constraints, not detected vessels or validated anatomy. They follow the same deformation as the scan.")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(note)
        form=QFormLayout()
        self.needle_exclusion_radius=self.spin(1,25,8,1)
        self.needle_exclusion_radius.setSuffix(" mm")
        self.needle_exclusion_radius.setToolTip("Radius in the reference CT. The simulated sphere becomes an ellipsoid under the shared deformation.")
        form.addRow("New region radius",self.needle_exclusion_radius)
        body.addLayout(form)
        self.needle_exclusion_add=QToolButton()
        self.needle_exclusion_add.setText("Add exclusion at crosshair")
        self.needle_exclusion_add.setEnabled(False)
        self.needle_exclusion_add.clicked.connect(self.add_needle_exclusion)
        body.addWidget(self.needle_exclusion_add)
        self.needle_exclusion_list=QTreeWidget()
        self.needle_exclusion_list.setColumnCount(2)
        self.needle_exclusion_list.setHeaderLabels(["Simulated region","Radius mm"])
        self.needle_exclusion_list.setRootIsDecorated(False)
        self.needle_exclusion_list.setFixedHeight(105)
        self.needle_exclusion_list.header().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.needle_exclusion_list.header().setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed)
        self.needle_exclusion_list.setColumnWidth(1,80)
        self.needle_exclusion_list.currentItemChanged.connect(lambda item,previous:
            self.needle_exclusion_remove.setEnabled(item is not None))
        body.addWidget(self.needle_exclusion_list)
        buttons=QHBoxLayout()
        for field,label,callback in (("needle_exclusion_remove","Remove selected",self.remove_needle_exclusion),
                                     ("needle_exclusion_clear","Clear exclusions",self.clear_needle_exclusions)):
            button=QToolButton()
            button.setText(label)
            button.setEnabled(False)
            button.clicked.connect(callback)
            setattr(self,field,button)
            buttons.addWidget(button,1)
        body.addLayout(buttons)
        form=QFormLayout()
        self.needle_exclusion_policy=QComboBox()
        self.needle_exclusion_policy.addItems(EXCLUSION_POLICIES)
        self.needle_exclusion_policy.setEnabled(False)
        self.needle_exclusion_policy.setToolTip("Current geometry screens the full route now. Predicted motion also screens the inserted shaft throughout execution using past target observations and the declared shared affine field.")
        self.needle_exclusion_policy.currentTextChanged.connect(self._needle_parameters_changed)
        form.addRow("Exclusion screening",self.needle_exclusion_policy)
        self.needle_clearance=self.spin(0,10,2,.5,decimals=2)
        self.needle_clearance.setSuffix(" mm")
        self.needle_search_radius=self.spin(0,20,8,1)
        self.needle_search_radius.setSuffix(" mm")
        self.needle_search_radius.setToolTip("Disk radius in reference CT millimetres, transformed with the manually designated entry patch.")
        for label,control in (("Required clearance",self.needle_clearance),("Entry patch radius",self.needle_search_radius)):
            form.addRow(label,control)
            control.valueChanged.connect(self._needle_parameters_changed)
        body.addLayout(form)
        note=QLabel("Search a bounded flat patch around the manual entry. Entries outside the CT or inside lung masks are rejected. The patch is a designated geometric surface, not a detected skin surface.")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(note)
        self.needle_search=QToolButton()
        self.needle_search.setText("Find shortest feasible entry")
        self.needle_search.setEnabled(False)
        self.needle_search.clicked.connect(self.search_needle_entries)
        body.addWidget(self.needle_search)
        self.needle_route_table=QTreeWidget()
        self.needle_route_table.setColumnCount(4)
        self.needle_route_table.setHeaderLabels(["Entry","Length","Bound","Status"])
        self.needle_route_table.setRootIsDecorated(False)
        self.needle_route_table.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.needle_route_table.setFixedHeight(160)
        self.needle_route_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.needle_route_table.header().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for column,width in ((1,55),(2,55),(3,68)):
            self.needle_route_table.header().setSectionResizeMode(column,QHeaderView.ResizeMode.Fixed)
            self.needle_route_table.setColumnWidth(column,width)
        self.needle_route_table.setToolTip("Entries and exclusions use planning-time geometry; observed target methods predict each entry's arrival endpoint. Length and conservative clearance bounds are in mm. Negative bounds mean rejection or unresolved clearance, not an exact penetration distance.")
        body.addWidget(self.needle_route_table)
        self.needle_route_readout=QLabel("No candidate routes checked.")
        self.needle_route_readout.setWordWrap(True)
        self.needle_route_readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        body.addWidget(self.needle_route_readout)
        self.needle_route_export=QToolButton()
        self.needle_route_export.setText("Export route check CSV…")
        self.needle_route_export.setEnabled(False)
        self.needle_route_export.clicked.connect(self.export_needle_route_check)
        body.addWidget(self.needle_route_export)
        layout.addWidget(group("Route constraints",body))

    def _needle_route_settings(self):
        return RouteSettings(patch_radius_mm=self.needle_search_radius.value(),clearance_mm=self.needle_clearance.value())

    def _needle_constraints_key(self):
        return self.needle_exclusions,self.needle_clearance.value()

    def _rebuild_exclusion_list(self):
        self.needle_exclusion_list.clear()
        for index,region in enumerate(self.needle_exclusions):
            row=QTreeWidgetItem([region.name,f"{region.radius_mm:g}"])
            row.setData(0,Qt.ItemDataRole.UserRole,index)
            text="Reference LPS: "+", ".join(f"{value:+.2f}" for value in region.center_lps_mm)+" mm"
            row.setToolTip(0,text)
            self.needle_exclusion_list.addTopLevelItem(row)
        self.needle_exclusion_clear.setEnabled(bool(self.needle_exclusions))
        self.needle_exclusion_remove.setEnabled(False)

    def add_needle_exclusion(self):
        if not self.motion_active or self.worker is not None:
            return
        if len(self.needle_exclusions)>=8:
            self.status.setText("Use at most eight simulated exclusion regions.")
            return
        self.pause_motion()
        reference=self.deformation.inverse(self.crosshair,self.motion_model.position(self.motion_time))
        names={region.name for region in self.needle_exclusions}
        name=next(f"Exclusion {index}" for index in range(1,10) if f"Exclusion {index}" not in names)
        try:
            region=create_exclusion_region(self.volume,reference,self.needle_exclusion_radius.value(),name)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self._invalidate_needle_plan()
        self.needle_exclusions=(*self.needle_exclusions,region)
        self._needle_exclusions_volume=self.volume
        self._rebuild_exclusion_list()
        self.refresh()
        self.status.setText("Added a simulated exclusion region. Red contours are modelled constraints, not anatomical segmentations.")

    def remove_needle_exclusion(self):
        item=self.needle_exclusion_list.currentItem()
        if item is None or self.worker is not None:
            return
        index=item.data(0,Qt.ItemDataRole.UserRole)
        self._invalidate_needle_plan()
        self.needle_exclusions=tuple(region for i,region in enumerate(self.needle_exclusions) if i!=index)
        self._rebuild_exclusion_list()
        self.refresh()

    def clear_needle_exclusions(self):
        if self.worker is not None:
            return
        self._invalidate_needle_plan()
        self.needle_exclusions=()
        self._needle_exclusions_volume=None
        self._rebuild_exclusion_list()
        self.refresh()

    def _route_context_matches(self,context):
        return (context is not None and self.ct_sequence is None and self.volume is context["volume"]
            and self.target is context["target"] and self.motion_model is not None
            and respiratory_model_id(self.motion_model)==context["model_id"]
            and self.deformation==context["deformation"] and self._needle_settings()==context["needle_settings"]
            and self._needle_route_settings()==context["route_settings"]
            and self.needle_entry_reference==context["entry_reference"]
            and self._needle_lung_key()==context["mask_key"] and self.needle_exclusions==context["exclusions"]
            and self.needle_targeting_method.currentText()==context["targeting_method"]
            and self._needle_exclusion_policy()==context["exclusion_policy"]
            and (context["observations"] is None or
                 self.target_observations is context["observations"]
                 and self._observation_settings()==context["observations"].settings
                 and self._needle_forecast_settings()==context["forecast_settings"]))

    def _needle_parameters_changed(self,*args):
        self._invalidate_needle_plan()
        if hasattr(self,"scene"):
            self._update_needle_display()

    def _invalidate_needle_plan(self,*args):
        self.pause_needle()
        had_plan=self.needle_plan is not None
        self._needle_generation+=1
        self.needle_plan=self.needle_evaluation=None
        self._needle_plan_volume=None
        self._needle_plan_mask_key=None
        self._needle_plan_constraint_key=None
        self.needle_route_selection=self.needle_constraint_evaluation=None
        if self._needle_results_dialog is not None:
            self._needle_results_dialog.invalidate()
        self._needle_route_context=None
        self._needle_prediction_error=None
        if hasattr(self,"needle_play"):
            for widget in (self.needle_play,self.needle_reset,self.needle_depth,self.needle_export,self.needle_results):
                widget.setEnabled(False)
            self.needle_depth.blockSignals(True)
            self.needle_depth.setValue(0)
            self.needle_depth.blockSignals(False)
            self.needle_plan_readout.setText("No path built.")
            self.needle_readout.setText("Build a path to preview insertion.")
            self.needle_result_readout.setText("No insertion evaluated.")
            self.needle_route_table.clear()
            self.needle_route_readout.setText("No candidate routes checked.")
            self.needle_route_export.setEnabled(False)
        if hasattr(self,"scene"):
            self.scene.set_needle(None)
            for view in self.slices:
                view.canvas.set_needle(None,0.,0.)
                view.canvas.set_needle_arrival(None,0.)
            if had_plan:
                self.scene.render()

    def set_needle_entry(self):
        if not self.motion_active or self.target is None or self.worker is not None:
            return
        self.pause_motion()
        reference=self.deformation.inverse(self.crosshair,self.motion_model.position(self.motion_time))
        try:
            reference=validate_needle_entry(self.volume,self._lung_target_mask(),reference)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self._invalidate_needle_plan()
        self.needle_entry_reference=reference
        self._needle_entry_volume=self.volume
        self._update_needle_display()
        self.status.setText("Manual entry selected inside the CT and outside lung masks. Confirm its chest-wall location visually.")

    def clear_needle_entry(self):
        self._invalidate_needle_plan()
        self.needle_entry_reference=self._needle_entry_volume=None
        self._update_needle_display()

    def go_to_needle_entry(self):
        if self.needle_entry_reference is None or not self.motion_active or self.worker is not None:
            return
        self.pause_motion()
        point=(np.asarray(self.needle_plan.entry_lps_mm) if self.needle_plan is not None else
               self.deformation.forward(self.needle_entry_reference,self.motion_model.position(self.motion_time)))
        self.set_crosshair(point)

    def _needle_context_matches(self,plan):
        return (self.ct_sequence is None and self.volume is self._needle_plan_volume
                and self._needle_plan_mask_key==self._needle_lung_key()
                and self._needle_plan_constraint_key==self._needle_constraints_key()
                and (self._needle_route_context is None or self._route_context_matches(self._needle_route_context))
                and self.target is plan.target and self.motion_model is not None
                and self.deformation==plan.deformation and self._needle_settings()==plan.settings
                and respiratory_model_id(self.motion_model)==plan.model_id)

    def _needle_lung_key(self):
        return tuple((name,id(mask)) for name,mask in self.masks.items()
                     if self.structures[name].kind=="lung")

    def build_needle_plan(self):
        self._build_needle_route(search=False)

    def search_needle_entries(self):
        self._build_needle_route(search=True)

    def _build_needle_route(self,*,search):
        if (not self.motion_active or self.target is None or self.needle_entry_reference is None
                or self.worker is not None):
            return
        ready,message=self._needle_prediction_ready()
        if not ready:
            self._update_needle_prediction_controls()
            self.status.setText(message)
            return
        self.pause_motion()
        generation=self._needle_generation
        target,model,volume=self.target,self.motion_model,self.volume
        deformation,settings,origin=self.deformation,self._needle_settings(),self.motion_time
        reference=self.needle_entry_reference
        entry=deformation.forward(reference,model.position(origin))
        mask=self._lung_target_mask()
        mask_key=self._needle_lung_key()
        exclusions=self.needle_exclusions
        route_settings=self._needle_route_settings()
        targeting_method=self.needle_targeting_method.currentText()
        exclusion_policy=self._needle_exclusion_policy()
        observations=self.target_observations if targeting_method!="Displayed centre" else None
        forecast_settings=self._needle_forecast_settings() if observations is not None else None
        past_times,past_positions=(observations.observations_through(origin) if observations is not None else (None,None))
        context=dict(volume=volume,target=target,model_id=respiratory_model_id(model),
            deformation=deformation,needle_settings=settings,route_settings=route_settings,
            entry_reference=reference,mask_key=mask_key,exclusions=exclusions,planning_time_s=origin,search=search,
            targeting_method=targeting_method,observations=observations,forecast_settings=forecast_settings,
            exclusion_policy=exclusion_policy)
        used_settings=RouteSettings(patch_radius_mm=route_settings.patch_radius_mm if search else 0.,
                                    clearance_mm=route_settings.clearance_mm)
        matrix=deformation.matrix(model.position(origin))
        def build():
            selection=None
            chosen_entry=entry
            if observations is not None:
                try:
                    fit=fit_baseline(past_times,past_positions,targeting_method,origin_s=origin,settings=forecast_settings)
                except ValueError as error:
                    return None,None,None,None,str(error)
                try:
                    selection=select_forecast_route(volume,mask,target,reference,matrix,fit,settings,
                        exclusions,used_settings,available_until_s=model.duration,
                        exclusion_policy=exclusion_policy,deformation=deformation)
                except ValueError as error:
                    if exclusion_policy!="Predicted motion":
                        raise
                    return None,None,None,None,str(error)
                if selection.chosen_index is None:
                    return None,None,selection,None,None
                plan=create_forecast_needle_plan(selection,context["model_id"],deformation)
            elif search or exclusions:
                # candidate ranking receives current geometry only; future motion is evaluated after selection.
                selection=select_geometric_route(volume,mask,target,reference,matrix,settings,
                    exclusions,used_settings,planning_time_s=origin,available_until_s=model.duration)
                if selection.chosen_index is None:
                    return None,None,selection,None,None
                chosen_entry=selection.chosen_entry_lps_mm
                plan=create_needle_plan(volume,mask,target,deformation,model,chosen_entry,settings,planning_time_s=origin)
            else:
                plan=create_needle_plan(volume,mask,target,deformation,model,chosen_entry,settings,planning_time_s=origin)
            # execution truth is queried only after the causal endpoint and entry have been selected.
            evaluation=evaluate_needle(plan,model)
            constraints=(evaluate_needle_constraints(plan,model,exclusions,clearance_mm=used_settings.clearance_mm)
                         if exclusions else None)
            return plan,evaluation,selection,constraints,None
        def accepted(result):
            plan,evaluation,selection,constraints,error=result
            if (generation!=self._needle_generation or self.volume is not volume or self.target is not target
                    or self.motion_model is not model or self.deformation!=deformation or self.motion_time!=origin
                    or self.needle_entry_reference!=reference or settings!=self._needle_settings()
                    or self._needle_lung_key()!=mask_key
                    or not self._route_context_matches(context)):
                return
            self._invalidate_needle_plan()
            if error is not None:
                key=(id(observations),origin,targeting_method,self.needle_prediction_history.value())
                self._needle_prediction_error=(key,error)
                self._update_needle_display()
                self.status.setText("Selected prediction or exclusion screening unavailable: "+error)
                return
            self.needle_plan,self.needle_evaluation=plan,evaluation
            self.needle_route_selection=selection
            self.needle_constraint_evaluation=constraints
            self._needle_route_context=context if selection is not None else None
            if plan is not None:
                self._needle_plan_volume=volume
                self._needle_plan_mask_key=mask_key
                self._needle_plan_constraint_key=self._needle_constraints_key()
            self._update_route_display()
            self._update_needle_display()
            self.scene.render()
            self.status.setText("No candidate satisfies the arrival and declared screening constraints. No insertion was selected."
                if plan is None and observations is not None else
                "No candidate satisfies the declared current-geometry constraints. No insertion was selected."
                if plan is None else "Arrival-aware route selected from past observations; simulated execution evaluated separately."
                if observations is not None else "Geometric route selected using current anatomy; target and exclusion motion evaluated separately."
                if selection is not None else "Finite manual needle path built. Insertion evaluated against the moving target, independently of display frames.")
        self.task(build,accepted,"Checking finite routes and evaluating the selected insertion…")

    def _update_route_display(self):
        selection=self.needle_route_selection
        self.needle_route_table.clear()
        if selection is None:
            return
        chosen_item=None
        fit=getattr(selection,"fit",None)
        for row in selection.rows:
            bound=row["clearance_lower_bound_mm"]
            length=row["length_mm"]
            item=QTreeWidgetItem([str(row["index"]+1),"—" if length is None else f"{length:.2f}",
                "—" if bound is None else f"{bound:.2f}","Chosen" if row["chosen"] else
                "Eligible" if row["status"]=="eligible" else "Rejected"])
            tip="LPS: "+", ".join(f"{value:+.2f}" for value in row["entry_lps_mm"])+" mm\n"+row["reason"]
            if bound is not None:
                tip+=f"\nConservative clearance bound: {bound:.6f} mm"
            if fit is not None and row["endpoint_lps_mm"] is not None:
                tip+=(f"\nPrediction {row['prediction_time_s']:.6f} s · physical arrival {row['arrival_s']:.6f} s"
                    "\nEndpoint LPS: "+", ".join(f"{value:+.4f}" for value in row["endpoint_lps_mm"])
                    +f" mm\nArrival residual: {row['intercept_residual_mm']:.3g} mm")
                predicted_bound=row.get("predicted_clearance_lower_bound_mm")
                if predicted_bound is not None:
                    tip+=f"\nPredicted insertion clearance bound: {predicted_bound:.6f} mm at {row['predicted_clearance_time_s']:.6f} s"
                if row.get("predicted_screening_reason"):
                    tip+="\n"+row["predicted_screening_reason"]
            for column in range(4):
                item.setToolTip(column,tip)
            self.needle_route_table.addTopLevelItem(item)
            if row["chosen"]:
                chosen_item=item
        if chosen_item is not None:
            self.needle_route_table.scrollToItem(chosen_item)
        eligible=sum(row["status"]=="eligible" for row in selection.rows)
        text=f"Planning time {selection.planning_time_s:g} s · {eligible} / {len(selection.rows)} eligible entries\n"
        if selection.chosen_index is None:
            text+=("Abstained: no candidate meets arrival, image-coverage and declared screening constraints." if fit is not None else
                   "Abstained: no candidate meets the declared geometry and clearance constraints.")
        else:
            text+=f"Entry {selection.chosen_index+1}: shortest eligible path; clearance and index break ties."
        if fit is not None:
            text+=f"\n{fit.method} · {fit.n_samples} fit samples · last observation {fit.last_observation_s:g} s."
            if selection.chosen_index is not None:
                chosen=selection.rows[selection.chosen_index]
                text+=f"\nPredicted arrival {chosen['arrival_s']:.4f} s · look ahead {chosen['horizon_s']:.4f} s."
        text+=(f"\nRequired surface clearance: {selection.route_settings.clearance_mm:g} mm. "
               "Bounds include the physical needle radius."
               if selection.exclusions else "\nNo exclusion regions specified: obstacle clearance is not assessed.")
        predicted=getattr(selection,"predicted_constraint_evaluation",None)
        if getattr(selection,"exclusion_policy","Current geometry")=="Predicted motion":
            text+="\nPredicted motion: past target changes transferred to exclusions through the declared affine field, anchored at current geometry."
            if predicted is not None:
                text+=f"\nPredicted minimum insertion bound {predicted.min_clearance_lower_bound_mm:.4f} mm at {predicted.min_clearance_time_s:.4f} s."
            text+="\nNumerical prediction screen; actual execution is evaluated separately."
        else:
            text+=("\nTarget predicted from past observations; exclusions screened at planning time. Execution truth evaluated after selection."
                   if fit is not None else "\nCurrent geometry only; later motion is evaluated separately.")
        self.needle_route_readout.setText(text)
        self.needle_route_export.setEnabled(True)

    def pause_needle(self):
        was_playing=self.needle_timer.isActive()
        self.needle_timer.stop()
        if hasattr(self,"needle_play"):
            self.needle_play.setText("Play insertion")
        if was_playing:
            self._sync_needle_results()

    def toggle_needle_preview(self):
        plan=self.needle_plan
        if self.needle_timer.isActive():
            self.pause_needle()
            return
        if plan is None or not self.motion_active or self.worker is not None or not self._needle_context_matches(plan):
            return
        self.pause_motion()
        self._invalidate_forecasts()
        if not plan.planning_time_s<=self.motion_time<plan.arrival_s:
            self.motion_time=plan.planning_time_s
            self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
            self.refresh()
        self._needle_anchor=perf_counter()-self.motion_time
        self.needle_timer.start()
        self.needle_play.setText("Pause insertion")
        self._sync_needle_results()

    def _needle_tick(self):
        plan=self.needle_plan
        if not self.needle_timer.isActive() or plan is None or not self.motion_active:
            return
        if not self._needle_context_matches(plan):
            self._invalidate_needle_plan()
            return
        self.motion_time=min(plan.arrival_s,perf_counter()-self._needle_anchor)
        self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
        if self.motion_time>=plan.arrival_s:
            self.pause_needle()
        self.refresh()

    def restart_needle_preview(self):
        if self.needle_plan is None or self.worker is not None or not self.motion_active:
            return
        self.pause_motion()
        self._invalidate_forecasts()
        self.motion_time=self.needle_plan.planning_time_s
        self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
        self.refresh()

    def _needle_depth_changed(self,value):
        plan=self.needle_plan
        if plan is None or self.worker is not None or not self.motion_active:
            return
        self.pause_motion()
        self._invalidate_forecasts()
        self.motion_time=(plan.arrival_s if value==1000 else
                          plan.start_s+plan.length_mm*value/1000./plan.settings.speed_mm_s)
        self._show_motion_settings(self.motion_model.settings_at(self.motion_time))
        self.refresh()

    def _update_needle_display(self):
        if self._needle_exclusions_volume is not None and self._needle_exclusions_volume is not self.volume:
            self._invalidate_needle_plan()
            self.needle_exclusions=()
            self._needle_exclusions_volume=None
            self._rebuild_exclusion_list()
        if self._needle_entry_volume is not None and self._needle_entry_volume is not self.volume:
            self._invalidate_needle_plan()
            self.needle_entry_reference=self._needle_entry_volume=None
        if self._needle_route_context is not None and not self._route_context_matches(self._needle_route_context):
            self._invalidate_needle_plan()
        plan=self.needle_plan
        if plan is not None and not self._needle_context_matches(plan):
            self._invalidate_needle_plan()
            plan=None
        available=self.motion_active and self.target is not None
        self.needle_entry_set.setEnabled(available)
        self.needle_entry_go.setEnabled(available and self.needle_entry_reference is not None)
        self.needle_entry_clear.setEnabled(self.needle_entry_reference is not None)
        self.needle_benchmark.setEnabled(available and self.needle_entry_reference is not None)
        self._update_needle_prediction_controls()
        self.needle_exclusion_add.setEnabled(self.motion_active and len(self.needle_exclusions)<8)
        self.scene.set_exclusions(self.needle_exclusions)
        matrix=self._motion_matrix()
        for view in self.slices:
            view.canvas.set_exclusions(self.needle_exclusions,matrix)
        self.needle_scope_note.setText("The rigid path stays fixed while anatomy moves. Target outcomes use the tip centre and finite inserted centreline. "
            +("Declared exclusion bounds include physical needle radius and margin; they are conservative bounds, not exact collision depths. "
              "Screening uses current geometry and optionally predicted exclusion motion; actual execution is evaluated separately. " if self.needle_exclusions else
              "No exclusion regions are specified; obstacle clearance is not assessed. ")
            +"Regions and entry patches are simulated geometry. Observation-based forecasts use a five-second limit and assume the declared shared affine motion. Numerical screening is not a continuous clearance guarantee. Clinical safety and skin detection are not assessed.")
        if self.needle_entry_reference is None:
            self.needle_entry_readout.setText("No entry selected. Select a chest-wall location outside the lung masks in the CT views.")
        else:
            point=(np.asarray(plan.entry_lps_mm) if plan is not None else
                   self.deformation.forward(self.needle_entry_reference,self.motion_model.position(self.motion_time))
                   if self.motion_active else np.asarray(self.needle_entry_reference))
            self.needle_entry_readout.setText("Entry LPS: "+", ".join(f"{x:+.2f}" for x in point)+" mm\nManual selection · chest-wall location unverified")
        visible=plan is not None and self.motion_active and self.motion_time>=plan.planning_time_s
        depth=plan.depth_at(self.motion_time) if visible else 0.
        self.scene.set_needle(plan if visible else None,depth)
        fit=getattr(self.needle_route_selection,"fit",None)
        arrival_point=(np.asarray(plan.endpoint_lps_mm) if visible and fit is not None and self.controls.currentIndex()==3 else None)
        self.scene.set_needle_arrival(arrival_point)
        for view in self.slices:
            tolerance=(.5/np.linalg.norm(self.volume.direction[view.axis]/self.volume.spacing)
                       if self.volume is not None else 0.)
            view.canvas.set_needle(plan if visible else None,depth,tolerance)
            view.canvas.set_needle_arrival(arrival_point,tolerance)
        for widget in (self.needle_play,self.needle_reset,self.needle_depth):
            widget.setEnabled(plan is not None and self.motion_active)
        self.needle_export.setEnabled(self.needle_evaluation is not None and plan is not None)
        self.needle_results.setEnabled(self.needle_evaluation is not None and plan is not None)
        self._sync_needle_results()
        if plan is None:
            return
        self.needle_depth.blockSignals(True)
        self.needle_depth.setValue(round(1000*depth/plan.length_mm))
        self.needle_depth.blockSignals(False)
        text=(f"Path {plan.length_mm:.2f} mm · frozen at {plan.planning_time_s:g} s\n"
            f"Start {plan.start_s:.3f} s → arrival {plan.arrival_s:.3f} s\nEndpoint LPS: "+
            ", ".join(f"{x:+.2f}" for x in plan.endpoint_lps_mm)+" mm")
        if fit is not None:
            text+=f"\n{fit.method} · last observed {fit.last_observation_s:g} s\nCyan: planned arrival centre · amber: actual target now"
        self.needle_plan_readout.setText(text)
        if visible:
            state=evaluate_needle_state(plan,self.motion_model,self.motion_time)
            phase="Waiting for execution" if self.motion_time<plan.start_s else "Insertion complete" if self.motion_time>=plan.arrival_s else "Inserting"
            self.needle_readout.setText(f"{phase} · {self.motion_time:.3f} s\nDepth {depth:.2f} / {plan.length_mm:.2f} mm\n"
                f"Tip-to-target-centre distance: {state['tip_error_mm']:.3f} mm\n"
                f"Tip centre inside target: {'Yes' if state['tip_normalized_distance']<=1+1e-9 else 'No'}\n"
                f"Inserted centreline intersects target: {'Yes' if state['shaft_normalized_distance']<=1+1e-9 else 'No'}")
        else:
            self.needle_readout.setText("Path hidden outside Motion/Needle or before the planning instant. Restart to replay this insertion.")
        result=self.needle_evaluation
        if result is not None:
            contact=lambda t:"Not found" if t is None else f"{t:.4f} s"
            text=(f"INSERTION INTERVAL · {plan.start_s:.3f}–{plan.arrival_s:.3f} s\n"
                f"Arrival tip-centre error: {result.arrival_tip_error_mm:.3f} mm\n"
                f"Minimum tip-centre error: {result.min_tip_error_mm:.3f} mm\n"
                f"First tip-centre contact: {contact(result.first_tip_hit_s)}\n"
                f"First finite-centreline contact: {contact(result.first_shaft_hit_s)}\n"
                f"Numerical evaluation: {result.step_s*1000:g} ms grid with contact refinement")
            constraints=self.needle_constraint_evaluation
            predicted=getattr(self.needle_route_selection,"predicted_constraint_evaluation",None)
            if predicted is not None:
                text+=(f"\nPREDICTED EXCLUSION SCREEN\nMinimum predicted bound: {predicted.min_clearance_lower_bound_mm:.3f} mm\n"
                    "Anchored shared affine forecast from past observations; numerical screening only.")
            if constraints is None:
                text+="\nObstacles / safety: not assessed"
            else:
                text+=(f"\nACTUAL EXCLUSION EXECUTION CHECK · {len(constraints.exclusions)} simulated regions\n"
                    f"Minimum clearance bound: {constraints.min_clearance_lower_bound_mm:.3f} mm\n"
                    f"Required clearance: {constraints.clearance_mm:g} mm\n"
                    f"Constraint violation: {'Found' if constraints.violated else 'Not found numerically'}\n"
                    f"First violation: {contact(constraints.first_violation_s)}\n"
                    "Future motion is evaluated after selection; candidates are not reranked using this result.\nClinical safety: not assessed")
            self.needle_result_readout.setText(text)

    def _needle_method_name(self,context):
        if context is not None and context["observations"] is not None:
            return {"Constant position":"observed_constant_position","Constant velocity":"constant_velocity_arrival",
                    "Sinusoidal fit":"sinusoidal_arrival"}[context["targeting_method"]]
        return ("geometric_entry_search" if context is not None and context["search"] else
                "manual_displayed_centre_constrained" if self.needle_constraint_evaluation is not None else "manual_displayed_centre")

    def _needle_forecast_metadata(self,selection,context):
        fit=getattr(selection,"fit",None)
        if fit is None:
            return dict(forecasting_method="not_used",fit_origin_s="",fit_history_window_s="",fit_velocity_window_s="",
                fit_min_rate_bpm="",fit_max_rate_bpm="",fit_history_start_s="",last_observation_s="",fit_n_samples="",
                fitted_frequency_hz="",intercept_limit_s="",observation_prefix_count="",observation_rate_hz="",
                observation_noise_std_mm="",recorded_through_s="")
        data=context["observations"]
        times,_=data.observations_through(fit.origin_s)
        return dict(forecasting_method=fit.method,fit_origin_s=fit.origin_s,fit_history_window_s=fit.settings.history_window_s,
            fit_velocity_window_s=fit.settings.velocity_window_s,fit_min_rate_bpm=fit.settings.min_rate_bpm,
            fit_max_rate_bpm=fit.settings.max_rate_bpm,fit_history_start_s=fit.history_start_s,
            last_observation_s=fit.last_observation_s,fit_n_samples=fit.n_samples,
            fitted_frequency_hz=fit.frequency_hz if fit.frequency_hz is not None else "",intercept_limit_s=5.,
            observation_prefix_count=len(times),observation_rate_hz=data.settings.rate_hz,
            observation_noise_std_mm=data.settings.noise_std_mm,recorded_through_s=data.through_s)

    def _needle_screening_metadata(self,selection,context):
        predicted=getattr(selection,"predicted_constraint_evaluation",None)
        policy=getattr(selection,"exclusion_policy","Current geometry")
        transfer=policy=="Predicted motion" and bool(selection.exclusions)
        deformation=context["deformation"] if transfer else None
        target=selection.target if transfer else None
        return dict(exclusion_screening_policy=policy,predicted_exclusions_assessed=predicted is not None,
            predicted_clearance_lower_bound_mm=predicted.min_clearance_lower_bound_mm if predicted is not None else "",
            predicted_clearance_time_s=predicted.min_clearance_time_s if predicted is not None else "",
            predicted_first_violation_s=predicted.first_violation_s if predicted is not None else "",
            predicted_evaluation_step_s=predicted.step_s if predicted is not None else "",
            exclusion_motion_transfer="anchored_target_forecast_shared_affine" if transfer else "not_used",
            predicted_anchor_matrix_json=json.dumps(selection.matrix.tolist(),separators=(",",":")) if transfer else "",
            motion_reference_base_z_mm=deformation.base_z if transfer else "",
            motion_reference_apex_z_mm=deformation.apex_z if transfer else "",
            motion_transfer_target_weight=(deformation.apex_z-target.center_lps_mm[2])/deformation.height if transfer else "",
            target_reference_l_mm=target.center_lps_mm[0] if transfer else "",
            target_reference_p_mm=target.center_lps_mm[1] if transfer else "",
            target_reference_s_mm=target.center_lps_mm[2] if transfer else "")

    def export_needle_evaluation(self):
        plan,result=self.needle_plan,self.needle_evaluation
        if plan is None or result is None or self.worker is not None:
            return
        if not self._needle_context_matches(plan):
            self._invalidate_needle_plan()
            self.status.setText("The scenario changed. Rebuild the insertion before exporting.")
            return
        path,_=QFileDialog.getSaveFileName(self,"Export simulated needle evaluation","needle-evaluation.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        temporary=None
        try:
            def check_current():
                if (self.needle_plan is not plan or self.needle_evaluation is not result
                        or not self._needle_context_matches(plan)):
                    raise ValueError("The insertion changed during export. Rebuild it before exporting.")
            check_current()
            protected=self._protected_export_paths()
            path=check_export_destination(path,protected)
            context=self._needle_route_context
            constraints=self.needle_constraint_evaluation
            method=self._needle_method_name(context)
            selection=self.needle_route_selection
            fit=getattr(selection,"fit",None)
            chosen=selection.rows[selection.chosen_index] if fit is not None else None
            metadata=dict(format_version=1,method=method,
                endpoint_basis="predicted_target_at_needle_arrival" if fit is not None else "current_displayed_target_centre",
                selection_used_future_truth=False,prediction_time_s=chosen["prediction_time_s"] if chosen is not None else "",
                prediction_horizon_s=chosen["horizon_s"] if chosen is not None else "",
                intercept_residual_mm=chosen["intercept_residual_mm"] if chosen is not None else "",
                outcome_definition="tip_centre_and_finite_inserted_centreline",
                obstacles_assessed=constraints is not None,needle_radius_used_in_outcome=constraints is not None,
                needle_radius_used_in_target_outcome=False,needle_radius_used_in_obstacle_constraint=constraints is not None,
                constraint_method="affine_sigma_min_finite_segment_lower_bound" if constraints is not None else "not_assessed",
                required_clearance_mm=constraints.clearance_mm if constraints is not None else "",
                min_execution_clearance_lower_bound_mm=constraints.min_clearance_lower_bound_mm if constraints is not None else "",
                first_constraint_violation_s=constraints.first_violation_s if constraints is not None else "",
                constraint_violation=constraints.violated if constraints is not None else "",
                clinical_safety_assessed=False,
                exclusions_json=self._exclusions_json(self.needle_exclusions),
                study_id=plan.target.study_id,model_id=plan.model_id,target_name=plan.target.name,
                target_radius_reference_mm=plan.target.radius_mm,planning_time_s=plan.planning_time_s,
                execution_start_s=plan.start_s,arrival_s=plan.arrival_s,path_length_mm=plan.length_mm,
                needle_radius_mm=plan.settings.radius_mm,speed_mm_s=plan.settings.speed_mm_s,
                delay_s=plan.settings.delay_s,evaluation_step_s=result.step_s,
                entry_l_mm=plan.entry_lps_mm[0],entry_p_mm=plan.entry_lps_mm[1],entry_s_mm=plan.entry_lps_mm[2],
                endpoint_l_mm=plan.endpoint_lps_mm[0],endpoint_p_mm=plan.endpoint_lps_mm[1],endpoint_s_mm=plan.endpoint_lps_mm[2])
            metadata.update(self._needle_forecast_metadata(selection,context))
            metadata.update(self._needle_screening_metadata(selection,context))
            fields=[*metadata,"record_kind","time_s","in_execution_interval","depth_mm",
                "tip_l_mm","tip_p_mm","tip_s_mm","true_target_l_mm","true_target_p_mm","true_target_s_mm",
                "tip_error_mm","tip_normalized_distance","shaft_normalized_distance",
                "tip_centre_inside_target","inserted_centreline_intersects",
                "min_tip_error_mm","min_tip_error_time_s","arrival_tip_error_mm",
                "first_tip_hit_s","first_shaft_hit_s","min_tip_normalized_distance","min_shaft_normalized_distance"]
            summary=dict(metadata,record_kind="interval_summary",min_tip_error_mm=result.min_tip_error_mm,
                min_tip_error_time_s=result.min_tip_error_time_s,arrival_tip_error_mm=result.arrival_tip_error_mm,
                first_tip_hit_s=result.first_tip_hit_s,first_shaft_hit_s=result.first_shaft_hit_s,
                min_tip_normalized_distance=result.min_tip_normalized_distance,
                min_shaft_normalized_distance=result.min_shaft_normalized_distance)
            temporary=path.with_name(f".{path.name}.{uuid4().hex}.part")
            with temporary.open("x",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                writer.writerow(summary)
                for time,depth,tip,target,error,tip_distance,shaft_distance in zip(
                    result.times_s,result.depth_mm,result.tip_lps_mm,result.target_lps_mm,
                    result.tip_error_mm,result.tip_normalized_distance,result.shaft_normalized_distance):
                    row=dict(metadata,record_kind="evaluated_state",time_s=time,
                        in_execution_interval=plan.start_s<=time<=plan.arrival_s,depth_mm=depth,
                        tip_error_mm=error,tip_normalized_distance=tip_distance,shaft_normalized_distance=shaft_distance,
                        tip_centre_inside_target=tip_distance<=1+1e-9,
                        inserted_centreline_intersects=shaft_distance<=1+1e-9)
                    row.update(zip(("tip_l_mm","tip_p_mm","tip_s_mm"),tip))
                    row.update(zip(("true_target_l_mm","true_target_p_mm","true_target_s_mm"),target))
                    writer.writerow(row)
            check_export_destination(path,protected)
            check_current()
            os.replace(temporary,path)
        except (ValueError,OSError) as error:
            self.status.setText(str(error))
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.status.setText(f"Exported simulated needle geometry, timed trace and separate interval/arrival results: {path}")

    def _exclusions_json(self,regions):
        return json.dumps([dict(name=region.name,center_lps_mm=region.center_lps_mm,
            radius_mm=region.radius_mm,study_id=region.study_id,kind=region.kind) for region in regions],separators=(",",":"))

    def export_needle_route_check(self):
        selection,context=self.needle_route_selection,self._needle_route_context
        if selection is None or context is None or self.worker is not None:
            return
        if not self._route_context_matches(context):
            self._invalidate_needle_plan()
            self.status.setText("The route context changed. Check candidate entries again before exporting.")
            return
        path,_=QFileDialog.getSaveFileName(self,"Export route check","route-check.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        temporary=None
        try:
            def check_current():
                if (self.needle_route_selection is not selection or self._needle_route_context is not context
                        or not self._route_context_matches(context)):
                    raise ValueError("The route changed during export. Recheck candidate entries before exporting.")
            check_current()
            protected=self._protected_export_paths()
            path=check_export_destination(path,protected)
            execution=self.needle_constraint_evaluation
            rows=selection.rows
            fit=getattr(selection,"fit",None)
            endpoint=selection.endpoint_lps_mm if selection.endpoint_lps_mm is not None else ("","","")
            chosen=rows[selection.chosen_index] if fit is not None and selection.chosen_index is not None else None
            metadata=dict(format_version=1,method=self._needle_method_name(context),
                endpoint_basis="predicted_target_at_needle_arrival" if fit is not None else "current_displayed_target_centre",selection_used_future_truth=False,
                selected_prediction_time_s=chosen["prediction_time_s"] if chosen is not None else "",
                selected_arrival_s=chosen["arrival_s"] if chosen is not None else "",
                selected_horizon_s=chosen["horizon_s"] if chosen is not None else "",
                selected_intercept_residual_mm=chosen["intercept_residual_mm"] if chosen is not None else "",
                constraint_method="affine_sigma_min_finite_segment_lower_bound",clinical_safety_assessed=False,
                study_id=selection.target.study_id,model_id=context["model_id"],planning_time_s=selection.planning_time_s,
                planning_matrix_json=json.dumps(selection.matrix.tolist(),separators=(",",":")),
                decision="abstained" if selection.chosen_index is None else "selected",
                chosen_candidate_index="" if selection.chosen_index is None else selection.chosen_index+1,
                candidate_count=len(rows),eligible_count=sum(row["status"]=="eligible" for row in rows),
                patch_radius_mm=selection.route_settings.patch_radius_mm,required_clearance_mm=selection.route_settings.clearance_mm,
                needle_radius_mm=selection.needle_settings.radius_mm,speed_mm_s=selection.needle_settings.speed_mm_s,
                delay_s=selection.needle_settings.delay_s,exclusion_count=len(selection.exclusions),
                obstacles_assessed=bool(selection.exclusions),exclusions_json=self._exclusions_json(selection.exclusions),
                execution_checked=execution is not None,
                min_execution_clearance_lower_bound_mm=execution.min_clearance_lower_bound_mm if execution is not None else "",
                first_constraint_violation_s=execution.first_violation_s if execution is not None else "",
                execution_constraint_violated=execution.violated if execution is not None else "",
                evaluation_step_s=execution.step_s if execution is not None else "",
                endpoint_l_mm=endpoint[0],endpoint_p_mm=endpoint[1],endpoint_s_mm=endpoint[2])
            metadata.update(self._needle_forecast_metadata(selection,context))
            metadata.update(self._needle_screening_metadata(selection,context))
            fields=[*metadata,"record_kind","candidate_index","entry_ref_l_mm","entry_ref_p_mm","entry_ref_s_mm",
                "entry_l_mm","entry_p_mm","entry_s_mm","length_mm","clearance_lower_bound_mm","status","reason","chosen",
                "exclusion_name","exclusion_ref_l_mm","exclusion_ref_p_mm","exclusion_ref_s_mm","exclusion_radius_mm",
                "time_s","constraint_violated","prediction_time_s","arrival_s","horizon_s","intercept_residual_mm",
                "observed_l_mm","observed_p_mm","observed_s_mm","predicted_screening_reason"]
            temporary=path.with_name(f".{path.name}.{uuid4().hex}.part")
            with temporary.open("x",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                writer.writerow(dict(metadata,record_kind="route_summary"))
                for candidate in rows:
                    row=dict(metadata,record_kind="candidate",candidate_index=candidate["index"]+1,
                        length_mm=candidate["length_mm"],clearance_lower_bound_mm=candidate["clearance_lower_bound_mm"],
                        status=candidate["status"],reason=candidate["reason"],chosen=candidate["chosen"])
                    row.update(zip(("entry_ref_l_mm","entry_ref_p_mm","entry_ref_s_mm"),candidate["entry_reference"]))
                    row.update(zip(("entry_l_mm","entry_p_mm","entry_s_mm"),candidate["entry_lps_mm"]))
                    if fit is not None:
                        row.update(zip(("endpoint_l_mm","endpoint_p_mm","endpoint_s_mm"),candidate["endpoint_lps_mm"] or ("","","")))
                        for name in ("prediction_time_s","arrival_s","horizon_s","intercept_residual_mm"):
                            row[name]=candidate[name]
                        for name in ("predicted_clearance_lower_bound_mm","predicted_clearance_time_s","predicted_first_violation_s","predicted_screening_reason"):
                            row[name]=candidate.get(name)
                        row["predicted_exclusions_assessed"]=candidate.get("predicted_clearance_lower_bound_mm") is not None
                    writer.writerow(row)
                if fit is not None:
                    times,positions=context["observations"].observations_through(selection.planning_time_s)
                    for time,position in zip(times,positions):
                        row=dict(record_kind="planning_observation",time_s=time)
                        row.update(zip(("observed_l_mm","observed_p_mm","observed_s_mm"),position))
                        writer.writerow(row)
                predicted=getattr(selection,"predicted_constraint_evaluation",None)
                if predicted is not None:
                    for time,bounds in zip(predicted.times_s,predicted.clearance_lower_bounds_mm):
                        for region,bound in zip(predicted.exclusions,bounds):
                            writer.writerow(dict(record_kind="predicted_exclusion_sample",time_s=time,
                                exclusion_name=region.name,clearance_lower_bound_mm=bound,
                                constraint_violated=bound<=predicted.clearance_mm+1e-9))
                for region in selection.exclusions:
                    row=dict(record_kind="exclusion_definition",exclusion_name=region.name,exclusion_radius_mm=region.radius_mm)
                    row.update(zip(("exclusion_ref_l_mm","exclusion_ref_p_mm","exclusion_ref_s_mm"),region.center_lps_mm))
                    writer.writerow(row)
                if execution is not None:
                    for time,bounds in zip(execution.times_s,execution.clearance_lower_bounds_mm):
                        for region,bound in zip(execution.exclusions,bounds):
                            writer.writerow(dict(record_kind="exclusion_execution_sample",time_s=time,
                                exclusion_name=region.name,clearance_lower_bound_mm=bound,
                                constraint_violated=bound<=execution.clearance_mm+1e-9))
            check_export_destination(path,protected)
            check_current()
            os.replace(temporary,path)
        except (ValueError,OSError) as error:
            self.status.setText(str(error))
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.status.setText(f"Exported planning-time candidate decisions and separate execution constraint checks: {path}")

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
        if self.needle_plan is not None and self._needle_context_matches(self.needle_plan):
            points=np.vstack((points,self.needle_plan.entry_lps_mm,self.needle_plan.endpoint_lps_mm))
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
        self._invalidate_forecasts()
        if hasattr(self,"needle_targeting_method") and self.needle_targeting_method.currentText()!="Displayed centre":
            self._invalidate_needle_plan()
            self._update_needle_prediction_controls()
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
            self._invalidate_forecasts()
            if self.needle_targeting_method.currentText()!="Displayed centre":
                self._invalidate_needle_plan()
            self.target_observations=data
            self.observation_plot.set_data(data)
            self.observation_readout.setText(f"{len(data.times_s)} samples · history 0–{data.through_s:g} s\n"
                f"Last sample {data.times_s[-1]:g} s · {settings.rate_hz:g} Hz\n"
                f"Simulated · noise SD {settings.noise_std_mm:g} mm/axis · seed {settings.seed}")
            self.observation_export.setEnabled(True)
            self.evaluation_export.setEnabled(True)
            self._update_forecast_controls()
            self._update_needle_prediction_controls()
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
            data.export_csv(path,include_truth=include_truth,protected_paths=self._protected_export_paths())
        except (ValueError,OSError) as error:
            self.status.setText(str(error))
            return
        self.status.setText(f"Exported simulated target {label}: {path}")

    def _protected_export_paths(self):
        protected=set(self._study_source_paths)
        for metadata in (self.source_info,self.lobe_info,self.airway_info):
            if metadata and metadata.get("source_path"):
                protected.add(Path(metadata["source_path"]))
        protected.update(Path(__file__).resolve().parent/name for name in (
            "run.py","motiontwin.py","README.md","requirements.txt","pyproject.toml",
            ".gitignore","THIRD_PARTY_LICENSES.txt"))
        return protected

    def export_forecasts(self,include_truth=False):
        result=self.forecast_result
        if result is None or self.worker is not None:
            return
        if not self._forecast_context_matches(result):
            self._invalidate_forecasts()
            self.status.setText("The scenario changed. Recompute forecasts before exporting.")
            return
        evaluation=result["validation"]
        if include_truth and not evaluation.rows and not (result["fits"] and result["truth_position"] is not None):
            self.status.setText("No completed forecast outcomes are available for evaluation export.")
            return
        label="forecast-evaluation" if include_truth else "forecasts"
        path,_=QFileDialog.getSaveFileName(self,f"Export {label}",f"target-{label}.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        temporary=None
        try:
            if self.forecast_result is not result or not self._forecast_context_matches(result):
                raise ValueError("The forecast changed while choosing an export destination. Recompute it before exporting.")
            protected=self._protected_export_paths()
            path=check_export_destination(path,protected)
            settings=result["settings"]
            metadata=dict(format_version=1,algorithm_version="mathematical-baselines-1",
                target_name=result["target"].name,target_kind=result["target"].kind,
                study_id=result["target"].study_id,model_id=result["observations"].model_id,
                recorded_through_s=result["observations"].through_s,
                horizon_s=result["horizon_s"],history_window_s=settings.history_window_s,
                velocity_window_s=settings.velocity_window_s,min_rate_bpm=settings.min_rate_bpm,
                max_rate_bpm=settings.max_rate_bpm)
            uncertainty=result["uncertainty_settings"]
            metadata.update(uncertainty_enabled=result["uncertainty_enabled"],region_nominal_coverage=uncertainty.nominal_coverage,
                region_min_scores=uncertainty.min_scores,region_max_scores=uncertainty.max_scores,
                region_min_spacing_s=uncertainty.min_spacing_s,
                region_definition="empirical_joint_3D_noisy_observation_error_ball",
                region_statistical_guarantee="none_dependent_rolling_histories",region_planning_effect="diagnostic_only")
            if result["uncertainty_enabled"]:
                metadata.update(format_version=2,algorithm_version="mathematical-baselines-observation-regions-1")
            fields=[*metadata,"record_kind","method","status","reason","origin_s","query_s",
                    "fit_samples","history_start_s","last_observation_s","fitted_frequency_hz",
                    "predicted_l_mm","predicted_p_mm","predicted_s_mm",
                    "region_status","region_reason","region_radius_mm","region_score_count","region_required_score_count",
                    "region_candidate_count","region_excluded_count","region_last_calibration_outcome_s","region_prefix_sha256",
                    "calibration_error_mm","calibration_outcome_l_mm","calibration_outcome_p_mm","calibration_outcome_s_mm"]
            if include_truth:
                fields.extend(("true_l_mm","true_p_mm","true_s_mm","error_3d_mm",
                    "region_observed_error_mm","region_observed_covered","region_true_error_mm","region_true_covered",
                    "evaluation_observed_l_mm","evaluation_observed_p_mm","evaluation_observed_s_mm"))
            rows=[]
            for method in BASELINE_METHODS:
                fit=result["fits"].get(method)
                truth=result["truth_position"]
                row=dict(metadata,record_kind="current_origin_evaluation" if include_truth else "current_forecast",
                    method=method,status="available" if fit is not None else "unavailable",
                    reason=result["unavailable"].get(method,""),origin_s=result["origin_s"],
                    query_s=result["origin_s"]+result["horizon_s"])
                if fit is not None:
                    prediction=result["predictions"][method]
                    row.update(fit_samples=fit.n_samples,history_start_s=fit.history_start_s,
                        last_observation_s=fit.last_observation_s,
                        fitted_frequency_hz=fit.frequency_hz if fit.frequency_hz is not None else "")
                    row.update(zip(("predicted_l_mm","predicted_p_mm","predicted_s_mm"),prediction))
                    if include_truth and truth is not None:
                        row.update(zip(("true_l_mm","true_p_mm","true_s_mm"),truth))
                        row["error_3d_mm"]=float(np.linalg.norm(prediction-truth))
                region=result["regions"].get(method)
                if result["uncertainty_enabled"]:
                    row.update(region_status="available" if region is not None and region.available else "unavailable",
                        region_reason=region.reason if region is not None else result["region_unavailable"].get(method,result["unavailable"].get(method,"No fit is available.")))
                    if region is not None:
                        row.update(region_radius_mm=region.radius_mm,region_score_count=region.n_scores,
                            region_required_score_count=region.required_score_count,region_candidate_count=region.candidate_count,
                            region_excluded_count=region.excluded_count,region_last_calibration_outcome_s=region.last_outcome_s,
                            region_prefix_sha256=region.prefix_sha256)
                        if include_truth:
                            assessed=result["region_evaluations"][method]
                            row.update(region_observed_error_mm=assessed["observed_error_mm"],region_observed_covered=assessed["observed_covered"],
                                region_true_error_mm=assessed["true_error_mm"],region_true_covered=assessed["true_covered"])
                            if result["region_observed_position"] is not None:
                                row.update(zip(("evaluation_observed_l_mm","evaluation_observed_p_mm","evaluation_observed_s_mm"),result["region_observed_position"]))
                else:
                    row["region_status"]="not_requested"
                if not include_truth or fit is not None and truth is not None:
                    rows.append(row)
                if region is not None:
                    for value in region.rows:
                        record=dict(metadata,record_kind="uncertainty_calibration",method=method,status=value["status"],
                            reason=value["reason"],origin_s=value["origin_s"],query_s=value["query_s"],
                            calibration_error_mm=value["error_mm"],region_radius_mm=region.radius_mm,
                            region_score_count=region.n_scores,region_prefix_sha256=region.prefix_sha256)
                        if value["predicted_lps_mm"] is not None:
                            record.update(zip(("predicted_l_mm","predicted_p_mm","predicted_s_mm"),value["predicted_lps_mm"]))
                        record.update(zip(("calibration_outcome_l_mm","calibration_outcome_p_mm","calibration_outcome_s_mm"),value["observed_lps_mm"]))
                        rows.append(record)
            if include_truth:
                for value in evaluation.rows:
                    row=dict(metadata,record_kind="paired_past_evaluation",method=value["method"],
                        status="available",reason="",origin_s=value["origin_s"],query_s=value["query_s"],
                        error_3d_mm=value["error_mm"])
                    row.update(zip(("predicted_l_mm","predicted_p_mm","predicted_s_mm"),value["predicted_lps_mm"]))
                    row.update(zip(("true_l_mm","true_p_mm","true_s_mm"),value["true_lps_mm"]))
                    rows.append(row)
                for value in evaluation.unavailable:
                    rows.append(dict(metadata,record_kind="excluded_past_origin",method=value["method"],
                        status="unavailable",reason=value["reason"],origin_s=value["origin_s"],
                        query_s=value["origin_s"]+result["horizon_s"]))
            temporary=path.with_name(f".{path.name}.{uuid4().hex}.part")
            with temporary.open("x",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            check_export_destination(path,protected)
            if self.forecast_result is not result or not self._forecast_context_matches(result):
                raise ValueError("The scenario changed during export. Recompute forecasts before exporting.")
            os.replace(temporary,path)
        except (ValueError,OSError) as error:
            self.status.setText(str(error))
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
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
        return self.ct_sequence is None and self.controls.currentIndex() in (1,3) and self.motion_model is not None

    def _workspace_changed(self,index):
        self.pause_phase_playback()
        self.pause_motion()
        self._invalidate_forecasts()
        self.extract_airways_action.setEnabled(index==0 and self.volume is not None and self.ct_sequence is None)
        if self.ct_sequence is not None:
            if index in (1,3):
                self.controls.blockSignals(True)
                self.controls.setCurrentIndex(0)
                self.controls.blockSignals(False)
            self.refresh()
            return
        if index in (1,3) and self.deformation is not None:
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
        self._invalidate_needle_plan()
        self._invalidate_observations()
        self.motion_time=0.
        self._show_motion_settings(self.motion_model.settings_at(0.))
        self.refresh()

    def pause_motion(self):
        self.motion_timer.stop()
        self.play_button.setText("Play")
        self.pause_needle()

    def toggle_motion(self):
        if not self.motion_active or self.worker is not None:
            return
        if self.motion_timer.isActive():
            self.pause_motion()
        elif self.motion_time < self.motion_model.duration:
            self.pause_needle()
            self._invalidate_forecasts()
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
            if value/100.!=self.motion_time:
                self._invalidate_forecasts()
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
        if initial or self.controls.currentIndex() in (1,3):
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
        self.controls.setTabEnabled(3,has_lungs)
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
        self.controls.setTabEnabled(3,False)
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
        self._update_forecast_controls()
        self._update_forecast_display()
        self._update_needle_display()
        self.scene.reset_camera_clipping_range()
        self.scene.render()

    def task(self,function,callback,label,*,phase_kind=None,progress=False,before_start=None):
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
            else "Planning comparison cancelled; no partial result was published." if phase_kind=="benchmark"
            else "Forecast study cancelled; no partial result was published." if phase_kind=="forecast-study"
            else "Respiratory phase preparation stopped."))
        self.worker.finished.connect(self._task_finished)
        self._update_phase_transport()
        if before_start is not None:
            before_start(self.worker)
        self._sync_needle_results()
        self.worker.start()

    def _task_result(self,callback,result):
        try:
            callback(result)
        except Exception as error:
            self._task_failed(str(error))

    def _task_failed(self,message):
        self.pause_phase_playback()
        self.status.setText("Planning comparison failed. The details are shown below." if self._phase_work_kind=="benchmark"
                            else "Forecast study failed. The details are shown below." if self._phase_work_kind=="forecast-study"
                            else "CT operation failed. The details are shown below.")
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
        self._sync_needle_results()
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
        self.needle_timer.stop()
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
