from dataclasses import fields
from hashlib import sha256
from math import prod
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile
from zlib import error as ZlibError
import json
import os
import re

import numpy as np
from scipy.interpolate import CubicHermiteSpline

import motiontwin as core
import motiontwin_learning as learning


MAX_BYTES = 512 * 1024 ** 2
MAX_MANIFEST = 16 * 1024 ** 2
MAX_ARRAYS = 1024
_CLASSES = {kind.__name__: kind for kind in (
    core.StructureStyle, core.BreathingSettings, core.LungDeformation,
    core.ResearchTarget, core.ObservationSettings, core.TargetObservations,
    core.ForecastSettings, core.NeedleSettings, core.NeedlePlan, core.NeedleEvaluation,
    core.ExclusionRegion, core.RouteSettings, core.RouteSelection, core.ForecastRouteSelection,
    core.ConstraintEvaluation, core.PredictedConstraintEvaluation, core.ExclusionMotionForecast,
    core.BaselineFit, core.BaselineEvaluation, core.UncertaintySettings, core.ForecastRegionCalibration,
    learning.LearningSettings, learning.LearnedPredictor, learning.LearnedFit, learning.LearningResult,
)}


def pack_surfaces(meshes):
    return {name: tuple(np.array(array, copy=True, order="C") for array in (
        mesh.points, np.asarray(mesh.faces).reshape(-1, 4), mesh["CT_HU"], mesh["CT_RGB"],
        mesh.point_data["Normals"] if "Normals" in mesh.point_data else np.empty((0, 3), dtype=np.float32)))
        for name, mesh in meshes.items()}


def restore_surfaces(records, volume, masks):
    if type(records) is not dict or set(records) != set(masks):
        raise ValueError("Saved display surfaces must match the case's anatomy masks.")
    import pyvista as pv
    meshes = {}
    for name, arrays in records.items():
        if (not isinstance(name, str) or not isinstance(arrays, (tuple, list)) or len(arrays) != 5
                or any(not isinstance(array, np.ndarray) for array in arrays)
                or not core._ct_surface_arrays_valid(arrays, volume)):
            raise ValueError("A saved display surface has invalid geometry or CT colours.")
        points, faces, hu, rgb, normals = arrays
        mesh = pv.PolyData(points, faces.ravel(), deep=True)
        mesh.point_data["CT_HU"], mesh.point_data["CT_RGB"] = hu.copy(), rgb.copy()
        if len(normals):
            mesh.point_data["Normals"] = normals.copy()
            mesh.point_data.active_normals_name = "Normals"
        mesh.field_data["CT_sampling_inset_mm"] = [min(volume.spacing) * .65 if "lung" in name else 0.]
        mesh.field_data["source"] = ["reference CT in physical LPS millimetres"]
        meshes[name] = mesh
    return meshes


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("The case contains duplicate JSON keys.")
        result[key] = value
    return result


def _size(shape, dtype):
    if (not isinstance(shape, (tuple, list)) or len(shape) > 4
            or any(type(value) is not int or not 0 <= value <= MAX_BYTES for value in shape)
            or dtype.fields is not None or dtype.kind not in "biuf" or dtype.itemsize not in (1, 2, 4, 8)):
        raise ValueError("The case contains an unsupported numerical array.")
    size = prod(shape) * dtype.itemsize
    if size > MAX_BYTES:
        raise ValueError("A case array exceeds the supported allocation budget.")
    return size


def _motion_fields(model):
    return dict(duration=model.duration, axes=model.axes, grid=model._grid,
                phase_x=model._phase.x, phase_c=model._phase.c,
                amplitude_x=model._amplitude.x, amplitude_c=model._amplitude.c,
                events=tuple(model.events), model_id=core.respiratory_model_id(model))


def _restore_motion(record):
    expected = {"duration", "axes", "grid", "phase_x", "phase_c", "amplitude_x", "amplitude_c", "events", "model_id"}
    if set(record) != expected:
        raise ValueError("The saved respiratory scenario is incomplete.")
    duration = core._target_number(record["duration"], "Motion duration", positive=True, maximum=1e6)
    axes, grid = np.asarray(record["axes"]), np.asarray(record["grid"])
    if (axes.shape != (3,) or axes.dtype.kind != "f" or not np.isfinite(axes).all()
            or not 0 < np.linalg.norm(axes) <= 1e6):
        raise ValueError("The saved respiratory axes are invalid.")
    def knots(values):
        return (values.ndim == 1 and values.dtype.kind == "f" and 2 <= values.size <= 200001
                and np.isfinite(values).all() and values[0] == 0. and values[-1] == duration
                and np.all(np.diff(values) > 0))
    if not knots(grid):
        raise ValueError("The saved respiratory integration grid is invalid.")
    model = core.RespiratoryModel.__new__(core.RespiratoryModel)
    model.duration, model.axes, model._grid = duration, axes.copy(), grid.copy()
    for name in ("phase", "amplitude"):
        x, coefficients = record[name + "_x"], record[name + "_c"]
        if (not isinstance(x, np.ndarray) or not isinstance(coefficients, np.ndarray)
                or not knots(x) or coefficients.shape != (4, x.size - 1)
                or coefficients.dtype.kind != "f" or not np.isfinite(coefficients).all()):
            raise ValueError("The saved respiratory spline is invalid.")
        setattr(model, "_" + name, CubicHermiteSpline.construct_fast(coefficients.copy(), x.copy()))
    events = record["events"]
    if (not isinstance(events, (list, tuple)) or not 1 <= len(events) <= 200001
            or any(not isinstance(item, (list, tuple)) or len(item) != 2
                   or not core._ct_finite_number(item[0]) or not 0 <= item[0] < duration
                   or not isinstance(item[1], core.BreathingSettings) for item in events)
            or events[0][0] != 0 or any(a[0] >= b[0] for a, b in zip(events, events[1:]))):
        raise ValueError("The saved respiratory setting history is invalid.")
    model.events = list(events)
    if core.respiratory_model_id(model) != record["model_id"]:
        raise ValueError("The saved respiratory scenario checksum does not match.")
    return model


class _Codec:
    def __init__(self, arrays=None):
        self.arrays = {} if arrays is None else arrays
        self.used = set()
        self.nodes = self.bytes = 0

    def visit(self, depth):
        self.nodes += 1
        if depth > 64 or self.nodes > 500000:
            raise ValueError("The case contains an excessively complex state.")

    def encode(self, value, depth=0):
        self.visit(depth)
        if isinstance(value, np.generic):
            value = value.item()
        if value is None or type(value) is bool:
            return value
        if type(value) is int and abs(value) <= 2 ** 63 - 1:
            return value
        if type(value) is float and np.isfinite(value):
            return value
        if isinstance(value, str) and len(value.encode("utf-8")) <= 8 * 1024 ** 2:
            return value
        if isinstance(value, np.ndarray):
            self.bytes += _size(value.shape, value.dtype)
            if self.bytes > MAX_BYTES or len(self.arrays) >= MAX_ARRAYS:
                raise ValueError("The case exceeds its supported array budget.")
            if value.dtype.kind == "f" and not np.isfinite(value).all():
                raise ValueError("Case arrays must contain finite values.")
            packed = value.dtype == np.dtype(bool)
            stored = np.packbits(value.reshape(-1)) if packed else value.copy(order="C")
            name = f"a{len(self.arrays)}.npy"
            self.arrays[name] = stored
            return {"$": "array", "name": name, "shape": list(value.shape), "dtype": value.dtype.str,
                    "packed": packed, "sha256": sha256(stored.tobytes()).hexdigest()}
        if type(value) is dict:
            if any(type(key) not in (str, int) for key in value):
                raise ValueError("Case dictionary keys must be text or integers.")
            return {"$": "dict", "items": [[self.encode(key, depth + 1), self.encode(item, depth + 1)]
                                            for key, item in value.items()]}
        if type(value) is list:
            return [self.encode(item, depth + 1) for item in value]
        if type(value) is tuple:
            return {"$": "tuple", "items": [self.encode(item, depth + 1) for item in value]}
        if type(value) is core.RespiratoryModel:
            return {"$": "RespiratoryModel", "fields": self.encode(_motion_fields(value), depth + 1)}
        kind = _CLASSES.get(type(value).__name__)
        if kind is not None and type(value) is kind:
            values = {field.name: getattr(value, field.name) for field in fields(kind) if field.init}
            return {"$": kind.__name__, "fields": self.encode(values, depth + 1)}
        raise ValueError(f"Unsupported case value: {type(value).__name__}.")

    def decode(self, value, depth=0):
        self.visit(depth)
        if value is None or type(value) in (str, bool, int, float):
            return self._scalar(value)
        if type(value) is list:
            return [self.decode(item, depth + 1) for item in value]
        if type(value) is not dict or "$" not in value:
            raise ValueError("The case contains an unsupported encoded value.")
        tag = value["$"]
        if tag == "array":
            if set(value) != {"$", "name", "shape", "dtype", "packed", "sha256"}:
                raise ValueError("The case array description is incomplete.")
            name = value["name"]
            if not isinstance(name, str) or name not in self.arrays or name in self.used:
                raise ValueError("The case has a missing or repeated array reference.")
            dtype = np.dtype(value["dtype"])
            self.bytes += _size(value["shape"], dtype)
            if self.bytes > MAX_BYTES or type(value["packed"]) is not bool:
                raise ValueError("The case exceeds its supported array budget.")
            stored = self.arrays[name]
            if sha256(stored.tobytes()).hexdigest() != value["sha256"]:
                raise ValueError("A case array checksum does not match its contents.")
            count = prod(value["shape"])
            if value["packed"]:
                if (dtype != np.dtype(bool) or stored.dtype != np.dtype("uint8")
                        or stored.shape != ((count + 7) // 8,)
                        or count % 8 and stored[-1] & ((1 << (8 - count % 8)) - 1)):
                    raise ValueError("The case contains an invalid packed mask.")
                result = np.unpackbits(stored, count=count).view(np.bool_).reshape(value["shape"])
            else:
                if dtype.kind == "b" or stored.shape != tuple(value["shape"]) or stored.dtype != dtype:
                    raise ValueError("The case array does not match its saved shape and type.")
                result = stored
            if result.dtype.kind == "f" and not np.isfinite(result).all():
                raise ValueError("Case arrays must contain finite values.")
            self.used.add(name)
            return result
        if tag in ("dict", "tuple") and set(value) == {"$", "items"} and type(value["items"]) is list:
            if tag == "tuple":
                return tuple(self.decode(item, depth + 1) for item in value["items"])
            result = {}
            for pair in value["items"]:
                if type(pair) is not list or len(pair) != 2:
                    raise ValueError("The case dictionary has invalid entries.")
                key, item = (self.decode(item, depth + 1) for item in pair)
                if type(key) not in (str, int) or key in result:
                    raise ValueError("The case dictionary has duplicate or invalid keys.")
                result[key] = item
            return result
        if set(value) != {"$", "fields"} or not isinstance(tag, str):
            raise ValueError("The case contains an invalid object record.")
        values = self.decode(value["fields"], depth + 1)
        if type(values) is not dict:
            raise ValueError("A case object requires named fields.")
        if tag == "RespiratoryModel":
            return _restore_motion(values)
        kind = _CLASSES.get(tag)
        if kind is None or set(values) != {field.name for field in fields(kind) if field.init}:
            raise ValueError("The case contains an unsupported object or incompatible fields.")
        return kind(**values)

    def _scalar(self, value):
        # apply the same limits to saved and opened primitive values.
        self.encode(value)
        return value


def check_case_destination(path, protected_paths=()):
    path = Path(path)
    if path.suffix.lower() != ".motiontwin" or path.is_dir():
        raise ValueError("Save a planning case to a .motiontwin file.")
    resolved = path.resolve()
    sources = [Path(source) for source in protected_paths]
    for source in tuple(sources):
        if source.is_file():
            sources.extend(core._ct_external_payload(source))
    for source in sources:
        if (os.path.normcase(str(resolved)) == os.path.normcase(str(source.resolve()))
                or source.is_dir() and resolved.is_relative_to(source.resolve())
                or path.exists() and source.exists() and os.path.samefile(path, source)):
            raise ValueError("A planning case cannot overwrite a source or protected project file.")
    return path


def write_case(path, state, *, protected_paths=(), before_replace=None):
    if type(state) is not dict:
        raise ValueError("A planning case requires a named state dictionary.")
    protected_paths = tuple(protected_paths)
    path = check_case_destination(path, protected_paths)
    codec = _Codec()
    encoded = codec.encode(state)
    content = _json(dict(format="MotionTwin planning case", version=1, state=encoded,
                         sha256=sha256(_json(encoded)).hexdigest()))
    if len(content) > MAX_MANIFEST:
        raise ValueError("The planning case manifest exceeds its supported size.")
    def check():
        check_case_destination(path, protected_paths)
        if before_replace is not None:
            before_replace()
        check_case_destination(path, protected_paths)
    with core.atomic_output(path, binary=True, before_replace=check) as stream:
        with ZipFile(stream, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("manifest.json", content)
            for name, array in codec.arrays.items():
                with archive.open(name, "w", force_zip64=True) as output:
                    np.lib.format.write_array(output, array, allow_pickle=False)
    return path


def read_case(path):
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            names = {member.filename for member in members}
            if (not 1 <= len(members) <= MAX_ARRAYS + 1 or len(names) != len(members)
                    or "manifest.json" not in names
                    or sum(member.file_size for member in members) > MAX_BYTES + MAX_MANIFEST
                    or any(member.file_size < 0 or member.file_size > MAX_BYTES for member in members)
                    or any(name != "manifest.json" and not re.fullmatch(r"a[0-9]{1,4}\.npy", name) for name in names)):
                raise ValueError("The case has unsupported archive members or allocations.")
            if archive.getinfo("manifest.json").file_size > MAX_MANIFEST:
                raise ValueError("The case manifest exceeds its supported size.")
            record = json.loads(archive.read("manifest.json").decode("utf-8"), object_pairs_hook=_unique,
                                parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Case numbers must be finite.")))
            if (type(record) is not dict or set(record) != {"format", "version", "state", "sha256"}
                    or record["format"] != "MotionTwin planning case" or type(record["version"]) is not int
                    or record["version"] != 1 or sha256(_json(record["state"])).hexdigest() != record["sha256"]):
                raise ValueError("The case version, format or manifest checksum is incompatible.")
            arrays = {}
            for name in names - {"manifest.json"}:
                with archive.open(name) as source:
                    version = np.lib.format.read_magic(source)
                    if version not in ((1, 0), (2, 0)):
                        raise ValueError("The case uses an unsupported array encoding.")
                    reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                              else np.lib.format.read_array_header_2_0)
                    shape, fortran, dtype = reader(source)
                    if fortran or _size(shape, dtype) != archive.getinfo(name).file_size - source.tell():
                        raise ValueError("The case has invalid array headers or allocations.")
                with archive.open(name) as source:
                    arrays[name] = np.lib.format.read_array(source, allow_pickle=False)
            codec = _Codec(arrays)
            state = codec.decode(record["state"])
            if type(state) is not dict or codec.used != set(arrays):
                raise ValueError("The case has unused arrays or an invalid root state.")
            return state
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError,
            UnicodeError, RecursionError, EOFError, RuntimeError, BadZipFile, ZlibError) as error:
        raise ValueError(f"Cannot open planning case: {error}") from error


def _locations(path, case_path):
    absolute = Path(path).expanduser().resolve()
    try:
        relative = os.path.relpath(absolute, Path(case_path).expanduser().resolve().parent)
    except ValueError:
        relative = None
    return dict(relative=relative, absolute=str(absolute))


def _candidates(record, case_path):
    if (not isinstance(record, dict) or not isinstance(record.get("absolute"), str)
            or not Path(record["absolute"]).is_absolute()
            or record.get("relative") is not None and (not isinstance(record["relative"], str)
                or not record["relative"] or Path(record["relative"]).is_absolute())):
        raise ValueError("The saved source location is invalid.")
    paths = []
    if record.get("relative") is not None:
        paths.append(Path(case_path).resolve().parent / record["relative"])
    paths.append(Path(record["absolute"]))
    return tuple(dict.fromkeys(path.resolve() for path in paths))


def _file_hash(path):
    before = core._ct_file_signature((path,))
    digest = sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 ** 2), b""):
            digest.update(block)
    if before != core._ct_file_signature((path,)):
        raise ValueError("A source changed while the case was being checked.")
    return digest.hexdigest()


def file_record(path, case_path):
    path = Path(path).expanduser().resolve()
    return dict(_locations(path, case_path), sha256=_file_hash(path))


def _valid_file_record(record):
    return (isinstance(record, dict) and set(record) == {"relative", "absolute", "sha256"}
            and isinstance(record["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]))


def resolve_file(record, case_path):
    if not _valid_file_record(record):
        raise ValueError("The saved file identity is invalid.")
    for path in _candidates(record, case_path):
        if path.is_file() and _file_hash(path) == record["sha256"]:
            return path
    raise ValueError("A case source file is missing or its contents changed.")


def _header(source):
    return {name: list(getattr(source.header, name)) for name in ("shape", "spacing", "origin", "direction")}


def source_record(path, case_path):
    source = core._ct_sequence_source(Path(path).expanduser().resolve())
    result = dict(_locations(source.path, case_path), header=_header(source),
                  files=[file_record(member, case_path) for member in source.files if member.is_file()])
    if source.signature != core._ct_file_signature(source.files):
        raise ValueError("A CT source changed while the case was being checked.")
    return result


def resolve_source(record, case_path):
    if (not isinstance(record, dict) or set(record) != {"relative", "absolute", "header", "files"}
            or not isinstance(record["files"], list) or not 1 <= len(record["files"]) <= 100000
            or any(not _valid_file_record(item) for item in record["files"])):
        raise ValueError("The saved CT source identity is invalid.")
    for path in _candidates(record, case_path):
        if not path.exists():
            continue
        try:
            source = core._ct_sequence_source(path)
            files = tuple(member for member in source.files if member.is_file())
            if (_header(source) != record["header"] or len(files) != len(record["files"])
                    or any(_file_hash(member) != item["sha256"] for member, item in zip(files, record["files"]))):
                continue
            if source.signature != core._ct_file_signature(source.files):
                raise ValueError("A CT source changed while the case was being checked.")
            return path
        except (OSError, ValueError):
            continue
    raise ValueError("A case CT or segmentation source is missing, changed or geometrically incompatible.")
