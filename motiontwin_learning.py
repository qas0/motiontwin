from dataclasses import asdict, dataclass, field
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import threading
from uuid import uuid4
import zipfile

import numpy as np

from motiontwin import (
    BASELINE_METHODS, BREATHING_PATTERNS, BreathingSettings, ForecastSettings,
    RespiratoryModel, fit_baseline, respiratory_model_id, check_export_destination,
    ForecastFit, PiecewiseLinearForecastSegment, _ct_external_payload,
)


LEARNED_METHOD = "Learned MLP"
LEARNING_HORIZONS = (.5, 1., 2., 3., 5.)
LEARNING_METHODS = (*BASELINE_METHODS, LEARNED_METHOD)
FEATURE_VERSION = "relative-lps-101-at-10hz-plus-horizon-1"
HISTORY_S = 10.
RATE_HZ = 10.
WINDOW_SAMPLES = 101
INPUT_SIZE = WINDOW_SAMPLES*3+1
MAX_EFFECTIVE_HORIZON_S = 5.2
_TRAIN_LOCK = threading.Lock()
_ARRAY_KEYS = ("x_mean", "x_scale", "y_mean", "y_scale", "w0", "b0", "w1", "b1", "w2", "b2")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _number(value, label, minimum, maximum, *, integer=False):
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating))
            or not np.isfinite(value) or not minimum<=value<=maximum or integer and int(value)!=value):
        raise ValueError(f"{label} must be {'an integer' if integer else 'finite'} between {minimum:g} and {maximum:g}.")
    return int(value) if integer else float(value)


def _immutable(array):
    if np.asarray(array).dtype.kind not in "iuf":
        raise ValueError("Learned parameters and preprocessing must be numeric arrays.")
    array=np.asarray(array,dtype="<f4")
    if not np.isfinite(array).all():
        raise ValueError("Learned parameters and preprocessing must be finite.")
    return np.frombuffer(array.tobytes(),dtype="<f4").reshape(array.shape)


def _cancel(cancelled):
    if cancelled is not None and cancelled():
        raise InterruptedError("Learned forecast training cancelled; no partial result was published.")


@contextmanager
def _training_lock(cancelled):
    while not _TRAIN_LOCK.acquire(timeout=.1):
        _cancel(cancelled)
    try:
        _cancel(cancelled)
        yield
    finally:
        _TRAIN_LOCK.release()


@dataclass(frozen=True)
class LearningSettings:
    preset: str = "Quick"
    seed: int = 1729
    hidden_units: int = 64
    max_epochs: int = 80
    patience: int = 10
    batch_size: int = 256
    learning_rate: float = .001

    def __post_init__(self):
        if self.preset not in ("Quick", "Extended"):
            raise ValueError("Choose Quick or Extended learned training.")
        for name,low,high in (("seed",0,2**32-1),("hidden_units",8,128),
                ("max_epochs",1,300),("patience",1,50),("batch_size",16,2048)):
            object.__setattr__(self,name,_number(getattr(self,name),name.replace("_"," "),low,high,integer=True))
        object.__setattr__(self,"learning_rate",_number(self.learning_rate,"Learning rate",1e-5,.05))


@dataclass(frozen=True)
class LearnedPredictor:
    _manifest_json: str = field(repr=False)
    _arrays: tuple = field(repr=False)

    def __post_init__(self):
        try:
            manifest=json.loads(self._manifest_json)
        except (ValueError, TypeError) as error:
            raise ValueError("The learned model manifest is invalid.") from error
        if (not isinstance(manifest,dict) or manifest.get("format_version")!=1
                or manifest.get("feature_version")!=FEATURE_VERSION
                or manifest.get("history_s")!=HISTORY_S or manifest.get("rate_hz")!=RATE_HZ
                or manifest.get("max_effective_horizon_s")!=MAX_EFFECTIVE_HORIZON_S):
            raise ValueError("The learned model uses an unsupported preprocessing protocol.")
        settings=LearningSettings(**manifest.get("settings",{}))
        width=settings.hidden_units
        if manifest.get("architecture")!=[INPUT_SIZE,width,width,3]:
            raise ValueError("The learned checkpoint architecture is incompatible with its settings.")
        shapes=((INPUT_SIZE,),(INPUT_SIZE,),(3,),(3,),
            (width,INPUT_SIZE),(width,),(width,width),(width,),(3,width),(3,))
        if not isinstance(self._arrays,(tuple,list)) or len(self._arrays)!=len(shapes):
            raise ValueError("The learned checkpoint has incomplete parameters.")
        arrays=tuple(_immutable(array) for array in self._arrays)
        if any(array.shape!=shape for array,shape in zip(arrays,shapes)):
            raise ValueError("The learned checkpoint parameter shapes do not match its architecture.")
        if np.any(arrays[1]<=0) or np.any(arrays[3]<=0):
            raise ValueError("Learned preprocessing scales must be positive.")
        if (not isinstance(manifest.get("best_epoch"),int) or not 1<=manifest["best_epoch"]<=settings.max_epochs
                or manifest.get("training_label")!="simulated_true_future_minus_last_noisy_observation"
                or manifest.get("normalization_split")!="train"):
            raise ValueError("The learned checkpoint has incomplete training provenance.")
        object.__setattr__(self,"_manifest_json",_json(manifest))
        object.__setattr__(self,"_arrays",arrays)

    @property
    def manifest(self):
        return json.loads(self._manifest_json)

    @property
    def model_id(self):
        digest=sha256(self._manifest_json.encode("utf-8"))
        for name,array in zip(_ARRAY_KEYS,self._arrays):
            digest.update(name.encode("ascii"))
            digest.update(array.tobytes())
        return digest.hexdigest()

    def _predict_displacement(self,features):
        features=np.asarray(features,dtype=float)
        if features.ndim!=2 or features.shape[1]!=INPUT_SIZE or features.shape[0]>2001 or not np.isfinite(features).all():
            raise ValueError("Learned inference requires bounded finite observed features.")
        x_mean,x_scale,y_mean,y_scale,w0,b0,w1,b1,w2,b2=(array.astype(float) for array in self._arrays)
        with np.errstate(over="ignore",invalid="ignore"):
            normalized=(features-x_mean)/x_scale
            hidden=np.maximum(normalized@w0.T+b0,0.)
            hidden=np.maximum(hidden@w1.T+b1,0.)
            prediction=(hidden@w2.T+b2)*y_scale+y_mean
        if not np.isfinite(prediction).all():
            raise ValueError("Learned inference produced non-finite values for this observed history.")
        return prediction.astype(float)


def _observed_window(times_s,observed_lps_mm,origin_s):
    origin=_number(origin_s,"Forecast origin",0.,1e6)
    raw_times=np.asarray(times_s)
    raw_positions=np.asarray(observed_lps_mm)
    if (raw_times.dtype.kind not in "iuf" or raw_times.ndim!=1 or not 1<=raw_times.size<=100001
            or not np.isfinite(raw_times).all() or np.any(raw_times<0) or np.any(np.diff(raw_times)<=0)
            or raw_positions.dtype.kind not in "iuf" or raw_positions.shape!=(raw_times.size,3)):
        raise ValueError("Learned forecasting requires increasing numeric times and matching LPS observations.")
    count=int(np.searchsorted(raw_times,origin,side="right"))
    if count<WINDOW_SAMPLES:
        raise ValueError("Learned forecasting needs ten seconds of observed history at 10 Hz (101 samples).")
    times=raw_times[count-WINDOW_SAMPLES:count].astype(float)
    positions=raw_positions[count-WINDOW_SAMPLES:count].astype(float)
    if not np.isfinite(positions).all():
        raise ValueError("Available learned-forecast observations must be finite.")
    if not np.allclose(np.diff(times),1./RATE_HZ,rtol=0,atol=1e-8):
        raise ValueError("This learned checkpoint requires a 10 Hz recording; no resampling or rate fallback is applied.")
    if origin-times[-1]>.11+1e-10:
        raise ValueError("The learned forecast requires a recent observation within 0.11 seconds of the origin.")
    return origin,times,positions


def _piecewise_network(predictor, history, anchor, age):
    x_mean,x_scale,y_mean,y_scale,w0,b0,w1,b1,w2,b2=(array.astype(float) for array in predictor._arrays)
    intercept=(np.r_[history.ravel(),age]-x_mean)/x_scale
    slope=np.zeros(INPUT_SIZE)
    slope[-1]=1./x_scale[-1]
    pieces=[(0.,5.,intercept,slope)]
    # a scalar horizon makes every ReLU layer piecewise affine; split at every activation change.
    for weight,bias in ((w0,b0),(w1,b1)):
        divided=[]
        for lower,upper,intercept,slope in pieces:
            offset=weight@intercept+bias
            rate=weight@slope
            roots=np.divide(-offset,rate,out=np.full_like(offset,np.inf),where=rate!=0.)
            knots=np.unique(np.r_[lower,roots[(roots>lower)&(roots<upper)],upper])
            for start,end in zip(knots[:-1],knots[1:]):
                active=offset+rate*(start+(end-start)/2.)>0.
                divided.append((float(start),float(end),np.where(active,offset,0.),np.where(active,rate,0.)))
        pieces=divided
    result=[]
    for lower,upper,intercept,slope in pieces:
        position=(w2@(intercept+slope*lower)+b2)*y_scale+y_mean+anchor
        velocity=(w2@slope)*y_scale
        result.append(PiecewiseLinearForecastSegment(lower,upper,tuple(position),tuple(velocity)))
    return tuple(result)


@dataclass(frozen=True)
class LearnedFit(ForecastFit):
    predictor: LearnedPredictor = field(repr=False)
    origin_s: float
    last_observation_s: float
    history_start_s: float
    _relative_history: np.ndarray = field(repr=False)
    _anchor_lps_mm: np.ndarray = field(repr=False)
    _segments: tuple = field(init=False,repr=False)
    _segment_starts: np.ndarray = field(init=False,repr=False)
    _segment_positions: np.ndarray = field(init=False,repr=False)
    _segment_velocities: np.ndarray = field(init=False,repr=False)
    method: str = field(default=LEARNED_METHOD,init=False)
    n_samples: int = field(default=WINDOW_SAMPLES,init=False)
    frequency_hz: None = field(default=None,init=False)
    note: str = field(default="Trained MLP; past noisy 10 Hz observations only. Synthetic training, fixed simulator axes.",init=False)

    def __post_init__(self):
        if not isinstance(self.predictor,LearnedPredictor):
            raise ValueError("Load a validated learned checkpoint before forecasting.")
        origin=_number(self.origin_s,"Forecast origin",0.,1e6)
        last=_number(self.last_observation_s,"Last observation",0.,origin)
        start=_number(self.history_start_s,"History start",0.,last)
        history=np.asarray(self._relative_history,dtype=float)
        anchor=np.asarray(self._anchor_lps_mm,dtype=float)
        if (history.shape!=(WINDOW_SAMPLES,3) or anchor.shape!=(3,) or not np.isfinite(history).all()
                or not np.isfinite(anchor).all() or abs(last-start-HISTORY_S)>1e-8
                or origin-last>.11+1e-10 or np.any(history[-1]!=0)):
            raise ValueError("The learned fit must capture a complete observed window and finite anchor.")
        for name,value in (("origin_s",origin),("last_observation_s",last),("history_start_s",start)):
            object.__setattr__(self,name,value)
        for name,array in (("_relative_history",history),("_anchor_lps_mm",anchor)):
            object.__setattr__(self,name,np.frombuffer(array.tobytes(),dtype=float).reshape(array.shape))
        segments=_piecewise_network(self.predictor,history,anchor,origin-last)
        object.__setattr__(self,"_segments",segments)
        for name,values in (("_segment_starts",[piece.lower_s for piece in segments]),
                ("_segment_positions",[piece.position_lps_mm for piece in segments]),
                ("_segment_velocities",[piece.velocity_lps_mm_s for piece in segments])):
            array=np.asarray(values,dtype=float)
            object.__setattr__(self,name,np.frombuffer(array.tobytes(),dtype=float).reshape(array.shape))

    def predict(self,query_times_s):
        raw=np.asarray(query_times_s)
        if raw.dtype.kind not in "iuf" or raw.ndim>1 or not 1<=raw.size<=2001:
            raise ValueError("Learned prediction times must be a scalar or bounded numeric vector.")
        query=raw.astype(float)
        effective=query-self.last_observation_s
        if (not np.isfinite(query).all() or np.any(query<self.origin_s-1e-10)
                or np.any(query>self.origin_s+5.+1e-10) or np.any(effective>MAX_EFFECTIVE_HORIZON_S+1e-10)):
            raise ValueError("Learned forecasts support the origin through five seconds ahead within the trained horizon.")
        horizons=(query-self.origin_s).ravel()
        indices=np.maximum(0,np.searchsorted(self._segment_starts,horizons,side="right")-1)
        prediction=self._segment_positions[indices]+(horizons-self._segment_starts[indices])[:,None]*self._segment_velocities[indices]
        if not np.isfinite(prediction).all():
            raise ValueError("Learned inference produced non-finite positions for this observed history.")
        return prediction[0] if raw.ndim==0 else prediction

    def linear_segments(self,lower_horizon_s,upper_horizon_s):
        lower=_number(lower_horizon_s,"Intercept interval start",0.,5.)
        upper=_number(upper_horizon_s,"Intercept interval end",lower,5.)
        if upper<=lower:
            return ()
        result=[]
        for piece in self._segments:
            start,end=max(lower,piece.lower_s),min(upper,piece.upper_s)
            if end>start:
                position=np.asarray(piece.position_lps_mm)+(start-piece.lower_s)*np.asarray(piece.velocity_lps_mm_s)
                result.append(PiecewiseLinearForecastSegment(start,end,tuple(position),piece.velocity_lps_mm_s))
        return tuple(result)


def fit_learned(times_s,observed_lps_mm,predictor,*,origin_s):
    if not isinstance(predictor,LearnedPredictor):
        raise ValueError("Load or train a learned checkpoint before forecasting.")
    origin,times,positions=_observed_window(times_s,observed_lps_mm,origin_s)
    return LearnedFit(predictor,origin,float(times[-1]),float(times[0]),positions-positions[-1],positions[-1])


def _profile_counts(settings):
    return (64,16,32) if settings.preset=="Quick" else (128,32,64)


def _physical_profile_id(subject,model=None):
    if model is None:
        model=RespiratoryModel(BreathingSettings(subject["amplitude_mm"],subject["rate_bpm"],subject["pattern"],subject["profile_seed"]))
    times=np.arange(601,dtype=float)/RATE_HZ
    displacement=subject["transfer_weight"]*model.position(times)
    return sha256(np.asarray(displacement,dtype="<f8").tobytes()).hexdigest()


def _subject_catalogue(settings,split,count):
    split_index=("train","validation","test").index(split)
    records=[]
    for index in range(count):
        streams=np.random.SeedSequence([settings.seed,split_index,index,83917]).spawn(3)
        rng=np.random.default_rng(streams[0])
        record=dict(subject_id=f"{split}-{index:04d}",split=split,pattern=BREATHING_PATTERNS[index%4],
            amplitude_mm=float(rng.uniform(4.,16.)),rate_bpm=float(rng.uniform(8.,24.)),
            noise_std_mm=float(rng.uniform(0.,1.5)),transfer_weight=float(rng.uniform(.1,1.)),
            offset_lps_mm=rng.uniform(-120.,120.,3).tolist(),
            profile_seed=int(streams[1].generate_state(1)[0]),observation_seed=int(streams[2].generate_state(1)[0]),
            origin_s=float(rng.integers(300,451)/10.))
        record["profile_id"]=_physical_profile_id(record)
        records.append(record)
    return tuple(records)


def _profile(subject,through_s):
    model=RespiratoryModel(BreathingSettings(subject["amplitude_mm"],subject["rate_bpm"],subject["pattern"],subject["profile_seed"]))
    subject["profile_id"]=_physical_profile_id(subject,model)
    times=np.arange(round(through_s*RATE_HZ)+1,dtype=float)/RATE_HZ
    truth=np.asarray(subject["offset_lps_mm"])+subject["transfer_weight"]*model.position(times)
    observed=truth+np.random.default_rng(subject["observation_seed"]).normal(0.,subject["noise_std_mm"],truth.shape)
    return times,observed,truth,respiratory_model_id(model)


def _training_arrays(subjects,settings,*,cancelled=None):
    features,labels=[],[]
    for subject in subjects:
        _cancel(cancelled)
        times,observed,truth,model_id=_profile(subject,55.2)
        subject["model_id"]=model_id
        model=RespiratoryModel(BreathingSettings(subject["amplitude_mm"],subject["rate_bpm"],subject["pattern"],subject["profile_seed"]))
        # each profile stays within its predetermined split, including all overlapping windows.
        split_index=("train","validation","test").index(subject["split"])
        rng=np.random.default_rng(np.random.SeedSequence([settings.seed,split_index,subject["profile_seed"],5729]))
        origins=np.arange(20.,48.01,2.) if subject["split"]=="train" else np.array([20.,30.,40.,48.])
        for origin in origins:
            _cancel(cancelled)
            end=round(origin*RATE_HZ)
            relative=observed[end-WINDOW_SAMPLES+1:end+1]-observed[end]
            horizons=np.r_[rng.uniform(0.,MAX_EFFECTIVE_HORIZON_S,4),rng.choice((0.,.5,1.,2.,3.,5.,5.2))]
            # training labels may use simulator truth; the feature vector contains observations and horizon only.
            future=np.asarray(subject["offset_lps_mm"])+subject["transfer_weight"]*model.position(origin+horizons)
            features.extend(np.column_stack((np.tile(relative.ravel(),(len(horizons),1)),horizons)))
            labels.extend(future-observed[end])
    return np.asarray(features,dtype=np.float32),np.asarray(labels,dtype=np.float32)


def _software():
    versions=dict(python=platform.python_version(),numpy=np.__version__)
    for name in ("torch","scipy"):
        try:
            versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name]="unavailable"
    return versions


def _summaries(rows):
    summaries=[]
    index={(row["subject_id"],row["horizon_s"],row["method"]):row for row in rows}
    for pattern in ("All",*BREATHING_PATTERNS):
        for method in LEARNING_METHODS:
            for horizon in LEARNING_HORIZONS:
                relevant=[row for row in rows if row["method"]==method and row["horizon_s"]==horizon
                    and (pattern=="All" or row["pattern"]==pattern)]
                for kind in ("true","observed"):
                    errors=[row[f"{kind}_error_mm"] for row in relevant if row["status"]=="available"]
                    deltas=[]
                    for row in relevant:
                        base=index[(row["subject_id"],horizon,"Constant position")]
                        if row["status"]=="available" and base["status"]=="available":
                            deltas.append(row[f"{kind}_error_mm"]-base[f"{kind}_error_mm"])
                    summaries.append(dict(pattern=pattern,method=method,horizon_s=horizon,truth_kind=kind,
                        attempted=len(relevant),available=len(errors),unavailable=len(relevant)-len(errors),
                        mean_error_mm=float(np.mean(errors)) if errors else None,
                        rmse_mm=float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
                        paired_count=len(deltas),paired_mean_delta_mm=float(np.mean(deltas)) if deltas else None))
    return tuple(summaries)


@dataclass(frozen=True)
class LearningResult:
    predictor: LearnedPredictor
    _manifest_json: str = field(repr=False)
    _subjects_json: str = field(repr=False)
    _history_json: str = field(repr=False)
    _rows_json: str = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.predictor,LearnedPredictor):
            raise ValueError("A learning result requires a frozen learned predictor.")
        manifest=json.loads(self._manifest_json)
        subjects=json.loads(self._subjects_json)
        history=json.loads(self._history_json)
        rows=json.loads(self._rows_json)
        if (manifest.get("predictor_id")!=self.predictor.model_id or not history
                or {subject["split"] for subject in subjects}!={"train","validation","test"}
                or len({subject["subject_id"] for subject in subjects})!=len(subjects)
                or len({subject["profile_id"] for subject in subjects})!=len(subjects)):
            raise ValueError("Learning results require separate subjects and the frozen evaluated predictor.")
        test_ids={subject["subject_id"] for subject in subjects if subject["split"]=="test"}
        expected={(subject,method,horizon) for subject in test_ids for method in LEARNING_METHODS for horizon in LEARNING_HORIZONS}
        actual={(row["subject_id"],row["method"],row["horizon_s"]) for row in rows}
        if actual!=expected or len(rows)!=len(expected):
            raise ValueError("The learning result must retain every attempted held-out forecast.")
        for row in rows:
            if row["predictor_id"]!=self.predictor.model_id or row["status"] not in ("available","unavailable"):
                raise ValueError("Held-out rows must identify the frozen model and their availability.")
            if row["status"]=="available" and any(not np.isfinite(row[f"{kind}_error_mm"]) or row[f"{kind}_error_mm"]<0 for kind in ("true","observed")):
                raise ValueError("Held-out error metrics must be finite physical distances.")
        for name,value in (("_manifest_json",manifest),("_subjects_json",subjects),("_history_json",history),("_rows_json",rows)):
            object.__setattr__(self,name,_json(value))

    @property
    def manifest(self):
        return json.loads(self._manifest_json)

    @property
    def subjects(self):
        return tuple(json.loads(self._subjects_json))

    @property
    def history(self):
        return tuple(json.loads(self._history_json))

    @property
    def rows(self):
        return tuple(json.loads(self._rows_json))

    @property
    def summaries(self):
        return _summaries(self.rows)

    @property
    def result_id(self):
        return sha256((self._manifest_json+self._subjects_json+self._history_json+self._rows_json).encode("utf-8")).hexdigest()

    def export_csv(self,path,protected_paths=()):
        path=check_export_destination(path,protected_paths)
        records=[dict(record_kind="protocol",details_json=self._manifest_json)]
        records.extend(dict(record_kind="subject",**subject) for subject in self.subjects)
        records.extend(dict(record_kind="training_epoch",**epoch) for epoch in self.history)
        records.extend(dict(record_kind="test_summary",**summary) for summary in self.summaries)
        records.extend(dict(record_kind="test_forecast",**row) for row in self.rows)
        fields=list(dict.fromkeys(key for record in records for key in record))
        temporary=Path(path).with_name(f"{uuid4().hex}.part")
        try:
            with temporary.open("x",encoding="utf-8",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader()
                for record in records:
                    writer.writerow({key:_json(value) if isinstance(value,(dict,list,tuple)) else value for key,value in record.items()})
            check_export_destination(path,protected_paths)
            os.replace(temporary,path)
        finally:
            temporary.unlink(missing_ok=True)
        return Path(path)


def train_motion_predictor(settings=None,*,progress=None,cancelled=None):
    settings=LearningSettings() if settings is None else settings
    if not isinstance(settings,LearningSettings) or any(hook is not None and not callable(hook) for hook in (progress,cancelled)):
        raise ValueError("Learning requires validated settings and callable progress/cancellation hooks.")
    notify=progress or (lambda message:None)
    _cancel(cancelled)
    counts=_profile_counts(settings)
    train=list(_subject_catalogue(settings,"train",counts[0]))
    validation=list(_subject_catalogue(settings,"validation",counts[1]))
    notify(f"Generating {len(train)} training and {len(validation)} validation profiles…")
    x_train,y_train=_training_arrays(train,settings,cancelled=cancelled)
    x_validation,y_validation=_training_arrays(validation,settings,cancelled=cancelled)
    x_mean=x_train.mean(axis=0,dtype=np.float64).astype(np.float32)
    x_scale=np.maximum(x_train.std(axis=0,dtype=np.float64),1e-4).astype(np.float32)
    y_mean=y_train.mean(axis=0,dtype=np.float64).astype(np.float32)
    y_scale=np.maximum(y_train.std(axis=0,dtype=np.float64),1e-4).astype(np.float32)
    x=(x_train-x_mean)/x_scale
    y=(y_train-y_mean)/y_scale
    vx=(x_validation-x_mean)/x_scale
    vy=(y_validation-y_mean)/y_scale
    _cancel(cancelled)
    try:
        import torch
    except ImportError as error:
        raise ValueError('Training requires PyTorch. Install the optional learning dependency with pip install ".[learning]".') from error
    notify("Training the two-layer CPU MLP; validation selects the saved epoch…")
    history=[]
    best_loss=np.inf
    best_epoch=0
    best=None
    _cancel(cancelled)
    with _training_lock(cancelled):
        original_threads=torch.get_num_threads()
        try:
            torch.set_num_threads(min(2,original_threads))
            with torch.random.fork_rng(devices=[]):
                torch.random.default_generator.manual_seed(settings.seed)
                network=torch.nn.Sequential(torch.nn.Linear(INPUT_SIZE,settings.hidden_units),torch.nn.ReLU(),
                    torch.nn.Linear(settings.hidden_units,settings.hidden_units),torch.nn.ReLU(),torch.nn.Linear(settings.hidden_units,3))
                optimizer=torch.optim.Adam(network.parameters(),lr=settings.learning_rate)
                tx,ty=torch.from_numpy(x),torch.from_numpy(y)
                tvx,tvy=torch.from_numpy(vx),torch.from_numpy(vy)
                permutation_rng=np.random.default_rng(np.random.SeedSequence([settings.seed,1193]))
                for epoch in range(1,settings.max_epochs+1):
                    _cancel(cancelled)
                    network.train()
                    total_loss=0.
                    order=permutation_rng.permutation(len(tx))
                    for start in range(0,len(order),settings.batch_size):
                        _cancel(cancelled)
                        indices=order[start:start+settings.batch_size]
                        optimizer.zero_grad(set_to_none=True)
                        loss=torch.nn.functional.mse_loss(network(tx[indices]),ty[indices])
                        if not torch.isfinite(loss):
                            raise ValueError("Learned training produced a non-finite loss; no model was published.")
                        loss.backward()
                        optimizer.step()
                        total_loss+=float(loss.detach())*len(indices)
                    network.eval()
                    with torch.inference_mode():
                        val_loss=float(torch.nn.functional.mse_loss(network(tvx),tvy))
                    if not np.isfinite(val_loss):
                        raise ValueError("Validation produced a non-finite loss; no model was published.")
                    improved=val_loss<best_loss-1e-6
                    if improved:
                        best_loss,best_epoch=val_loss,epoch
                        best=tuple(parameter.detach().numpy().copy() for parameter in network.parameters())
                    history.append(dict(epoch=epoch,train_mse=total_loss/len(tx),validation_mse=val_loss,best=improved))
                    notify(f"Epoch {epoch}/{settings.max_epochs} · train {history[-1]['train_mse']:.5f} · validation {val_loss:.5f} · best {best_epoch}")
                    if epoch-best_epoch>=settings.patience:
                        break
        finally:
            torch.set_num_threads(original_threads)
    _cancel(cancelled)
    source_checksums={name:sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ("motiontwin.py","motiontwin_learning.py")}
    manifest=dict(format_version=1,feature_version=FEATURE_VERSION,settings=asdict(settings),
        history_s=HISTORY_S,rate_hz=RATE_HZ,max_effective_horizon_s=MAX_EFFECTIVE_HORIZON_S,
        architecture=[INPUT_SIZE,settings.hidden_units,settings.hidden_units,3],
        normalization_split="train",training_label="simulated_true_future_minus_last_noisy_observation",
        train_samples=len(x),validation_samples=len(vx),train_subjects=len(train),validation_subjects=len(validation),
        best_epoch=best_epoch,epochs_completed=len(history),best_validation_mse=best_loss,
        loss_units="mean squared standardized 3D components",train_subject_ids=[row["profile_id"] for row in train],
        validation_subject_ids=[row["profile_id"] for row in validation],software=_software(),source_sha256=source_checksums,
        simulator_scope="Synthetic respiratory profiles, fixed RespiratoryModel axes and shared-affine transfer weights; no patient validation.",
        physical_profile_id_definition="sha256_scaled_noiseless_lps_displacement_at_10hz_0_through_60s_excludes_offset_noise_and_split",
        normalization_training_sha256=sha256(x_train.tobytes()+y_train.tobytes()).hexdigest())
    predictor=LearnedPredictor(_json(manifest),(x_mean,x_scale,y_mean,y_scale,*best))
    frozen_id=predictor.model_id
    notify(f"Frozen best epoch {best_epoch}. Evaluating separate held-out profiles against all three baselines…")
    test=list(_subject_catalogue(settings,"test",counts[2]))
    rows=[]
    for index,subject in enumerate(test):
        _cancel(cancelled)
        origin=subject["origin_s"]
        times,observed,_,model_id=_profile(subject,origin)
        subject["model_id"]=model_id
        prefix_id=sha256(np.asarray(times,dtype="<f8").tobytes()+np.asarray(observed,dtype="<f8").tobytes()).hexdigest()
        fits,unavailable={},{}
        for method in LEARNING_METHODS:
            _cancel(cancelled)
            try:
                fits[method]=(fit_learned(times,observed,predictor,origin_s=origin) if method==LEARNED_METHOD else
                    fit_baseline(times,observed,method,origin_s=origin,settings=ForecastSettings()))
            except ValueError as error:
                unavailable[method]=str(error)
        # test outcomes are generated only after the trained model is frozen and every causal fit exists.
        future_times,future_observed,future_truth,_=_profile(subject,origin+max(LEARNING_HORIZONS))
        for method in LEARNING_METHODS:
            for horizon in LEARNING_HORIZONS:
                _cancel(cancelled)
                query=origin+horizon
                sample=round(query*RATE_HZ)
                true=future_truth[sample]
                noisy=future_observed[sample]
                prediction=None
                reason=unavailable.get(method,"")
                if method in fits:
                    try:
                        prediction=fits[method].predict(query)
                    except ValueError as error:
                        reason=str(error)
                rows.append(dict(subject_id=subject["subject_id"],pattern=subject["pattern"],method=method,
                    origin_s=origin,horizon_s=horizon,query_s=query,status="available" if prediction is not None else "unavailable",
                    reason=reason,predicted_lps_mm=None if prediction is None else prediction.tolist(),
                    true_lps_mm=true.tolist(),observed_lps_mm=noisy.tolist(),
                    true_error_mm=None if prediction is None else float(np.linalg.norm(prediction-true)),
                    observed_error_mm=None if prediction is None else float(np.linalg.norm(prediction-noisy)),
                    true_residual_lps_mm=None if prediction is None else (true-prediction).tolist(),
                    observed_residual_lps_mm=None if prediction is None else (noisy-prediction).tolist(),
                    prefix_sha256=prefix_id,predictor_id=frozen_id,model_id=model_id))
        notify(f"Held-out profile {index+1}/{len(test)} evaluated.")
    _cancel(cancelled)
    identities=[row["profile_id"] for row in (*train,*validation,*test)]
    all_subjects=(*train,*validation,*test)
    if (len(set(identities))!=len(identities)
            or any(len({row[key] for row in all_subjects})!=len(all_subjects)
                for key in ("model_id","profile_seed","observation_seed"))):
        raise ValueError("A respiratory profile was duplicated across learning splits.")
    result_manifest=dict(manifest,predictor_id=frozen_id,test_subjects=len(test),
        test_horizons_s=list(LEARNING_HORIZONS),methods=list(LEARNING_METHODS),
        evaluation_label_populations=["simulated_true_target_centre","later_noisy_observation"],
        model_frozen_before_test=True,selection_used_test_outcomes=False,
        test_profile_ids=[row["profile_id"] for row in test],
        interpretation="One synthetic simulator family and shared axes; profiles, not patients. Outcomes are not intervention results.")
    return LearningResult(predictor,_json(result_manifest),_json([*train,*validation,*test]),_json(history),_json(rows))


def _checkpoint_destination(path,protected_paths):
    path=Path(path)
    if path.suffix.lower()!=".npz":
        raise ValueError("Save a learned checkpoint to a .npz file.")
    resolved=path.resolve()
    sources=[Path(source) for source in protected_paths]
    for source in tuple(sources):
        if source.is_file():
            sources.extend(_ct_external_payload(source))
        elif source.is_dir():
            sources.extend(member for member in source.iterdir() if member.is_file())
    for source in sources:
        if (resolved==source.resolve() or source.is_dir() and resolved.is_relative_to(source.resolve())
                or path.exists() and source.exists() and os.path.samefile(path,source)):
            raise ValueError("A learned checkpoint cannot overwrite a protected source or project file.")
    return path


def save_predictor(predictor,path,protected_paths=()):
    if not isinstance(predictor,LearnedPredictor):
        raise ValueError("Only a validated learned predictor can be saved.")
    path=_checkpoint_destination(path,protected_paths)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(f"{uuid4().hex}.part")
    metadata=dict(manifest=predictor.manifest,model_id=predictor.model_id)
    try:
        with temporary.open("xb") as stream:
            np.savez_compressed(stream,metadata=np.frombuffer(_json(metadata).encode("utf-8"),dtype=np.uint8),
                **dict(zip(_ARRAY_KEYS,predictor._arrays)))
        _checkpoint_destination(path,protected_paths)
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def load_predictor(path):
    path=Path(path)
    try:
        with path.open("rb") as stream:
            content=stream.read(2_000_001)
        if len(content)>2_000_000:
            raise ValueError("The learned checkpoint exceeds its supported size.")
        with zipfile.ZipFile(BytesIO(content)) as archive:
            members=archive.infolist()
            if (len(members)!=len(_ARRAY_KEYS)+1 or len({member.filename for member in members})!=len(members)
                    or {member.filename for member in members}!={name+".npy" for name in ("metadata",*_ARRAY_KEYS)}
                    or any(member.file_size>1_000_000 for member in members)
                    or sum(member.file_size for member in members)>2_000_000):
                raise ValueError("The learned checkpoint has unsupported members or allocations.")
            headers={}
            for member in members:
                with archive.open(member) as stream:
                    version=np.lib.format.read_magic(stream)
                    if version==(1,0):
                        shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
                    elif version==(2,0):
                        shape,fortran,dtype=np.lib.format.read_array_header_2_0(stream)
                    else:
                        raise ValueError("The learned checkpoint uses an unsupported array encoding.")
                    headers[member.filename]=(shape,fortran,dtype)
                    if (not shape or len(shape)>2 or any(isinstance(size,bool) or not 0<size<=200_000 for size in shape)
                            or fortran or dtype.hasobject or dtype.kind not in "uif"
                            or stream.tell()+int(np.prod(shape))*dtype.itemsize!=member.file_size):
                        raise ValueError("The learned checkpoint contains invalid array headers or allocations.")
                    if member.filename=="metadata.npy":
                        if len(shape)!=1 or shape[0]>200_000 or dtype!=np.dtype("uint8"):
                            raise ValueError("The learned checkpoint metadata is invalid.")
                        record=json.loads(stream.read(shape[0]).decode("utf-8"))
            settings=LearningSettings(**record["manifest"]["settings"])
            width=settings.hidden_units
            shapes=((INPUT_SIZE,),(INPUT_SIZE,),(3,),(3,),
                (width,INPUT_SIZE),(width,),(width,width),(width,),(3,width),(3,))
            for name,expected in zip(_ARRAY_KEYS,shapes):
                shape,fortran,dtype=headers[name+".npy"]
                if shape!=expected or dtype!=np.dtype("<f4"):
                    raise ValueError("The learned checkpoint parameter headers do not match the architecture.")
        with np.load(BytesIO(content),allow_pickle=False) as archive:
            if set(archive.files)!={"metadata",*_ARRAY_KEYS}:
                raise ValueError("The learned checkpoint has incomplete or unexpected parameter names.")
            metadata=archive["metadata"]
            if metadata.dtype!=np.uint8 or metadata.ndim!=1 or metadata.size>200_000:
                raise ValueError("The learned checkpoint metadata is invalid.")
            record=json.loads(metadata.tobytes().decode("utf-8"))
            predictor=LearnedPredictor(_json(record["manifest"]),tuple(archive[key] for key in _ARRAY_KEYS))
        if predictor.model_id!=record["model_id"]:
            raise ValueError("The learned checkpoint checksum does not match its contents.")
        return predictor
    except (OSError,KeyError,TypeError,UnicodeError,ValueError,RecursionError,RuntimeError,EOFError,OverflowError,zipfile.BadZipFile) as error:
        raise ValueError(f"Cannot load learned checkpoint: {error}") from error
