from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QToolButton, QSizePolicy,
)

from motiontwin_charts import InsertionResultPlot


class NeedleResultsDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner=owner
        self.evaluation=self.constraints=self.predicted=None
        self.events=[]
        self.can_navigate=False
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Insertion results")
        self.resize(1040,700)
        self.setMinimumSize(780,570)
        layout=QVBoxLayout(self)
        self.context_label=QLabel("No current insertion result.")
        self.context_label.setWordWrap(True)
        layout.addWidget(self.context_label)
        cards=QHBoxLayout()
        self.values={}
        for key,title in (("arrival","Arrival centre error"),("minimum","Closest tip centre"),
                          ("contact","First tip-centre contact"),("clearance","Actual exclusion check")):
            box=QGroupBox(title)
            content=QVBoxLayout(box)
            value=QLabel("—")
            value.setWordWrap(True)
            value.setStyleSheet("font-size:15px;font-weight:600;color:#c9e1eb")
            content.addWidget(value)
            self.values[key]=value
            cards.addWidget(box,1)
        layout.addLayout(cards)
        self.summary=QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.splitter=QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.plot=InsertionResultPlot()
        self.plot.setMinimumWidth(380)
        self.plot.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.plot.clicked.connect(self._plot_selected)
        self.splitter.addWidget(self.plot)
        events_box=QGroupBox("Computed events")
        events_layout=QVBoxLayout(events_box)
        self.event_table=QTreeWidget()
        self.event_table.setHeaderLabels(["Event","Time s","Meaning"])
        self.event_table.setRootIsDecorated(False)
        self.event_table.header().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.header().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.header().setStretchLastSection(True)
        self.event_table.currentItemChanged.connect(self._event_selected)
        events_layout.addWidget(self.event_table,1)
        self.event_detail=QLabel("Select an event to inspect its meaning.")
        self.event_detail.setWordWrap(True)
        events_layout.addWidget(self.event_detail)
        self.go_button=QToolButton()
        self.go_button.setText("Go to selected event")
        self.go_button.clicked.connect(self._go_to_selected)
        events_layout.addWidget(self.go_button)
        self.splitter.addWidget(events_box)
        self.splitter.setSizes([620,380])
        layout.addWidget(self.splitter,1)
        self.state=QLabel()
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        controls=QHBoxLayout()
        self.play_button=QToolButton()
        self.play_button.setText("Play insertion")
        self.play_button.clicked.connect(self._play)
        self.restart_button=QToolButton()
        self.restart_button.setText("Restart insertion")
        self.restart_button.clicked.connect(self._restart)
        self.export_button=QToolButton()
        self.export_button.setText("Export evaluation CSV…")
        self.export_button.clicked.connect(self._export)
        for button in (self.play_button,self.restart_button,self.export_button):
            controls.addWidget(button)
        controls.addStretch()
        close=QToolButton()
        close.setText("Close")
        close.clicked.connect(self.close)
        controls.addWidget(close)
        layout.addLayout(controls)
        self.invalidate()

    def invalidate(self):
        self.evaluation=self.constraints=self.predicted=None
        self.events=[]
        self.can_navigate=False
        self.plot.set_data(None)
        self.event_table.clear()
        self.context_label.setText("No current insertion result.")
        for value in self.values.values():
            value.setText("—")
        self.summary.setText("Build a path in Needle to inspect its evaluated insertion.")
        self.event_detail.setText("No event selected.")
        self.state.setText("The plan is unavailable or has changed. Build a current path to inspect new results.")
        for button in (self.go_button,self.play_button,self.restart_button,self.export_button):
            button.setEnabled(False)

    def set_results(self,evaluation,constraints=None,predicted=None,*,time_s=None,can_navigate=False):
        if evaluation is None:
            if self.evaluation is not None:
                self.invalidate()
            return
        if constraints is not None and constraints.plan is not evaluation.plan:
            raise ValueError("Insertion and exclusion results must describe the same frozen plan.")
        changed=(evaluation is not self.evaluation or constraints is not self.constraints or predicted is not self.predicted)
        self.evaluation,self.constraints,self.predicted=evaluation,constraints,predicted
        self.can_navigate=bool(can_navigate)
        plan=evaluation.plan
        if changed:
            self.plot.set_data(evaluation,constraints,time_s=time_s)
            self.context_label.setText(f"{plan.target.name} · fixed path {plan.length_mm:.2f} mm · planned at {plan.planning_time_s:.4f} s")
            self.values["arrival"].setText(f"{evaluation.arrival_tip_error_mm:.3f} mm")
            self.values["minimum"].setText(f"{evaluation.min_tip_error_mm:.3f} mm\nat {evaluation.min_tip_error_time_s:.4f} s")
            self.values["contact"].setText("Not found" if evaluation.first_tip_hit_s is None else f"{evaluation.first_tip_hit_s:.4f} s")
            assessed=constraints is not None and bool(constraints.exclusions)
            self.values["clearance"].setText("Unassessed" if not assessed else
                f"{'Violation found' if constraints.violated else 'No violation detected'}\n{constraints.min_clearance_lower_bound_mm:.3f} mm minimum bound")
            text=(f"Execution summary: {plan.start_s:.4f}–{plan.arrival_s:.4f} s. "
                f"Delay: {plan.settings.delay_s:g} s; speed: {plan.settings.speed_mm_s:g} mm/s; needle radius: {plan.settings.radius_mm:g} mm. "
                "Contact uses the affine target geometry, not a fixed radius on the centre-distance graph.")
            if predicted is not None:
                text+=f" Predicted exclusion-screen minimum: {predicted.min_clearance_lower_bound_mm:.3f} mm; actual execution is shown separately."
            self.summary.setText(text)
            self._build_events()
        else:
            self.plot.set_time(time_s)
        self.play_button.setEnabled(self.can_navigate)
        self.restart_button.setEnabled(self.can_navigate)
        self.play_button.setText("Pause insertion" if self.owner.needle_timer.isActive() else "Play insertion")
        self.export_button.setEnabled(self.owner.worker is None)
        self._event_selected(self.event_table.currentItem(),None)
        phase=("before this evaluated trace" if time_s is None or time_s<plan.planning_time_s else
               "waiting for insertion" if time_s<plan.start_s else "inserting" if time_s<plan.arrival_s else
               "at arrival" if time_s==plan.arrival_s else "after this evaluated trace")
        self.state.setText((f"Displayed time: {time_s:.4f} s · {phase}. " if time_s is not None else "")+
            ("Hover inspects samples. Click a trace sample or use Go to seek the existing animation." if self.can_navigate else
             "Results remain available for inspection. Return to Motion or Needle and finish any active operation to navigate.")+
            " Exclusion clearance is a conservative numerical bound; clinical safety is not assessed.")

    def _build_events(self):
        result=self.evaluation
        plan=result.plan
        rows=[("Planning instant",plan.planning_time_s,"The fixed route was created at this time."),
            ("Insertion starts",plan.start_s,"Execution begins after the configured delay."),
            ("Closest tip centre",result.min_tip_error_time_s,"Minimum tip-to-target-centre distance during execution."),
            ("First tip contact",result.first_tip_hit_s,"First numerically detected tip-centre contact with the affine target during execution."),
            ("First shaft contact",result.first_shaft_hit_s,"First finite inserted-centreline intersection with the target; excludes shaft radius."),
            ("Arrival",plan.arrival_s,"The tip reaches the fixed endpoint.")]
        if self.constraints is not None and self.constraints.exclusions:
            rows.extend([("Minimum exclusion bound",self.constraints.min_clearance_time_s,"Minimum conservative capsule clearance bound during actual execution."),
                ("First exclusion violation",self.constraints.first_violation_s,"First bound at or below the required clearance margin during actual execution.")])
        else:
            rows.append(("Exclusion check",None,"Unassessed: no evaluated exclusion regions were supplied."))
        self.events=[dict(label=label,time_s=time,available=time is not None,meaning=meaning) for label,time,meaning in rows]
        self.event_table.blockSignals(True)
        self.event_table.clear()
        for event in self.events:
            item=QTreeWidgetItem([event["label"],"—" if event["time_s"] is None else f"{event['time_s']:.4f}",event["meaning"]])
            item.setData(0,Qt.ItemDataRole.UserRole,event["time_s"])
            for column in range(3):
                item.setToolTip(column,event["meaning"])
            self.event_table.addTopLevelItem(item)
        self.event_table.blockSignals(False)

    def _event_selected(self,current,previous):
        time=None if current is None else current.data(0,Qt.ItemDataRole.UserRole)
        self.go_button.setEnabled(self.can_navigate and time is not None)
        self.event_detail.setText("Select an event to inspect its meaning." if current is None else
            current.text(0)+": "+current.text(2)+(" No such event was found in the numerical evaluation." if time is None and current.text(0)!="Exclusion check" else ""))

    def _go_to_selected(self):
        current=self.event_table.currentItem()
        time=None if current is None else current.data(0,Qt.ItemDataRole.UserRole)
        if time is not None:
            self._plot_selected(time)

    def _plot_selected(self,time):
        if self.evaluation is not None:
            self.owner.seek_needle_result(time,self.evaluation)

    def _play(self):
        if self.can_navigate and self.owner.worker is None and self.owner._needle_result_is_current(self.evaluation):
            self.owner.toggle_needle_preview()

    def _restart(self):
        if self.can_navigate and self.owner.worker is None and self.owner._needle_result_is_current(self.evaluation):
            self.owner.restart_needle_preview()

    def _export(self):
        if self.owner.worker is None and self.owner._needle_result_is_current(self.evaluation):
            self.owner.export_needle_evaluation()
