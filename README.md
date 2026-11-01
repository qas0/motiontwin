# MotionTwin

A desktop CT viewer with linked axial, coronal and sagittal views, discrete respiratory CT playback, landmark displacement measurements, 3D lung rendering, five-lobe segmentation, central airway extraction and a simulated breathing preview with research targets and timed observations. Built with Python, PySide6, PyVistaQt and VTK.

## Run

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\run.py
```

In VS Code, open `run.py` and choose **Run Python File**, or press F5. The launcher selects the project environment and working directory. `python -m motiontwin` also opens the app.

For a first installation with Python 3.11 or 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\run.py
```

## Files

- `run.py`: interface, CT panels, 3D rendering and playback controls.
- `motiontwin.py`: image loading, physical coordinates, lung surfaces and respiratory model.
- `motiontwin_charts.py`: interactive observation, forecast, landmark, coverage and insertion charts.
- `motiontwin_results.py`: insertion results, computed events and linked animation controls.
- `motiontwin_routes.py`: cached route decisions, candidate details and the linked reference entry-patch map.
- `motiontwin_learning.py`: synthetic training, held-out comparisons, validated model checkpoints and learned inference.
- `motiontwin_learning_ui.py`: training controls, cancellation, loss plots and the learned forecasting report.
- `motiontwin_trajectory.py`: physical trajectory frames, bounded oblique CT sampling and aligned segmentation sections.
- `motiontwin_trajectory_ui.py`: linked needle-aligned CT inspection and millimetre navigation.
- `motiontwin_annotation.py`: physical voxel brushes, bounded undo/redo, region measurements and cropped boundary reconstruction.
- `motiontwin_annotation_ui.py`: annotation tools, draft/application lifecycle and linked CT/3D display.
- `requirements.txt` and `pyproject.toml`: dependencies and package settings.
- `THIRD_PARTY_LICENSES.txt`: public CT licence and attribution.

Local data, reference material, display caches and development tests are excluded from GitHub.

## Imaging

**File > Open CT** loads static NIfTI, NRRD and MetaImage volumes. **Open DICOM series** loads one series. Imported CTs can be viewed without masks; segmented surfaces require aligned masks.

**File > Import segmentation** accepts an aligned static 3D label image in NIfTI, NRRD or MetaImage format. Choose a positive label, or combine all nonzero labels, then give the region a name and identify it as lung tissue or another structure. Selecting an existing name replaces that structure's mask while keeping its display settings. Masks must match the CT's dimensions, spacing, origin and orientation.

The structure tree lists the current scan and its actual segmentation layers. Select a structure to rename it, choose its colour or adjust its **Surface / overlay** opacity. Its **Show** checkbox controls both the 3D surface and its CT overlay; enable **CT segmentation overlays** to display overlays on the CT panels. Hiding an overlapping structure leaves the other visible layers intact.

**CT-coloured surface** uses colours sampled from the source CT on the selected 3D surface. Choosing a colour switches that surface to solid colour. The separate **3D CT texture opacity** slider adjusts the reconstructed CT texture. Display settings apply to the current study and reset when another CT is opened.

Click a CT panel to position the shared crosshair. Scroll to move through slices; Ctrl+scroll zooms. The CT display controls adjust window/level. Drag the 3D view to rotate it, or use a camera preset and **Fit**.

The top toolbar provides the same file actions as the File menu. Drag the divider beside the sidebar to resize it. Red, green and yellow headers identify the CT planes and contain their slice sliders and physical positions. File controls are unavailable while a scan or mask is loading.

Coordinates use LPS millimetres. Axial images show anterior at the top; coronal and sagittal images show superior at the top. Overlays and scrolling use the scan's physical spacing and orientation, including oblique scans. Invalid imports leave the current study open. Adding or replacing a mask preserves the camera, crosshair and current motion preview. Changing display settings reuses the existing surfaces and sampled CT planes.

A verified local public CT opens at startup. Without it, the viewer starts empty. **File > Open example CT** downloads the roughly 40 MB Slicer chest example. Its lung envelopes and dense tissue layers are threshold-derived display masks, not expert segmentations or verified vascular anatomy. The source licence is included in `THIRD_PARTY_LICENSES.txt`.

The example stores packed masks and bounded meshes in `data/public-example/display-cache.npz`. Cache validity depends on the source checksum, image geometry and display settings. Missing or invalid caches are rebuilt. The first reconstruction measured about 32 seconds on the development laptop. Initial reconstruction and renderer setup can briefly pause the interface; normal launches reuse the saved geometry.

## Target annotation

In **Imaging → Target annotation**, choose **New region**, then drag **Paint** on an existing CT view. **Erase** refines the same binary voxel mask. Brush diameter is measured in millimetres. **Current slice** edits source voxels intersected by that CT plane; oblique planes can intersect multiple source layers. **3D sphere** also edits neighbouring slices. Continuous strokes fill the space between pointer samples. Oblique and reflected CT grids use their original physical geometry.

Choose **Navigate**, or Shift+click, to move the crosshair while editing. Slice scrolling and Ctrl+scroll zoom remain available. A physical brush outline shows its footprint. **Undo / Redo** (Ctrl+Z / Ctrl+Y) operate on whole strokes; **Clear** is also undoable. Escape cancels the current stroke. History retains recent edits within a 32 MiB budget; an individual edit exceeding that budget is rejected and rolled back.

The linked CT overlays update while drawing. The 3D boundary is reconstructed after each completed edit in a worker using cropped source-grid masks and the existing bounded surface pipeline. No CT pixels, anatomical masks or reference meshes are modified. Reference volume uses foreground voxel count times physical voxel volume; centroid uses voxel centres. **Box L/P/S** is the outer voxel-cell bounding box along the LPS axes, rather than a lesion diameter. **Centre** brings the applied region into the linked CT crosshair.

**Apply region** accepts a nonempty draft. **Cancel** restores the previously applied region; **Replace region** starts a fresh draft and replaces the previous annotation only when applied. **Remove** explicitly deletes the applied annotation. **Show region** controls its matching CT overlays and 3D boundary. Drawing locks study/phase changes until Apply or Cancel; closing with a draft asks whether to discard it.

There is one user-defined region per open study, retained for this session. On an acquired CT sequence it belongs only to the phase where it was drawn; switching phases hides it, and returning restores it. It is not automatically propagated. During the static-CT breathing preview the annotation follows the same declared affine transform as the anatomy, with measurements still reported in the reference frame.

Annotation is manual and does not establish automatic lesion detection or expert review. It remains independent of the existing simulated spherical planning target. Region-based planning and saving/reopening complete cases are separate future features.

## Lung lobes

**File > Lung lobes > Generate from current CT** computes five lobe masks from the open scan using lungmask's fused LTRCLobes and R231 models. This optional operation runs in a worker with one slice per batch and at most four CPU threads. It downloads two checksum-verified model files, approximately 124 MB each, when they are missing. A run on the example CT took about six minutes on the development laptop; generation is separate from normal startup and playback.

To enable generation on a new installation, install the optional dependency from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[lobes]"
```

The viewer can display saved or supplied lobe masks without this dependency. **Import five-lobe labels** accepts an aligned NIfTI, NRRD or MetaImage label volume with this mapping:

| Label | Structure |
|---|---|
| 0 | Background |
| 1 | Left upper lobe |
| 2 | Left lower lobe |
| 3 | Right upper lobe |
| 4 | Right middle lobe |
| 5 | Right lower lobe |

All five labels must be present; additional, fractional and misaligned labels are rejected. Each lobe has its own colour, visibility and surface/overlay opacity. The original envelopes and high-density detail remain in the tree, initially hidden so the lobe boundaries can be inspected. The CT values, existing surfaces and current motion reference remain unchanged.

`data/lobes/lobe-cache.npz` stores the five label regions, bounded surfaces, colours and method provenance. Its fingerprint covers all CT voxels and physical geometry. The matching result opens automatically with that scan; a missing, invalid or different-source cache leaves the standard CT viewer available. Generating or importing another result replaces this cache. Replace lobe masks together through **Import five-lobe labels**; ordinary single-structure imports cannot alter part of the recorded lobe set.

Normal viewing uses the saved lobe masks and surfaces without importing the segmentation models.

These are **automated estimates, not expert-reviewed lobe boundaries**. Inspect their coloured overlays against the CT; fissures and dense tissue can affect segmentation quality. Method and model attribution are retained in `THIRD_PARTY_LICENSES.txt`.

## Central airways

In **Imaging**, position the crosshair inside the dark tracheal air column above the main bronchial split. Choose **File > Airways > Extract from tracheal seed**, check the LPS coordinates and seed intensity, then press **Extract**. The coordinates can also be adjusted in the dialog. On the bundled CTChest example, LPS **X 4.57, Y 10.35, Z −75.25 mm** provides a tracheal seed. Extraction is unavailable in Motion because its seed must refer to the original static CT.

The operation grows a six-connected region through source air voxels, increasing its upper HU threshold until rapid growth or a physical size limit indicates possible spread into lung air spaces. It refines the last threshold in one-HU steps. Broad lung regions, exterior air, tissue seeds and insufficient extraction are rejected. On the example CT, extraction and caching took about eight seconds and retained 22,756 voxels at an upper threshold of −840 HU. No additional package, model download or network connection is required.

The cyan **Trachea and bronchi** layer has independent visibility, colour and opacity in the CT overlays and 3D view. Adding or replacing it preserves the lobes, existing surfaces, camera, crosshair and current motion reference. An airway mask alone does not enable respiratory simulation. The approach follows the seeded workflow described by the [Slicer Airway Segmentation extension](https://github.com/Slicer/SlicerAirwaySegmentation/blob/master/README.md); MotionTwin uses its own conservative growth limits.

**Import aligned airway mask** accepts a static NIfTI, NRRD or MetaImage mask on exactly the CT's physical grid. It must have background zero and one positive foreground label forming a single six-connected tree. Empty, fractional, disconnected or misaligned masks leave the current study unchanged. Ordinary structure imports cannot replace a recorded airway result; use the airway import action instead.

`data/airways/airways-cache.npz` stores the mask, bounded surface and method provenance with a fingerprint of the source CT and its geometry. A matching saved result opens automatically with the CT, independently of the lobe cache. A different or invalid cache is ignored; extraction runs only when requested.

Viewing the saved airway and lobe layers does not load the lobe-generation models. Source fingerprints, label validity and mesh checksums are verified on each load.

The result represents the **central airway lumen**, including the trachea, main bronchi and supported proximal branches. Distal branches may be incomplete, particularly with the example's 2.5 mm slice spacing. The growth limits and resulting segmentation are not clinically validated or expert-reviewed. Inspect the overlays against the source scan.

## Respiratory CT sequences

**File > Open 4D CT sequence**, also available as **4D CT** in the toolbar, opens a JSON file listing the phases of one patient's respiratory CT study. The existing four-view layout remains in place. A **Respiratory phases** panel provides a selector, slider and Previous/Next buttons; all three CT panels and the 3D viewport change to the selected phase together.

Supply separate static 3D NIfTI, NRRD or MetaImage volumes, or a directory containing one classic single-frame DICOM CT series for each phase. Phase order is explicit, independent of filenames. For example, save the following as `sequence.json` beside the named images:

```json
{
  "version": 1,
  "name": "Respiratory CT study",
  "segments": [
    {"id": "left_lung", "label": 1, "name": "Left lung", "color": "#79b5bf", "kind": "lung"},
    {"id": "right_lung", "label": 2, "name": "Right lung", "color": "#8ec6cc", "kind": "lung"}
  ],
  "phases": [
    {"percent": 0, "time_s": 0, "image": "phase00.nrrd", "segmentation": "labels00.nrrd"},
    {"percent": 50, "time_s": 2, "image": "phase50.nrrd", "segmentation": "labels50.nrrd"}
  ]
}
```

Paths are relative to the JSON file unless absolute. Use forward slashes in JSON paths, or escape Windows backslashes. The example describes the format; its image files must come from your dataset.

- Provide 2–100 phases with unique, strictly increasing percentages from 0 inclusive to 100 exclusive. A percentage identifies a respiratory phase; it is not elapsed seconds.
- `time_s` is optional. If used, supply finite, nonnegative, strictly increasing values for every phase. The viewer displays these supplied times without inventing timing for untimed phases.
- All CT phases must share dimensions, spacing, origin and direction. Every segmentation must already align with its own phase. The loader validates all image headers before accepting the sequence; it performs no registration or resampling. DICOM identifiers, when present, must agree on patient, study and frame of reference.
- `segmentation` is optional for each phase. Omit the top-level `segments` list when none are supplied. Segment labels must be positive integers with unique IDs and names; unknown foreground labels are rejected. IDs use letters, digits and underscores, starting with a letter or underscore. Declared labels absent from a phase produce no surface there. Use `kind: "other"` for structures outside lung tissue.
- Only the selected phase's supplied masks produce segmentation overlays and surfaces. An unsegmented phase displays its CT volume without borrowing another phase's lung anatomy or the bundled example's cached masks.

Each phase must reference a distinct CT source and, when provided, a distinct segmentation source. CT and segmentation paths must also be separate.

Navigation preserves the world crosshair, camera, slice zoom, window/level and display edits for shared segment IDs. Source files are checked again before use; missing, replaced or invalid phase data leaves the current displayed phase in place. Voxel validation and surface preparation run when a phase is first requested, so a later phase with invalid pixel labels can be rejected even after its header passed the initial check.

The loader reads pixels on demand and normally caches at most two phases within a 512 MiB array budget, including CT voxels, masks and surface arrays. The built-in ten-phase example retains up to six phases within the same byte budget. A phase larger than that budget can be displayed but is not retained in this cache. The active viewport has additional display allocations. Geometry is inspected without reading every phase's pixels using [SimpleITK image-information reading](https://simpleitk.readthedocs.io/en/master/link_AdvancedImageReading_docs.html).

Single 4D files, enhanced or multiframe DICOM, and directories mixing temporal series must first be exported into separate 3D phase volumes or classic single-frame CT series with their correct geometry. Opening a static CT or the static public example exits sequence mode and restores the existing simulation and segmentation tools. In sequence mode, include masks in the manifest so their phase association remains explicit.

The shared respiratory playback bar offers **Play / Pause**, **Reset**, **Loop** and a **Preview rate** in phases per second. Playback displays each supplied phase in order and keeps its CT, segmentation surfaces and landmark observations together. The preview rate controls display pacing; it does not specify CT acquisition frame rate or a patient's breathing period. Supplied timestamps remain visible without being changed. Slower loading holds the current image until the next complete phase is ready; no intermediate scans are generated.

The first Play prepares phase surfaces in a worker with progress. Pause remains available during preparation and stops it between phases; during a phase load it holds the displayed phase and discards the pending automatic switch. Manual phase selection, landmark editing, changing workspace or opening another study stops playback. Reset returns to the first supplied phase. With Loop off, playback stops at the last phase; pressing Play there starts again from the first.

Source-matched surfaces are saved separately from CT voxels in `data/phase-surfaces/` for imported sequences and `data/respiratory-example/surfaces/` for the built-in example. These are derived display caches, excluded from GitHub. Evicted phases reuse their own cached surfaces instead of repeating surface decimation on every cycle. Source signatures, physical geometry, labels, array bounds and checksums are checked; invalid surfaces regenerate. Missing or unwritable caches preserve ordinary browsing and report any playback-preparation failure. Cold preparation can take several seconds per segmented phase; valid saved surfaces are reused on subsequent openings.

## Landmark measurements

The **Landmarks** tab is available for respiratory CT sequences. Click a CT view to position the crosshair, then explicitly confirm the same anatomical feature in each supplied phase. Changing the crosshair alone never records or tracks a point. Select a reference phase to calculate signed left/posterior/superior displacement and its 3D magnitude in millimetres. Missing observations remain unmeasured; the plot and 3D path break at unmarked supplied phases. The table and plot select the corresponding CT phase.

**Export CSV** preserves positions, reference phase, provenance, optional source timestamps and missing rows. **Import points** accepts these exported coordinates for the same unchanged local sequence files. Moving or replacing CT sources requires reopening the sequence and recording annotations against the new source snapshot. Points are measured in the supplied image frame; this does not estimate registration or continuous motion.

**Respiratory example** in the toolbar, or **File > Open respiratory CT example**, opens a preset study without a file picker. The action is available on every installation. On first use, the app downloads about 700 MiB directly from the provider, checks the pinned SHA-256 hashes, and prepares all ten acquired phases (0% through 90%), their source lung masks and published expert landmark 39. A progress window provides **Cancel**. Failed or cancelled setup keeps the currently displayed study; verified phase files are reused when setup is retried. Later openings work offline. The separate **Import 4D CT** action imports the user's own sequence manifest.

The preset's reference is the provider's 10% phase. The losslessly compressed CT and mask files occupy about 199 MiB; temporary source archives are removed, and scans and derived surface caches are excluded from GitHub. Source voxel values and cropped first-voxel origin are preserved, with LPS axes checked against the original DICOM. No acquisition timestamps or extra phase images are inferred. All 40 valid expert landmarks are retained locally for all ten phases; the provider's excluded artifact point is omitted. The landmark CSV is generated against each installation's own source paths.

The POPI scans are provided for research by the Léon Bérard Cancer Center and CREATIS Laboratory, Lyon, France. Publications using the data should acknowledge those institutions and cite Vandemeulebroucke, Sarrut and Clarysse, *The POPI-model, a point-validated pixel-based breathing thorax model*, ICCR 2007. Provider attribution, source hashes and conversion details are retained beside the local data. See the [provider's dataset and reuse guidelines](https://github.com/open-vv/popi-model/blob/master/popi-model.md).

The original Slicer example remains available as a static CT with its lobes, airways and controlled breathing preview. The separate POPI example supplies acquired phase data. Synthetic development fixtures and real-example checks validate software behavior and geometry; they do not establish clinical validity.

## Motion

Observation, forecast, landmark and held-out coverage charts support **Hover** for the nearest actual sample, **Ctrl+wheel** for horizontal zoom, **middle-drag** to pan, and **Reset** or **Home** to restore the complete range. Ordinary wheel scrolling still moves the sidebar. **Expand** opens a larger linked chart with independent zoom; its component selector stays linked to the embedded view. Observation and forecast charts offer signed superior, posterior and left displacement in LPS millimetres. Chart inspection does not change recordings, fit new models or move the simulation timeline. Explicit landmark clicks retain their phase-navigation action.

Hover readouts identify each sample's actual time or supplied phase percentage, its value and available assessment counts. Missing measurements and unavailable coverage remain unmeasured. Coverage uses markers at tested horizons; uncertainty bars apply only to the computed forecast query. Clearing or replacing the source results also clears enlarged charts. The interactive charts use Qt directly and add no dependency.

Load a CT with at least one lung mask, then open **Motion**. Choose Regular, Mild irregularity, Strong irregularity or Stress test. Set base amplitude, breathing rate and an irregular-pattern seed, then press **Play**. **Pause** holds the current frame. The slider seeks within 60 seconds; release its handle to update. **Reset** restarts with the displayed settings and seed. Return to **Imaging** to view the original static CT.

After time zero, setting changes blend over one second of simulation time while preserving motion history and phase. Seeking restores the settings at that time; further changes replace the subsequent scenario. Opening another CT resets motion. Adding a mask keeps the current preview.

Frequency is integrated on a 0.01-second grid. Displacement is `(.15, .25, -1) * A(t) * sin(phase(t))` in LPS millimetres. Velocity differentiates the same amplitude and phase splines. Stress testing introduces seeded changes around 12, 24 and 38 seconds, with 0.8-second transitions.

The deformation is `u(p,t) = (apex_z - p.z) / lung_height * displacement(t)`. It fixes the apex and varies movement with height. CT samples, masks and 3D surfaces use the same affine transform. The crosshair marks a fixed world position, not a tracked lesion.

**The preview deforms one static scan; it is not acquired 4D CT.** It also deforms non-lung structures and does not model tissue mechanics, mass conservation or image registration. Positions outside the source scan are shown as background. Original scan values and mesh geometry stay unchanged.

Playback updates existing actors and samples the three current CT planes, capped at 256 pixels per side; static Imaging uses 384. A 67 ms timer follows elapsed time, skipping display frames when rendering is slower. Display frame rate does not change breathing rate or the 60-second timeline. Pausing excludes paused time; playback resumes from the displayed position.

In **Motion**, click a lung location in the CT views, set a reference radius and choose **Set at crosshair**. The complete sphere must fit within the reference scan and the union of its lung masks. Selection during breathing is mapped back into the reference CT. The amber **simulated research target** follows the same affine deformation as the anatomy, including its changing shape and exact slice intersections. **Go to target** centres the crosshair on its current position; **Clear** removes it. Returning to Imaging shows its reference position. This is an explicit experimental target, not a lesion detected in the CT. Opening another study clears it; incompatible lung-mask replacements remove it.

Set the observation rate, per-axis Gaussian noise standard deviation and noise seed. Seek to a simulation time, then choose **Record history to current time**. A 10 Hz recording through 2.35 seconds contains 24 samples at 0, 0.1, …, 2.3 seconds. Seek directly to 60 seconds for a complete history without waiting for playback. Sampling is independent of rendering speed; identical settings preserve the same noisy prefix when the history is extended. Noise affects observations only. The chart compares superior–inferior observations with simulated evaluation truth; recorded arrays are immutable snapshots. Changing the target, breathing scenario or sampling settings discards the old recording. Ordinary playback and seeking retain its labelled cutoff.

**Export observations CSV** contains noisy LPS positions, timestamps and source/sampling identifiers. **Export evaluation CSV (with truth)** additionally contains simulated true positions, seeds and available breathing-setting events. Seeds and simulator settings are withheld from observation exports to prevent reconstructing hidden truth. Evaluation metadata identifies the exact motion profile; descriptive setting events alone are not a replay recipe for arbitrary transition profiles. Future prediction code can request only past timestamps and noisy positions through `observations_through(t)`. Files are written atomically, with source-overwrite protection. These controls apply to the simulated static-CT preview; acquired POPI phases retain their separate landmark measurements and have no invented timing or lesion annotations.

### Mathematical forecasts

After recording target observations, seek to a forecast origin and choose **Look ahead** (0.1–5 seconds), then **Compute mathematical baselines**. Recording through 60 seconds and seeking back to 30 seconds allows the forecast to be checked against a later recorded outcome. **Display method** switches between the cached results: constant position holds the last noisy observation; constant velocity fits a line to the latest second; sinusoidal fit estimates a shared LPS frequency from the selected history. It searches 6–36 breaths/min independently of the simulator settings and needs at least 20 sampled seconds with sufficiently dense sampling. Insufficient or nonperiodic history gives an explicit unavailable result.

The cyan marker is the predicted future centre in physical LPS millimetres; the amber target remains at the current simulation time. CT markers appear only in intersecting slice planes. The plot shows past noisy observations and the forecast, plus separate simulated truth when the recording covers the query time. Predictions may extend beyond the recording; unknown future errors are not reported. Changing time, target, scenario or forecast settings clears stale forecasts. Changing the displayed method or image appearance reuses the results.

Historical validation compares available methods on up to 40 common past origins whose forecast outcomes precede the displayed time. The table reports mean Euclidean 3D error and 3D RMSE in millimetres. Every fit uses only observations at or before its own origin; exact simulated positions are supplied separately for scoring. Origins where a compared method fails are excluded for all compared methods. These are correlated historical checks within the selected simulated scenario, not held-out patient results or intervention outcomes.

**Export forecasts CSV** records predictions, availability reasons and fitting parameters without hidden simulator settings, seeds or truth. **Export forecast evaluation CSV** explicitly includes known simulated outcomes, their 3D errors and historical exclusions. Both use atomic writes and the same source-overwrite protection as observation exports. Acquired respiratory phases retain their separate landmark workflow; forecasts do not invent acquisition times for POPI.

### Learned respiratory forecasting

In **Motion > Motion forecasts**, choose **Train / load learned predictor**. **Train and evaluate** runs a compact CPU neural network in a cancellable worker. Quick uses 64 training, 16 validation and 32 final-test synthetic profiles; Extended uses 128, 32 and 64. The default network has two 64-unit ReLU hidden layers. Width, maximum epochs and seed are configurable. Adam minimises mean squared standardized displacement error, with mini-batches and early stopping after ten epochs without validation improvement. The best validation epoch is frozen before any final-test profiles are generated or scored.

Training requires the optional PyTorch dependency, installed from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[learning]"
```

Normal startup does not import PyTorch, train a model or load a checkpoint. Saved inference uses NumPy, so viewing and forecasting with a loaded checkpoint do not require PyTorch. Training uses at most two CPU threads and restores its previous thread and random-generator state afterwards.

The inputs are a ten-second window of 101 noisy LPS observations at 10 Hz, relative to the last available observation, plus the requested horizon. The model predicts a three-dimensional displacement from that observation. No simulator phase, respiratory settings, seeds or future positions enter its features. The checkpoint requires a 10 Hz recording and a recent observation; incompatible histories give an explicit unavailable result. Motion forecasts cover the origin through five seconds ahead, including origins between samples. Synthetic training labels may use true future positions; held-out evaluation distinguishes true-centre errors from errors against later noisy observations.

Whole profiles are separated before overlapping windows are generated. Training-only means and scales are reused for validation, test and inference. Profiles vary breathing pattern, amplitude (4–16 mm), rate (8–24 breaths/min), noise (0–1.5 mm per axis), reference offset and shared-affine transfer weight (0.1–1). Physical waveform identities and separate random streams are checked across the splits. These are simulated trajectories from one fixed-axis respiratory family, not independent patient data or learned patient biomechanics.

On successful completion, the validated model is saved atomically to `data/learning/motion-model.npz` and **Learned MLP** becomes available in the forecast selector. Record observations, seek to an origin covered by that history, then choose **Compute forecasts**. The existing markers and charts display the learned prediction alongside the three mathematical methods. Changing the display method reuses cached results. Loading different weights clears old forecasts and dependent learned needle plans while retaining observations, CT data and geometric or mathematical needle plans. On a later launch, opening the learned-predictor window loads the verified default checkpoint when available; **Load saved model** also reloads it explicitly.

The training window provides recorded training/validation losses, the selected epoch, every test forecast and a comparison at 0.5, 1, 2, 3 and 5 seconds ahead. All four methods receive the same past observations for each test profile. Availability counts include failed methods; mean error and 3D RMSE use available forecasts. Paired differences against constant position use common available cases and show their count. Pattern and outcome-population filters reuse the completed report. The historical table in Motion continues to assess mathematical baselines; the separate final-test report supplies the learned comparison. A learned predictor is not assumed to outperform the existing methods.

**Export evaluation CSV** retains the complete protocol, profile catalogue, training history, all test trials and summaries regardless of display filters. Checkpoints contain bounded numeric arrays and JSON, with preprocessing, shape, finite-value and checksum validation; loading does not execute pickled objects. Source files and loaded model checkpoints are protected from evaluation exports. Cancellation, failed training or a failed save preserves the previously active model. A checkpoint retains weights and training provenance; a full final-test report is exported separately, rather than reconstructed from weights after restart.

The learned predictor supplies point forecasts in Motion and arrival-aware endpoints in Needle. Mathematical uncertainty radii are not transferred to the neural model; its uncertainty remains explicitly uncalibrated.

### Empirical forecast regions

After recording a target history, enable **Motion > Estimate observation-error region**, choose nominal observation coverage of 80%, 90% or 95%, then compute the mathematical baselines. The selected method shows a cyan sphere at its future predicted centre and exact sphere intersections in the CT planes. The chart marks only the future query's superior–inferior projection of the radius. The amber target and original CT anatomy keep their existing behaviour. This optional assessment does not change needle endpoints, route eligibility, ranking or exclusion screening.

The radius uses joint Euclidean LPS errors from completed historical forecasts at the same look-ahead. Each historical fit sees only observations through its own origin and is scored against an actual later noisy observation. Forecast windows are spaced by at least the look-ahead or 0.5 seconds, whichever is larger, with up to 40 records and a common warm-up of at least 20 seconds. Failed historical fits are reported and excluded. The selected sorted error has rank `ceil((n + 1) * coverage)`, with at least nine valid scores; 95% requires at least nineteen. Insufficient history gives an explicit unavailable radius while available point forecasts remain usable. Longer look-aheads often need more history than this 60-second simulation provides.

The finite-rank correction follows the order-statistic construction described by [Angelopoulos and Bates](https://arxiv.org/abs/2107.07511). Rolling, correlated histories and repeated refitting here do not establish its exchangeability assumptions, so nominal coverage is a requested empirical level, not a formal coverage guarantee. Errors against noisy observations also do not calibrate probabilities for the unobserved true target centre.

Later recorded-observation coverage and simulated true-centre coverage are shown separately, after the radius is frozen. A noisy outcome is assessed only when the query matches an actual recorded sample; off-grid outcomes are not interpolated. Simulated truth is assessed only when the recording covers that query. Forecasts beyond the recording retain their historical radius without invented outcome scores. Changing the method reuses cached results; changing the forecast context clears them. The assessment is off by default and adds no startup calculation.

Forecast exports include the historical calibration origins, actual noisy outcomes, predictions, residuals, exclusions and prefix identity. Future observations and true-centre coverage appear only in the explicitly labelled evaluation export. The existing protected atomic writes also apply.

### Held-out synthetic forecast study

Define a target in **Motion**, then choose **Validate on held-out scenarios** under Mathematical forecasts. This opens a separate, cancellable study; no existing recording or manual needle entry is required. **Quick** uses 32 calibration and 32 evaluation subjects; **Extended** uses 64 of each. Each synthetic subject has one forecast origin and all three methods are evaluated at exactly 0.5, 1, 2, 3 and 5 seconds ahead. The study preserves the current scan, anatomy, scenario, observations, forecasts and insertion plan.

Subjects use split-specific random streams and distinct respiratory-profile identities. Amplitude is sampled uniformly from 4–16 mm, base rate from 8–24 breaths/min, per-axis observation-noise SD from 0–1.5 mm, and breathing pattern uniformly from the four supported patterns. Origins are sampled on a fixed 10 Hz grid between 30 and 45 seconds. The selected target and shared affine geometry remain fixed; these subjects represent varied simulated respiratory trajectories rather than acquired patients. The study captures the Motion fit-history setting and generates its own observations independently of the current recording controls.

Every method fits only its subject's past noisy prefix, once for all five horizons. Actual future sample labels are obtained afterwards. Two distinct calibration residual populations are retained: noisy-future-observation minus prediction, and simulated true-centre minus prediction. Each method/horizon receives a separate pooled radius for each population, using the same finite-rank correction and minimum score requirement described above. All radii are frozen before any evaluation subject is generated. No evaluation outcome is used to choose, enlarge or retune a radius.

**Held-out evaluation** shows the tested-horizon coverage chart, calibration counts, assessed/attempted subjects, covered/assessed outcomes, radius, and mean/RMSE 3D error with its own sample count. Switch between true-centre and observed errors or filter by breathing pattern without rerunning. Pattern views retain the pooled calibration radii; they do not imply pattern-conditional coverage. **Frozen calibration** exposes counts, ranks and unavailable reasons. **Every forecast** retains both splits and each failure. Missing fits, unavailable evaluation outcomes and insufficient calibration counts remain explicit; error statistics can remain available when coverage cannot be assessed.

**Export study evaluation CSV** writes one versioned protocol manifest, the complete subject catalogue, frozen radii, overall/per-pattern evaluation summaries and every forecast record. Signed LPS residual vectors are retained alongside their norms, with observation-prefix, model, software and code identities. This is an explicitly simulated evaluation export containing seeds and true labels. Writes are atomic and protected against source overwrites; changed reference inputs or protocol settings reject stale exports. The study runs only when requested and adds no startup work.

This study supplies held-out residual evidence within the declared simulator mixture. It does not train a learned predictor or change route selection. The shared anatomy, fixed respiratory axes, model-family advantage for regular breathing, finite subject counts and unavailable-fit selection limit interpretation. Longer-horizon calibration here is separate from the Stage 16 rolling-history display; no automatic transfer to a different target, dataset or planner is performed.

### Straight-needle insertion

Define a target in **Motion**, then open **Needle**. Position the CT crosshair at a manually chosen chest-wall location and press **Set entry at crosshair**. Entries must be inside the oriented reference CT and outside its available lung masks. This checks geometric inclusion only; skin is not detected or validated. **Go to entry** returns to the selected position, and **Clear** removes it and its path.

Set shaft radius, insertion speed and execution delay, then choose **Build path to displayed target centre**. The finite path joins the entry to the target centre displayed at that planning instant, independently of forecasting. Declared exclusions are checked when provided. Its endpoint stays fixed while the target and anatomy move. The 3D view shows a physical cylindrical shaft and conical tip, with thin centreline annotations that stay readable through the anatomy. CT panels show the finite path and inserted centreline only where they cross the physical slice slab. Original CT pixels, masks and anatomical meshes remain unchanged.

**Play insertion** waits for the execution delay, advances at the selected millimetres per second and stops at arrival. The depth slider advances or retracts the needle and seeks the corresponding respiratory time. **Restart** returns to the planning instant. Playback follows elapsed simulation time, independently of displayed frames. Insertions that would finish beyond the 60-second motion timeline are rejected. Returning to Imaging hides the needle; the stored path can be revisited. Target, breathing, lung-mask or insertion-setting changes require rebuilding; observation noise and display settings do not change the geometric path.

Evaluation reports arrival tip-to-target-centre distance, the minimum distance during insertion, first tip-centre contact and first finite inserted-centreline contact. Tests use the actual affine-deformed target, including its changing shape. The execution interval excludes the waiting period. A 5 ms time grid with local-minimum and contact refinement is a numerical interval check, not a proof of continuous collision freedom. Target contact concerns the tip centre and centreline; exclusion constraints additionally include the physical needle radius. Target contact is not a clinical success measure.

After building a path, choose **Inspect insertion results**. The separate window shows the stored centre-distance trace, normalized target-contact ratios, or actual exclusion-clearance bound. Contact uses the affine target boundary at ratio 1; a fixed physical radius is not a contact threshold on the centre-distance chart. Clearance includes needle radius and is compared with the configured margin. With no evaluated exclusion regions it remains **Unassessed**. The genuine waiting samples remain visible for distance and contact; clearance begins at insertion start, and all summary minima and contacts use execution only.

Select a computed event to read its meaning, then use **Go to selected event** to seek its exact calculated time. Clicking a trace seeks the nearest stored sample; hovering, zooming and selecting an event do not move the animation or recompute the plan. The live cursor follows the existing insertion playback. **Play insertion**, **Restart insertion** and the existing CSV export are also available in this window. Imaging permits result inspection while motion actions are disabled. Changing a plan input clears open results and enlarged charts. Predicted exclusion screening, when present, is labelled separately from actual execution.

**Export insertion evaluation CSV** writes the fixed path, settings, an interval summary and the timed trace with explicitly named simulated true target positions. Source-overwrite protection and atomic writes also apply here. Acquired respiratory CT phases retain their separate landmark workflow; this insertion preview uses the controlled static-CT simulation.

### Needle-aligned CT inspection

After building a current path, choose **Needle > Inspect CT along trajectory**. A separate nonmodal window shows two perpendicular longitudinal CT planes through the full fixed path and a movable cross-section normal to it. Opening pauses playback and preserves the original CT panels, camera, crosshair and stored plan. No prediction, route search or execution evaluation is rerun.

Use the millimetre position control, slider, **Entry** or **Endpoint**, or click either longitudinal image. The wheel moves one millimetre along the route; Shift+wheel moves 0.1 mm. Selecting a station updates the linked main crosshair and a labelled 3D inspection marker. Inspection position is independent of insertion depth and respiratory time. Closing removes the inspection marker and retains the selected crosshair. Returning to static Imaging disables linked route navigation; Motion or Needle restores it.

The path defines a stable orthonormal physical frame. Both longitudinal views include the complete route with end margins; all three planes use equal millimetre scales, direction labels and rulers. CT intensities are linearly sampled from the original volume, using the inverse of the currently displayed anatomical transform. Segmentation layers use nearest-neighbour labels on exactly the same grids, retaining overlapping masks and current layer colours. The local overlay checkbox works within the main CT-overlay setting. Hover reports the nearest sampled pixel's LPS coordinates and interpolated HU value.

Checkerboard marks positions outside source CT coverage; those pixels have no reported tissue intensity or segmentation. Displayed anatomical time and the frozen planning instant are labelled separately. The viewer samples bounded 2D planes, reuses longitudinal samples when only the station changes and recolours existing samples for window/level changes. It creates no additional CT phases or full resampled 3D volumes. Changing or replacing a plan or scan clears its inspector samples; busy operations disable navigation.

### Route constraints

In **Needle**, scroll to **Route constraints**. Set **New region radius**, position the crosshair, and choose **Add exclusion at crosshair**. Up to eight user-defined regions can be added, removed or cleared. Red contours and wireframes follow the shared affine deformation. These regions are explicit simulated constraints, not detected vessels, expert anatomical masks or automatically inferred risks. Their complete reference spheres must fit inside the CT.

**Build path** checks the single manual entry against declared exclusions. **Find shortest feasible entry** enumerates thirteen points on a designated flat disk around that entry; a zero patch radius checks only its centre. Candidates outside the oriented CT, inside lung masks, beyond the available insertion timeline or below the required clearance bound are rejected. The shortest eligible route wins; greater clearance and then candidate index break exact ties. When none qualifies, the application abstains, clears the insertion and retains each rejection reason for inspection and export. The flat patch is a manual geometric search surface, not detected skin or verified clinical accessibility.

Clearance is a conservative world-space lower bound for the finite needle capsule against affine-deformed exclusion spheres. It includes physical needle radius and the requested millimetre margin. A negative bound is rejection or unresolved clearance, not an exact penetration depth. **Current geometry** screens the full route at the planning instant. The optional **Predicted motion** policy adds the insertion-interval screen described below. After selection, a separate sampled-and-refined execution check reports actual simulated constraint violations as the regions move; that future information never reranks candidates. A route can pass screening and fail during execution. These checks do not establish clinical safety or assess unspecified anatomy.

**Export route check CSV** includes the planning transform, exclusion definitions, all candidate coordinates/bounds/reasons, selected or abstained decision and a separate execution-bound trace when available. It also works after abstention. Changing regions, margin, patch, target, scenario, lung masks or insertion settings discards stale decisions. Display changes and ordinary timeline inspection preserve their labelled planning instant. Opening another study clears the regions. Without declared exclusions, obstacle assessment remains explicitly unavailable.

After a route check, choose **Inspect route decision**, or double-click a candidate in the compact table. The separate window links every candidate to its actual position on the manually defined reference entry patch. Its equal-scale axes are orthonormal patch coordinates in millimetres, with their LPS basis displayed. The candidate table and full detail panel show the saved eligibility reason, physical entry, endpoint, length, timing and available bounds. Selecting a candidate inspects it; the algorithm's chosen entry, needle path, timeline, observations and CT display are preserved.

All eligible and rejected candidates remain accessible, including an entirely rejected search. Planning-time bounds and predicted insertion bounds are separate fields; missing checks remain unavailable or unassessed. Actual execution belongs to the chosen path and is inspected through **Inspect insertion results**. The route explorer reuses stored decisions, supports the existing protected CSV export, and clears when the planning context changes. It does not fit, rerank or substitute a candidate during inspection.

### Arrival-aware target planning

In **Needle**, **Targeting method** selects the endpoint calculation. **Displayed centre** retains the geometric reference workflow above. **Constant position** holds the last noisy observation, **Constant velocity** extrapolates a line fitted to the latest second, and **Sinusoidal fit** estimates periodic motion from past noisy positions. Loading a validated predictor in Motion also enables **Learned MLP**, without changing the selected Needle method.

Record observations in **Motion**, seek to a planning time covered by that recording, then choose a method in **Needle** and build a path or search the manual entry patch. Sinusoidal fitting needs at least 20 sampled seconds; its **Prediction history** is separate from the Motion forecast controls. Unavailable or insufficient fits give an explicit reason without falling back to another method.

**Learned MLP** requires the latest 101 observations at 10 Hz, covering ten seconds, with the final observation within 0.11 seconds of planning. Its window is fixed by the checkpoint; the sinusoidal history control does not change it. Weights and the past observation window are frozen before selection. The horizon input makes this ReLU network piecewise affine in time: the solver enumerates activation boundaries and solves the physical interception equation on each linear segment, including tangencies and boundary roots. NumPy evaluates the same cached segments in float64 for both predictions and interception checks; saved weights remain unchanged. It checks the resulting endpoint against physical arrival and rejects inconsistent or unreachable solutions. No training, future observations or simulated future target positions enter that solve. For a continuous interval of exact intercepts, only its earliest positive-length boundary is considered; later constraint changes inside that interval are not searched.

Each entry solves its own interception time: look-ahead equals execution delay plus predicted path length divided by insertion speed. The endpoint is the selected method's predicted target centre at that physical arrival. Forecasts use only observations at or before the planning instant. Routes outside the five-second prediction range, available simulation timeline or current CT coverage are rejected. When earlier intercepts fail the declared constraints, a later feasible intercept may be used. Candidate ranking otherwise keeps the same shortest-route, clearance and index rules. No feasible intercept means abstention.

The cyan **Planned arrival** marker shows the fixed endpoint; the amber target continues to follow the simulated anatomy. A built plan retains its observation snapshot while you seek or replay insertion, including beyond the recording cutoff. Changing observations, sampling, targeting method or prediction history discards dependent plans. Displayed-centre paths remain independent of observations. To build a new observed route at a later planning instant, extend the recording first.

Learned plans and exports identify their exact checkpoint. Replacing its weights clears dependent learned plans and comparisons, while geometric and mathematical plans remain usable. Reloading identical weights preserves the existing learned plan. The route and insertion CSV summaries retain the training manifest once, alongside model identity and the interception solver; separate execution rows retain simulated outcomes.

With **Current geometry**, exclusions are screened at their planning-time positions. **Predicted motion** additionally forecasts their movement over insertion. Actual exclusion movement and the moving target are evaluated separately after selection, without reranking entries. Arrival-aware target prediction does not guarantee clearance from moving obstacles. Target error and contact are simulated outcomes, not patient results or clinical success measures.

**Export route check CSV** adds the frozen past noisy observation prefix, fitting metadata and each candidate's own predicted endpoint, query time, physical arrival, horizon and numerical interception residual. Selected fields stay blank after abstention. Planning rows contain no future observations, hidden truth, noise seed or simulator parameters. The insertion evaluation export separately records actual simulated target outcomes, labelled as truth.

### Predicted exclusion screening

Choose an observation-based **Targeting method**, add declared exclusions, then set **Route constraints > Exclusion screening > Predicted motion**. Build a path or search the existing manual entry patch. The default **Current geometry** policy remains available for comparison. Displayed-centre planning and studies without exclusions keep current-geometry screening; the prediction control is disabled when it does not apply.

The exclusion forecast uses changes in the target predictor, not future simulated positions. Under the declared affine field, target motion has weight `(apex_z - target_reference_z) / lung_height`. The forecast transfers the target's predicted change from the planning instant through that weight, anchored to the current anatomical transform. Constant observation offsets therefore do not shift all exclusions at the start. Target endpoints still use the absolute target forecast; the anchored exclusion estimate can differ by the fit's current position error. This is an explicit shared-motion assumption, not independent tracking of vessels or other anatomy.

Each candidate retains its planning-time full-route clearance check. The additional screen checks the finite inserted capsule from insertion start to arrival, including physical radius and clearance margin, using a 5 ms grid with minimum and contact refinement. It checks the inserted portion rather than treating the entire future path as already occupied. Screening occurs inside the intercept search, so an earlier rejected intercept can be followed by a later feasible one. Unsupported transforms, unidentifiable target height, excessive predicted compression and failed numerical refinement reject the route rather than admit it through a fallback.

The route readout and candidate tooltips distinguish predicted insertion clearance from current clearance. The insertion results separately label **Predicted exclusion screen** and **Actual exclusion execution check**. Seeking or replaying retains the frozen forecast; changing screening policy or relevant inputs invalidates it. The route CSV records the policy, per-candidate predicted diagnostics and distinct `predicted_exclusion_sample` and `exclusion_execution_sample` records. Anchoring, reference geometry and transfer weight are exported for inspection. The insertion CSV adds the predicted summary while retaining its actual outcome trace.

This is a deterministic numerical screen under an estimated motion field, using the selected mathematical or learned point predictor. Forecast error can still cause actual violations; neither the grid nor the conservative spatial bound establishes continuous clearance or clinical safety. No calibrated neural uncertainty model is used.

### Controlled planning comparisons

Define a target and manual entry, then choose **Needle > Compare planning methods**. A separate comparison window runs constant position, constant velocity and sinusoidal arrival planning on identical cases, adding **Learned MLP** when a predictor is loaded. It keeps the current CT, display, breathing scenario, observations and insertion plan. No existing observation recording is required: the comparison generates its own controlled histories in a cancellable worker.

**Quick** checks 32 cases / 96 method trials: four breathing patterns × noise of 0 or 1 mm per axis × execution delays of 0 or 1.5 s × speeds of 15 or 30 mm/s. Its planning origin is 31.15 s. **Extended** checks 128 cases / 384 trials by adding a second seeded replicate and a second origin at 42.65 s. With declared exclusions, **Compare current and predicted exclusion motion** is enabled by default, doubling the trials to 192 or 768. Turn it off to reproduce the single-policy comparison. Without exclusions, duplicate policy trials are suppressed. Regular breathing has the same deterministic waveform across profile seeds; its observation noise can differ. These repetitions are correlated scenarios, not independent patients.

A loaded MLP adds one trial per case and policy: Quick becomes 128 trials, or 256 with both policies; Extended becomes 512 or 1,024. The comparison freezes the checkpoint and includes its identity and training provenance. Incompatible sampling remains an explicit unavailable learned trial and stays in attempted-case denominators. The comparison does not retrain or select weights using insertion outcomes. Neural forecast-region diagnostics remain unavailable until a separate calibration protocol is implemented.

Learned comparisons require the checkpoint's training and validation waveform catalogue and reject exact waveform overlap with either split. This check excludes reference translations and observation noise, so changing only those does not hide a repeated physical trajectory. Scenario repetitions within the comparison remain correlated, and distinct waveforms from the same simulator do not establish patient-level generalisation.

The window captures the current base amplitude, breathing rate, observation sampling rate, Needle prediction history, shaft radius, reference entry patch, clearance and exclusions. The protocol supplies the varied patterns, noise, delays, speeds and origins. Every method receives exactly the same past noisy observations and reference entry candidates for each case. Constant position is the observed static baseline; the noiseless **Displayed centre** route is excluded from this comparison. Each method solves its own actual arrival, then receives a separate simulated execution evaluation. Timing, CT-coverage and declared-constraint rejections remain in the results.

The summary reports evaluated insertions / attempted cases, mean and p95 arrival error, arrival contacts / attempted cases, and exclusion violations / assessed insertions. Hover over a method for median error, unavailable-fit, abstention and evaluation-failure counts, plus contacts during insertion. An arrival contact is distinct from passing through the target earlier. Arrival errors use evaluated insertions only; failed or abstained cases have blank errors. The all-case contact denominator includes every attempted case. Without declared exclusions, obstacle outcomes remain **Unassessed**. A sampled-and-refined clearance check is not a guarantee of continuous collision freedom.

Use **All cases** or a breathing-pattern filter to inspect cached summaries without rerunning. Paired differences compare each method with constant position only on cases where both produced evaluated insertions; negative differences favour the named method, and the paired denominator is always shown. **Every trial** retains each status and reason. Do not interpret a lower conditional mean error without checking execution coverage, abstentions and paired counts.

When both policies are compared, every method/policy pair receives the same case observations and reference candidates. The **Exclusions** column identifies the policy; method-versus-static differences stay within the same policy. **Screening trade-off** compares policies within each method, showing evaluated cases, abstention, arrival-contact-without-violation counts over all attempted cases, and violations over assessed executions. Unexecuted cases contribute no successful arrival to the all-case rate. Policy comparisons and per-pattern comparisons are also exported, so reducing conditional violations by abstaining more cannot be presented as an unqualified improvement.

**Export evaluation CSV** writes one versioned protocol manifest, overall and per-pattern summaries, paired comparisons and every trial. It records source/mask/candidate identities, physical geometry, scenario and noise seeds, software versions, core-code checksum, protocol/result identifiers and outcome definitions. This is explicitly a simulated evaluation artifact, so it includes seeds for repeatability; prediction fitting still receives only past noisy positions. Exports are atomic and protected against overwriting source data. Changed inputs reject stale results; cancelling never publishes a partial comparison.

The optional **Assess empirical observation-error regions** control adds a separate forecast assessment at the requested look-ahead, rounded forward to the next actual observation sample. This probe is independent of each needle's arrival time. Calibration uses the case's past noisy history; only afterwards is its later observation and simulated true centre scored. **Forecast regions** reports availability across attempted cases and coverage/radii across distinct forecast probes. Repeated delay, speed and screening-policy cases with the same model, noisy prefix and query add no coverage evidence. Distinct probes can still be correlated; unavailable regions remain in the counts. CSV exports include protocol definitions, per-trial diagnostics and aggregate region records. Leaving the control off preserves the original comparison workload.

These comparisons evaluate frozen mathematical and learned point planners. They use one reference anatomy and the existing shared affine simulator, whose regular breathing matches the sinusoidal model. Predicted exclusion screening assumes that shared affine field and remains subject to forecast error. There are no patient-cohort results, statistical independence claims or guaranteed uncertainty estimates.

## Performance

The viewer samples overlapping binary overlays together using a temporary packed display array, while retaining every original mask separately. Hidden layers are sampled only when needed, and previously sampled labels are reused while paused or changing display settings. Saved study layers attach before the first CT panel refresh. CT resolution, surface geometry, lighting, transparency and respiratory equations remain unchanged.

A before/after check on the development laptop used the same cached CTChest study, five lobes, airway layer and window size:

| Operation | Before | Current |
|---|---:|---:|
| Cached study opening after viewer initialisation | 8.4 s | 4.5 s |
| Median slice navigation and painting | 407 ms | 128 ms |
| Median motion preparation, rendering and painting | 115 ms | 75 ms |
| Displayed motion frames per second | 6–7 | 12–13 |

These are local measurements, not fixed performance guarantees. Python startup, uncached reconstruction and segmentation generation are separate costs. Faster display does not alter CT acquisition or create additional measured respiratory phases.

## Tests

When the local `tests/` folder is present, run `python -m pytest`. The suite covers image formats, coordinate transforms, label validation, aligned segmentation imports and replacement, shared structure controls, overlapping masks, source-matched lobe and airway caches, long cache paths, seed validation and leakage rejection, generation failures, motion derivatives, phase continuity, repeatability, toolbar loading states and sidebar resizing. Performance regressions check exact packed-overlay parity on oblique and reflected scans, lazy label reuse, batched loading, source replacement and elapsed-time playback through uneven frames.

Sequence checks cover manifest order and timing, header-only inspection, DICOM identity and frame restrictions, source changes including detached voxel data, exact integer labels, byte-limited caching, synchronised views, phase-specific geometry, invalid first-phase data and late worker results. Desktop checks also cover real-scan rendering, camera presets, laptop layout and preservation of source data. Sequence fixtures are synthetic; a hard-link alias test is skipped when the environment does not permit creating links.

Playback checks cover ordered discrete phases, preview pacing, looping, end/reset behavior, cancellation during preparation and phase loading, source changes, stale deferred navigation and synchronized landmark displays. Surface-cache checks cover source/label identity, corrupt archives, bounded allocations, cropped image boundaries and reuse after memory eviction. The real ten-phase POPI example is also checked through the production loader and desktop playback; its local provenance records exact source-conversion and cache-reuse checks.

Target checks cover full-sphere containment on oriented grids, shared 3D deformation and exact slice intersections, cropped image boundaries, inverse selection, reproducible sampling and noise, past-only observation access, immutable histories, settings invalidation, separate observation/evaluation exports and late worker rejection after a study change.

Forecast checks cover analytic trajectories, irregular sampling, frequency fitting, noise and sparse-history rejection, bounded extrapolation, causal prefixes, paired 3D error calculations, stale worker rejection, physical markers, preserved CT/camera/mesh data and truth-separated exports.

Learning checks cover profile-level separation, training-only normalization, causal observed features, validation-only epoch selection, frozen-model test evaluation, exact physical labels, repeatability, cancellation, saved inference parity, malformed checkpoint allocation guards, protected atomic exports, worker lifecycles, unavailable histories and preservation of CT and needle state.

Needle checks cover oriented entry validation, finite-segment geometry, affine target intersections, physical shaft/tip dimensions, timing and retraction, contact refinement between sampled times, immutable traces, stale-plan rejection, physical slice overlays and protected evaluation exports.

Insertion-results checks cover stored sample values and units, execution-only clearance, unavailable regions, exact event navigation, cached cursor updates, linked expansion, transport synchronization, stale-result clearing and preservation of the CT, camera, meshes and frozen observations.

Trajectory-inspection checks cover stable orthonormal frames, anisotropic and reflected image geometry, analytical CT ramps, inverse affine sampling, overlapping nearest-neighbour masks, source coverage, physical rulers and pixel projections, independent station navigation, sample reuse, compact layouts, stale-plan rejection and preservation of the original scan and planning state.

Constraint checks cover physical-radius affine clearance bounds, finite capsules, reflected and oblique scans, deterministic entry enumeration, complete abstention, current-geometry selection without future motion access, separate execution violations, source/context invalidation, exact region overlays and selected/abstained CSV exports.

Route-explorer checks cover reference-patch projection on rotated and reflected anatomy, equal millimetre scales, finite marker selection, table/map/filter linkage, zero-radius patches, unavailable fields, candidate-specific forecast endpoints, cached inspection, abstention, worker guards, stale-context clearing and complete protected exports. Inspection also preserves the source CT, masks, anatomical meshes, camera, timeline and chosen plan.

Arrival-planning checks cover analytic static and velocity intercepts, sinusoidal crossings and tangencies, candidate-specific times, causal prefixes, bounded extrapolation, explicit abstention, preserved geometric planning, frozen observation contexts, physical arrival markers and truth-separated exports.

Learned-arrival checks cover ReLU activation boundaries, analytic segment roots, multiple intersections, physical residuals, frozen checkpoint identity, incompatible-history rejection, future-data isolation, model replacement and stale-worker rejection, matched four-method comparisons and inference without PyTorch.

Comparison checks cover the full factor grid, repeatable seed derivation, identical observations and candidates across methods, selection before execution truth, failure-inclusive denominators, paired-case deltas, per-pattern summaries, no-exclusion blanks, cancellation, immutable results, protected exports and preservation of the current study and insertion plan.

Predicted-exclusion checks cover origin anchoring, constant-offset cancellation, shared-field validation, unsupported motion rejection, physical finite-capsule bounds, inserted-length timing, future-data isolation, current-policy compatibility, predicted/actual trace separation and matched within-method policy comparisons.

Forecast-region checks cover causal historical cutoffs, joint physical residuals, finite-rank selection, insufficient-score availability, cancellation, future-label isolation, separate observed/true coverage, physical sphere intersections, frozen needle-plan preservation, protected exports and distinct-probe benchmark denominators.

Held-out-study checks cover disjoint subject/model/noise identities, exact sampled horizons, one causal fit per subject/method, calibration frozen before evaluation generation, separate true/observed residuals, ranked radii, failure-inclusive denominators, immutable validated results, cancellation, repeatability, source/plan preservation, cached chart filters and protected complete-study exports.
