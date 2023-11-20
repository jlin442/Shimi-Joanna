import os
import librosa
from components import *

# handles the main window of the app, including Canvas and the Dance Library 

class MainWindow(QWidget):
    def __init__(self, dances_csv_path, json_path):
        super().__init__()
        self.setWindowTitle("Shimi Gesture Composer")
        self.dances_csv_path = dances_csv_path
        self.json_path = json_path

        canvas = Canvas(json_path)
        self.sequences = canvas.sequence_layout
        canvas.transport.save_btn.clicked.connect(self.sequences.save_dances)
        canvas.transport.delete_btn.clicked.connect(self.sequences.delete_all_dances)

        library_scroll = QScrollArea()
        library_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        library_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        library_scroll.setWidgetResizable(True)
        self.library = Library(dances_csv_path=dances_csv_path)
        self.library.new_gesture_signal.connect(self.new_gesture_callback)
        library_scroll.setWidget(self.library)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(canvas, 1)
        layout.addWidget(library_scroll, 0)
        self.setLayout(layout)


    def new_gesture_callback(self, danceblock: DanceBlock):
        danceblock.save(self.dances_csv_path)
        self.library.reload_dances()    

    def open_file(self):
        dg = QFileDialog()
        dg.setFileMode(QFileDialog.AnyFile)
        dg.setFilter("Audio files (*.wav)")
        dg.AcceptOpen = True
        fname = dg.selectedFiles()
        print(fname)
        return fname


if __name__ == "__main__":
    app = QApplication([])
    json_path = "Closer.json"
    window = MainWindow(dances_csv_path="gestures", json_path=json_path)
    window.show()
    app.exec()
