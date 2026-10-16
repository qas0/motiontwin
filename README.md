# MotionTwin

A Python desktop workstation for lung CT visualisation, synthetic respiratory motion, motion prediction and simulated needle-trajectory planning. The interface uses PySide6, PyVistaQt and VTK.

## Two main code files

| File | Purpose |
| --- | --- |
| **`run.py`** | Run this file. Contains the GUI, interactive 3D rendering, linked CT panels and command-line entrypoint. |
| **`motiontwin.py`** | Scientific core: image loading, anatomy, respiratory motion, geometry, planning, prediction, training and research evaluation. |

Default configurations are built into the core. Each file has labelled sections so the imaging, simulation, AI and interface code remain easy to locate.

The other five repository files support these two: `requirements.txt` lists dependencies; `pyproject.toml` supports optional installation; `.gitignore` keeps local data/results out of Git; this README explains usage; `THIRD_PARTY_LICENSES.txt` retains the public CT sample's licence.

## Run

Use 64-bit Python 3.11 or 3.12 and a working desktop OpenGL driver. From this folder in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\run.py
```

If the local environment already exists, just open **`run.py`** in VS Code and choose **Run Python File**, or use the last command above. The launcher selects the project environment and working directory automatically.

No training or external dataset is needed for the synthetic demo:

```powershell
.\.venv\Scripts\python.exe .\run.py demo
```

Normal startup opens the public CT example when a verified local copy is already cached; otherwise it opens synthetic anatomy. Startup does not download data.

## Workspaces

- **3D planning:** interactive lung reconstruction, structure visibility, opacity, camera controls, physical cutaway and finite inserted needle.
- **CT review:** linked axial, coronal, sagittal and 3D panels, LPS coordinates, crosshair navigation, window/level and segmentation overlays.
- **Research & analysis:** computed planning results and separate synthetic experiments, training and research exports.

Use **Imaging → Synthetic anatomy** for the breathing/planning model. Use **Imaging → Open public CT example** for the optional approximately 40 MB real chest CT. The example comes from [3D Slicer](https://www.slicer.org/wiki/File:CT-chest.nrrd), is checksum-verified, and is stored locally with provenance and its complete licence. The sample is static. Its lung/detail masks are threshold-derived display structures, without invented lesion, measured breathing or planning-obstacle annotations.

**Render** selects CT reconstruction, Lung motion or Anatomy surfaces. **Quality → Interactive** reduces rendering work on a laptop. Physical target/entry geometry, observation history and planner calculations are independent of display quality. A static public CT stays distinct from synthetic 4D respiration.

## Command-line options

```powershell
.\.venv\Scripts\python.exe .\run.py --help
.\.venv\Scripts\python.exe .\run.py train
.\.venv\Scripts\python.exe .\run.py evaluate
```

Training/evaluation use built-in settings; optional YAML overrides are accepted with `--config path/to/settings.yaml`. The module entrypoint also works: `python -m motiontwin demo`. Optional editable installation with `python -m pip install --no-build-isolation -e .` provides the `motiontwin` console command.

Learned planning needs a compatible locally trained checkpoint. Models, datasets, caches, screenshots and research results belong under `data/` or `outputs/` and are excluded from this source-only repository. The supplied source does not contain pretrained weights or patient data.

## Scope and verification

This is a research prototype. Synthetic images and motion are procedural; a public static CT does not establish patient-specific motion prediction or clinical performance. The needle is rigid/straight, targets are evaluated as spheres, and synthetic collision geometry uses finite capsules. Later AI-calibration and research validation stages remain separate work.

The compact layout preserves the previous functionality: **172 automated regression tests**, independent configuration/checkpoint checks, and actual Windows GUI checks were run locally. Developer tests, retained blueprints/references, verification records and the pre-consolidation source backup remain local and are excluded from the seven-file GitHub publication set.

The complete Slicer licence in `THIRD_PARTY_LICENSES.txt` applies to the optional public CT material; it does not imply endorsement or license the original MotionTwin code on the contributors' behalf.
