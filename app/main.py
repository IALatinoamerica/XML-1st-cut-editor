import os
import sys
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QWidget,
)

from .xml_processor import XMLProcessingError, process_xml


class ProcessorWorker(QObject):
    finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)

    def __init__(
        self,
        input_path: str,
        output_path: str,
        min_silence_ms: int,
        silence_threshold_db: int,
    ) -> None:
        super().__init__()
        self._input_path = input_path
        self._output_path = output_path
        self._min_silence_ms = min_silence_ms
        self._silence_threshold_db = silence_threshold_db

    def run(self) -> None:
        try:
            process_xml(
                self._input_path,
                self._output_path,
                self._min_silence_ms,
                self._silence_threshold_db,
                log=self.log_message.emit,
            )
        except XMLProcessingError as exc:
            self.finished.emit(False, str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            self.finished.emit(False, f"Unexpected error: {exc}")
        else:
            self.finished.emit(True, "Processing completed successfully.")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XML First Cut Editor")
        self._thread: Optional[QThread] = None
        self._worker: Optional[ProcessorWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QGridLayout()
        central_widget.setLayout(layout)

        input_label = QLabel("Input XML")
        self.input_line = QLineEdit()
        browse_input_btn = QPushButton("Browse…")
        browse_input_btn.clicked.connect(self._browse_input)

        output_label = QLabel("Output XML")
        self.output_line = QLineEdit()
        browse_output_btn = QPushButton("Browse…")
        browse_output_btn.clicked.connect(self._browse_output)

        controls_group = QGroupBox("Silence Detection")
        controls_layout = QGridLayout()
        controls_group.setLayout(controls_layout)

        threshold_label = QLabel("Silence threshold (dBFS)")
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(-100, -1)
        self.threshold_spin.setValue(-40)
        self.threshold_spin.setSingleStep(1)

        duration_label = QLabel("Minimum silence duration (ms)")
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(50, 30000)
        self.duration_spin.setSingleStep(50)
        self.duration_spin.setValue(500)

        controls_layout.addWidget(threshold_label, 0, 0)
        controls_layout.addWidget(self.threshold_spin, 0, 1)
        controls_layout.addWidget(duration_label, 1, 0)
        controls_layout.addWidget(self.duration_spin, 1, 1)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self._start_processing)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_line, 0, 1)
        layout.addWidget(browse_input_btn, 0, 2)
        layout.addWidget(output_label, 1, 0)
        layout.addWidget(self.output_line, 1, 1)
        layout.addWidget(browse_output_btn, 1, 2)
        layout.addWidget(controls_group, 2, 0, 1, 3)
        layout.addWidget(self.log_output, 3, 0, 1, 3)
        layout.addWidget(self.process_button, 4, 0, 1, 3)

        self.statusBar().showMessage("Ready")

    def _browse_input(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Premiere XML", "", "XML Files (*.xml)")
        if not file_path:
            return
        self.input_line.setText(file_path)
        if not self.output_line.text():
            suggested = self._suggest_output_path(file_path)
            self.output_line.setText(suggested)

    def _browse_output(self) -> None:
        default_path = self.output_line.text() or self._suggest_output_path(self.input_line.text())
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Processed XML", default_path, "XML Files (*.xml)")
        if file_path:
            self.output_line.setText(file_path)

    @staticmethod
    def _suggest_output_path(input_path: str) -> str:
        if not input_path:
            return ""
        directory, filename = os.path.split(input_path)
        name, _ = os.path.splitext(filename)
        return os.path.join(directory, f"{name}_cut.xml")

    def _start_processing(self) -> None:
        input_path = self.input_line.text().strip()
        output_path = self.output_line.text().strip() or self._suggest_output_path(input_path)

        if not input_path:
            QMessageBox.warning(self, "Missing input", "Please select the input XML file exported from Premiere.")
            return
        if not os.path.isfile(input_path):
            QMessageBox.critical(self, "Invalid input", "The selected input XML file does not exist.")
            return
        if not output_path:
            QMessageBox.warning(self, "Missing output", "Please define a destination file for the processed XML.")
            return

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        min_silence_ms = self.duration_spin.value()
        silence_threshold = self.threshold_spin.value()

        self.log_output.clear()
        self.statusBar().showMessage("Processing…")
        self.process_button.setEnabled(False)

        self._thread = QThread()
        self._worker = ProcessorWorker(
            input_path=input_path,
            output_path=output_path,
            min_silence_ms=min_silence_ms,
            silence_threshold_db=silence_threshold,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log_message.connect(self._append_log)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self._processing_finished)

        self._thread.start()

    def _append_log(self, message: str) -> None:
        self.log_output.append(message)

    def _processing_finished(self, success: bool, message: str) -> None:
        self.process_button.setEnabled(True)
        if success:
            self.statusBar().showMessage("Done")
            QMessageBox.information(self, "Finished", message)
        else:
            self.statusBar().showMessage("Error")
            QMessageBox.critical(self, "Processing failed", message)
        self._thread = None
        self._worker = None


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(700, 500)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
