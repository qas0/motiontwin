from itertools import product

import numpy as np

from motiontwin import Volume, world_to_index, mesh_from_mask, _bounded_surface, DISPLAY_MAX_CELLS


class AnnotationMask:
    def __init__(self, volume, mask=None, *, history_bytes=32 * 1024 ** 2):
        if not isinstance(volume, Volume):
            raise ValueError("Annotation requires a source CT.")
        if mask is not None and (np.asarray(mask).dtype != bool or np.shape(mask) != volume.shape):
            raise ValueError("The annotation must be a boolean mask on the source CT grid.")
        self.mask = (np.zeros(volume.shape, dtype=bool) if mask is None
                     else np.array(mask, dtype=bool, order="C", copy=True))
        self.spacing, self.origin = volume.spacing, volume.origin
        self.direction = volume.direction.copy()
        self.affine = volume.affine
        self.inverse = np.linalg.inv(self.affine)
        self.history_bytes = int(history_bytes)
        if self.history_bytes < 1024:
            raise ValueError("Annotation history requires at least 1024 bytes.")
        self.undo_stack, self.redo_stack = [], []
        self.history_limited = False
        self.revision = 0
        self._stroke = None
        self._measurement_revision = -1
        self._measurement_cache = None

    def begin(self, *, erase=False):
        if self._stroke is not None:
            raise ValueError("Finish the current annotation stroke first.")
        self._stroke = dict(value=not erase, chunks=[], bytes=0)

    def paint(self, start, end, radius_mm, *, normal=None):
        if self._stroke is None:
            raise ValueError("Begin an annotation stroke before drawing.")
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        radius = float(radius_mm)
        if (start.shape != (3,) or end.shape != (3,) or not np.isfinite([start, end]).all()
                or not np.isfinite(radius) or not 0 < radius <= 50):
            raise ValueError("Use finite LPS positions and a brush radius up to 50 mm.")
        half_thickness = 0.
        if normal is not None:
            normal = np.asarray(normal, dtype=float)
            if normal.shape != (3,) or not np.isfinite(normal).all() or not np.isclose(np.linalg.norm(normal), 1.):
                raise ValueError("A slice brush requires a unit physical plane normal.")
            if abs(float((end - start) @ normal)) > 1e-5:
                raise ValueError("A slice stroke must stay on its displayed plane.")
            # include source voxel cells intersected by the displayed plane.
            normal_steps = self.affine[:3, :3].T @ normal
            normal_steps[np.abs(normal_steps) < 1e-12 * np.linalg.norm(normal_steps)] = 0.
            half_thickness = .5 * np.abs(normal_steps).sum()
        extent = np.sqrt(radius ** 2 + half_thickness ** 2)
        corners = np.array(list(product(*zip(np.minimum(start, end) - extent,
                                             np.maximum(start, end) + extent))))
        indices = corners @ self.inverse[:3, :3].T + self.inverse[:3, 3]
        if not np.isfinite(indices).all():
            raise ValueError("The brush position cannot be mapped onto the source grid.")
        lower = np.maximum(0, np.ceil(indices.min(axis=0) - 1e-8))
        upper = np.minimum(np.array(self.mask.shape[::-1]) - 1, np.floor(indices.max(axis=0) + 1e-8))
        if np.any(lower > upper):
            return False
        lower, upper = lower.astype(int), upper.astype(int)
        x, y = np.meshgrid(np.arange(lower[0], upper[0] + 1), np.arange(lower[1], upper[1] + 1))
        segment = end - start
        squared_length = float(segment @ segment)
        changed = False
        # process one source slice at a time instead of allocating a 3D point grid.
        for z in range(lower[2], upper[2] + 1):
            xyz = np.stack((x, y, np.full_like(x, z)), axis=-1)
            world = xyz @ self.affine[:3, :3].T + self.affine[:3, 3]
            relative = world - start
            fraction = np.clip(relative @ segment / squared_length, 0., 1.) if squared_length else 0.
            distance = relative - np.asarray(fraction)[..., None] * segment
            distance_squared = np.sum(distance ** 2, axis=-1)
            selected = distance_squared <= radius ** 2 + 1e-8
            if normal is not None:
                height = relative @ normal
                selected = ((distance_squared - height ** 2 <= radius ** 2 + 1e-8)
                            & (np.abs(height) <= half_thickness + 1e-8))
                boundary = selected & np.isclose(np.abs(height), half_thickness, rtol=0, atol=1e-8)
                if np.any(boundary):
                    # nearest-neighbour cells own their lower source-index faces.
                    touch = xyz[boundary] - .5 * np.sign(height[boundary, None]) * np.sign(normal_steps)
                    world_touch = touch @ self.affine[:3, :3].T + self.affine[:3, 3]
                    world_touch -= ((world_touch - start) @ normal)[:, None] * normal
                    sampled = world_to_index(world_touch, self.spacing, self.origin, self.direction)
                    selected[boundary] &= np.all(np.floor(sampled + .5) == xyz[boundary], axis=-1)
            patch = self.mask[z, lower[1]:upper[1] + 1, lower[0]:upper[0] + 1]
            rows, columns = np.nonzero(selected & (patch != self._stroke["value"]))
            if not len(rows):
                continue
            flat = np.ravel_multi_index((np.full_like(rows, z), rows + lower[1], columns + lower[0]), self.mask.shape)
            if self._stroke["bytes"] + flat.nbytes > self.history_bytes:
                self.cancel()
                raise ValueError("This stroke exceeds the edit-memory limit. Use shorter strokes or a smaller brush.")
            patch[rows, columns] = self._stroke["value"]
            self._stroke["chunks"].append(flat)
            self._stroke["bytes"] += flat.nbytes
            changed = True
        if changed:
            self.revision += 1
        return changed

    def finish(self):
        if self._stroke is None:
            return False
        stroke, self._stroke = self._stroke, None
        if not stroke["chunks"]:
            return False
        command = (np.concatenate(stroke["chunks"]), stroke["value"])
        self.redo_stack.clear()
        while self.undo_stack and sum(item[0].nbytes for item in self.undo_stack) + command[0].nbytes > self.history_bytes:
            self.undo_stack.pop(0)
            self.history_limited = True
        self.undo_stack.append(command)
        return True

    def cancel(self):
        if self._stroke is not None:
            for indices in self._stroke["chunks"]:
                self.mask.ravel()[indices] = not self._stroke["value"]
            self._stroke = None
            self.revision += 1

    def undo(self):
        self.cancel()
        if self.undo_stack:
            indices, value = self.undo_stack.pop()
            self.mask.ravel()[indices] = not value
            self.redo_stack.append((indices, value))
            self.revision += 1

    def redo(self):
        self.cancel()
        if self.redo_stack:
            indices, value = self.redo_stack.pop()
            self.mask.ravel()[indices] = value
            self.undo_stack.append((indices, value))
            self.revision += 1

    def clear(self):
        self.begin(erase=True)
        if np.count_nonzero(self.mask) * np.dtype(np.intp).itemsize > self.history_bytes:
            self.cancel()
            raise ValueError("Clearing this region exceeds the undo-memory limit. Erase smaller parts instead.")
        indices = np.flatnonzero(self.mask)
        self._stroke["chunks"] = [indices] if len(indices) else []
        self._stroke["bytes"] = indices.nbytes
        self.mask.ravel()[indices] = False
        self.revision += 1
        self.finish()

    def measurements(self):
        if self._measurement_revision == self.revision:
            return self._measurement_cache
        self._measurement_revision = self.revision
        count = 0
        total = np.zeros(3)
        lower, upper = np.array(self.mask.shape[::-1]), np.zeros(3, dtype=int)
        world_lower, world_upper = np.full(3, np.inf), np.full(3, -np.inf)
        # bounded temporary arrays also keep volumetry usable for large regions.
        for z, section in enumerate(self.mask):
            y, x = np.nonzero(section)
            if not len(x):
                continue
            count += len(x)
            total += [x.sum(dtype=float), y.sum(dtype=float), z * len(x)]
            lower = np.minimum(lower, [x.min(), y.min(), z])
            upper = np.maximum(upper, [x.max(), y.max(), z])
            for axis in range(3):
                coordinates = (x * self.affine[axis, 0] + y * self.affine[axis, 1]
                               + z * self.affine[axis, 2] + self.affine[axis, 3])
                world_lower[axis] = min(world_lower[axis], coordinates.min())
                world_upper[axis] = max(world_upper[axis], coordinates.max())
        if not count:
            self._measurement_cache = None
            return None
        centre = total / count @ self.affine[:3, :3].T + self.affine[:3, 3]
        cell_extent = np.abs(self.affine[:3, :3]).sum(axis=1)
        self._measurement_cache = dict(voxels=count, volume_mm3=float(count * abs(np.linalg.det(self.affine[:3, :3]))),
                    centroid_lps_mm=centre, dimensions_lps_mm=world_upper - world_lower + cell_extent,
                    lower_xyz=lower, upper_xyz=upper,
                    provenance="user-defined manual voxel annotation", expert_reviewed=False)
        return self._measurement_cache

    def surface(self):
        measured = self.measurements()
        if measured is None:
            return None
        lower, upper = measured["lower_xyz"], measured["upper_xyz"]
        slices = tuple(slice(int(a), int(b) + 1) for a, b in zip(lower[::-1], upper[::-1]))
        cropped = self.mask[slices]
        origin = lower @ self.affine[:3, :3].T + self.affine[:3, 3]
        geometry = Volume(cropped, self.spacing, origin, self.direction)
        return _bounded_surface(mesh_from_mask(cropped, geometry, smooth_iterations=0), DISPLAY_MAX_CELLS)

    def volume(self):
        return Volume(self.mask, self.spacing, self.origin, self.direction)
