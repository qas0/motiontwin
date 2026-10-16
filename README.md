# MotionTwin

A Python desktop viewer for CT scans and a 3D lung reconstruction, using PySide6, PyVistaQt and VTK.

## Main files

| File | Purpose |
| --- | --- |
| **run.py** | Main file to run. The GUI, three linked CT views and interactive lung rendering. |
| **motiontwin.py** | CT loading, physical coordinates, reslicing, lung masks and display surfaces. |

The other repository files are requirements.txt, pyproject.toml, .gitignore, this README and THIRD_PARTY_LICENSES.txt. Local CT data, original requirements, visual references and development tests are excluded from GitHub.

## Run

From this project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\run.py
```

You can also open **run.py** in VS Code and choose **Run Python File**, or press F5. The launcher selects the local project environment and working directory.

For a first installation with Python 3.11 or 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\run.py
```

`python -m motiontwin` and `run.py gui` also launch the viewer. The former demo, train and evaluate commands have been removed.

## Retained functionality

- Linked axial, coronal and sagittal CT views, with physical LPS coordinates, crosshair navigation, scrolling, zoom and window/level presets.
- Interactive 3D CT/lung rendering, camera presets, fit, lung opacity and available lung/detail visibility.
- Import of static NIfTI, NRRD and MetaImage CT volumes, one DICOM series, and aligned left/right lung masks.
- The existing public chest CT example and its attributed, threshold-derived display masks.

Normal startup opens the public example when a checksum-verified local copy exists. Otherwise the viewer starts empty. Startup does not download a scan or substitute synthetic anatomy. **File → Open example CT** can explicitly download the approximately 40 MB example if needed. It is disabled while that example is already open. Imported CTs use their actual source values and geometry; lung surfaces require aligned lung masks.

The left panel contains CT display and lung visibility controls. **File → Open CT** and **Open DICOM series** load your own scan files; **Load lung mask** loads an aligned segmentation defining a lung surface. These actions need the corresponding files and do not edit the example automatically. CT import and supplied-mask reconstruction are required by the blueprint; DICOM is its optional extension. The public example is a convenience for viewing a real scan without supplying your own data. Controls are disabled when the required CT or masks are absent. Manual window/level values display **Custom** as a status, rather than a selectable preset with no action.

The public example's lung envelopes and high-density lung detail are display approximations, not expert segmentations or verified vascular anatomy. The complete source licence is in THIRD_PARTY_LICENSES.txt.

## Cleanup scope

Patient/breathing simulation, 4D playback, predictions, learned models, uncertainty, trajectories, targets, needles, research parameters, experiments, training, analysis plots and their exports have been removed from the application and core code. Render-mode/workspace switching and cutaway controls have also been removed. These stages will be implemented separately when requested.

Obsolete helpers, stage tests/reports, generated experiments, checkpoints and previous backup/copy folders were deleted. No new backups or archives were created. The original blueprint, supplied visual references, CT data and licences remain locally as context; they describe the longer-term project, not currently implemented features.

The retained imaging tests can be run with `python -m pytest`. This cleanup does not establish completion of any future scientific stage.
