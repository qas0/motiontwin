from pathlib import Path
from dataclasses import replace
import re

import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox, QComboBox, QCheckBox, QStyle

import motiontwin as mt
from motiontwin import (BASELINE_METHODS, RouteSettings, fit_baseline, calibrate_forecast_region,
    evaluate_forecast_region, select_validation_origins, evaluate_baselines, select_forecast_route,
    create_forecast_needle_plan, select_geometric_route, create_needle_plan, evaluate_needle,
    evaluate_needle_constraints)
from motiontwin_learning import LEARNED_METHOD, LearnedPredictor, LearningResult, fit_learned
from motiontwin_annotation import AnnotationMask
from motiontwin_registration import RegistrationResult, load_pair
from motiontwin_cases import (write_case, read_case, source_record, resolve_source,
    file_record, resolve_file, pack_surfaces, restore_surfaces)


CONTROL_NAMES = (
    "window_control", "level_control", "opacity", "segmentation_visible", "camera",
    "phase_rate", "phase_loop", "breathing_pattern", "motion_amplitude", "breathing_rate",
    "motion_seed", "target_mode", "target_radius", "observation_rate", "observation_noise", "observation_seed",
    "forecast_method", "forecast_horizon", "forecast_history", "forecast_uncertainty", "forecast_coverage",
    "needle_radius", "needle_speed", "needle_delay", "needle_targeting_method", "needle_prediction_history",
    "needle_exclusion_radius", "needle_exclusion_policy", "needle_clearance", "needle_search_radius")


def control_value(control):
    return (control.currentText() if isinstance(control, QComboBox) else
            control.isChecked() if isinstance(control, QCheckBox) else control.value())


def set_control(control, value):
    blocked = control.blockSignals(True)
    if isinstance(control, QComboBox):
        control.setCurrentText(value)
    elif isinstance(control, QCheckBox):
        control.setChecked(value)
    else:
        control.setValue(value)
    control.blockSignals(blocked)


class PlanningCases:
    def __init__(self, owner):
        self.owner, self.path = owner, None
        menu = owner.file_menu
        self.open_action = menu.addAction("Open planning case…", self.open)
        self.save_action = menu.addAction("Save planning case", self.save)
        self.save_as_action = menu.addAction("Save planning case as…", lambda: self.save(save_as=True))
        self.open_action.setShortcut("Ctrl+O")
        self.save_action.setShortcut("Ctrl+S")
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.open_action.setToolTip("Restore a saved study, annotations, views and planning state.")
        self.save_action.setToolTip("Save a planning case with verified references to the original CT files.")
        first = owner.file_toolbar.actions()[0]
        for action, label, icon in ((self.open_action, "Open case", QStyle.StandardPixmap.SP_DialogOpenButton),
                (self.save_action, "Save case", QStyle.StandardPixmap.SP_DialogSaveButton)):
            action.setIcon(owner.style().standardIcon(icon))
            action.setIconText(label)
            owner.file_toolbar.insertAction(first, action)
        owner.file_toolbar.insertSeparator(first)
        self._saved_token = None
        self._restoring = False

    def sync(self):
        ready = self.owner.worker is None and self.owner.annotation_panel.draft is None
        self.open_action.setEnabled(ready)
        self.save_action.setEnabled(ready and self.owner.volume is not None)
        self.save_as_action.setEnabled(self.save_action.isEnabled())

    def reset(self):
        if not self._restoring:
            self.path = None
            self.owner.setWindowTitle("MotionTwin | Pulmonary CT and Motion Preview")
            self._saved_token = self._token()
        self.sync()

    def _view(self):
        w, camera = self.owner, self.owner.scene.camera
        return dict(controls={name: control_value(getattr(w, name)) for name in CONTROL_NAMES},
            crosshair=w.crosshair.copy(), zoom=[v.canvas.zoom for v in w.slices],
            camera=[list(camera.position), list(camera.focal_point), list(camera.up),
                    bool(camera.parallel_projection), camera.parallel_scale, camera.view_angle],
            workspace=w.controls.currentIndex(), splitter=w.main_splitter.sizes())

    def _token(self):
        w, panel = self.owner, self.owner.annotation_panel
        landmarks = w.landmarks
        view = self._view()
        view["crosshair"] = view["crosshair"].tolist()
        return repr((view, w.structures, w._phase_styles, w.phase_index,
            [(key, id(mask)) for key, mask in w.masks.items()],
            id(panel.region), getattr(panel.region, "revision", None), panel.region_phase,
            panel.show_region.isChecked(), panel.color, panel.diameter.value(), panel.scope.currentText(),
            mt.respiratory_model_id(w.motion_model) if w.motion_model is not None else None,
            w.motion_time, w.target, id(w.target_observations), w.needle_entry_reference,
            w.needle_exclusions, id(w.needle_plan), id(w.needle_route_selection),
            getattr(w.learned_predictor, "model_id", None), id(w.learning_result), w.forecast_result is not None,
            (w.registration_reference.currentIndex(), w.registration_moving.currentIndex(),
             w.registration_method.currentText(), id(w.registration_result)),
            (landmarks.name, landmarks.reference_index, landmarks.provenance,
             {key: point.tolist() for key, point in landmarks.points.items()},
             landmarks.sources) if landmarks is not None else None))

    def allow_replace(self, continuation):
        if self._restoring or self.owner.volume is None or self._token() == self._saved_token:
            return True
        answer = QMessageBox.question(self.owner, "Save planning case?",
            "Save the current annotations, view and planning changes before continuing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            self.save(after=continuation)
        return answer == QMessageBox.StandardButton.Discard

    def _ready(self):
        w = self.owner
        training = w._learning_dialog is not None and w._learning_dialog._worker is not None
        if w.worker is not None or training or w.annotation_panel.draft is not None:
            w.status.setText("Finish the current operation and Apply or Cancel the annotation draft before saving or opening a case.")
            return False
        w.pause_phase_playback()
        w.pause_motion()
        return True

    def _snapshot(self):
        w, panel = self.owner, self.owner.annotation_panel
        if w.volume is None:
            raise ValueError("Open a CT study before saving a planning case.")
        if w.ct_sequence is None and w._study_ct_path is None:
            raise ValueError("This CT has no source-file reference. Open its original CT file before saving a case.")
        if w.ct_sequence is None and w.registration_result is not None:
            raise ValueError("An acquired phase registration requires its original respiratory sequence.")
        if isinstance(w.target, mt.AnnotatedTarget):
            if (w.ct_sequence is not None or panel.region is None or panel.region_phase is not None
                    or w.target_mode.currentText() != "Annotated region"
                    or mt.create_annotated_target(w.volume, w._lung_target_mask(), panel.region.mask, w.target.name) != w.target):
                raise ValueError("The planning region no longer matches its applied annotation. Select the target again before saving.")
        if w.needle_plan is not None and not w._needle_context_matches(w.needle_plan):
            raise ValueError("The selected plan is stale. Rebuild or clear it before saving the case.")
        planning = None
        if w.needle_plan is not None or w.needle_route_selection is not None:
            context = w._needle_route_context
            if context is None:
                context = dict(planning_time_s=w.needle_plan.planning_time_s, search=False,
                    needle_settings=w._needle_settings(), route_settings=w._needle_route_settings(),
                    entry_reference=w.needle_entry_reference, exclusions=w.needle_exclusions,
                    targeting_method="Displayed centre", forecast_settings=None,
                    exclusion_policy=w._needle_exclusion_policy(), learned_model_id=None)
            if w._needle_route_context is not None and not w._route_context_matches(context):
                raise ValueError("The saved route decision is stale. Rebuild it before saving.")
            context = {key: value for key, value in context.items()
                       if key not in ("volume", "target", "observations", "mask_key", "model_id", "deformation")}
            planning = dict(context=context, plan=w.needle_plan,
                chosen_index=getattr(w.needle_route_selection, "chosen_index", None))
        landmarks = w.landmarks
        registration = None
        if w.ct_sequence is not None:
            registration = dict(reference=w.registration_reference.currentIndex(),
                moving=w.registration_moving.currentIndex(), method=w.registration_method.currentText(),
                result=w.registration_result)
            result = registration["result"]
            if result is not None and (not isinstance(result, RegistrationResult)
                    or result.reference_index != registration["reference"]
                    or result.moving_index != registration["moving"]
                    or result.settings.method != registration["method"] or w._registration_volumes is None):
                raise ValueError("The registration no longer matches its selected phase pair. Clear or calculate it again before saving.")
        return dict(view=self._view(), masks=w.masks if w.ct_sequence is None else {},
            surfaces=pack_surfaces(w.scene._source_meshes) if w.ct_sequence is None else {},
            styles=w.structures if w.ct_sequence is None else w._phase_styles,
            source_info=w.source_info, lobe_info=w.lobe_info, airway_info=w.airway_info,
            imported_masks=w.imported_masks, volume_name=w.volume.name,
            source_paths=[str(path.resolve()) for path in w._study_source_paths],
            volume_id=mt.target_study_id(w.volume), phase_index=w.phase_index,
            annotation=dict(mask=panel.region.mask if panel.region is not None else None,
                phase=panel.region_phase if panel.region is not None else None, color=panel.color,
                visible=panel.show_region.isChecked(), diameter=panel.diameter.value(), scope=panel.scope.currentText()),
            landmarks=(dict(name=landmarks.name, reference=landmarks.reference_index,
                provenance=landmarks.provenance,
                points=[(index, point, landmarks.sources[index]) for index, point in landmarks.points.items()])
                if landmarks is not None else None),
            model=w.motion_model, deformation=w.deformation, time=w.motion_time,
            target=w.target, observations=w.target_observations, predictor=w.learned_predictor,
            learning_result=w.learning_result, entry=w.needle_entry_reference, exclusions=w.needle_exclusions,
            planning=planning, forecast=w.forecast_result is not None and w._forecast_context_matches(w.forecast_result),
            registration=registration)

    def save(self, path=None, *, save_as=False, after=None):
        if not self._ready() or self.owner.volume is None:
            return
        if isinstance(path, bool):
            path = None
        if path is None:
            path = None if save_as else self.path
            if path is None:
                path, _ = QFileDialog.getSaveFileName(self.owner, "Save planning case",
                    str(self.path or "planning-case.motiontwin"), "MotionTwin case (*.motiontwin)")
        if not path:
            return
        path = Path(path).expanduser().resolve()
        if not path.suffix:
            path = path.with_suffix(".motiontwin")
        try:
            state = self._snapshot()
            token = self._token()
        except ValueError as error:
            self.owner.status.setText(str(error))
            return
        w, sequence, ct_path = self.owner, self.owner.ct_sequence, self.owner._study_ct_path
        registration_volumes = w._registration_volumes
        protected = w._protected_export_paths()
        successful = False
        def write():
            if sequence is None:
                source = source_record(ct_path, path)
                if mt.target_study_id(mt.load_volume(ct_path)) != state["volume_id"]:
                    raise ValueError("The original CT changed after it was opened. Reopen it before saving a case.")
                state["study"] = dict(kind="static", source=source)
            else:
                records = []
                for index, sources in enumerate(sequence._sources):
                    sequence._check_sources(index)
                    records.append([source_record(source.path, path) for source in sources])
                state["study"] = dict(kind="sequence", manifest=file_record(sequence._manifest, path), sources=records)
                if state["registration"]["result"] is not None:
                    state["registration"]["result"].validate_sources(*registration_volumes)
            def check():
                if sequence is None:
                    resolve_source(state["study"]["source"], path)
                else:
                    self._check_sequence(state["study"], path, sequence)
            write_case(path, state, protected_paths=protected, before_replace=check)
            return path
        def accepted(saved):
            nonlocal successful
            self.path, self._saved_token = saved, token
            successful = True
            w.setWindowTitle(f"{saved.stem} | MotionTwin")
            w.status.setText(f"Planning case saved: {saved.name} · original CT files remain referenced.")
        def finished():
            if successful and after is not None:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, after)
        w.task(write, accepted, "Saving planning case and verifying source files…", phase_kind="case-save",
            before_start=lambda worker: worker.finished.connect(finished))

    def _schema(self):
        schema = {}
        for name in CONTROL_NAMES:
            control = getattr(self.owner, name)
            if isinstance(control, QComboBox):
                schema[name] = [control.itemText(index) for index in range(control.count())]
                if name in ("forecast_method", "needle_targeting_method"):
                    schema[name] += [LEARNED_METHOD]
            elif isinstance(control, QCheckBox):
                schema[name] = bool
            else:
                schema[name] = (control.minimum(), 30. if name == "motion_amplitude" else control.maximum(),
                                isinstance(control.value(), int))
        return schema

    def open(self, path=None):
        if not self._ready():
            return
        if isinstance(path, bool):
            path = None
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self.owner, "Open planning case",
                str(self.path.parent if self.path else ""), "MotionTwin case (*.motiontwin)")
        if not path or not self.allow_replace(lambda: self.open(path)):
            return
        path = Path(path).expanduser().resolve()
        schema = self._schema()
        self.owner.task(lambda: self._prepare(read_case(path), path, schema),
            lambda prepared: self._apply(path, prepared), "Verifying and restoring planning case…", phase_kind="case-open")

    @staticmethod
    def _check_sequence(study, path, sequence):
        if resolve_file(study["manifest"], path) != sequence._manifest:
            raise ValueError("The saved sequence manifest does not match the restored source.")
        records = study["sources"]
        if len(records) != len(sequence._sources):
            raise ValueError("The saved sequence phase count changed.")
        for index, (saved, sources) in enumerate(zip(records, sequence._sources)):
            sequence._check_sources(index)
            if len(saved) != len(sources) or any(resolve_source(record, path) != source.path
                    for record, source in zip(saved, sources)):
                raise ValueError("The saved sequence phase sources changed.")

    @staticmethod
    def _validate_view(view, schema):
        if set(view["controls"]) != set(schema):
            raise ValueError("This case uses incompatible application controls.")
        for name, rule in schema.items():
            value = view["controls"][name]
            valid = (type(value) is bool if rule is bool else value in rule if isinstance(rule, list) else
                type(value) in (int, float) and np.isfinite(value) and rule[0] <= value <= rule[1]
                and (not rule[2] or type(value) is int))
            if not valid:
                raise ValueError(f"The saved {name.replace('_', ' ')} setting is incompatible.")
        camera = view["camera"]
        if (len(view["zoom"]) != 3 or not np.isfinite(view["zoom"]).all()
                or np.any(np.asarray(view["zoom"]) < .5) or np.any(np.asarray(view["zoom"]) > 5)
                or type(view["workspace"]) is not int or not 0 <= view["workspace"] <= 3
                or np.shape(view["crosshair"]) != (3,) or not np.isfinite(view["crosshair"]).all()
                or len(camera) != 6 or np.shape(camera[:3]) != (3, 3)
                or not np.isfinite(np.asarray(camera[:3])).all() or type(camera[3]) is not bool
                or not np.isfinite(camera[4:]).all() or not 0 < camera[4] < 1e8 or not 1 <= camera[5] <= 179
                or np.linalg.norm(np.subtract(camera[0], camera[1])) < 1e-8
                or np.linalg.norm(np.cross(np.subtract(camera[0], camera[1]), camera[2])) < 1e-8
                or len(view["splitter"]) != 2 or any(type(v) is not int or not 0 <= v <= 100000 for v in view["splitter"])):
            raise ValueError("The saved view geometry is invalid.")

    def _prepare(self, state, path, schema):
        state.setdefault("registration", None)
        required = {"view", "masks", "styles", "source_info", "lobe_info", "airway_info", "imported_masks",
            "volume_name", "volume_id", "phase_index", "annotation", "landmarks", "model", "deformation", "time",
            "target", "observations", "predictor", "learning_result", "entry", "exclusions", "planning", "forecast", "study", "source_paths", "surfaces", "registration"}
        if (set(state) != required or type(state["forecast"]) is not bool or type(state["imported_masks"]) is not bool
                or type(state["masks"]) is not dict or type(state["styles"]) is not dict
                or any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", key)
                    for key in state["styles"])
                or any(value is not None and type(value) is not dict for value in
                    (state["source_info"], state["lobe_info"], state["airway_info"]))):
            raise ValueError("The planning case contains incompatible study fields.")
        for key in ("lobe_info", "airway_info"):
            if state[key] is not None:
                mt._anatomy_provenance(state[key], key.replace('_', ' '))
        source_info = state["source_info"]
        if source_info is not None:
            labels = source_info.get("display_labels", {})
            if (type(labels) is not dict or any(not isinstance(value, str) for value in labels.values())
                    or source_info.get("source_path") is not None and not isinstance(source_info["source_path"], str)):
                raise ValueError("The saved CT display provenance is invalid.")
            for name in labels.values():
                mt.StructureStyle(name, "#79b5bf")
        if (type(state["source_paths"]) is not list or any(not isinstance(value, str) or not value
                for value in state["source_paths"])):
            raise ValueError("The saved source-file protections are invalid.")
        predictor, report = state["predictor"], state["learning_result"]
        if (predictor is not None and not isinstance(predictor, LearnedPredictor)
                or report is not None and (not isinstance(report, LearningResult) or predictor is None
                    or report.predictor.model_id != predictor.model_id)):
            raise ValueError("The saved learning report does not match its predictor.")
        # earlier cases contain only the original spherical planning target.
        state["view"]["controls"].setdefault("target_mode", "Sphere")
        self._validate_view(state["view"], schema)
        study, sequence, landmarks = state["study"], None, None
        if study["kind"] == "static":
            ct_path = resolve_source(study["source"], path)
            volume = mt.load_volume(ct_path)
            masks, styles = state["masks"], state["styles"]
            if (state["phase_index"] is not None or set(masks) != set(styles) or len(masks) > 64
                    or any(mask.dtype != bool or mask.shape != volume.shape or not mask.any() for mask in masks.values())):
                raise ValueError("The saved anatomy does not match the CT grid.")
            meshes = restore_surfaces(state["surfaces"], volume, masks)
        elif study["kind"] == "sequence":
            ct_path = None
            sequence = mt.load_ct_sequence(resolve_file(study["manifest"], path),
                surface_cache_dir=Path(__file__).resolve().parent / "data" / "phase-surfaces")
            self._check_sequence(study, path, sequence)
            index = state["phase_index"]
            if type(index) is not int or not 0 <= index < len(sequence.phases):
                raise ValueError("The saved respiratory phase is invalid.")
            data = sequence.phase(index)
            volume, masks, meshes = data.volume, data.masks, data.meshes
            if set(state["styles"]) != set(sequence.styles):
                raise ValueError("The saved phase structure definitions changed.")
            styles = {key: state["styles"][key] for key in data.styles}
            saved = state["landmarks"]
            landmarks = mt.LandmarkSeries(sequence, saved["name"], saved["reference"], provenance=saved["provenance"])
            for index, point, source in saved["points"]:
                landmarks.set_point(index, point, source)
        else:
            raise ValueError("The planning case study type is unsupported.")
        if (mt.target_study_id(volume) != state["volume_id"] or not isinstance(state["volume_name"], str)
                or not 1 <= len(state["volume_name"]) <= 200
                or any(not isinstance(style, mt.StructureStyle) for style in state["styles"].values())
                or len({style.name.casefold() for style in state["styles"].values()}) != len(state["styles"])):
            raise ValueError("The saved CT identity or structure styles are incompatible.")
        volume.name = state["volume_name"]
        registration, registration_volumes = state["registration"], None
        if registration is not None:
            if (sequence is None or type(registration) is not dict
                    or set(registration) != {"reference", "moving", "method", "result"}
                    or any(type(registration[key]) is not int or not 0 <= registration[key] < len(sequence.phases)
                           for key in ("reference", "moving"))
                    or registration["method"] not in ("Rigid", "Rigid + deformable")):
                raise ValueError("The saved registration phase selection is invalid.")
            result = registration["result"]
            if result is not None:
                if (not isinstance(result, RegistrationResult) or registration["reference"] == registration["moving"]
                        or result.reference_index != registration["reference"] or result.moving_index != registration["moving"]
                        or result.settings.method != registration["method"]):
                    raise ValueError("The saved registration does not match its selected phase pair.")
                registration_volumes = load_pair(sequence, registration["reference"], registration["moving"])
                result.validate_sources(*registration_volumes)
        controls = state["view"]["controls"]
        for name in ("forecast_method", "needle_targeting_method"):
            if controls[name] == LEARNED_METHOD and state["predictor"] is None:
                raise ValueError("The saved method requires its learned predictor.")
        annotation = state["annotation"]
        mt.StructureStyle("Annotation", annotation["color"])
        if (type(annotation["visible"]) is not bool or type(annotation["diameter"]) not in (int, float)
                or not 1 <= annotation["diameter"] <= 100 or annotation["scope"] not in ("Current slice", "3D sphere")):
            raise ValueError("The saved annotation display settings are invalid.")
        region = region_mesh = None
        if annotation["mask"] is not None:
            phase = annotation["phase"]
            if (phase is not None if sequence is None else type(phase) is not int or not 0 <= phase < len(sequence.phases)):
                raise ValueError("The annotation belongs to an invalid respiratory phase.")
            region = AnnotationMask(volume, annotation["mask"])
            if region.measurements() is None:
                raise ValueError("An applied annotation cannot be empty.")
            region_mesh = region.surface()
            region.mask.flags.writeable = False
        lung_mask = np.zeros(volume.shape, dtype=bool)
        for key, mask in masks.items():
            if styles[key].kind == "lung":
                np.logical_or(lung_mask, mask, out=lung_mask)
        model, deformation, target = state["model"], state["deformation"], state["target"]
        if deformation is not None and not isinstance(deformation, mt.LungDeformation):
            raise ValueError("The saved motion reference is invalid.")
        maximum_amplitude = min(30., np.floor(deformation.height * .20 / 1.8 * 10) / 10) if deformation is not None else 30.
        if controls["motion_amplitude"] > maximum_amplitude:
            raise ValueError("The saved breathing amplitude exceeds this lung reference's range.")
        if (sequence is not None and any(state[key] is not None for key in
                ("model", "deformation", "target", "observations", "entry", "planning"))
                or type(state["time"]) not in (int, float) or not np.isfinite(state["time"])
                or not 0 <= state["time"] <= (model.duration if model is not None else 0)):
            raise ValueError("The saved motion context is incompatible with this study.")
        if model is not None:
            if (not isinstance(model, mt.RespiratoryModel) or model.duration != 60.
                    or not isinstance(deformation, mt.LungDeformation) or not lung_mask.any()):
                raise ValueError("The saved motion requires its reference lung anatomy.")
            deformation.matrix(model.position(state["time"]))
        if deformation is not None:
            margin = np.linalg.norm(np.asarray(volume.spacing)) * 2
            if (not isinstance(deformation, mt.LungDeformation) or not lung_mask.any()
                    or deformation.base_z < volume.bounds[0, 2] - margin
                    or deformation.apex_z > volume.bounds[1, 2] + margin):
                raise ValueError("The saved motion reference lies outside the CT anatomy.")
        if target is not None:
            mt.validate_planning_target(volume, lung_mask, target)
            if isinstance(target, mt.AnnotatedTarget):
                if controls["target_mode"] != "Annotated region" or sequence is not None or region is None:
                    raise ValueError("The saved region target requires its applied reference-CT annotation.")
                checked = mt.create_annotated_target(volume, lung_mask, region.mask, target.name)
                if checked != target:
                    raise ValueError("The saved planning region does not match its applied annotation.")
            elif controls["target_mode"] != "Sphere":
                raise ValueError("The saved planning target does not match its selected mode.")
        entry = state["entry"]
        if entry is not None:
            state["entry"] = mt.validate_needle_entry(volume, lung_mask, entry)
        state["exclusions"] = mt._exclusion_regions(state["exclusions"], mt.target_study_id(volume))
        for exclusion in state["exclusions"]:
            if mt.create_exclusion_region(volume, exclusion.center_lps_mm, exclusion.radius_mm, exclusion.name) != exclusion:
                raise ValueError("An exclusion belongs to a different CT source.")
        observations = state["observations"]
        if observations is not None:
            if (model is None or observations.target != target or observations.deformation != deformation
                    or observations.model_id != mt.respiratory_model_id(model)
                    or observations.settings != mt.ObservationSettings(controls["observation_rate"],
                        controls["observation_noise"], controls["observation_seed"])
                    or observations.through_s > model.duration):
                raise ValueError("The saved observations do not match the motion scenario.")
            observations = state["observations"] = replace(observations, target=target)
        planning_result = context = None
        saved = state["planning"]
        if saved is not None:
            if model is None or target is None or entry is None:
                raise ValueError("The saved plan is missing its source context.")
            context = dict(saved["context"], volume=volume, target=target, model_id=mt.respiratory_model_id(model),
                deformation=deformation, observations=observations if controls["needle_targeting_method"] != "Displayed centre" else None)
            expected_settings = mt.NeedleSettings(controls["needle_radius"], controls["needle_speed"], controls["needle_delay"])
            if (context["needle_settings"] != expected_settings or context["entry_reference"] != state["entry"]
                    or context["exclusions"] != state["exclusions"]
                    or context["route_settings"] != mt.RouteSettings(controls["needle_search_radius"], controls["needle_clearance"])
                    or context["targeting_method"] != controls["needle_targeting_method"]
                    or context["exclusion_policy"] != controls["needle_exclusion_policy"]
                    or type(context["search"]) is not bool
                    or not 0 <= context["planning_time_s"] <= model.duration
                    or context["learned_model_id"] is not None
                    and context["learned_model_id"] != getattr(state["predictor"], "model_id", None)
                    or context["observations"] is not None
                    and context["forecast_settings"] != mt.ForecastSettings(history_window_s=controls["needle_prediction_history"])):
                raise ValueError("The saved plan settings do not match the planning case.")
            planning_result = calculate_planning(context, volume, lung_mask, model, state["predictor"])
            plan, _, selection, _, error = planning_result
            if (error is not None or plan != saved["plan"]
                    or getattr(selection, "chosen_index", None) != saved["chosen_index"]):
                raise ValueError("The selected plan cannot be reproduced with this application version.")
        forecast = None
        if state["forecast"]:
            if observations is None or model is None or state["view"]["workspace"] not in (1, 3):
                raise ValueError("The saved forecast is missing its observation context.")
            forecast = calculate_forecasts(observations, model, state["time"], controls["forecast_horizon"],
                mt.ForecastSettings(history_window_s=controls["forecast_history"]), controls["forecast_uncertainty"],
                mt.UncertaintySettings(nominal_coverage=float(controls["forecast_coverage"].rstrip('%')) / 100), state["predictor"])
        if state["view"]["workspace"] in (1, 3) and (sequence is not None or model is None):
            raise ValueError("The saved workspace requires simulated lung motion.")
        if state["view"]["workspace"] == 2 and sequence is None:
            raise ValueError("The landmark workspace requires a respiratory CT sequence.")
        if sequence is None:
            resolve_source(study["source"], path)
        else:
            self._check_sequence(study, path, sequence)
        return dict(state=state, volume=volume, masks=masks, styles=styles, meshes=meshes, ct_path=ct_path,
            sequence=sequence, landmarks=landmarks, region=region, region_mesh=region_mesh,
            planning_result=planning_result, context=context, forecast=forecast,
            registration_volumes=registration_volumes)

    def _apply(self, path, prepared):
        w, s = self.owner, prepared["state"]
        self._restoring = True
        try:
            w._invalidate_registration()
            if prepared["sequence"] is None:
                w.accept_volume(prepared["volume"], masks=prepared["masks"],
                    prebuilt_meshes=prepared["meshes"], source_info=s["source_info"], source_path=prepared["ct_path"])
                w.structures = dict(prepared["styles"])
                w.scene.set_structures(w.structures)
                w.lobe_info, w.airway_info, w.imported_masks = s["lobe_info"], s["airway_info"], s["imported_masks"]
            else:
                sequence = prepared["sequence"]
                w._accept_phase(s["phase_index"], sequence.phase(s["phase_index"]), sequence=sequence)
                w._phase_styles = dict(s["styles"])
                w.structures = dict(prepared["styles"])
                w.scene.set_structures(w.structures)
                w.landmarks = prepared["landmarks"]
            w._rebuild_structure_tree()
            w.scene._update_bounds()
            w._update_metadata()
            w._study_source_paths.update(Path(value) for value in s["source_paths"])
            w.learned_predictor, w.learning_result, w.learned_model_path = None, None, None
            for combo in (w.forecast_method, w.needle_targeting_method):
                blocked = combo.blockSignals(True)
                index = combo.findText(LEARNED_METHOD)
                if index >= 0:
                    combo.removeItem(index)
                combo.blockSignals(blocked)
            w.learning_model_status.setText("No learned predictor loaded. Training and saved-model loading are available above.")
            w.forecast_compute.setText("Compute mathematical baselines")
            if s["predictor"] is not None:
                w.accept_learned_predictor(s["predictor"], result=s["learning_result"])
            blocked = w.motion_amplitude.blockSignals(True)
            w.motion_amplitude.setMaximum(min(30., np.floor(s["deformation"].height * .20 / 1.8 * 10) / 10)
                if s["deformation"] is not None else 30.)
            w.motion_amplitude.blockSignals(blocked)
            for name, value in s["view"]["controls"].items():
                set_control(getattr(w, name), value)
            w.window_level()
            w._texture_opacity_changed(w.opacity.value())
            w.motion_model, w.deformation, w.motion_time = s["model"], s["deformation"], s["time"]
            w.target, w.target_observations = s["target"], s["observations"]
            if isinstance(w.target, mt.AnnotatedTarget):
                w.scene.set_target(w.target, mesh=prepared["region_mesh"])
            else:
                w.scene.set_target(w.target)
            w.needle_entry_reference, w.needle_exclusions = s["entry"], s["exclusions"]
            w._needle_entry_volume = w.volume if s["entry"] is not None else None
            w._needle_exclusions_volume = w.volume if s["exclusions"] else None
            w._rebuild_exclusion_list()
            data = w.target_observations
            w.observation_plot.set_data(data)
            w.observation_readout.setText(f"{len(data.times_s)} samples · history 0–{data.through_s:g} s\nSimulated observations restored from planning case."
                if data is not None else "No observations recorded.")
            w.observation_export.setEnabled(data is not None)
            w.evaluation_export.setEnabled(data is not None)
            result = prepared["planning_result"]
            if result is not None:
                w.needle_plan, w.needle_evaluation, w.needle_route_selection, w.needle_constraint_evaluation, _ = result
                context = prepared["context"]
                context["mask_key"] = w._needle_lung_key()
                w._needle_route_context = context if w.needle_route_selection is not None else None
                if w.needle_plan is not None:
                    w._needle_plan_volume = w.volume
                    w._needle_plan_mask_key = w._needle_lung_key()
                    w._needle_plan_constraint_key = w._needle_constraints_key()
            panel = w.annotation_panel
            panel.reset()
            panel._study = w.ct_sequence if w.ct_sequence is not None else w.volume
            panel.region, panel.region_phase = prepared["region"], s["annotation"]["phase"]
            panel.color = s["annotation"]["color"]
            set_control(panel.show_region, s["annotation"]["visible"])
            set_control(panel.diameter, s["annotation"]["diameter"])
            set_control(panel.scope, s["annotation"]["scope"])
            panel._region_mesh = prepared["region_mesh"]
            if panel.region is not None:
                panel._show_mesh(panel._region_mesh, panel.region, panel.region.revision)
            blocked = w.controls.blockSignals(True)
            w.controls.setCurrentIndex(s["view"]["workspace"])
            w.controls.blockSignals(blocked)
            w.motion_seed.setEnabled(w.breathing_pattern.currentText() != "Regular")
            w.extract_airways_action.setEnabled(w.ct_sequence is None and w.controls.currentIndex() == 0)
            w.crosshair = np.asarray(s["view"]["crosshair"]).copy()
            for view, zoom in zip(w.slices, s["view"]["zoom"]):
                view.canvas.zoom = zoom
            w.main_splitter.setSizes(s["view"]["splitter"])
            camera = s["view"]["camera"]
            w.scene.camera.position, w.scene.camera.focal_point, w.scene.camera.up = camera[:3]
            w.scene.camera.parallel_projection, w.scene.camera.parallel_scale, w.scene.camera.view_angle = camera[3:]
            w.forecast_result = prepared["forecast"]
            w._sync_registration()
            registration = s["registration"]
            if registration is not None:
                for name in ("reference", "moving"):
                    control = getattr(w, "registration_" + name)
                    blocked = control.blockSignals(True)
                    control.setCurrentIndex(registration[name])
                    control.blockSignals(blocked)
                set_control(w.registration_method, registration["method"])
                w.registration_result = registration["result"]
                w._registration_volumes = prepared["registration_volumes"]
            w._sync_registration()
            w._update_route_display()
            w.refresh()
            self.path = path
            w.setWindowTitle(f"{path.stem} | MotionTwin")
            self._saved_token = self._token()
            w.status.setText(f"Planning case restored: {path.name} · playback paused.")
        finally:
            self._restoring = False


def calculate_forecasts(data, model, origin, horizon, settings, uncertainty_enabled, uncertainty_settings, predictor, cancelled=None):
    target = data.target
    times, positions = data.observations_through(origin)
    methods = (*BASELINE_METHODS, LEARNED_METHOD) if predictor is not None else BASELINE_METHODS
    fits,predictions,unavailable,regions,region_evaluations,region_unavailable={},{},{},{},{},{}
    for method in BASELINE_METHODS:
        try:
            fit=fit_baseline(times,positions,method,origin_s=origin,settings=settings)
            predictions[method]=fit.predict(origin+horizon)
            fits[method]=fit
            if uncertainty_enabled:
                try:
                    regions[method]=calibrate_forecast_region(times,positions,method,origin_s=origin,horizon_s=horizon,
                        settings=uncertainty_settings,forecast_settings=settings,cancelled=cancelled)
                except ValueError as error:
                    region_unavailable[method]=str(error)
        except ValueError as error:
            unavailable[method]=str(error)
    if predictor is not None:
        try:
            fit=fit_learned(times,positions,predictor,origin_s=origin)
            predictions[LEARNED_METHOD]=fit.predict(origin+horizon)
            fits[LEARNED_METHOD]=fit
        except ValueError as error:
            unavailable[LEARNED_METHOD]=str(error)
        if uncertainty_enabled:
            region_unavailable[LEARNED_METHOD]="The learned point forecast has no calibrated observation-error region. Mathematical calibration is not transferred to this model."
    origins=select_validation_origins(times,through_s=origin,horizon_s=horizon,settings=settings)
    # evaluation labels follow the shared deformation; the fitting functions never receive them.
    weight=(data.deformation.apex_z-target.center_lps_mm[2])/data.deformation.height
    def truth_at(query):
        return np.asarray(target.center_lps_mm)+weight*model.position(query)
    labels=truth_at(origins+horizon) if len(origins) else np.empty((0,3))
    validation=evaluate_baselines(times,positions,origins,labels,horizon_s=horizon,
        settings=settings,methods=tuple(method for method in BASELINE_METHODS if method in fits) or None)
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
        methods=methods,learned_model_id=getattr(predictor,"model_id",None),
        validation=validation,history_times_s=times,history_observed_lps_mm=positions,
        forecast_times_s=future_times,truth_times_s=truth_times,truth_curve_lps_mm=truth_curve,
        truth_position=truth_curve[-1].copy() if covered else None)


def calculate_planning(context, volume, mask, model, learned_predictor):
    target, deformation = context["target"], context["deformation"]
    settings, origin = context["needle_settings"], context["planning_time_s"]
    reference, exclusions = context["entry_reference"], context["exclusions"]
    route_settings, targeting_method = context["route_settings"], context["targeting_method"]
    observations, forecast_settings = context["observations"], context["forecast_settings"]
    search, exclusion_policy = context["search"], context["exclusion_policy"]
    entry = deformation.forward(reference, model.position(origin))
    matrix = deformation.matrix(model.position(origin))
    used_settings = RouteSettings(patch_radius_mm=route_settings.patch_radius_mm if search else 0.,
        clearance_mm=route_settings.clearance_mm)
    past_times, past_positions = observations.observations_through(origin) if observations is not None else (None, None)
    selection=None
    chosen_entry=entry
    if observations is not None:
        try:
            fit=(fit_learned(past_times,past_positions,learned_predictor,origin_s=origin)
                 if targeting_method==LEARNED_METHOD else
                 fit_baseline(past_times,past_positions,targeting_method,origin_s=origin,settings=forecast_settings))
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


