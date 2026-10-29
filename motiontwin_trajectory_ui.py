import numpy as np

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QSizePolicy,
    QSlider, QSplitter, QToolButton, QVBoxLayout, QWidget,
)

from motiontwin import Volume
from motiontwin_trajectory import TrajectoryFrame, sample_trajectory_slice


def _orientation(vector):
    letters=(("R","L"),("A","P"),("I","S"))
    order=np.argsort(-np.abs(vector))
    return "".join(letters[index][int(vector[index]>0)] for index in order
                   if abs(vector[index])>=.2*max(abs(vector)))


def _tick_step(scale):
    requested=62./max(scale,1e-9)
    magnitude=10.**np.floor(np.log10(requested))
    return next(value*magnitude for value in (1.,2.,5.,10.) if value*magnitude>=requested)


class TrajectorySliceCanvas(QWidget):
    station_selected=Signal(float)
    station_scrolled=Signal(float)
    sample_hovered=Signal(str)

    def __init__(self,kind,title):
        super().__init__()
        self.kind,self.title=kind,title
        self.slice_data=self.plane=self.frame=None
        self.station_mm=0.
        self.window_width,self.window_level=1500.,-500.
        self.styles={}
        self.show_overlays=True
        self.can_navigate=False
        self._image=None
        self.setMinimumSize(240,170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Click a longitudinal CT view to inspect that position along the fixed route. "
            "Wheel moves 1 mm along the route; Shift+wheel moves 0.1 mm. Hover reads a sampled CT pixel."
            if kind!="cross_section" else
            "CT perpendicular to the planned needle. Wheel moves 1 mm along the route; Shift+wheel moves 0.1 mm. "
            "Hover reads a sampled CT pixel; the magenta marker is the inspection centre.")

    @property
    def available_rect(self):
        return QRectF(46.,43.,max(1.,self.width()-69.),max(1.,self.height()-82.))

    @property
    def pixels_per_mm(self):
        if self.plane is None:
            return 1.
        rows,columns=self.plane.shape
        return min(self.available_rect.width()/(columns*self.plane.spacing[0]),
                   self.available_rect.height()/(rows*self.plane.spacing[1]))

    @property
    def image_rect(self):
        rect=self.available_rect
        if self.plane is None:
            return rect
        rows,columns=self.plane.shape
        scale=self.pixels_per_mm
        width,height=columns*self.plane.spacing[0]*scale,rows*self.plane.spacing[1]*scale
        return QRectF(rect.center().x()-width/2.,rect.center().y()-height/2.,width,height)

    def world_to_screen(self,point):
        if self.plane is None:
            raise ValueError("A CT plane is required before projecting inspection coordinates.")
        pixel=np.asarray(self.plane.world_to_pixel(point),dtype=float)
        if pixel.shape!=(2,):
            raise ValueError("Select one physical inspection point.")
        rect,scale=self.image_rect,self.pixels_per_mm
        return QPointF(rect.left()+(pixel[0]+.5)*self.plane.spacing[0]*scale,
                       rect.bottom()-(pixel[1]+.5)*self.plane.spacing[1]*scale)

    def screen_to_world(self,position):
        if self.plane is None or not self.image_rect.contains(position):
            return None
        rect,scale=self.image_rect,self.pixels_per_mm
        pixel=((position.x()-rect.left())/(self.plane.spacing[0]*scale)-.5,
               (rect.bottom()-position.y())/(self.plane.spacing[1]*scale)-.5)
        return self.plane.pixel_to_world(pixel)

    def set_data(self,data,frame,station_mm,*,width,level,styles=None,show_overlays=True,can_navigate=False):
        self.slice_data=data
        self.plane=None if data is None else data.plane
        self.frame=frame
        self.station_mm=float(station_mm)
        self.window_width,self.window_level=float(width),float(level)
        self.styles={} if styles is None else dict(styles)
        self.show_overlays=bool(show_overlays)
        self.can_navigate=bool(can_navigate)
        self._recolor()

    def set_station(self,station_mm):
        self.station_mm=float(station_mm)
        self.update()

    def set_appearance(self,width,level,styles,show_overlays):
        self.window_width,self.window_level=float(width),float(level)
        self.styles=dict(styles)
        self.show_overlays=bool(show_overlays)
        self._recolor()

    def clear(self):
        self.slice_data=self.plane=self.frame=self._image=None
        self.can_navigate=False
        self.update()

    def _recolor(self):
        data=self.slice_data
        if data is None:
            self._image=None
            self.update()
            return
        low=self.window_level-self.window_width/2.
        grey=np.clip((data.plane.image-low)*255./self.window_width,0.,255.).astype(np.uint8)
        rgb=np.repeat(grey[...,None],3,axis=2)
        if self.show_overlays:
            for name,mask in data.overlays.items():
                style=self.styles.get(name)
                if style is None or not style.visible:
                    continue
                color=QColor(style.color)
                alpha=float(style.opacity)
                shade=np.array([color.red(),color.green(),color.blue()])
                selected=mask&data.coverage
                rgb[selected]=np.rint((1.-alpha)*rgb[selected]+alpha*shade).astype(np.uint8)
        rows,columns=np.indices(data.coverage.shape)
        background=np.where((rows//8+columns//8)%2,34,43).astype(np.uint8)
        rgb[~data.coverage]=background[~data.coverage,None]
        shown=np.ascontiguousarray(rgb[::-1])
        self._image=QImage(shown.data,shown.shape[1],shown.shape[0],shown.strides[0],
                           QImage.Format.Format_RGB888).copy()
        self.update()

    def _rulers(self,painter):
        rect,plane,scale=self.image_rect,self.plane,self.pixels_per_mm
        centre=(np.asarray(self.frame.entry_lps_mm) if self.kind!="cross_section"
                else self.frame.point_at(self.station_mm))
        offset=(plane.origin-centre)@np.vstack((plane.u,plane.v)).T
        step=_tick_step(scale)
        painter.setPen(QColor("#a4b6bf"))
        font=painter.font()
        font.setPointSizeF(8.)
        painter.setFont(font)
        for axis in (0,1):
            count=plane.shape[1-axis]
            spacing=plane.spacing[axis]
            lower,upper=offset[axis]-.5*spacing,offset[axis]+(count-.5)*spacing
            ticks=np.arange(np.ceil(lower/step),np.floor(upper/step)+1)*step
            for value in ticks:
                label=f"{0. if abs(value)<step*1e-9 else value:g}"
                if axis==0:
                    x=rect.left()+(value-lower)*scale
                    painter.drawLine(QPointF(x,rect.bottom()),QPointF(x,rect.bottom()+4.))
                    painter.drawText(QRectF(x-24.,rect.bottom()+5.,48.,15.),Qt.AlignmentFlag.AlignHCenter,label)
                else:
                    y=rect.bottom()-(value-lower)*scale
                    painter.drawLine(QPointF(rect.left()-4.,y),QPointF(rect.left(),y))
                    painter.drawText(QRectF(0.,y-7.,rect.left()-7.,15.),Qt.AlignmentFlag.AlignRight,label)
        painter.drawText(QRectF(rect.left(),self.height()-19.,rect.width(),15.),
            Qt.AlignmentFlag.AlignHCenter,"distance from entry · mm" if self.kind!="cross_section" else "offset from route · mm")

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor("#101416"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        painter.fillRect(QRectF(0.,0.,self.width(),28.),QColor("#263740"))
        painter.setPen(QColor("#e1eaf0"))
        font=painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(9.,3.,self.width()-18.,22.),Qt.AlignmentFlag.AlignVCenter,self.title)
        font.setBold(False)
        painter.setFont(font)
        if self._image is None:
            painter.setPen(QColor("#a4adb4"))
            painter.drawText(self.available_rect,Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                "Build a current needle path to inspect its CT.")
            return
        rect=self.image_rect
        painter.drawImage(rect,self._image)
        painter.setPen(QPen(QColor("#53636e"),1.))
        painter.drawRect(rect)
        self._rulers(painter)
        side_y=(rect.center().y()-9. if self.kind=="cross_section"
                else rect.top()+rect.height()*.25-9.)
        for label_box,label in ((QRectF(rect.left()+3.,side_y,25.,18.),_orientation(-self.plane.u)),
                (QRectF(rect.right()-28.,side_y,25.,18.),_orientation(self.plane.u)),
                (QRectF(rect.center().x()-20.,rect.top()+2.,40.,17.),_orientation(self.plane.v))):
            painter.fillRect(label_box,QColor(8,13,17,155))
            painter.setPen(QColor("#b9d1de"))
            painter.drawText(label_box,Qt.AlignmentFlag.AlignCenter,label)
        painter.save()
        painter.setClipRect(rect)
        selected=self.world_to_screen(self.frame.point_at(self.station_mm))
        if self.kind!="cross_section":
            entry=self.world_to_screen(self.frame.entry_lps_mm)
            endpoint=self.world_to_screen(self.frame.endpoint_lps_mm)
            painter.setPen(QPen(QColor("#edf1f4"),1.5,Qt.PenStyle.DashLine))
            painter.drawLine(entry,endpoint)
            painter.setPen(QPen(QColor("#edf1f4"),1.5))
            painter.drawEllipse(entry,4.,4.)
            painter.setPen(QPen(QColor("#63dff0"),1.5))
            painter.drawEllipse(endpoint,4.,4.)
            painter.setPen(QPen(QColor("#e4a8e8"),1.5))
            painter.drawLine(QPointF(selected.x(),rect.top()),QPointF(selected.x(),rect.bottom()))
        painter.setPen(QPen(QColor("#e4a8e8"),1.5))
        painter.drawLine(selected-QPointF(7.,0.),selected+QPointF(7.,0.))
        painter.drawLine(selected-QPointF(0.,7.),selected+QPointF(0.,7.))
        painter.drawEllipse(selected,3.,3.)
        painter.restore()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.can_navigate and self.kind!="cross_section":
            world=self.screen_to_world(event.position())
            if world is not None:
                self.station_selected.emit(float(self.frame.station_of(world,clamp=True)))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        point=self.screen_to_world(event.position())
        if point is None or self.slice_data is None:
            self.sample_hovered.emit("")
        else:
            pixel=np.rint(self.plane.world_to_pixel(point)).astype(int)
            column,row=np.clip(pixel,(0,0),np.asarray(self.plane.shape[::-1])-1)
            physical=self.plane.pixel_to_world((column,row))
            coords=", ".join(f"{value:+.2f}" for value in physical)
            value=(f"{float(self.plane.image[row,column]):.1f} HU" if self.slice_data.coverage[row,column]
                   else "outside source CT coverage")
            self.sample_hovered.emit(f"{self.title} · sampled LPS {coords} mm · {value}")
        super().mouseMoveEvent(event)

    def leaveEvent(self,event):
        self.sample_hovered.emit("")
        super().leaveEvent(event)

    def wheelEvent(self,event):
        delta=event.angleDelta().y()
        if self.can_navigate and self.frame is not None and delta:
            step=.1 if event.modifiers()&Qt.KeyboardModifier.ShiftModifier else 1.
            self.station_scrolled.emit(float(delta/120.*step))
            event.accept()
            return
        super().wheelEvent(event)


class TrajectoryInspectorDialog(QDialog):
    station_changed=Signal(float)

    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.plan=self.volume=self.frame=None
        self.source_matrix=None
        self.can_navigate=False
        self.display_time_s=None
        self.masks,self.styles={},{}
        self.station_mm=0.
        self._sample_key=self._appearance_key=None
        self._longitudinal={}
        self._cross_section=None
        self._width,self._level=1500.,-500.
        self._master_overlays=True
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Needle-aligned CT inspector")
        self.resize(1100,760)
        self.setMinimumSize(800,580)
        layout=QVBoxLayout(self)
        self.context_label=QLabel()
        self.context_label.setWordWrap(True)
        self.context_label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.context_label)
        controls=QHBoxLayout()
        self.entry_button=QToolButton()
        self.entry_button.setText("Entry")
        self.entry_button.clicked.connect(lambda:self.set_station(0.))
        controls.addWidget(self.entry_button)
        self.station_slider=QSlider(Qt.Orientation.Horizontal)
        self.station_slider.setRange(0,10000)
        self.station_slider.setTracking(False)
        self.station_slider.setToolTip("Inspection position along the frozen path; does not advance insertion or simulation time.")
        self.station_slider.valueChanged.connect(lambda value:self.set_station(
            self.frame.length_mm*value/10000.) if self.frame is not None else None)
        controls.addWidget(self.station_slider,1)
        self.station=QDoubleSpinBox()
        self.station.setDecimals(3)
        self.station.setSingleStep(1.)
        self.station.setSuffix(" mm")
        self.station.setKeyboardTracking(False)
        self.station.valueChanged.connect(self.set_station)
        controls.addWidget(self.station)
        self.endpoint_button=QToolButton()
        self.endpoint_button.setText("Endpoint")
        self.endpoint_button.clicked.connect(lambda:self.set_station(self.frame.length_mm) if self.frame is not None else None)
        controls.addWidget(self.endpoint_button)
        self.overlays=QCheckBox("Segmentation overlays")
        self.overlays.setChecked(True)
        self.overlays.toggled.connect(self._overlay_changed)
        controls.addWidget(self.overlays)
        layout.addLayout(controls)
        self.position_label=QLabel()
        self.position_label.setWordWrap(True)
        self.position_label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.position_label)
        self.splitter=QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        longitudinal=QSplitter(Qt.Orientation.Vertical)
        longitudinal.setChildrenCollapsible(False)
        self.panels={}
        for kind,title in (("longitudinal_1","Longitudinal 1"),("longitudinal_2","Longitudinal 2"),
                           ("cross_section","Perpendicular cross-section")):
            panel=TrajectorySliceCanvas(kind,title)
            panel.station_selected.connect(self.set_station)
            panel.station_scrolled.connect(lambda delta:self.set_station(self.station_mm+delta))
            panel.sample_hovered.connect(self._hovered)
            self.panels[kind]=panel
            if kind=="cross_section":
                self.splitter.addWidget(panel)
            else:
                longitudinal.addWidget(panel)
        self.splitter.insertWidget(0,longitudinal)
        self.splitter.setSizes([650,430])
        longitudinal.setSizes([280,280])
        layout.addWidget(self.splitter,1)
        self.readout=QLabel()
        self.readout.setWordWrap(True)
        self.readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        layout.addWidget(self.readout)
        footer=QHBoxLayout()
        note=QLabel("White: route · cyan: endpoint · magenta: inspection · checkerboard: outside CT.")
        self.scope_note=note
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        footer.addWidget(note,1)
        close=QToolButton()
        close.setText("Close")
        close.clicked.connect(self.close)
        footer.addWidget(close)
        layout.addLayout(footer)
        self.invalidate()

    def invalidate(self):
        self.plan=self.volume=self.frame=self.source_matrix=None
        self.masks,self.styles={},{}
        self._sample_key=self._appearance_key=None
        self._longitudinal={}
        self._cross_section=None
        self.can_navigate=False
        self.station_mm=0.
        self.context_label.setText("No current needle path.")
        self.position_label.setText("Build a path in Needle to inspect the source CT along its trajectory.")
        self.readout.setText("The plan is unavailable or has changed; previous CT samples have been cleared.")
        for panel in self.panels.values():
            panel.clear()
        self._enable_controls()

    def set_context(self,plan,volume,*,masks=None,styles=None,source_matrix=None,width=1500.,level=-500.,
                    can_navigate=False,display_time_s=None,show_overlays=True):
        if plan is None:
            self.invalidate()
            return
        if not isinstance(volume,Volume) or not np.isfinite([width,level]).all() or width<=0:
            raise ValueError("CT inspection requires a volume and finite positive window width.")
        matrix=np.eye(4) if source_matrix is None else np.asarray(source_matrix,dtype=float)
        if (matrix.shape!=(4,4) or not np.isfinite(matrix).all()
                or not np.allclose(matrix[3],[0.,0.,0.,1.],rtol=0,atol=1e-12)):
            raise ValueError("CT inspection requires a finite affine source-to-display transform.")
        try:
            inverse=np.linalg.inv(matrix)
        except np.linalg.LinAlgError as error:
            raise ValueError("The current CT transform is singular.") from error
        if display_time_s is not None and not np.isfinite(display_time_s):
            raise ValueError("The displayed CT time must be finite when supplied.")
        masks={} if masks is None else dict(masks)
        styles={} if styles is None else dict(styles)
        visible={key:mask for key,mask in masks.items() if key in styles and styles[key].visible}
        changed=plan is not self.plan or volume is not self.volume
        frame=TrajectoryFrame.from_plan(plan) if changed else self.frame
        key=(id(plan),id(volume),tuple((name,id(mask)) for name,mask in visible.items()),matrix.tobytes())
        effective_overlays=bool(show_overlays) and self.overlays.isChecked()
        appearance=(float(width),float(level),tuple(styles.items()),effective_overlays)
        station=0. if changed else self.station_mm
        if key!=self._sample_key:
            longitudinal={kind:sample_trajectory_slice(volume,frame,kind,masks=visible,world_to_reference=inverse)
                          for kind in ("longitudinal_1","longitudinal_2")}
            cross=sample_trajectory_slice(volume,frame,"cross_section",station,masks=visible,world_to_reference=inverse)
        else:
            longitudinal,cross=self._longitudinal,self._cross_section
        self.plan,self.volume,self.frame=plan,volume,frame
        self.source_matrix=matrix.copy()
        self.masks,self.styles=visible,styles
        self.can_navigate=bool(can_navigate)
        self._master_overlays=bool(show_overlays)
        self.display_time_s=display_time_s
        self._width,self._level=float(width),float(level)
        if changed:
            self.station_mm=station
        self._longitudinal,self._cross_section=longitudinal,cross
        self.station.blockSignals(True)
        self.station.setRange(0.,frame.length_mm)
        self.station.setValue(self.station_mm)
        self.station.blockSignals(False)
        self.station_slider.blockSignals(True)
        self.station_slider.setValue(round(self.station_mm/frame.length_mm*10000))
        self.station_slider.blockSignals(False)
        if key!=self._sample_key or appearance!=self._appearance_key:
            for kind,panel in self.panels.items():
                panel.set_data(cross if kind=="cross_section" else longitudinal[kind],frame,self.station_mm,
                    width=width,level=level,styles=styles,show_overlays=effective_overlays,can_navigate=can_navigate)
        else:
            for panel in self.panels.values():
                panel.can_navigate=bool(can_navigate)
        self._sample_key,self._appearance_key=key,appearance
        time=(f"displayed anatomy {display_time_s:.3f} s" if display_time_s is not None else "original static CT")
        self.context_label.setText(f"{plan.target.name} · path {frame.length_mm:.2f} mm · planned at {plan.planning_time_s:.3f} s · {time}. "
            f"W {width:g} / L {level:g}. Source intensities are resampled in physical LPS millimetres.")
        self._enable_controls()
        self._position_readout()
        self._hovered("")

    def _enable_controls(self):
        for widget in (self.station,self.station_slider,self.entry_button,self.endpoint_button):
            widget.setEnabled(self.frame is not None and self.can_navigate)
        self.overlays.setEnabled(self.frame is not None and bool(self.masks) and self._master_overlays)
        self.overlays.setToolTip("Show supplied segmentation masks on the resampled CT planes."
            if self._master_overlays else "Enable CT segmentation overlays in the main Imaging view first.")

    def set_navigation_enabled(self,enabled):
        self.can_navigate=bool(enabled) and self.frame is not None
        for panel in self.panels.values():
            panel.can_navigate=self.can_navigate
        self._enable_controls()
        self._hovered("")

    def _position_readout(self):
        if self.frame is None:
            return
        point=self.frame.point_at(self.station_mm)
        self.position_label.setText(f"From entry {self.station_mm:.3f} mm · remaining {self.frame.length_mm-self.station_mm:.3f} mm · "
            "LPS "+", ".join(f"{value:+.3f}" for value in point)+" mm")

    def set_station(self,value):
        if self.frame is None or not self.can_navigate:
            return False
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.integer,np.floating)) or not np.isfinite(value):
            raise ValueError("The inspection position must be a finite distance in millimetres.")
        station=float(np.clip(value,0.,self.frame.length_mm))
        previous=self.station_mm
        previous_cross=self._cross_section
        previous_plan=self.plan
        if station!=self.station_mm:
            self.station_mm=station
            self._cross_section=sample_trajectory_slice(self.volume,self.frame,"cross_section",station,
                masks=self.masks,world_to_reference=np.linalg.inv(self.source_matrix))
            self._display_station()
        callback=getattr(self.owner,"inspect_trajectory_station",None)
        if callback is not None and not callback(station,self.plan):
            if self.plan is previous_plan:
                self.station_mm,self._cross_section=previous,previous_cross
                self._display_station()
            self.readout.setText("This inspection position cannot be linked to the current CT view.")
            return False
        if self.plan is not previous_plan or self.frame is None:
            return False
        self._display_station()
        self._hovered("")
        self.station_changed.emit(station)
        return True

    def _display_station(self):
        station=self.station_mm
        self.panels["cross_section"].set_data(self._cross_section,self.frame,station,width=self._width,level=self._level,
            styles=self.styles,show_overlays=self._master_overlays and self.overlays.isChecked(),can_navigate=self.can_navigate)
        for kind in ("longitudinal_1","longitudinal_2"):
            self.panels[kind].set_station(station)
        self.station.blockSignals(True)
        self.station.setValue(station)
        self.station.blockSignals(False)
        self.station_slider.blockSignals(True)
        self.station_slider.setValue(round(station/self.frame.length_mm*10000))
        self.station_slider.blockSignals(False)
        self._position_readout()

    def _overlay_changed(self,checked):
        effective=self._master_overlays and checked
        for panel in self.panels.values():
            panel.set_appearance(self._width,self._level,self.styles,effective)
        if self._appearance_key is not None:
            self._appearance_key=(*self._appearance_key[:-1],bool(effective))

    def _hovered(self,text):
        if text:
            self.readout.setText(text)
        elif self.frame is not None:
            self.readout.setText("Click a longitudinal CT or scroll a panel to inspect the fixed route. Insertion depth and time stay separate."
                if self.can_navigate else "CT samples remain available. Return to Motion or Needle and finish any active operation to navigate.")
