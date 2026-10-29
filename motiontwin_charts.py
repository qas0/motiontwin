import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QToolButton,
    QSizePolicy, QDialog, QToolTip, QTreeWidget, QHeaderView)

from motiontwin import BASELINE_METHODS, NeedleEvaluation, ConstraintEvaluation


def result_table(headers, *, uniform_rows=False):
    table = QTreeWidget()
    table.setHeaderLabels(headers)
    table.setRootIsDecorated(False)
    if uniform_rows:
        table.setUniformRowHeights(True)
        table.setAlternatingRowColors(True)
        for column in range(len(headers) - 1):
            table.header().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
    else:
        table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.header().setStretchLastSection(True)
    return table


class InteractiveChart(QWidget):
    def __init__(self, *, components=False):
        super().__init__()
        self.series=[]
        self.inspection=[]
        self._spec={}
        self._view_range=None
        self._context=None
        self._hover=None
        self._drag=None
        self._detail_dialog=self._detail_chart=None
        self.compact=False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(265)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.toolbar=QWidget(self)
        buttons=QHBoxLayout(self.toolbar)
        buttons.setContentsMargins(0,0,0,0)
        buttons.setSpacing(4)
        self.axis_combo=QComboBox()
        for name,axis in (("SI · S",2),("AP · P",1),("LR · L",0)):
            self.axis_combo.addItem(name,axis)
        self.axis_combo.setFixedWidth(78)
        self.axis_combo.setToolTip("Signed LPS displacement: superior, posterior or left, relative to the reference target.")
        self.axis_combo.setVisible(components)
        self.axis_combo.currentIndexChanged.connect(lambda:self._refresh_chart(reset=True))
        buttons.addWidget(self.axis_combo)
        buttons.addStretch()
        self.reset_button=QToolButton()
        self.reset_button.setText("Reset")
        self.reset_button.setToolTip("Restore the complete chart range (Home).")
        self.reset_button.clicked.connect(self.reset_view)
        self.expand_button=QToolButton()
        self.expand_button.setText("Expand")
        self.expand_button.setToolTip("Open a larger linked chart; inspection and zoom keep the calculation unchanged.")
        self.expand_button.clicked.connect(self.enlarge_chart)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.expand_button)
        self.setToolTip("Hover to inspect actual samples. Ctrl+wheel zooms; middle-drag pans. Home resets the view.")

    @property
    def component(self):
        return self.axis_combo.currentData()

    @property
    def view_range(self):
        return self._view_range or self._spec.get("xlim",(0.,1.))

    @property
    def plot_rect(self):
        return QRectF(52,65,max(1,self.width()-70),max(1,self.height()-(115 if self.compact else 150)-self._legend_height()))

    def resizeEvent(self,event):
        self.toolbar.setGeometry(6,4,max(1,self.width()-12),28)
        super().resizeEvent(event)

    def _legend_height(self):
        width=max(1,self.width()-16)
        x,rows=0,1
        for series in self.series:
            size=self.fontMetrics().horizontalAdvance(series["name"])+25
            if x and x+size>width:
                rows+=1
                x=0
            x+=size
        return rows*18 if self.series else 0

    def _refresh_chart(self,*,reset=False):
        self._spec=self._chart_spec()
        self.series=self._spec.get("series",[])
        if reset:
            self._view_range=None
            self._clear_inspection()
        ready=bool(self.series)
        self.reset_button.setEnabled(ready)
        self.expand_button.setEnabled(ready)
        self.update()
        if self._detail_chart is not None:
            self._copy_to(self._detail_chart)
            self._detail_dialog.setWindowTitle(self._detail_chart._spec.get("title","Chart inspection"))

    def _copy_to(self,other):
        raise NotImplementedError

    def _clear_inspection(self):
        self.inspection=[]
        self._hover=None
        self._drag=None
        self.unsetCursor()
        QToolTip.hideText()

    def reset_view(self):
        self._view_range=None
        self._clear_inspection()
        self.update()

    def zoom_at(self,factor,anchorFraction=.5):
        if not self.series or not np.isfinite(factor) or factor<=0:
            return
        full=self._spec["xlim"]
        low,high=self.view_range
        fraction=float(np.clip(anchorFraction,0.,1.))
        anchor=low+fraction*(high-low)
        span=float(np.clip((high-low)*factor,max(1e-6,(full[1]-full[0])/1000),full[1]-full[0]))
        low=float(np.clip(anchor-fraction*span,full[0],full[1]-span))
        self._view_range=(low,low+span)
        self._clear_inspection()
        self.update()

    def _point(self,x,y):
        low,high=self.view_range
        ymin,ymax=self._spec.get("ylim",(0.,1.))
        rect=self.plot_rect
        return QPointF(rect.left()+(x-low)/(high-low)*rect.width(),rect.bottom()-(y-ymin)/(ymax-ymin)*rect.height())

    def mouseMoveEvent(self,event):
        point=event.position()
        rect=self.plot_rect
        if self._drag is not None:
            start,initial=self._drag
            span=initial[1]-initial[0]
            delta=(point.x()-start)/rect.width()*span
            full=self._spec["xlim"]
            low=float(np.clip(initial[0]-delta,full[0],full[1]-span))
            self._view_range=(low,low+span)
        self.inspection=[]
        self._hover=None
        if self.series and rect.contains(point):
            low,high=self.view_range
            x=low+(point.x()-rect.left())/rect.width()*(high-low)
            tolerance=(high-low)/rect.width()*2
            for series in self.series:
                xs=np.asarray(series["x"],dtype=float)
                if not len(xs) or x<xs.min()-tolerance or x>xs.max()+tolerance:
                    continue
                candidates=np.flatnonzero((xs>=low-tolerance)&(xs<=high+tolerance))
                if not len(candidates):
                    continue
                index=int(candidates[np.argmin(np.abs(xs[candidates]-x))])
                value=float(series["y"][index])
                notes=series.get("notes",())
                self.inspection.append(dict(name=series["name"],x=float(xs[index]),
                    y=value if np.isfinite(value) else None,note=notes[index] if len(notes) else ""))
            if self.inspection:
                self._hover=min(self.inspection,key=lambda row:abs(row["x"]-x))["x"]
                QToolTip.showText(event.globalPosition().toPoint(),self._inspection_text(),self)
        if not self.inspection:
            QToolTip.hideText()
        self.update()

    def leaveEvent(self,event):
        self.inspection=[]
        self._hover=None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton and self.series and self.plot_rect.contains(event.position()):
            self._drag=(event.position().x(),self.view_range)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self,event):
        self._drag=None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def wheelEvent(self,event):
        if event.modifiers()&Qt.KeyboardModifier.ControlModifier and self.plot_rect.contains(event.position()):
            fraction=(event.position().x()-self.plot_rect.left())/self.plot_rect.width()
            self.zoom_at(.8 if event.angleDelta().y()>0 else 1.25,fraction)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Home:
            self.reset_view()
        elif event.key() in (Qt.Key.Key_Plus,Qt.Key.Key_Equal):
            self.zoom_at(.8)
        elif event.key()==Qt.Key.Key_Minus:
            self.zoom_at(1.25)
        else:
            super().keyPressEvent(event)

    def enlarge_chart(self):
        if self._detail_dialog is not None:
            self._detail_dialog.raise_()
            self._detail_dialog.activateWindow()
            return
        if not self.series:
            return
        dialog=QDialog(self.window())
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle(self._spec.get("title","Chart inspection"))
        dialog.resize(920,540)
        layout=QVBoxLayout(dialog)
        chart=type(self)()
        chart.expand_button.hide()
        chart.axis_combo.setCurrentIndex(self.axis_combo.currentIndex())
        chart.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        layout.addWidget(chart)
        self._detail_dialog,self._detail_chart=dialog,chart
        self._copy_to(chart)
        chart.axis_combo.currentIndexChanged.connect(self.axis_combo.setCurrentIndex)
        if hasattr(self,"clicked"):
            chart.clicked.connect(self.clicked.emit)
        def closed(*args):
            self._detail_dialog=self._detail_chart=None
        dialog.finished.connect(closed)
        dialog.show()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor("#242628"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#d5d8dc"))
        title=self.fontMetrics().elidedText(self._spec.get("title",""),Qt.TextElideMode.ElideRight,max(1,self.width()-16))
        painter.drawText(8,49,title)
        rect=self.plot_rect
        if not self.series:
            painter.setPen(QColor("#b5bdc5"))
            painter.drawText(QRectF(12,65,self.width()-24,self.height()-80),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                self._spec.get("empty","No chart data available."))
            return
        low,high=self.view_range
        ymin,ymax=self._spec["ylim"]
        for value in np.linspace(ymin,ymax,4):
            y=self._point(low,value).y()
            painter.setPen(QPen(QColor("#3c4146"),1))
            painter.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            painter.setPen(QColor("#c2c7cd"))
            label=f"{value:.0%}" if self._spec.get("percent") else f"{value:.1f}"
            painter.drawText(QRectF(0,y-9,46,18),Qt.AlignmentFlag.AlignRight,label)
        tick_count=max(2,min(6,int(rect.width()/80)))
        ticks=[value for value in self._spec.get("xticks",np.linspace(low,high,tick_count)) if low<=value<=high]
        last_tick=None
        for value in ticks:
            x=self._point(value,ymin).x()
            if last_tick is not None and x-last_tick<45:
                continue
            last_tick=x
            painter.setPen(QColor("#c2c7cd"))
            painter.drawText(QRectF(x-27,rect.bottom()+3,54,18),Qt.AlignmentFlag.AlignCenter,
                f"{value:.2f}".rstrip("0").rstrip(".")+self._spec.get("xunit","s"))
        painter.save()
        painter.setClipRect(rect.adjusted(-5,-1,5,1))
        for interval in self._spec.get("shaded",()):
            left=max(low,interval["start_s"])
            right=min(high,interval["end_s"])
            if right>left:
                shade=QRectF(self._point(left,ymax),self._point(right,ymin))
                painter.fillRect(shade,QColor("#343b43"))
                if shade.width()>75:
                    painter.setPen(QColor("#b8c1ca"))
                    painter.drawText(shade.adjusted(5,4,-5,-4),Qt.AlignmentFlag.AlignBottom|Qt.TextFlag.TextWordWrap,interval["label"])
        for value in self._spec.get("horizontal",()):
            painter.setPen(QPen(QColor("#92999f"),1,Qt.PenStyle.DashLine))
            painter.drawLine(self._point(low,value),self._point(high,value))
        for value in self._spec.get("vertical",()):
            painter.setPen(QPen(QColor("#92999f"),1,Qt.PenStyle.DashLine))
            painter.drawLine(self._point(value,ymin),self._point(value,ymax))
        for series in self.series:
            painter.setPen(QPen(QColor(series["color"]),1.8,Qt.PenStyle.DashLine if series.get("dashed") else Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(series["color"]))
            previous=None
            for x,y in zip(series["x"],series["y"]):
                if not np.isfinite(y):
                    previous=None
                    continue
                point=self._point(x,y)
                if previous is not None and series.get("line",True):
                    painter.drawLine(previous,point)
                if series.get("points",False):
                    painter.drawEllipse(point,2.5,2.5)
                previous=point
        if not any(np.isfinite(series["y"]).any() for series in self.series):
            painter.setPen(QColor("#c0c6cc"))
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,"No measured or assessed values")
        for x,y,radius in self._spec.get("bars",()):
            painter.setPen(QPen(QColor("#49dcf4"),2))
            painter.drawLine(self._point(x,y-radius),self._point(x,y+radius))
            for bound in (y-radius,y+radius):
                point=self._point(x,bound)
                painter.drawLine(point-QPointF(4,0),point+QPointF(4,0))
        if self._hover is not None:
            painter.setPen(QPen(QColor("#dbe3e8"),1,Qt.PenStyle.DotLine))
            painter.drawLine(self._point(self._hover,ymin),self._point(self._hover,ymax))
        label_ends=[rect.left()-5]*3
        for event in self._spec.get("events",()):
            if not low<=event["time_s"]<=high:
                continue
            point=self._point(event["time_s"],ymax)
            painter.setPen(QPen(QColor(event["color"]),1,Qt.PenStyle.DotLine))
            painter.drawLine(point,self._point(event["time_s"],ymin))
            text=self.fontMetrics().elidedText(event["label"],Qt.TextElideMode.ElideRight,145)
            width=self.fontMetrics().horizontalAdvance(text)+6
            left=max(rect.left()+3,min(point.x()+4,rect.right()-width))
            row=next((index for index,end in enumerate(label_ends) if left>end+5),None)
            if row is not None:
                painter.drawText(QPointF(left,rect.top()+14+row*17),text)
                label_ends[row]=left+width
        painter.restore()
        x,y=8,rect.bottom()+37
        for series in self.series:
            size=self.fontMetrics().horizontalAdvance(series["name"])+25
            if x>8 and x+size>self.width()-8:
                x=8
                y+=18
            painter.setPen(QColor(series["color"]))
            painter.drawText(x,y,series["name"])
            x+=size
        painter.setPen(QColor("#c4cbd2"))
        text=self._inspection_text() if self.inspection else "Hover to inspect · Ctrl+wheel zoom · middle-drag pan"
        if not self.compact:
            painter.drawText(QRectF(8,y+7,self.width()-16,max(38,self.height()-y-12)),Qt.TextFlag.TextWordWrap,text)

    def _inspection_text(self):
        lines=[]
        for row in self.inspection:
            unit=self._spec.get("yunit","mm")
            suffix="" if self._spec.get("percent") or not unit else " "+unit
            value="unavailable" if row["y"] is None else f"{row['y']:.3f}"+suffix
            if row["y"] is not None and self._spec.get("percent"):
                value=f"{row['y']:.1%}"
            lines.append(f"{row['name']}: {row['x']:.3f}{self._spec.get('xunit','s')} · {value}"+(" · "+row["note"] if row["note"] else ""))
        return "\n".join(lines)


class ObservationPlot(InteractiveChart):
    def __init__(self):
        self.data=None
        super().__init__(components=True)
        self._refresh_chart()

    def set_data(self,data):
        changed=data is not self.data
        self.data=data
        self._refresh_chart(reset=changed)

    def _chart_spec(self):
        if self.data is None:
            return dict(title="Target observations",empty="Define a target and record observations in Motion to inspect its history.")
        axis=self.component
        data=self.data
        reference=data.target.center_lps_mm[axis]
        observed=data.observed_lps_mm[:,axis]-reference
        truth=data.evaluation_ground_truth_lps_mm[:,axis]-reference
        values=np.r_[observed,truth,0.]
        margin=max(.5,float(np.ptp(values))*.1)
        return dict(title=f"Target {'LPS'[axis]} displacement (mm)",xlim=(0.,max(.1,data.through_s)),
            ylim=(float(values.min())-margin,float(values.max())+margin),series=[
            dict(name="Noisy observations",x=data.times_s,y=observed,color="#93cbe0",line=False,points=True),
            dict(name="Simulated truth",x=data.times_s,y=truth,color="#ffc465")])

    def _copy_to(self,other):
        other.axis_combo.setCurrentIndex(self.axis_combo.currentIndex())
        other.set_data(self.data)


class ForecastPlot(InteractiveChart):
    def __init__(self):
        self.data=self.method=None
        super().__init__(components=True)
        self._refresh_chart()

    def set_data(self,data,method=None):
        changed=data is not self.data or method!=self.method
        self.data,self.method=data,method
        self._refresh_chart(reset=changed)

    def _chart_spec(self):
        data=self.data
        fit=None if data is None else data["fits"].get(self.method)
        if fit is None:
            return dict(title="Target forecast",empty="Compute baselines from recorded observations." if data is None else data["unavailable"].get(self.method,"Forecast unavailable."))
        axis=self.component
        origin=data["origin_s"]
        start=max(float(data["history_times_s"][0]),origin-min(5.,data["settings"].history_window_s))
        past=data["history_times_s"]>=start-1e-10
        reference=data["target"].center_lps_mm[axis]
        future=data["forecast_times_s"]
        predicted=fit.predict(future)[:,axis]-reference
        series=[dict(name="Past observations",x=data["history_times_s"][past],y=data["history_observed_lps_mm"][past,axis]-reference,color="#93cbe0",line=False,points=True),
            dict(name="Forecast",x=future,y=predicted,color="#49dcf4",dashed=True)]
        if len(data["truth_times_s"]):
            series.append(dict(name="Evaluation truth",x=data["truth_times_s"],y=data["truth_curve_lps_mm"][:,axis]-reference,color="#ffc465"))
        values=np.concatenate([item["y"] for item in series])
        region=data.get("regions",{}).get(self.method)
        bars=[]
        if region is not None and region.available:
            bars=[(float(future[-1]),float(predicted[-1]),region.radius_mm)]
            values=np.r_[values,predicted[-1]-region.radius_mm,predicted[-1]+region.radius_mm]
            series[1]["notes"]=[""]*(len(future)-1)+[f"Empirical 3D radius {region.radius_mm:.3f} mm; axis projection at query"]
        margin=max(.5,float(np.ptp(values))*.1)
        return dict(title=f"Forecast {'LPS'[axis]} displacement (mm) · origin {origin:g}s"+(" · 3D radius projection" if bars else ""),
            xlim=(start,origin+data["horizon_s"]),ylim=(float(values.min())-margin,float(values.max())+margin),
            series=series,vertical=[origin],bars=bars)

    def _copy_to(self,other):
        other.axis_combo.setCurrentIndex(self.axis_combo.currentIndex())
        other.set_data(self.data,self.method)


class ForecastCoveragePlot(InteractiveChart):
    def __init__(self):
        self.rows=()
        self.nominal=.9
        super().__init__()
        self._refresh_chart()

    def set_data(self,rows,nominal=.9):
        rows=tuple(dict(row) for row in rows)
        changed=rows!=self.rows or nominal!=self.nominal
        self.rows,self.nominal=rows,nominal
        self._refresh_chart(reset=changed)

    def _chart_spec(self):
        series=[]
        for method,color in zip(BASELINE_METHODS,("#c0c6cc","#93cbe0","#ffc465")):
            rows=sorted((row for row in self.rows if row["method"]==method),key=lambda row:row["horizon_s"])
            if rows:
                series.append(dict(name=method,x=[row["horizon_s"] for row in rows],
                    y=[row["coverage"] if row["coverage"] is not None else np.nan for row in rows],color=color,line=False,points=True,
                    notes=[f"{row['covered_count']}/{row['assessed_count']} assessed · {row.get('error_kind','')} · nominal {self.nominal:.0%}" for row in rows]))
        population="True-centre" if self.rows and self.rows[0].get("error_kind")=="true" else "Noisy-observation"
        return dict(title=f"{population} coverage · nominal {self.nominal:.0%}",xlim=(.5,5.),ylim=(0.,1.),
            percent=True,series=series,xticks=(.5,1.,2.,3.,5.),horizontal=[self.nominal],empty="Run the study to inspect coverage at its tested horizons.")

    def _copy_to(self,other):
        other.set_data(self.rows,self.nominal)


class LandmarkPlot(InteractiveChart):
    clicked=Signal(int)

    def __init__(self):
        self.rows=[]
        self.index=0
        super().__init__()
        self._refresh_chart()
        self.setToolTip("Hover to inspect a supplied phase; click to view its CT. Ctrl+wheel zooms. Missing observations remain unmeasured.")

    def set_data(self,rows,index):
        changed=rows!=self.rows
        self.rows,self.index=rows,index
        self._refresh_chart(reset=changed)

    def _x(self,percent):
        return self._point(percent,0.).x()

    def _chart_spec(self):
        if not self.rows:
            return dict(title="Landmark displacement (mm)",empty="Open a respiratory sequence and record a landmark in the supplied phases.")
        maximum=max([row["distance_mm"] or 0. for row in self.rows]+[1.])*1.15
        return dict(title="Landmark displacement (mm) · supplied phases",xunit="%",xlim=(self.rows[0]["phase_percent"],self.rows[-1]["phase_percent"]),
            ylim=(0.,maximum),vertical=[self.rows[self.index]["phase_percent"]],series=[dict(name="Measured displacement",
            x=[row["phase_percent"] for row in self.rows],y=[row["distance_mm"] if row["distance_mm"] is not None else np.nan for row in self.rows],
            notes=["Not measured" if row["distance_mm"] is None else "Recorded phase landmark" for row in self.rows],color="#ffc465",points=True)])

    def mousePressEvent(self,event):
        if self.rows and event.button()==Qt.MouseButton.LeftButton and self.plot_rect.contains(event.position()):
            index=min(range(len(self.rows)),key=lambda i:abs(self._x(self.rows[i]["phase_percent"])-event.position().x()))
            self.clicked.emit(index)
            return
        super().mousePressEvent(event)

    def _copy_to(self,other):
        other.set_data(self.rows,self.index)


class InsertionResultPlot(InteractiveChart):
    clicked=Signal(float)

    def __init__(self):
        self.evaluation=self.constraints=None
        self.time_s=None
        self._traces={}
        self._events=()
        super().__init__()
        self.metric_combo=QComboBox()
        self.metric_combo.addItem("Tip–target centre distance","distance")
        self.metric_combo.addItem("Target contact · normalized","contact")
        self.metric_combo.addItem("Exclusion clearance bound","clearance")
        self.metric_combo.setMinimumWidth(165)
        self.metric_combo.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.metric_combo.setToolTip("Inspect stored simulation outcomes. Normalized distance ≤1 intersects the deformed target; clearance includes physical needle radius.")
        self.toolbar.layout().insertWidget(0,self.metric_combo,1)
        self.metric_combo.currentIndexChanged.connect(lambda:self._refresh_chart(reset=True))
        self.setToolTip("Hover to inspect stored samples. Click to seek to an actual sample; middle-drag pans. Event lines mark calculated summary times.")
        self._refresh_chart()

    @property
    def events(self):
        return tuple(dict(event) for event in self._events)

    def set_data(self,evaluation=None,constraints=None,*,time_s=None):
        if evaluation is not None and not isinstance(evaluation,NeedleEvaluation):
            raise ValueError("An insertion chart requires a stored needle evaluation.")
        if constraints is not None and (not isinstance(constraints,ConstraintEvaluation)
                or evaluation is None or constraints.plan!=evaluation.plan):
            raise ValueError("Exclusion results must identify the same insertion plan.")
        self._set_time_value(time_s)
        changed=evaluation is not self.evaluation or constraints is not self.constraints
        if changed:
            self.evaluation,self.constraints=evaluation,constraints
            self._traces={}
            self._events=()
            if evaluation is not None:
                plan=evaluation.plan
                times=evaluation.times_s
                distance=dict(name="Tip–target centre",x=times,y=evaluation.tip_error_mm,color="#93cbe0")
                tip=dict(name="Tip contact ratio",x=times,y=evaluation.tip_normalized_distance,color="#93cbe0")
                shaft=dict(name="Inserted centreline ratio",x=times,y=evaluation.shaft_normalized_distance,color="#ffc465")
                self._traces={"distance":[distance],"contact":[tip,shaft]}
                if constraints is not None and constraints.exclusions:
                    self._traces["clearance"]=[dict(name="Minimum clearance lower bound",x=constraints.times_s,
                        y=np.min(constraints.clearance_lower_bounds_mm,axis=1),color="#c5a5e8")]
                events=[dict(time_s=plan.planning_time_s,label="Planning",color="#a8b1b9"),
                    dict(time_s=plan.start_s,label="Insertion start",color="#93cbe0"),
                    dict(time_s=plan.arrival_s,label="Arrival",color="#e1e8ed")]
                for time,label,color in ((evaluation.first_tip_hit_s,"First tip contact","#93cbe0"),
                        (evaluation.first_shaft_hit_s,"First centreline contact","#ffc465"),
                        (constraints.first_violation_s if constraints is not None else None,"First clearance violation","#e88a8a")):
                    if time is not None:
                        events.append(dict(time_s=time,label=label,color=color))
                self._events=tuple(sorted(events,key=lambda event:event["time_s"]))
        self.metric_combo.setEnabled(evaluation is not None)
        if changed or not self._spec:
            self._refresh_chart(reset=True)
        else:
            self._update_cursor()

    def _set_time_value(self,time_s):
        if time_s is not None:
            if (isinstance(time_s,(bool,np.bool_)) or not isinstance(time_s,(int,float,np.integer,np.floating))
                    or not np.isfinite(time_s) or time_s<0):
                raise ValueError("Chart time must be a finite nonnegative simulation time.")
            time_s=float(time_s)
        self.time_s=time_s

    def set_time(self,time_s):
        self._set_time_value(time_s)
        self._update_cursor()

    def _update_cursor(self):
        self._spec["vertical"]=[] if self.time_s is None else [self.time_s]
        self.update()
        if self._detail_chart is not None:
            self._detail_chart.set_time(self.time_s)

    def _chart_spec(self):
        result=self.evaluation
        if result is None:
            return dict(title="Insertion results",empty="Build and evaluate a needle path to inspect its calculated insertion outcomes.")
        plan=result.plan
        metric=self.metric_combo.currentData()
        series=self._traces.get(metric,[])
        if metric=="clearance" and not series:
            return dict(title="Exclusion clearance unavailable",
                empty="No declared exclusion regions were evaluated for this path. Clearance is unassessed.")
        values=np.concatenate([np.asarray(item["y"]) for item in series])
        horizontal=[]
        unit="mm"
        if metric=="contact":
            title="Target contact ratio · 1 = deformed target boundary"
            horizontal=[1.]
            unit=""
            lower=0.
            upper=max(1.2,float(values.max())*1.05)
        elif metric=="clearance":
            title=f"Clearance lower bound (mm) · required {self.constraints.clearance_mm:g} mm"
            horizontal=[self.constraints.clearance_mm]
            margin=max(.5,float(np.ptp(values))*.08)
            lower=min(0.,float(values.min()),self.constraints.clearance_mm)-margin
            upper=max(float(values.max()),self.constraints.clearance_mm)+margin
        else:
            title="Tip-to-target-centre distance (mm)"
            lower=0.
            upper=max(1.,float(values.max())*1.05)
        return dict(title=title,xlim=(plan.planning_time_s,plan.arrival_s),ylim=(lower,upper),
            yunit=unit,series=series,horizontal=horizontal,
            vertical=[] if self.time_s is None else [self.time_s],events=self.events,
            shaded=[dict(start_s=plan.planning_time_s,end_s=plan.start_s,label="Execution delay")] if plan.start_s>plan.planning_time_s else [])

    def mousePressEvent(self,event):
        if self.series and event.button()==Qt.MouseButton.LeftButton and self.plot_rect.contains(event.position()):
            low,high=self.view_range
            query=low+(event.position().x()-self.plot_rect.left())/self.plot_rect.width()*(high-low)
            times=np.asarray(self.series[0]["x"])
            if query<times[0] or query>times[-1]:
                event.accept()
                return
            # navigation uses a stored sample, including the genuine waiting trace when available.
            time=float(times[int(np.argmin(np.abs(times-query)))])
            self.clicked.emit(time)
            event.accept()
            return
        super().mousePressEvent(event)

    def enlarge_chart(self):
        fresh=self._detail_dialog is None
        super().enlarge_chart()
        if fresh and self._detail_chart is not None:
            self._detail_chart.metric_combo.currentIndexChanged.connect(self.metric_combo.setCurrentIndex)

    def _copy_to(self,other):
        other.metric_combo.setCurrentIndex(self.metric_combo.currentIndex())
        other.set_data(self.evaluation,self.constraints,time_s=self.time_s)
