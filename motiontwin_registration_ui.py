from dataclasses import replace

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QSizePolicy, QSlider, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from motiontwin import StructureStyle, Volume


class RegistrationInspectorDialog(QDialog):
    def __init__(self, owner, view_class=None):
        super().__init__(owner)
        self.result = self.reference = self.moving = None
        self.crosshair = np.zeros(3)
        self._samples = {}
        self._landmarks = []
        self._landmark_key = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Respiratory phase alignment")
        self.resize(1080, 760)
        self.setMinimumSize(820, 600)
        layout = QVBoxLayout(self)
        self.context_label = QLabel()
        self.context_label.setWordWrap(True)
        layout.addWidget(self.context_label)
        tools = QHBoxLayout()
        self.mode = QComboBox()
        for title, key in (("Blend", "blend"), ("Checkerboard", "checkerboard"),
                ("Absolute HU difference", "difference"), ("Reference CT", "reference"), ("Moving CT", "moving")):
            self.mode.addItem(title, key)
        self.mode.currentIndexChanged.connect(self._appearance_changed)
        tools.addWidget(self.mode)
        self.alignment = QComboBox()
        self.alignment.addItems(["Registered", "Before registration"])
        self.alignment.currentIndexChanged.connect(self._appearance_changed)
        tools.addWidget(self.alignment)
        self.blend = QSlider(Qt.Orientation.Horizontal)
        self.blend.setRange(0, 100)
        self.blend.setValue(50)
        self.blend.setMaximumWidth(140)
        self.blend.valueChanged.connect(self._appearance_changed)
        tools.addWidget(self.blend)
        self.blend_label = QLabel()
        tools.addWidget(self.blend_label)
        self.centre = QToolButton()
        self.centre.setText("Centre")
        self.centre.clicked.connect(lambda: self.set_crosshair(self.reference.center) if self.reference is not None else None)
        tools.addWidget(self.centre)
        tools.addStretch()
        layout.addLayout(tools)
        appearance = QHBoxLayout()
        self.window = self._spin(1, 4000, 1500, 50)
        self.level = self._spin(-1500, 2000, -500, 50)
        self.difference_range = self._spin(1, 2000, 300, 25)
        self.difference_range.setToolTip("Absolute-difference display range is zero to this HU value; outside coverage remains unassessed.")
        for title, control in (("CT window · HU", self.window), ("CT level · HU", self.level),
                ("Difference range · HU", self.difference_range)):
            appearance.addWidget(QLabel(title))
            appearance.addWidget(control)
        appearance.addStretch()
        layout.addLayout(appearance)
        grid = QGridLayout()
        self.views = {}
        view_class = type(owner.slices[0]) if view_class is None else view_class
        for name, position in (("axial", (0, 0)), ("coronal", (1, 0)), ("sagittal", (1, 1))):
            view = view_class(name, self)
            view.set_quality(256)
            view.selected.connect(self.set_crosshair)
            self.views[name] = view
            grid.addWidget(view, *position)
        details = QGroupBox("Alignment checks")
        details.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        information = QVBoxLayout(details)
        self.quality_label = QLabel()
        self.quality_label.setWordWrap(True)
        self.quality_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        information.addWidget(self.quality_label)
        self.landmark_table = QTreeWidget()
        self.landmark_table.setHeaderLabels(["Landmark", "Before mm", "After mm", "Source"])
        self.landmark_table.setRootIsDecorated(False)
        self.landmark_table.setAlternatingRowColors(True)
        self.landmark_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.landmark_table.header().setStretchLastSection(True)
        self.landmark_table.setMinimumHeight(85)
        self.landmark_table.setMaximumHeight(100)
        self.landmark_table.currentItemChanged.connect(self._landmark_selected)
        information.addWidget(self.landmark_table, 1)
        self.landmark_note = QLabel()
        self.landmark_note.setWordWrap(True)
        information.addWidget(self.landmark_note)
        grid.addWidget(details, 0, 1)
        for axis in range(2):
            grid.setRowStretch(axis, 1)
            grid.setColumnStretch(axis, 1)
        layout.addLayout(grid, 1)
        self.coverage_label = QLabel()
        self.coverage_label.setWordWrap(True)
        layout.addWidget(self.coverage_label)
        footer = QHBoxLayout()
        note = QLabel("Reference LPS mm · click to link slices; scroll to slice; Ctrl+scroll to zoom.\n"
            "Grey hatching: outside supported CT coverage. Comparison modes use shared before/after coverage.")
        note.setWordWrap(True)
        footer.addWidget(note, 1)
        close = QToolButton()
        close.setText("Close")
        close.clicked.connect(self.close)
        footer.addWidget(close)
        layout.addLayout(footer)
        self._missing_styles = {
            "outside_ct": StructureStyle("Outside supported CT", "#30383f", 1., kind="other"),
            "outside_ct_stripe": StructureStyle("Outside supported CT stripe", "#46515a", 1., kind="other"),
        }
        self.invalidate()

    def _spin(self, lower, upper, value, step):
        control = QDoubleSpinBox()
        control.setRange(lower, upper)
        control.setDecimals(0)
        control.setSingleStep(step)
        control.setValue(value)
        control.setKeyboardTracking(False)
        control.valueChanged.connect(self._appearance_changed)
        return control

    def invalidate(self):
        self.result = self.reference = self.moving = None
        self._samples.clear()
        self._landmarks = []
        self._landmark_key = None
        self.context_label.setText("No current acquired-phase registration.")
        self.quality_label.setText("Register a reference and moving respiratory CT phase to inspect alignment.")
        self.coverage_label.setText("Previous image samples have been cleared.")
        self.landmark_note.setText("Paired landmarks are independent checks, not fitting inputs.")
        self.landmark_table.clear()
        for view in self.views.values():
            view.volume = view.canvas.plane = None
            view.canvas._image = view.canvas._image_buffer = None
            view.canvas._overlay_images = []
            view.canvas._mask_images.clear()
            view.canvas._mask_sources.clear()
            view.slider.setEnabled(False)
            view.position_label.setText("— mm")
            view.canvas.update()
        self._enable_controls()

    def _enable_controls(self):
        ready = self.result is not None
        key = self.mode.currentData()
        for control in (self.mode, self.centre):
            control.setEnabled(ready)
        self.alignment.setEnabled(ready and key != "reference")
        self.blend.setEnabled(ready and key == "blend")
        self.blend_label.setText(f"Moving {self.blend.value()}%")
        self.window.setEnabled(ready and key != "difference")
        self.level.setEnabled(ready and key != "difference")
        self.difference_range.setEnabled(ready and key == "difference")

    def set_result(self, result, reference, moving, *, landmarks=None, pair_label=None, width=1500., level=-500.):
        if (not isinstance(reference, Volume) or not isinstance(moving, Volume)
                or not callable(getattr(result, "map_points", None))
                or not np.isfinite((width, level)).all() or width <= 0):
            raise ValueError("Alignment inspection requires a registration, source CT pair and valid CT window.")
        changed = result is not self.result or reference is not self.reference or moving is not self.moving
        if not changed:
            if self.set_landmarks(landmarks):
                self._refresh()
            return
        if changed:
            result.validate_sources(reference, moving)
            self._samples.clear()
            self._landmark_key = None
            self.crosshair = reference.center.copy()
        self.result, self.reference, self.moving = result, reference, moving
        if changed:
            for control, value in ((self.window, width), (self.level, level)):
                control.blockSignals(True)
                control.setValue(value)
                control.blockSignals(False)
        label = pair_label or f"Reference phase {result.reference_index + 1}: {reference.name} → moving phase {result.moving_index + 1}: {moving.name}"
        self.context_label.setText(f"{label}\n{result.settings.method} · mapping reference physical coordinates to moving CT")
        metrics = result.metrics
        lines = [f"Shared comparison samples: {metrics['comparison_voxels']:,}",
            f"Clipped-HU RMSE: {metrics['rmse_before_hu']:.2f} → {metrics['rmse_after_hu']:.2f} HU",
            f"Moving coverage: {metrics['overlap_before']:.1%} → {metrics['overlap_after']:.1%}"]
        if metrics.get("jacobian_min") is not None:
            lines.append(f"Sampled Jacobian: {metrics['jacobian_min']:.3f}–{metrics['jacobian_max']:.3f}")
        if metrics.get("max_displacement_mm") is not None:
            lines.append(f"Largest sampled displacement: {metrics['max_displacement_mm']:.2f} mm")
        self.quality_label.setText("\n".join(lines))
        self.quality_label.setToolTip("Image disagreement uses the same supported reference working-grid samples before and after, clipped to −1000…400 HU. "
            "A lower image error alone does not verify anatomical correspondence. Jacobian and displacement checks are sampled on the working grid.")
        self.set_landmarks(landmarks)
        self._refresh()

    def set_landmarks(self, landmarks=None):
        rows = []
        if landmarks is not None and self.result is not None:
            if hasattr(landmarks, "points"):
                points = landmarks.points
                a, b = self.result.reference_index, self.result.moving_index
                if a in points and b in points:
                    rows = [dict(name=landmarks.name, reference_lps_mm=points[a], moving_lps_mm=points[b],
                        source=f"{landmarks.sources.get(a, 'unknown')} / {landmarks.sources.get(b, 'unknown')}")]
            else:
                rows = [dict(row) for row in landmarks]
        key = repr(rows)
        if key == self._landmark_key:
            return False
        if hasattr(landmarks, "validate_sources"):
            landmarks.validate_sources()
        prepared = []
        for row in rows:
            reference = np.asarray(row["reference_lps_mm"], dtype=float)
            moving = np.asarray(row["moving_lps_mm"], dtype=float)
            if reference.shape != (3,) or moving.shape != (3,) or not np.isfinite((reference, moving)).all():
                raise ValueError("A paired alignment landmark requires finite reference and moving LPS coordinates.")
            mapped, support = self.result.map_points(reference, return_support=True)
            observed = bool(self._coverage(self.reference, reference) & self._coverage(self.moving, moving))
            supported = observed and bool(support) and bool(self._coverage(self.moving, mapped))
            prepared.append(dict(row, reference_lps_mm=reference.copy(), moving_lps_mm=moving.copy(),
                before_mm=float(np.linalg.norm(reference - moving)) if observed else None,
                after_mm=float(np.linalg.norm(mapped - moving)) if supported else None))
        self._landmarks = prepared
        self._landmark_key = key
        blocked = self.landmark_table.blockSignals(True)
        self.landmark_table.clear()
        for index, row in enumerate(prepared):
            item = QTreeWidgetItem([str(row.get("name", "Landmark")),
                "Outside CT" if row["before_mm"] is None else f"{row['before_mm']:.3f}",
                "Outside support" if row["after_mm"] is None else f"{row['after_mm']:.3f}", str(row.get("source", "unspecified"))])
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            self.landmark_table.addTopLevelItem(item)
        self.landmark_table.blockSignals(blocked)
        self.landmark_note.setText("Paired landmark error is measured independently; landmarks were not used to fit this registration. Select a row to inspect its reference location."
            if prepared else "No paired landmark is available for these phases. Confirm the same feature in both phases in Landmarks to check alignment independently.")
        return True

    def _landmark_selected(self, current, previous):
        if current is not None:
            self.set_crosshair(self._landmarks[current.data(0, Qt.ItemDataRole.UserRole)]["reference_lps_mm"])

    def set_crosshair(self, point):
        if self.reference is None:
            return
        point = np.asarray(point, dtype=float)
        if point.shape != (3,) or not np.isfinite(point).all():
            raise ValueError("Select a finite reference LPS point.")
        self.crosshair = np.clip(point, *self.reference.bounds)
        self._refresh()

    @staticmethod
    def _coverage(volume, points):
        indices = volume.world_to_index(points)
        return np.all((indices >= -1e-7) & (indices <= np.asarray(volume.shape[::-1]) - 1 + 1e-7), axis=-1)

    def _sample(self, name):
        axis = self.views[name].axis
        key = float(self.crosshair[axis])
        cached = self._samples.get(name)
        if cached is not None and cached[0] == key:
            return cached[1]
        plane = self.reference.slice_grid(name, self.crosshair, max_pixels=256)
        points = plane.world_grid()
        mapped, mapping_support = self.result.map_points(points, return_support=True)
        samples = dict(plane=plane, reference=self.reference.sample_world(points),
            before=self.moving.sample_world(points), after=self.moving.sample_world(mapped),
            reference_support=self._coverage(self.reference, points),
            before_support=self._coverage(self.moving, points),
            after_support=self._coverage(self.moving, mapped) & mapping_support)
        self._samples[name] = key, samples
        return samples

    def _appearance_changed(self, *args):
        self._enable_controls()
        self._refresh()

    def _refresh(self):
        if self.result is None:
            return
        key, registered = self.mode.currentData(), self.alignment.currentIndex() == 0
        fractions = []
        for name, view in self.views.items():
            sampled = self._sample(name)
            plane, reference = sampled["plane"], sampled["reference"]
            moving = sampled["after" if registered else "before"]
            common = sampled["reference_support"] & sampled["before_support"] & sampled["after_support"]
            coverage = common
            if key == "reference":
                image, coverage = reference, sampled["reference_support"]
            elif key == "moving":
                image, coverage = moving, sampled["after_support" if registered else "before_support"]
            elif key == "difference":
                image = np.abs(reference - moving)
            elif key == "checkerboard":
                rows, columns = np.indices(plane.shape)
                checker = (np.floor(columns * plane.spacing[0] / 20) + np.floor(rows * plane.spacing[1] / 20)) % 2 == 0
                image = np.where(checker, reference, moving)
            else:
                weight = self.blend.value() / 100.
                image = (1 - weight) * reference + weight * moving
            displayed = replace(plane, image=np.where(coverage, image, -1000.))
            rows, columns = np.indices(plane.shape)
            stripe = (rows + columns) % 12 < 3
            masks = {"outside_ct": replace(plane, image=~coverage),
                "outside_ct_stripe": replace(plane, image=~coverage & stripe)}
            view.set_data(self.reference, self.crosshair, plane=displayed, mask_planes=masks, structures=self._missing_styles)
            view.canvas.window = self.difference_range.value() if key == "difference" else self.window.value()
            view.canvas.level = self.difference_range.value() / 2 if key == "difference" else self.level.value()
            view.canvas.set_landmark(None, 0.)
            if self._landmarks:
                current = self.landmark_table.currentItem()
                index = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else 0
                view.canvas.set_landmark(self._landmarks[index]["reference_lps_mm"], min(plane.spacing))
            view.canvas.update()
            fractions.append(f"{name.title()} {coverage.mean():.1%}")
        frame = "reference CT" if key == "reference" else "registered moving CT" if registered else "moving CT before registration"
        self.coverage_label.setText(f"{frame} · supported pixels: " + " · ".join(fractions)
            + (f" · absolute difference display 0–{self.difference_range.value():g} HU" if key == "difference" else ""))
        self._enable_controls()
