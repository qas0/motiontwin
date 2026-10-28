from html import escape

import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QToolButton, QSizePolicy,
    QWidget, QComboBox, QScrollArea, QToolTip,
)

from motiontwin import RouteSelection, ForecastRouteSelection


def reference_patch_projection(selection, rows=None):
    if not isinstance(selection, (RouteSelection, ForecastRouteSelection)):
        raise ValueError("A patch map requires a stored route decision.")
    origin=np.asarray(selection.entry_reference,dtype=float)
    normal=np.asarray(selection.target.center_lps_mm,dtype=float)-origin
    length=np.linalg.norm(normal)
    if not np.isfinite(length) or length<=1e-9:
        raise ValueError("The reference entry and target must define a patch direction.")
    normal/=length
    u=np.cross(np.eye(3)[np.argmin(np.abs(normal))],normal)
    u/=np.linalg.norm(u)
    v=np.cross(normal,u)
    basis=np.vstack((u,v))
    points={}
    for row in selection.rows if rows is None else rows:
        entry=np.asarray(row["entry_reference"],dtype=float)
        if entry.shape!=(3,) or not np.isfinite(entry).all():
            raise ValueError("Patch candidates must contain finite reference LPS coordinates.")
        points[row["index"]]=basis@(entry-origin)
    return origin.copy(),basis,points


def _number(value, unit="mm"):
    return "Unavailable" if value is None else f"{value:.4f}"+(f" {unit}" if unit else "")


def _coordinates(value):
    return "Unavailable" if value is None else ", ".join(f"{coordinate:+.4f}" for coordinate in value)+" mm"


class RouteCandidateMap(QWidget):
    selected=Signal(int)

    def __init__(self):
        super().__init__()
        self.selection=None
        self.rows=()
        self.origin=self.basis=None
        self.points={}
        self.visible_indices=frozenset()
        self.selected_index=self.hovered_index=None
        self._extent=1.
        self.setMinimumSize(280,250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setToolTip("Inspect actual reference entry locations. Selecting a point keeps the planned needle path and CT unchanged.")

    @property
    def plot_rect(self):
        return QRectF(48,39,max(1,self.width()-68),max(1,self.height()-111))

    @property
    def pixels_per_mm(self):
        rect=self.plot_rect
        return min(rect.width(),rect.height())/(2*self._extent)

    def set_results(self,selection,rows=None):
        if selection is self.selection:
            return
        if selection is None:
            self.selection=None
            self.rows=()
            self.origin=self.basis=None
            self.points={}
            self.visible_indices=frozenset()
            self.selected_index=self.hovered_index=None
            QToolTip.hideText()
            self.update()
            return
        rows=tuple(dict(row) for row in (selection.rows if rows is None else rows))
        origin,basis,points=reference_patch_projection(selection,rows)
        self.selection,self.rows=selection,rows
        self.origin,self.basis,self.points=origin,basis,points
        self.visible_indices=frozenset(points)
        self.selected_index=self.hovered_index=None
        extent=max(selection.route_settings.patch_radius_mm,
            max((float(np.linalg.norm(point)) for point in points.values()),default=0.),1.)
        self._extent=extent*1.2
        QToolTip.hideText()
        self.update()

    def set_visible_indices(self,indices):
        self.visible_indices=frozenset(index for index in indices if index in self.points)
        if self.hovered_index not in self.visible_indices:
            self.hovered_index=None
            QToolTip.hideText()
        if self.selected_index not in self.visible_indices:
            self.selected_index=None
        self.update()

    def select_candidate(self,index):
        self.selected_index=index if index in self.visible_indices else None
        self.update()

    def point_position(self,index):
        point=self.points[index]
        centre=self.plot_rect.center()
        scale=self.pixels_per_mm
        return QPointF(centre.x()+point[0]*scale,centre.y()-point[1]*scale)

    def hit_test(self,position):
        if not self.plot_rect.adjusted(-12,-12,12,12).contains(position):
            return None
        candidates=[]
        for index in self.visible_indices:
            point=self.point_position(index)
            distance=(point.x()-position.x())**2+(point.y()-position.y())**2
            if distance<=12**2:
                candidates.append((distance,index!=self.selected_index,
                    index!=self.selection.chosen_index,index))
        return min(candidates)[-1] if candidates else None

    def mouseMoveEvent(self,event):
        index=self.hit_test(event.position())
        self.hovered_index=index
        if index is None:
            QToolTip.hideText()
        else:
            row=next(row for row in self.rows if row["index"]==index)
            status="Algorithm choice" if row["chosen"] else row["status"].capitalize()
            text=(f"<b>Entry {index+1} · {escape(status)}</b><br>"
                f"Reference LPS: {escape(_coordinates(row['entry_reference']))}<br>"
                f"Planning-time LPS: {escape(_coordinates(row['entry_lps_mm']))}<br>"
                f"{escape(row['reason'])}")
            QToolTip.showText(event.globalPosition().toPoint(),text,self)
        self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            index=self.hit_test(event.position())
            if index is not None:
                self.selected.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def leaveEvent(self,event):
        self.hovered_index=None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor("#242628"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#d8dee5"))
        painter.drawText(10,23,"Reference entry patch · mm")
        if not self.points:
            painter.setPen(QColor("#bdc6cd"))
            painter.drawText(self.rect().adjusted(12,35,-12,-12),
                Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                "Build or search a route to inspect its reference entry candidates.")
            return
        rect=self.plot_rect
        centre=rect.center()
        scale=self.pixels_per_mm
        edge=self._extent*scale
        square=QRectF(centre.x()-edge,centre.y()-edge,edge*2,edge*2)
        for fraction in (-1.,-.5,0.,.5,1.):
            offset=edge*fraction
            painter.setPen(QPen(QColor("#606b75" if fraction==0 else "#3d454d"),1))
            painter.drawLine(QPointF(centre.x()+offset,square.top()),QPointF(centre.x()+offset,square.bottom()))
            painter.drawLine(QPointF(square.left(),centre.y()-offset),QPointF(square.right(),centre.y()-offset))
            if fraction in (-1.,0.,1.):
                label=f"{self._extent*fraction:g}"
                painter.setPen(QColor("#bfc8d0"))
                painter.drawText(QRectF(centre.x()+offset-24,square.bottom()+3,48,18),Qt.AlignmentFlag.AlignCenter,label)
                painter.drawText(QRectF(0,centre.y()-offset-9,square.left()-5,18),Qt.AlignmentFlag.AlignRight,label)
        radius=self.selection.route_settings.patch_radius_mm*scale
        if radius>0:
            painter.setPen(QPen(QColor("#778694"),1,Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(centre,radius,radius)
        painter.setPen(QColor("#cbd3db"))
        painter.drawText(QRectF(square.left(),square.bottom()+21,square.width(),18),Qt.AlignmentFlag.AlignCenter,"u offset (mm)")
        painter.save()
        painter.translate(13,centre.y())
        painter.rotate(-90)
        painter.drawText(QRectF(-65,-8,130,18),Qt.AlignmentFlag.AlignCenter,"v offset (mm)")
        painter.restore()
        for row in self.rows:
            index=row["index"]
            if index not in self.visible_indices:
                continue
            position=self.point_position(index)
            colour=QColor("#92c6af" if row["status"]=="eligible" else "#e29595")
            painter.setPen(QPen(colour,1.5))
            painter.setBrush(colour)
            painter.drawEllipse(position,5.,5.)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if row["chosen"]:
                painter.setPen(QPen(QColor("#ffc465"),2))
                painter.drawEllipse(position,9.,9.)
            if index==self.selected_index:
                painter.setPen(QPen(QColor("#eff6fc"),1.8))
                painter.drawEllipse(position,12.,12.)
            elif index==self.hovered_index:
                painter.setPen(QPen(QColor("#c6d5e3"),1,Qt.PenStyle.DotLine))
                painter.drawEllipse(position,12.,12.)
            painter.setPen(QColor("#e1e7ed"))
            painter.drawText(position+QPointF(10,-9),str(index+1))
        painter.setPen(QColor("#bec8d2"))
        painter.drawText(QRectF(10,self.height()-40,self.width()-20,38),Qt.TextFlag.TextWordWrap,
            "Green: eligible · red: rejected\nAmber ring: chosen · white ring: inspected")


class RouteResultsDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.selection=None
        self.rows=()
        self._items={}
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Route decision")
        self.resize(1080,730)
        self.setMinimumSize(800,570)
        layout=QVBoxLayout(self)
        self.context_label=QLabel()
        self.context_label.setTextFormat(Qt.TextFormat.PlainText)
        self.context_label.setWordWrap(True)
        layout.addWidget(self.context_label)
        self.summary=QLabel()
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.splitter=QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        upper=QSplitter(Qt.Orientation.Horizontal)
        upper.setChildrenCollapsible(False)
        self.plot=RouteCandidateMap()
        self.plot.selected.connect(self.select_candidate)
        upper.addWidget(self.plot)
        candidates=QGroupBox("Checked candidates")
        candidate_layout=QVBoxLayout(candidates)
        self.filter_combo=QComboBox()
        for title,value in (("All candidates","all"),("Eligible","eligible"),("Rejected","rejected")):
            self.filter_combo.addItem(title,value)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        candidate_layout.addWidget(self.filter_combo)
        self.candidate_table=QTreeWidget()
        self.candidate_table.setHeaderLabels(["Entry","Length mm","Current mm","Predicted mm","Scheduled s","Status"])
        self.candidate_table.setRootIsDecorated(False)
        self.candidate_table.setUniformRowHeights(True)
        self.candidate_table.setAlternatingRowColors(True)
        self.candidate_table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        for column in range(5):
            self.candidate_table.header().setSectionResizeMode(column,QHeaderView.ResizeMode.ResizeToContents)
        self.candidate_table.header().setStretchLastSection(True)
        self.candidate_table.currentItemChanged.connect(self._row_selected)
        self.candidate_table.setToolTip("Current is the full-route planning-time clearance lower bound. Predicted is the inserted-needle interval bound. Values are millimetres; absent checks remain unassessed.")
        candidate_layout.addWidget(self.candidate_table,1)
        upper.addWidget(candidates)
        upper.setSizes([370,680])
        self.splitter.addWidget(upper)
        details=QGroupBox("Inspected candidate")
        detail_layout=QVBoxLayout(details)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        self.detail=QLabel()
        self.detail.setTextFormat(Qt.TextFormat.RichText)
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse|Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.detail.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        scroll.setWidget(self.detail)
        detail_layout.addWidget(scroll)
        self.splitter.addWidget(details)
        self.splitter.setSizes([390,200])
        layout.addWidget(self.splitter,1)
        controls=QHBoxLayout()
        self.export_button=QToolButton()
        self.export_button.setText("Export route check CSV…")
        self.export_button.clicked.connect(self._export)
        controls.addWidget(self.export_button)
        controls.addStretch()
        close=QToolButton()
        close.setText("Close")
        close.clicked.connect(self.close)
        controls.addWidget(close)
        layout.addLayout(controls)
        self.invalidate()

    def invalidate(self):
        self.selection=None
        self.rows=()
        self._items={}
        self.candidate_table.blockSignals(True)
        self.candidate_table.clear()
        self.candidate_table.blockSignals(False)
        self.plot.set_results(None)
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(0)
        for index,label in enumerate(("All candidates","Eligible","Rejected")):
            self.filter_combo.setItemText(index,f"{label} (0)")
        self.filter_combo.blockSignals(False)
        self.filter_combo.setEnabled(False)
        self.context_label.setText("No current route decision.")
        self.summary.setText("Build a checked path or search the manual entry patch in Needle.")
        self.detail.setText("The route inputs have changed or no decision is available. Run the route check to inspect current candidates.")
        self.export_button.setEnabled(False)

    def set_results(self,selection,*,busy=False):
        if selection is None:
            self.invalidate()
            return
        if not isinstance(selection,(RouteSelection,ForecastRouteSelection)):
            raise ValueError("The route explorer requires a stored geometric or forecast decision.")
        if selection is self.selection:
            self.export_button.setEnabled(not busy and self.owner.worker is None)
            return
        rows=tuple(dict(row) for row in selection.rows)
        self.plot.set_results(selection,rows)
        self.selection,self.rows=selection,rows
        forecast=isinstance(selection,ForecastRouteSelection)
        method=selection.fit.method if forecast else "Displayed centre"
        self.context_label.setText(f"{selection.target.name} · {method} · planned at {selection.planning_time_s:.4f} s · reference patch radius {selection.route_settings.patch_radius_mm:g} mm")
        eligible=sum(row["status"]=="eligible" for row in rows)
        decision=(f"Algorithm choice: Entry {selection.chosen_index+1}." if selection.chosen_index is not None else
            "Abstained: no eligible candidate; no needle path was selected.")
        self.summary.setText(f"{len(rows)} checked · {eligible} eligible · {len(rows)-eligible} rejected. {decision}\n"
            "Ranking: shortest eligible path, then greater current clearance, then entry number. Inspection keeps the decision and CT unchanged.")
        self.candidate_table.blockSignals(True)
        self.candidate_table.clear()
        self._items={}
        for row in rows:
            arrival=(row.get("arrival_s") if forecast else selection.planning_time_s+selection.needle_settings.delay_s+
                row["length_mm"]/selection.needle_settings.speed_mm_s if row["length_mm"] is not None else None)
            bound=row["clearance_lower_bound_mm"]
            predicted=row.get("predicted_clearance_lower_bound_mm")
            status="Algorithm choice" if row["chosen"] else row["status"].capitalize()
            values=[str(row["index"]+1),"—" if row["length_mm"] is None else f"{row['length_mm']:.3f}",
                "—" if bound is None else f"{bound:.3f}","—" if predicted is None else f"{predicted:.3f}",
                "—" if arrival is None else f"{arrival:.4f}",status]
            item=QTreeWidgetItem(values)
            item.setData(0,Qt.ItemDataRole.UserRole,row["index"])
            for column in range(len(values)):
                item.setToolTip(column,row["reason"])
            item.setForeground(5,QColor("#ffc465" if row["chosen"] else "#92c6af" if row["status"]=="eligible" else "#e29595"))
            self.candidate_table.addTopLevelItem(item)
            self._items[row["index"]]=item
        self.candidate_table.blockSignals(False)
        for index,(label,count) in enumerate((("All candidates",len(rows)),("Eligible",eligible),("Rejected",len(rows)-eligible))):
            self.filter_combo.setItemText(index,f"{label} ({count})")
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)
        self.filter_combo.setEnabled(True)
        self.plot.set_visible_indices(self._items)
        initial=selection.chosen_index if selection.chosen_index is not None else next(iter(self._items),None)
        self.select_candidate(initial)
        self.export_button.setEnabled(not busy and self.owner.worker is None)

    def _apply_filter(self,*args):
        state=self.filter_combo.currentData()
        visible=[]
        for row in self.rows:
            shown=state=="all" or row["status"]==state
            self._items[row["index"]].setHidden(not shown)
            if shown:
                visible.append(row["index"])
        self.plot.set_visible_indices(visible)
        current=self.candidate_table.currentItem()
        if current is None or current.isHidden():
            self.candidate_table.setCurrentItem(None)
            self._row_selected(None,None)

    def select_candidate(self,index):
        if isinstance(index,(bool,np.bool_)) or index not in self._items:
            return False
        item=self._items[index]
        if item.isHidden():
            self.filter_combo.setCurrentIndex(0)
        self.candidate_table.setCurrentItem(item)
        self.candidate_table.scrollToItem(item)
        self._row_selected(item,None)
        return True

    def _row_selected(self,current,previous):
        index=None if current is None else current.data(0,Qt.ItemDataRole.UserRole)
        self.plot.select_candidate(index)
        if index is None:
            self.detail.setText("Select a visible candidate to inspect its stored route details. The algorithm's decision remains unchanged.")
            return
        row=next(row for row in self.rows if row["index"]==index)
        selection=self.selection
        forecast=isinstance(selection,ForecastRouteSelection)
        status="Algorithm choice" if row["chosen"] else row["status"].capitalize()
        endpoint=row.get("endpoint_lps_mm") if forecast else selection.endpoint_lps_mm
        arrival=(row.get("arrival_s") if forecast else selection.planning_time_s+selection.needle_settings.delay_s+
            row["length_mm"]/selection.needle_settings.speed_mm_s if row["length_mm"] is not None else None)
        current_bound=_number(row["clearance_lower_bound_mm"]) if selection.exclusions else "Unassessed: no declared exclusions"
        if selection.exclusions and row["clearance_lower_bound_mm"] is None:
            current_bound="Unavailable: this candidate did not reach the clearance check"
        predicted=row.get("predicted_clearance_lower_bound_mm")
        predicted_bound=(_number(predicted) if predicted is not None else
            "Unassessed: no declared exclusions" if not selection.exclusions else
            "Not requested: current-geometry screening" if not forecast or selection.exclusion_policy!="Predicted motion" else
            "Unavailable for this candidate")
        values=[("Path length",_number(row["length_mm"])),("Scheduled arrival",_number(arrival,"s")),
            ("Current full-route clearance lower bound",current_bound),
            ("Predicted insertion clearance lower bound",predicted_bound),
            ("Required clearance",_number(selection.route_settings.clearance_mm)),
            ("Reference entry LPS",_coordinates(row["entry_reference"])),
            ("Planning-time entry LPS",_coordinates(row["entry_lps_mm"])),
            ("Fixed endpoint LPS",_coordinates(endpoint))]
        if forecast:
            values.extend([("Prediction time",_number(row.get("prediction_time_s"),"s")),
                ("Intercept residual",_number(row.get("intercept_residual_mm"))),
                ("Predicted minimum time",_number(row.get("predicted_clearance_time_s"),"s"))])
        body="".join(f"<tr><td style='padding-right:18px;color:#bbc8d3'>{escape(label)}</td><td>{escape(value)}</td></tr>" for label,value in values)
        u,v=self.plot.basis
        basis=("u = ("+", ".join(f"{value:+.3f}" for value in u)+"); v = ("+
            ", ".join(f"{value:+.3f}" for value in v)+") in reference LPS")
        note=(" Actual execution is evaluated only for the algorithm-chosen route; inspect its insertion results separately."
            if selection.chosen_index is not None else " No insertion was selected, so no actual execution is available.")
        self.detail.setText(f"<b>Entry {index+1} · {escape(status)}</b><p>{escape(row['reason'])}</p><table>{body}</table>"
            +(f"<p>{escape(row.get('predicted_screening_reason',''))}</p>" if row.get("predicted_screening_reason") else "")
            +f"<p>Patch axes: {escape(basis)}. The origin is the manual reference entry; equal millimetre scales are used.</p>"
            +f"<p>Schedules describe candidate geometry, including rejected routes, and are not execution outcomes. Clearance values are conservative numerical bounds including physical needle radius; eligibility uses the required margin.{escape(note)}</p>")

    def _export(self):
        if self.owner.worker is None and self.owner._route_result_is_current(self.selection):
            self.owner.export_needle_route_check()
