import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QFormLayout,
    QWidget, QLabel, QToolButton, QButtonGroup, QComboBox, QCheckBox, QMessageBox, QSizePolicy)

from motiontwin_annotation import AnnotationMask


class AnnotationPanel(QGroupBox):
    def __init__(self, owner):
        super().__init__("Target annotation")
        self.owner = owner
        self.region = self.draft = None
        self.region_phase = None
        self._study = None
        self._previous = None
        self._actor = self._mesh_for = None
        self._preview_mesh = self._region_mesh = None
        self._mesh_revision = -1
        self._overlay_keys = {}
        self.color = "#efa6d5"
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.new_button = self._button("New region", self.new_region, row)
        self.edit_button = self._button("Edit", self.edit_region, row)
        self.go_button = self._button("Centre", self.go_to_region, row)
        self.go_button.setToolTip("Move the linked CT crosshair to the region's physical centroid.")
        row.addStretch()
        layout.addLayout(row)
        row = QHBoxLayout()
        self.show_region = QCheckBox("Show region")
        self.show_region.setToolTip("Show the annotation in all CT planes and the 3D viewport.")
        self.show_region.setChecked(True)
        self.show_region.setStyleSheet("QCheckBox::indicator:checked:disabled { background:#7d9eb8; border-color:#c2d4df; }")
        self.show_region.toggled.connect(self.sync)
        row.addWidget(self.show_region, 1)
        self.remove_button = self._button("Remove", self.remove_region, row)
        layout.addLayout(row)
        self.editor = QWidget()
        body = QVBoxLayout(self.editor)
        body.setContentsMargins(0, 2, 0, 2)
        row = QHBoxLayout()
        self.tools = QButtonGroup(self)
        for index, label in enumerate(("Paint", "Erase", "Navigate")):
            button = self._button(label, self.sync, row)
            button.setCheckable(True)
            self.tools.addButton(button, index)
        self.tools.button(0).setChecked(True)
        row.addStretch()
        body.addLayout(row)
        form = QFormLayout()
        self.diameter = owner.spin(1, 100, 8, 1, 1)
        self.diameter.setSuffix(" mm")
        self.diameter.valueChanged.connect(self.sync)
        form.addRow("Brush diameter", self.diameter)
        self.scope = QComboBox()
        self.scope.addItems(["Current slice", "3D sphere"])
        self.scope.setToolTip("Slice mode edits source voxels intersected by this CT plane. 3D mode also edits neighbouring slices.")
        self.scope.currentIndexChanged.connect(self.sync)
        form.addRow("Brush extent", self.scope)
        body.addLayout(form)
        row = QHBoxLayout()
        self.undo_button = self._button("Undo", self.undo, row)
        self.redo_button = self._button("Redo", self.redo, row)
        self.clear_button = self._button("Clear", self.clear, row)
        row.addStretch()
        body.addLayout(row)
        row = QHBoxLayout()
        self.apply_button = self._button("Apply region", self.apply, row)
        self.cancel_button = self._button("Cancel", self.cancel, row)
        row.addStretch()
        self.apply_button.setStyleSheet("QToolButton { border-color:#dca2c6; font-weight:600; }")
        body.addLayout(row)
        hint = QLabel("Drag to draw. Navigate or Shift+click moves the crosshair. Scroll changes slice; Ctrl+scroll zooms. Esc cancels the current stroke.")
        hint.setWordWrap(True)
        body.addWidget(hint)
        layout.addWidget(self.editor)
        self.readout = QLabel("Draw a user-defined region on the source CT.")
        self.readout.setWordWrap(True)
        self.readout.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.readout)
        self.note = QLabel("Manual reference-CT annotation · this session.\nIndependent of the spherical planning target.")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color:#b9bec5; font-size:10px")
        layout.addWidget(self.note)
        for label in (hint, self.readout, self.note):
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, owner)
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, owner)
        self.undo_shortcut.activated.connect(self.undo)
        self.redo_shortcut.activated.connect(self.redo)
        self.editor.hide()
        for widget in (self.new_button, self.edit_button, self.go_button, self.show_region, self.remove_button,
                       self.undo_shortcut, self.redo_shortcut):
            widget.setEnabled(False)

    def _button(self, text, callback, layout):
        button = QToolButton()
        button.setText(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def _current(self):
        return self.draft if self.draft is not None else self.region if self.region_phase == self.owner.phase_index else None

    def _start(self, mask=None):
        if self.owner.volume is None or self.owner.worker is not None or self.draft is not None:
            return
        self.owner.controls.setCurrentIndex(0)
        self.owner.pause_phase_playback()
        self.owner.pause_motion()
        self._was_visible = self.show_region.isChecked()
        self.draft = AnnotationMask(self.owner.volume, mask)
        self._editing_existing = mask is not None
        self._apply_pending = False
        self._previous = None
        self.tools.button(0).setChecked(True)
        self.show_region.setChecked(True)
        self._mesh_for = None
        self._remove_actor()
        self.sync()
        self.owner.status.setText("Annotation draft · paint on the linked CT views, then Apply or Cancel.")
        self._update_readout()
        if mask is not None:
            self._show_mesh(self._region_mesh, self.draft, self.draft.revision)
        self.owner.scene.render()

    def new_region(self):
        self._start()

    def edit_region(self):
        if self.region is not None and self.region_phase == self.owner.phase_index:
            self._start(self.region.mask)

    def cancel(self):
        if self.draft is None or self.owner.worker is not None:
            return
        self.draft.cancel()
        self._release_pointer()
        self.draft = None
        self._previous = None
        self._mesh_for = None
        self._overlay_keys.clear()
        self._remove_actor()
        self.show_region.setChecked(self._was_visible)
        self.sync()
        if self._current() is not None:
            self._show_mesh(self._region_mesh, self.region, self.region.revision)
        self._update_readout()
        self.owner.scene.render()
        self.owner.status.setText("Annotation draft discarded. The previously applied region was retained.")

    def apply(self):
        if self.draft is None or self.owner.worker is not None:
            return
        if self.draft.measurements() is None:
            self.owner.status.setText("The region is empty. Paint some voxels or Cancel to retain the previous region.")
            return
        if self._mesh_for is not self.draft or self._mesh_revision != self.draft.revision:
            self._rebuild(apply_after=True)
            return
        self.region, self.draft = self.draft, None
        self._region_mesh = self._preview_mesh
        self.region_phase = self.owner.phase_index
        self.region.undo_stack.clear()
        self.region.redo_stack.clear()
        self.region.mask.flags.writeable = False
        self.sync()
        self._update_readout()
        self.owner.status.setText("User-defined annotation applied · the spherical planning target is unchanged.")

    def handle_stroke(self, canvas, action, point):
        if self.draft is None or self.owner.worker is not None:
            return
        try:
            if action == "begin":
                self._stroke_preview_current = (self._mesh_for is self.draft and self._mesh_revision == self.draft.revision)
                self.draft.begin(erase=self.tools.checkedId() == 1)
                self._previous = point
                self.owner.status.setText("Drawing annotation · release to update measurements and the 3D boundary.")
            if action in ("begin", "move"):
                if action == "move" and self._previous is not None and np.array_equal(point, self._previous):
                    return
                normal = canvas.plane.normal if self.scope.currentIndex() == 0 else None
                self.draft.paint(point if self._previous is None else self._previous, point,
                                 self.diameter.value() / 2., normal=normal)
                self._previous = point
                self._refresh_overlays()
            elif action == "break":
                self._previous = None
            elif action in ("end", "cancel"):
                changed = self.draft.finish() if action == "end" else self.draft.cancel()
                if action == "cancel" and self._stroke_preview_current:
                    self._mesh_revision = self.draft.revision
                self._previous = None
                self._update_readout()
                self.sync()
                if changed:
                    self._rebuild()
                elif action == "cancel":
                    self.owner.status.setText("Current annotation stroke cancelled.")
                elif action == "end":
                    self.owner.status.setText("No voxel changes in this stroke.")
        except ValueError as error:
            self.draft.cancel()
            if self._stroke_preview_current:
                self._mesh_revision = self.draft.revision
            canvas._annotation_drawing = False
            self._previous = None
            self.sync()
            self.owner.status.setText(str(error))

    def undo(self):
        if self.draft is not None and self.owner.worker is None:
            self.draft.finish()
            self._release_pointer()
            self.draft.undo()
            self._rebuild()

    def redo(self):
        if self.draft is not None and self.owner.worker is None:
            self.draft.cancel()
            self._release_pointer()
            self.draft.redo()
            self._rebuild()

    def clear(self):
        if self.draft is not None and self.owner.worker is None:
            try:
                self.draft.clear()
                self._rebuild()
            except ValueError as error:
                self.owner.status.setText(str(error))

    def _remove_actor(self):
        if self._actor is not None:
            self.owner.scene.remove_actor(self._actor, render=False)
            self._actor = None

    def _release_pointer(self):
        for view in self.owner.slices:
            view.canvas._annotation_drawing = False

    def _show_mesh(self, mesh, model, revision):
        self._remove_actor()
        self._preview_mesh, self._mesh_for, self._mesh_revision = mesh, model, revision
        if mesh is not None and mesh.n_points:
            self._actor = self.owner.scene.add_mesh(mesh.copy(), color=self.color,
                smooth_shading=True, name="user_annotation",
                reset_camera=False, render=False)
            self._actor.SetUserMatrix(self.owner.scene.motion_matrix)
            self._actor.SetVisibility(self.show_region.isChecked())
        self.owner.scene.reset_camera_clipping_range()

    def _rebuild(self, *, apply_after=False):
        model = self._current()
        if model is None or self.owner.worker is not None:
            return
        revision = model.revision
        def accepted(mesh):
            if self._current() is not model or model.revision != revision:
                return
            self._show_mesh(mesh, model, revision)
            self._update_readout()
            self.sync()
            self.owner.scene.render()
            self.owner.status.setText("Annotation draft updated · Apply region to accept, or Cancel to discard changes."
                                      if mesh is not None else "Empty annotation draft · Paint to define a region, or Cancel.")
            if apply_after:
                # the worker is still registered until its finished signal is processed.
                self._apply_pending = True
        self.owner.task(model.surface, accepted, "Reconstructing the user-defined region boundary…")

    def _update_readout(self):
        model = self._current()
        measured = None if model is None else model.measurements()
        if measured is None:
            text = "Empty draft · paint to define the region." if self.draft is not None else "Draw a user-defined region on the source CT."
            if self.region is not None and self.region_phase != self.owner.phase_index:
                text = f"Region belongs to phase {self.owner.ct_sequence.phases[self.region_phase].percent:g}%. Return to that phase to inspect or edit it."
        else:
            centre = ", ".join(f"{value:+.2f}" for value in measured["centroid_lps_mm"])
            dimensions = " × ".join(f"{value:.2f}" for value in measured["dimensions_lps_mm"])
            text = (f"{'DRAFT' if self.draft is not None else 'USER-DEFINED REGION'} · {measured['voxels']:,} voxels\n"
                    f"Reference volume  {measured['volume_mm3']:.2f} mm³ · {measured['volume_mm3'] / 1000:.4g} mL\n"
                    f"Box L/P/S  {dimensions} mm\nCentroid LPS  {centre} mm")
            if model.history_limited:
                text += "\nUndo retains the latest edits within 32 MiB."
        self.readout.setText(text)

    def _refresh_overlays(self):
        model = self._current() if self.show_region.isChecked() else None
        matrix = self.owner._motion_matrix()
        inverse = np.linalg.inv(matrix)
        for view in self.owner.slices:
            canvas = view.canvas
            key = (id(model), getattr(model, "revision", None), id(canvas.plane), matrix.tobytes())
            if self._overlay_keys.get(canvas) == key:
                continue
            image = None
            if model is not None and canvas.plane is not None:
                image = model.volume().reslice_like(canvas.plane, interpolation=0, cval=0,
                    coordinate_mapper=lambda points: points @ inverse[:3, :3].T + inverse[:3, 3]).image
            canvas.set_annotation(image, self.color)
            self._overlay_keys[canvas] = key

    def sync(self, *args):
        owner = self.owner
        study = owner.ct_sequence if owner.ct_sequence is not None else owner.volume
        if study is not self._study:
            self.reset()
            self._study = study
        editing, ready = self.draft is not None, owner.volume is not None and owner.worker is None
        here = self.region is not None and self.region_phase == owner.phase_index
        self.new_button.setText("Replace region" if self.region is not None else "New region")
        self.new_button.setEnabled(ready and not editing)
        self.new_button.setToolTip("Create a fresh draft. Apply replaces the previous annotation; Cancel retains it.")
        self.edit_button.setEnabled(ready and here and not editing)
        self.go_button.setEnabled(ready and here and not editing)
        self.remove_button.setEnabled(ready and self.region is not None and not editing)
        self.show_region.setEnabled(ready and not editing and here)
        self.editor.setVisible(editing)
        self.undo_button.setEnabled(ready and editing and bool(self.draft.undo_stack))
        self.redo_button.setEnabled(ready and editing and bool(self.draft.redo_stack))
        nonempty = editing and self.draft.measurements() is not None
        self.clear_button.setEnabled(ready and nonempty)
        self.apply_button.setEnabled(ready and nonempty)
        self.cancel_button.setEnabled(ready and editing)
        self.undo_shortcut.setEnabled(self.undo_button.isEnabled())
        self.redo_shortcut.setEnabled(self.redo_button.isEnabled())
        owner.controls.tabBar().setEnabled(not editing)
        owner.file_menu.setEnabled(not editing and owner.worker is None)
        owner.file_toolbar.setEnabled(owner.file_menu.isEnabled())
        owner.phase_group.setEnabled(not editing)
        owner.phase_transport.setEnabled(not editing)
        for view in owner.slices:
            view.canvas.annotation_busy = editing and not ready
            view.canvas.annotation_tool = (("paint", "erase", "navigate")[self.tools.checkedId()]
                                           if editing and ready else "navigate")
            view.canvas.annotation_radius = self.diameter.value() / 2.
            view.canvas.update()
        self._refresh_overlays()
        if self._actor is not None:
            visible = self._current() is not None and self.show_region.isChecked()
            if bool(self._actor.GetVisibility()) != visible:
                self._actor.SetVisibility(visible)
                owner.scene.render()
        if getattr(self, "_apply_pending", False) and owner.worker is None:
            self._apply_pending = False
            self.apply()
        self._update_readout()

    def reset(self):
        self.region = self.draft = self._study = None
        self.region_phase = None
        self._mesh_for = self._preview_mesh = self._region_mesh = None
        self._apply_pending = False
        self._previous = None
        self._remove_actor()
        self._release_pointer()
        self._overlay_keys.clear()

    def go_to_region(self):
        if self.region is not None and self.region_phase == self.owner.phase_index:
            self.owner.set_crosshair(self.owner.deformation.forward(self.region.measurements()["centroid_lps_mm"],
                self.owner.motion_model.evaluate(self.owner.motion_time)[0]) if self.owner.motion_active
                else self.region.measurements()["centroid_lps_mm"])

    def remove_region(self):
        if self.region is None or self.draft is not None or self.owner.worker is not None:
            return
        if QMessageBox.question(self.owner, "Remove annotation?", "Remove the user-defined annotation from this study?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        self.region = self._region_mesh = self._preview_mesh = self._mesh_for = None
        self._remove_actor()
        self.sync()
        self.owner.scene.render()

    def can_close(self):
        if self.draft is None:
            return True
        if (self._editing_existing and np.array_equal(self.draft.mask, self.region.mask)
                or not self._editing_existing and not self.draft.mask.any()):
            return True
        return QMessageBox.question(self.owner, "Discard annotation draft?", "Discard the current annotation draft and close MotionTwin?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Discard
