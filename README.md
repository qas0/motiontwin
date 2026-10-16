# MotionTwin

A desktop CT viewer with linked axial, coronal and sagittal views, 3D lung rendering and a simulated breathing preview. Built with Python, PySide6, PyVistaQt and VTK.

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
- `requirements.txt` and `pyproject.toml`: dependencies and package settings.
- `THIRD_PARTY_LICENSES.txt`: public CT licence and attribution.

Local data, reference material, display caches and development tests are excluded from GitHub.

## Imaging

**File > Open CT** loads static NIfTI, NRRD and MetaImage volumes. **Open DICOM series** loads one series. **Load lung mask** adds an aligned left or right lung segmentation. Imported CTs can be viewed without masks; lung surfaces require them.

Click a CT panel to position the shared crosshair. Scroll to move through slices; Ctrl+scroll zooms. The left panel controls window/level, segmentation overlays, lung visibility and opacity. Drag the 3D view to rotate it, or use a camera preset and **Fit**.

Coordinates use LPS millimetres. Axial images show anterior at the top; coronal and sagittal images show superior at the top. Overlays and scrolling use the scan's physical spacing and orientation, including oblique scans. Invalid imports leave the current study open. Adding a mask preserves the camera and crosshair.

A verified local public CT opens at startup. Without it, the viewer starts empty. **File > Open example CT** downloads the roughly 40 MB Slicer chest example. Its lung envelopes and dense tissue layers are threshold-derived display masks, not expert segmentations or verified vascular anatomy. The source licence is included in `THIRD_PARTY_LICENSES.txt`.

The example stores packed masks and bounded meshes in `data/public-example/display-cache.npz`. Cache validity depends on the source checksum, image geometry and display settings. Missing or invalid caches are rebuilt. The first reconstruction measured about 32 seconds on the development laptop; cached loading took about 2 seconds. Initial reconstruction and renderer setup can briefly pause the interface.

## Motion

Load a CT with at least one lung mask, then open **Motion**. Choose Regular, Mild irregularity, Strong irregularity or Stress test. Set base amplitude, breathing rate and an irregular-pattern seed, then press **Play**. **Pause** holds the current frame. The slider seeks within 60 seconds; release its handle to update. **Reset** restarts with the displayed settings and seed. Return to **Imaging** to view the original static CT.

After time zero, setting changes blend over one second of simulation time while preserving motion history and phase. Seeking restores the settings at that time; further changes replace the subsequent scenario. Opening another CT resets motion. Adding a mask keeps the current preview.

Frequency is integrated on a 0.01-second grid. Displacement is `(.15, .25, -1) * A(t) * sin(phase(t))` in LPS millimetres. Velocity differentiates the same amplitude and phase splines. Stress testing introduces seeded changes around 12, 24 and 38 seconds, with 0.8-second transitions.

The deformation is `u(p,t) = (apex_z - p.z) / lung_height * displacement(t)`. It fixes the apex and varies movement with height. CT samples, masks and 3D surfaces use the same affine transform. The crosshair marks a fixed world position, not a tracked lesion.

**The preview deforms one static scan; it is not acquired 4D CT.** It also deforms non-lung structures and does not model tissue mechanics, mass conservation or image registration. Positions outside the source scan are shown as background. Original scan values and mesh geometry stay unchanged.

Playback updates existing actors and samples the three current CT planes, capped at 256 pixels per side; static Imaging uses 384. A 67 ms timer follows elapsed time, skipping display frames when rendering is slower. Measurements on the development laptop were approximately 12-13 displayed frames per second, with 53 ms median frame preparation and rendering time. Performance varies with hardware, scan size and overlays.

## Tests

When the local `tests/` folder is present, run `python -m pytest`. The 84 checks cover image formats, coordinate transforms, mask alignment, cache validation, motion derivatives, phase continuity, repeatability and interface behaviour. Desktop checks also cover real-scan playback, mouse/keyboard controls and preservation of source data.
