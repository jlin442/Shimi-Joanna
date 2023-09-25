import os
import librosa
from components import *


class MainWindow(QWidget):
    def __init__(self, dances_csv_path):
        super().__init__()
        self.setWindowTitle("Shimi Gesture Composer")
        self.dances_csv_path = dances_csv_path
        library_scroll = QScrollArea()
        library_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        library_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        library_scroll.setWidgetResizable(True)
        self.library = Library(dances_csv_path=dances_csv_path)
        library_scroll.setWidget(self.library)

        canvas = Canvas()
        canvas.transport.new_gesture_signal.connect(self.new_gesture_callback)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(canvas, 1)
        layout.addWidget(library_scroll, 0)
        self.setLayout(layout)

    def new_gesture_callback(self, danceblock: DanceBlock):
        danceblock.save(self.dances_csv_path)
        self.library.reload_dances()


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow(dances_csv_path="gestures")
    window.show()
    app.exec()
