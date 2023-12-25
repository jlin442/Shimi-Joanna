import os
import librosa
from components import *
import socket
# ----------------

# STRUCTURE OF APP 

# Class inheritances by script (high to low):
    # app.py -> components.py -> model.py
        # app.py calls classes in components.py, which calls classes in model.py
# json_handling.py is a container for multiple functions, independent of the above

#-----------------

class MainWindow(QWidget): # handles the main window of the app, including Canvas and the Dance Library
    def __init__(self, dances_csv_path, json_path):
        super().__init__()
        self.setWindowTitle("Shimi Gesture Composer")
        self.dances_csv_path = dances_csv_path
        self.json_path = json_path

        canvas = Canvas(json_path)
        self.sequences = canvas.sequence_layout
        canvas.transport.file_btn.clicked.connect(self.open_file)
        canvas.transport.send_btn.clicked.connect(self.send_dance_to_shimi)
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
        fname, _ = QFileDialog().getOpenFileName(self,
            "Select a JSON File", 
            "music&data", 
            "JSON (*.json)"
        )
        print(fname)

    def send_dance_to_shimi(self):
        dances = self.sequences.play_dances()
        print (dances)

        # EDIT HERE !!!! --------------
            # Note: The variable (dances) is the list that we want to send to Shimi

        # server_ip = '127.0.0.1'  
        # server_port = 12345

        # audio,sr = librosa.load('music&data\EDM\Happier.wav', mono=True, sr=None) 

        # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # try:
        #     client_socket.connect((server_ip, server_port))
        #     client_socket.sendall(dances.encode())
        #     client_socket.sendall(audio.encode())

        # except ConnectionRefusedError:
        #     print("Connection was refused. Make sure the server is running.")
        # client_socket.close()

        # ----------------------------- thanks


if __name__ == "__main__":
    app = QApplication([])
    json_path = "music&data\EDM\Happier.json"
    window = MainWindow(dances_csv_path="gestures", json_path=json_path)
    window.show()
    app.exec()
