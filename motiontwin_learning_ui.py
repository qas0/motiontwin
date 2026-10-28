import importlib.util
import json
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QToolButton, QProgressBar, QTabWidget, QWidget, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QSplitter, QSizePolicy, QFileDialog,
    QPlainTextEdit, QScrollArea, QFrame,
)

from motiontwin import BASELINE_METHODS, BREATHING_PATTERNS
from motiontwin_charts import InteractiveChart
from motiontwin_learning import (
    LEARNED_METHOD, LEARNING_HORIZONS, LearningSettings,
    train_motion_predictor, save_predictor, load_predictor,
)


def torch_available():
    try:
        return importlib.util.find_spec("torch") is not None
    except (ImportError, ValueError):
        return False


def _number(value):
    return "—" if value is None else f"{value:.3f}"


class TrainingLossPlot(InteractiveChart):
    def __init__(self):
        self.history=()
        self.best_epoch=None
        super().__init__()
        self.setMinimumHeight(240)
        self._refresh_chart()

    def set_data(self,history=(),best_epoch=None):
        history=tuple(dict(row) for row in history)
        changed=history!=self.history or best_epoch!=self.best_epoch
        self.history,self.best_epoch=history,best_epoch
        self._refresh_chart(reset=changed)

    def _chart_spec(self):
        if not self.history:
            return dict(title="Training and validation loss",empty="Complete a training run to inspect its recorded loss and selected epoch.")
        epochs=[row["epoch"] for row in self.history]
        series=[dict(name=label,x=epochs,y=[row[key] for row in self.history],color=colour,
            points=len(epochs)==1) for label,key,colour in
            (("Training","train_mse","#93cbe0"),("Validation","validation_mse","#ffc465"))]
        upper=max(float(max(item["y"])) for item in series)
        ticks=tuple(epochs[index] for index in sorted(set(np.linspace(0,len(epochs)-1,min(6,len(epochs)),dtype=int))))
        return dict(title="Standardized component MSE by epoch · best validation marked",
            xlim=(float(epochs[0]),float(max(epochs[-1],epochs[0]+1))),
            ylim=(0.,max(.001,upper*1.08)),series=series,xunit="",yunit="",xticks=ticks,
            vertical=[] if self.best_epoch is None else [self.best_epoch])

    def _copy_to(self,other):
        other.set_data(self.history,self.best_epoch)


class LearnedErrorPlot(InteractiveChart):
    def __init__(self):
        self.rows=()
        self.truth_kind="true"
        super().__init__()
        self.setMinimumHeight(240)
        self._refresh_chart()

    def set_data(self,rows=(),truth_kind="true"):
        rows=tuple(dict(row) for row in rows)
        changed=rows!=self.rows or truth_kind!=self.truth_kind
        self.rows,self.truth_kind=rows,truth_kind
        self._refresh_chart(reset=changed)

    def _chart_spec(self):
        series=[]
        for method,colour in zip((*BASELINE_METHODS,LEARNED_METHOD),("#c0c6cc","#93cbe0","#ffc465","#c5a5e8")):
            rows=sorted((row for row in self.rows if row["method"]==method),key=lambda row:row["horizon_s"])
            if rows:
                series.append(dict(name=method,x=[row["horizon_s"] for row in rows],
                    y=[row["rmse_mm"] if row["rmse_mm"] is not None else np.nan for row in rows],
                    color=colour,line=False,points=True,
                    notes=[f"{row['available']}/{row['attempted']} available · {row['unavailable']} unavailable" for row in rows]))
        values=[float(value) for item in series for value in item["y"] if np.isfinite(value)]
        return dict(title=("True-centre" if self.truth_kind=="true" else "Noisy-observation")+" held-out 3D RMSE (mm)",
            xlim=(.5,5.),ylim=(0.,max(1.,max(values,default=0.)*1.1)),xunit="s",yunit="mm",
            series=series,xticks=LEARNING_HORIZONS,empty="Train and evaluate a model to compare all four methods on identical held-out profiles.")

    def _copy_to(self,other):
        other.set_data(self.rows,self.truth_kind)


class LearningWorker(QThread):
    result=Signal(object)
    failed=Signal(str)
    cancelled=Signal()
    progress=Signal(str)

    def __init__(self,settings,parent=None):
        super().__init__(parent)
        self.settings=settings

    def run(self):
        try:
            result=train_motion_predictor(self.settings,progress=self.progress.emit,
                cancelled=self.isInterruptionRequested)
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.result.emit(result)
        except InterruptedError as error:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.failed.emit(str(error))
        except Exception as error:
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.failed.emit(str(error))


class LearningDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.learning_result=owner.learning_result
        self._summary_rows=()
        self._worker=None
        self._pending_result=None
        self._cancel_requested=False
        self._close_after_finish=False
        self._failure=None
        self.setWindowTitle("Learned respiratory forecasting")
        self.resize(1080,730)
        self.setMinimumSize(800,600)
        layout=QVBoxLayout(self)
        intro=QLabel("Train a compact neural predictor from synthetic respiratory histories, select its best validation epoch, then compare it with three mathematical methods on separate test profiles.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        parameters=QHBoxLayout()
        self.preset=QComboBox()
        self.preset.addItem("Quick · 64 / 16 / 32 profiles","Quick")
        self.preset.addItem("Extended · 128 / 32 / 64 profiles","Extended")
        parameters.addWidget(self.preset,2)
        self.seed=QSpinBox()
        self.seed.setRange(0,2**31-1)
        self.seed.setValue(1729)
        parameters.addWidget(QLabel("Seed"))
        parameters.addWidget(self.seed,1)
        self.hidden_units=QComboBox()
        for width in (32,64,128):
            self.hidden_units.addItem(f"{width} × {width}",width)
        self.hidden_units.setCurrentIndex(1)
        parameters.addWidget(QLabel("Hidden layers"))
        parameters.addWidget(self.hidden_units,1)
        self.epochs=QSpinBox()
        self.epochs.setRange(1,300)
        self.epochs.setValue(80)
        parameters.addWidget(QLabel("Max epochs"))
        parameters.addWidget(self.epochs,1)
        layout.addLayout(parameters)
        note=QLabel("Counts are training / validation / final-test profiles. Inputs: 10 seconds of observed LPS motion at 10 Hz plus the forecast horizon. Normalization uses training data only; test outcomes never select the model.")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons=QHBoxLayout()
        self.train_button=QToolButton()
        self.train_button.setText("Train and evaluate")
        self.train_button.clicked.connect(self.train_model)
        self.run_button=self.train_button
        self.cancel_button=QToolButton()
        self.cancel_button.setText("Cancel training")
        self.cancel_button.clicked.connect(self.cancel_run)
        self.load_button=QToolButton()
        self.load_button.setText("Load saved model")
        self.load_button.setToolTip(str(owner.learned_checkpoint_path))
        self.load_button.clicked.connect(self.load_default)
        self.export_button=QToolButton()
        self.export_button.setText("Export evaluation CSV…")
        self.export_button.clicked.connect(self.export_results)
        for button in (self.train_button,self.cancel_button,self.load_button,self.export_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.progress=QProgressBar()
        self.progress.setRange(0,1)
        self.progress.setValue(0)
        self.progress.setFormat("Training runs only when requested")
        layout.addWidget(self.progress)
        self.readout=QLabel("No training is running.")
        self.readout.setWordWrap(True)
        layout.addWidget(self.readout)
        self.model_status=QLabel()
        self.model_status.setWordWrap(True)
        layout.addWidget(self.model_status)
        self.tabs=QTabWidget()
        comparison=QWidget()
        comparison_layout=QVBoxLayout(comparison)
        filters=QHBoxLayout()
        self.pattern=QComboBox()
        self.pattern.addItem("All breathing patterns","All")
        for pattern in BREATHING_PATTERNS:
            self.pattern.addItem(pattern,pattern)
        self.error_kind=QComboBox()
        self.error_kind.addItem("True centre","true")
        self.error_kind.addItem("Noisy observation","observed")
        self.horizon=QComboBox()
        self.horizon.addItem("All horizons",None)
        for horizon in LEARNING_HORIZONS:
            self.horizon.addItem(f"{horizon:g} s ahead",horizon)
        for control in (self.pattern,self.error_kind,self.horizon):
            filters.addWidget(control,1)
            control.currentIndexChanged.connect(self._show_results)
        comparison_layout.addLayout(filters)
        self.comparison_scroll=QScrollArea()
        self.comparison_scroll.setWidgetResizable(True)
        self.comparison_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.comparison_body=QWidget()
        self.comparison_body.setMinimumHeight(380)
        comparison_body_layout=QVBoxLayout(self.comparison_body)
        comparison_body_layout.setContentsMargins(0,0,0,0)
        comparison_splitter=QSplitter(Qt.Orientation.Vertical)
        comparison_splitter.setChildrenCollapsible(False)
        self.comparison_splitter=comparison_splitter
        self.error_plot=LearnedErrorPlot()
        self.error_plot.compact=True
        self.error_plot.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        comparison_splitter.addWidget(self.error_plot)
        self.summary_table=self._table(["Method","Ahead s","Available / tried","Mean 3D mm","RMSE mm","Paired Δ mm (n)"])
        self.summary_table.setMinimumHeight(120)
        comparison_splitter.addWidget(self.summary_table)
        comparison_splitter.setSizes([240,180])
        comparison_body_layout.addWidget(comparison_splitter)
        self.comparison_scroll.setWidget(self.comparison_body)
        comparison_layout.addWidget(self.comparison_scroll,1)
        self.tabs.addTab(comparison,"Held-out comparison")
        training=QWidget()
        training_layout=QVBoxLayout(training)
        self.training_scroll=QScrollArea()
        self.training_scroll.setWidgetResizable(True)
        self.training_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.training_body=QWidget()
        self.training_body.setMinimumHeight(315)
        training_body_layout=QVBoxLayout(self.training_body)
        training_body_layout.setContentsMargins(0,0,0,0)
        self.loss_plot=TrainingLossPlot()
        self.loss_plot.compact=True
        self.loss_plot.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        training_body_layout.addWidget(self.loss_plot,1)
        self.training_note=QLabel("Loss is mean squared standardized 3D component error. Model selection uses validation loss; final-test performance is shown separately.")
        self.training_note.setWordWrap(True)
        training_body_layout.addWidget(self.training_note)
        self.training_scroll.setWidget(self.training_body)
        training_layout.addWidget(self.training_scroll,1)
        self.tabs.addTab(training,"Training")
        self.trials_table=self._table(["Test profile","Pattern","Method","Ahead s","Status","True mm","Observed mm"])
        self.tabs.addTab(self.trials_table,"Every forecast")
        self.protocol=QPlainTextEdit()
        self.protocol.setReadOnly(True)
        self.protocol.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.tabs.addTab(self.protocol,"Protocol")
        layout.addWidget(self.tabs,1)
        footer=QHBoxLayout()
        scope=QLabel("Synthetic profiles share the respiratory simulator. Results assess forecasting; learned needle planning and calibrated uncertainty are separate stages.")
        scope.setWordWrap(True)
        footer.addWidget(scope,1)
        self.close_button=QToolButton()
        self.close_button.setText("Close")
        self.close_button.clicked.connect(self.reject)
        footer.addWidget(self.close_button)
        layout.addLayout(footer)
        self._update_model_status()
        if self.learning_result is not None:
            self._display_completed(self.learning_result)
        elif owner.learned_predictor is not None:
            self._display_checkpoint(owner.learned_predictor)
        self._set_busy(False)
        if not torch_available():
            self.readout.setText('PyTorch is needed for training. Install it with .\\.venv\\Scripts\\python.exe -m pip install ".[learning]". Saved-model inference remains available without PyTorch.')

    @staticmethod
    def _table(headers):
        table=QTreeWidget()
        table.setHeaderLabels(headers)
        table.setRootIsDecorated(False)
        table.setUniformRowHeights(True)
        table.setAlternatingRowColors(True)
        for column in range(len(headers)-1):
            table.header().setSectionResizeMode(column,QHeaderView.ResizeMode.ResizeToContents)
        table.header().setStretchLastSection(True)
        return table

    def _update_model_status(self):
        predictor=self.owner.learned_predictor
        if predictor is None:
            self.model_status.setText("No learned predictor is loaded. Train one here, or load the saved model.")
        else:
            self.model_status.setText(f"Loaded model {predictor.model_id[:16]} · saved weights are used for inference in Motion.")
        if not torch_available():
            self.model_status.setText(self.model_status.text()+" Training requires the optional learning dependency.")

    def _set_busy(self,busy):
        for control in (self.preset,self.seed,self.hidden_units,self.epochs):
            control.setEnabled(not busy)
        available=torch_available()
        self.train_button.setEnabled(not busy and available)
        self.train_button.setToolTip("Train on CPU with bounded threads; saves only a completed model." if available else
            'Install the optional training dependency from the project folder: .\\.venv\\Scripts\\python.exe -m pip install ".[learning]"')
        self.load_button.setEnabled(not busy and Path(self.owner.learned_checkpoint_path).is_file())
        self.cancel_button.setEnabled(busy and not self._cancel_requested)
        self.export_button.setEnabled(not busy and self.learning_result is not None)

    def train_model(self):
        if self._worker is not None or not torch_available():
            return
        settings=LearningSettings(preset=self.preset.currentData(),seed=self.seed.value(),
            hidden_units=self.hidden_units.currentData(),max_epochs=self.epochs.value())
        self._pending_result=None
        self._failure=None
        self._cancel_requested=False
        self._close_after_finish=False
        worker=LearningWorker(settings,self)
        self._worker=worker
        worker.progress.connect(self._report_progress)
        worker.result.connect(self._received)
        worker.failed.connect(self._failed)
        worker.cancelled.connect(self._cancelled)
        worker.finished.connect(self._finished)
        self.progress.setRange(0,0)
        self.progress.setFormat("Training and held-out evaluation")
        self.readout.setText("Preparing disjoint synthetic profiles. The existing model remains active until this run completes.")
        self._set_busy(True)
        worker.start()

    def run_training(self):
        self.train_model()

    def _received(self,result):
        if not self._cancel_requested:
            self._pending_result=result

    def _report_progress(self,message):
        if not self._cancel_requested:
            self.readout.setText(message)

    def _failed(self,message):
        self._failure=message

    def _cancelled(self):
        self._cancel_requested=True

    def cancel_run(self):
        if self._worker is not None:
            self._cancel_requested=True
            self._worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.readout.setText("Cancelling after the current numerical operation. The previous model and report will be kept.")

    def cancel_training(self):
        self.cancel_run()

    def _finished(self):
        worker=self._worker
        self._worker=None
        if worker is not None:
            worker.deleteLater()
        result=self._pending_result
        self._pending_result=None
        self.progress.setRange(0,1)
        self.progress.setValue(0)
        if self._cancel_requested:
            self.readout.setText("Training cancelled. The previous model and report were kept.")
            self.progress.setFormat("Cancelled")
        elif self._failure is not None:
            self.readout.setText("Training failed; the previous model and report were kept. "+self._failure)
            self.progress.setFormat("Failed")
        elif result is not None:
            try:
                path=Path(self.owner.learned_checkpoint_path)
                save_predictor(result.predictor,path,
                    protected_paths=self.owner._protected_export_paths(include_learned=False))
                self.owner.accept_learned_predictor(result.predictor,path=path,result=result)
                self.learning_result=result
                self._display_completed(result)
                self.progress.setValue(1)
                self.progress.setFormat("Completed and saved")
            except Exception as error:
                self.readout.setText("The completed model could not be published. The previous model remains active. "+str(error))
                self.progress.setFormat("Save failed")
        self._update_model_status()
        self._set_busy(False)
        if self._close_after_finish:
            super().reject()

    def load_default(self):
        if self._worker is not None:
            return
        try:
            path=Path(self.owner.learned_checkpoint_path)
            predictor=load_predictor(path)
            self.owner.accept_learned_predictor(predictor,path=path)
        except Exception as error:
            self.readout.setText("Saved model unavailable; the previous model was kept. "+str(error))
            return
        self.learning_result=self.owner.learning_result
        if self.learning_result is None:
            self._display_checkpoint(predictor)
        else:
            self._display_completed(self.learning_result)
        self._update_model_status()
        self._set_busy(False)

    def _display_checkpoint(self,predictor):
        self._summary_rows=()
        self.summary_table.clear()
        self.trials_table.clear()
        self.loss_plot.set_data()
        self.error_plot.set_data()
        self.training_note.setText("No full training or held-out test report is retained for this checkpoint. Its saved training configuration and selected epoch are available in Protocol; loss curves and evaluation outcomes are not reconstructed.")
        self.protocol.setPlainText(json.dumps(predictor.manifest,indent=2,sort_keys=True))
        self.readout.setText("Saved model loaded. Its weights and preprocessing are verified; a previous test report is not reconstructed from the checkpoint. Train and evaluate to create a new report.")

    def _display_completed(self,result):
        manifest=result.manifest
        self._summary_rows=result.summaries
        self.loss_plot.set_data(result.history,manifest.get("best_epoch"))
        self.training_note.setText(f"Best epoch {manifest.get('best_epoch','—')} / {manifest.get('epochs_completed','—')} completed · "
            f"{manifest.get('train_samples','—')} training samples · {manifest.get('validation_samples','—')} validation samples. "
            "Loss is mean squared standardized 3D component error; the test set is scored only after model selection.")
        self.protocol.setPlainText(json.dumps(manifest,indent=2,sort_keys=True))
        self.trials_table.clear()
        for row in result.rows:
            item=QTreeWidgetItem([str(row["subject_id"]),row["pattern"],row["method"],f"{row['horizon_s']:g}",
                row["status"].replace("_"," "),_number(row.get("true_error_mm")),_number(row.get("observed_error_mm"))])
            for column in range(7):
                item.setToolTip(column,row.get("reason",""))
            self.trials_table.addTopLevelItem(item)
        self._show_results()
        self.readout.setText(f"Completed: {manifest.get('train_subjects','—')} training, {manifest.get('validation_subjects','—')} validation and "
            f"{manifest.get('test_subjects','—')} held-out test profiles. All four methods use the same test observations. "
            "Mean/RMSE use available forecasts; paired differences include only common available cases.")

    def _show_results(self,*args):
        result=self.learning_result
        if result is None:
            return
        pattern=self.pattern.currentData()
        kind=self.error_kind.currentData()
        horizon=self.horizon.currentData()
        rows=[row for row in self._summary_rows if row["pattern"]==pattern and row["truth_kind"]==kind
            and (horizon is None or row["horizon_s"]==horizon)]
        self.error_plot.set_data(rows,kind)
        self.summary_table.clear()
        for row in rows:
            paired=("—" if row["paired_mean_delta_mm"] is None else
                f"{row['paired_mean_delta_mm']:+.3f} (n={row['paired_count']})")
            item=QTreeWidgetItem([row["method"],f"{row['horizon_s']:g}",f"{row['available']} / {row['attempted']}",
                _number(row["mean_error_mm"]),_number(row["rmse_mm"]),paired])
            tip=(f"{row['unavailable']} unavailable forecasts remain in the attempted count. "
                "Paired Δ is mean error minus constant-position error on common available cases; negative favours the named method. "
                "These are simulated forecast outcomes, not insertion outcomes.")
            for column in range(6):
                item.setToolTip(column,tip)
            self.summary_table.addTopLevelItem(item)

    def export_results(self):
        result=self.learning_result
        if result is None or self._worker is not None:
            return
        path,_=QFileDialog.getSaveFileName(self,"Export learned forecast evaluation","learned-forecast-evaluation.csv","CSV (*.csv)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".csv"
        if result is not self.learning_result or self._worker is not None:
            self.readout.setText("The evaluation changed while choosing an export destination. Inspect its current report before exporting.")
            return
        try:
            result.export_csv(path,protected_paths=self.owner._protected_export_paths())
            self.readout.setText("Exported the complete protocol, subject catalogue, training history and every test forecast, independent of the current filters.")
        except Exception as error:
            self.readout.setText("Evaluation export failed. "+str(error))

    def reject(self):
        if self._worker is not None:
            self._close_after_finish=True
            self.cancel_run()
            return
        super().reject()

    def closeEvent(self,event):
        if self._worker is not None:
            self._close_after_finish=True
            self.cancel_run()
            event.ignore()
            return
        super().closeEvent(event)
