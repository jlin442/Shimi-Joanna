import glob
import os.path
import random
import typing
import librosa
from PyQt6.QtWidgets import *
from pyqtgraph import PlotWidget, plot
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import QtCore
from PyQt6 import QtGui
import numpy as np
import pyaudio
from model import *
import actualtempo

input = 'Closer.wav'

class TransportBar(QFrame):
    position_signal = pyqtSignal(float)
    stream_ended_signal = pyqtSignal()
    new_gesture_signal = pyqtSignal(DanceBlock)

    def __init__(self):
        super().__init__()
        self.play_btn = QPushButton(text="Play")
        self.time_lbl = QLabel(self.format_seconds(0))
        self.tempo = actualtempo.tempo(input)
        self.tempo_lbl = QLabel(f"{self.tempo} BPM")
        self.new_gesture_btn = QPushButton(text="New Gesture")
        self.play_btn.clicked.connect(self.play_pause)
        self.new_gesture_btn.clicked.connect(lambda: self.launch_popup())


        self.beatlbl = QLabel("Beat:")

        layout = QHBoxLayout()
        layout.addWidget(self.new_gesture_btn, 0)
        layout.addWidget(self.play_btn, 0)
        layout.addWidget(self.time_lbl, 1)
        layout.addWidget(self.beatlbl,1)
        layout.addWidget(self.tempo_lbl, 0)
        self.setLayout(layout)

        self.is_playing = False
        self.audio, self.fs = None, None
        self.currentPosition = 0

        self.p = pyaudio.PyAudio()
        self.stream = None

        self.stream_ended_signal.connect(self.stream_ended_callback)

    def __del__(self):
        if self.stream is not None:
            self.stream.close()
        self.p.terminate()

    def seek(self, percentage):
        (percentage, measure) = actualtempo.beatseek(percentage)
        self.currentPosition = int(percentage * len(self.audio))
        self.time_lbl.setText(self.format_seconds(self.currentPosition / self.fs))
        self.beatlbl.setText(f"Beat: {measure}")

    @staticmethod
    def format_seconds(seconds):
        """
        Formats seconds to hh mm ss.

        Args:
        seconds: The number of seconds to format.

        Returns:
        A string in the format hh:mm:ss.
        """

        hours = int(seconds) // 3600
        minutes = int(seconds % 3600) // 60
        seconds = int(seconds) % 60
        return f'{hours:01d}:{minutes:02d}:{seconds:02d}'

    def set_audio(self, audio, fs):
        self.audio = audio
        self.fs = fs

    def set_tempo(self, tempo):
        self.tempo = actualtempo.tempo(input)
        self.tempo_lbl.setText(f"{self.tempo} BPM")

    def play_pause(self):
        if not self.is_playing:
            self.play()
        else:
            self.pause()

    def play(self):
        self.is_playing = True
        self.play_btn.setText("Pause")
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=1,
                                  rate=self.fs,
                                  output=True,
                                  stream_callback=self.stream_callback)

    def pause(self):
        self.is_playing = False
        self.play_btn.setText("Play")
        self.stream.stop_stream()

    def stream_callback(self, in_data, frame_count, time_info, status):
        end = np.minimum(self.currentPosition + frame_count, self.currentPosition + len(self.audio))
        data = self.audio[self.currentPosition: end]
        self.currentPosition += len(data)
        sec = self.currentPosition / self.fs
        self.position_signal.emit(sec)
        if len(data) < frame_count:
            self.stream_ended_signal.emit()
        self.time_lbl.setText(self.format_seconds(sec))
        return data, pyaudio.paContinue

    def stream_ended_callback(self):
        self.pause()
        self.seek(0)
        self.position_signal.emit(0)

    def launch_popup(self, name="Untitled"):
        pop = TextEdit(name, self, content=None, callback=self.text_callback)
        pop.show()

    def text_callback(self, name, instruction: InstructionSet):
        d = DanceBlock(name, instruction)
        self.new_gesture_signal.emit(d)


class WaveformView(PlotWidget):
    def __init__(self, mouse_press_callback):
        super().__init__()
        self.mouse_press_callback = mouse_press_callback
        self.getPlotItem().hideAxis('bottom')
        self.getPlotItem().hideAxis('left')
        self.setMouseEnabled(x=False, y=False)
        self.setYRange(-1, 1, padding=0)
        self.setContentsMargins(0, 0, 0, 0)
        self.hideButtons()

    @staticmethod
    def compress(x: np.ndarray, kernel):
        out = np.zeros(len(x) // kernel)
        for i in range(len(out)):
            temp = x[i * kernel: (i + 1) * kernel]
            m = np.max(temp)
            n = np.min(temp)
            if m < abs(n):
                m = n
            out[i] = m
        return out

    def render(self, x, kernel=5):
        x = self.compress(x, kernel)
        self.setXRange(0, len(x), padding=0)
        self.plot(x)

    def mousePressEvent(self, ev):
        self.mouse_press_callback(ev.position().x())


class SequenceView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setLayout(layout)
        p = self.palette()
        p.setColor(self.backgroundRole(), 0)
        self.setPalette(p)
        self.setAcceptDrops(True)

        self.sequence = Sequence()

    def dragEnterEvent(self, ev) -> None:
        if isinstance(ev.mimeData().parent(), Library):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        data = ev.mimeData()
        instructions = np.frombuffer(data.data("application/octet-stream"), dtype=int).reshape(-1, 4).tolist()
        danceblock = DanceBlock(name=data.text(), instructions=InstructionSet(instructions), color=data.colorData())
        self.sequence.append(danceblock)
        self.populate_layout()

    def populate_layout(self):
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        for d in self.sequence:
            self.layout().addWidget(Gesture(d, delete_callback=self.delete_callback))

    def delete_callback(self, ev, danceblock_ref: DanceBlock):
        self.sequence.remove(danceblock_ref)
        self.populate_layout()


class TextEdit(QDialog):
    def __init__(self, name, parent, content: InstructionSet = None, callback=None):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.resize(600, 300)
        self.new_gesture = content is None
        self.table_view = QTableView(self)
        if content is None:
            content = InstructionSet([[0, 0, 0, 4]])
        self.table_view.setModel(content)

        self.callback = callback

        ok_btn = QPushButton(text="Save" if self.new_gesture else "Ok")
        ok_btn.clicked.connect(self.handle_ok)
        cancel_btn = QPushButton(text="Cancel")
        cancel_btn.clicked.connect(self.handle_cancel)

        self.name_textbox = QLineEdit()
        self.name_textbox.setText(name)
        if isinstance(self.parent().parent(), SequenceView):
            self.name_textbox.setEnabled(False)
        layout = QVBoxLayout()
        layout.addWidget(self.name_textbox)
        layout.addWidget(self.table_view)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)

    def handle_ok(self, ev):
        self.close()
        if self.callback is not None:
            self.callback(self.name_textbox.text(), self.table_view.model())

    def handle_cancel(self, ev):
        self.close()


class Gesture(QLabel):
    def __init__(self, danceblock: DanceBlock, delete_callback=None):
        super().__init__(danceblock.name)
        self.danceblock = danceblock
        self.setFixedHeight(64)
        self.setFixedWidth(len(danceblock) * 20)
        self.setAlignment(Qt.AlignmentFlag.AlignLeading)
        self.setStyleSheet(f"background-color: {danceblock.color}")
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.delete_callback = delete_callback

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and isinstance(self.parent(), Library):
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())
            mime_data.setData("application/octet-stream", self.danceblock.instructions.tobytes())
            mime_data.setColorData(self.danceblock.color)
            mime_data.setParent(self.parent())
            drag.setMimeData(mime_data)
            Qt.DropAction.dropAction = drag.exec()

    def mouseDoubleClickEvent(self, ev: typing.Optional[QtGui.QMouseEvent]):
        if ev.button() == Qt.MouseButton.LeftButton and isinstance(self.parent(), SequenceView):
            self.launch_popup(self.text())

    def launch_popup(self, name):
        pop = TextEdit(name, self, content=self.danceblock.instructions, callback=self.text_callback)
        pop.show()

    def text_callback(self, name, instruction: InstructionSet):
        # self.danceblock.update(self.parse_content(text))
        self.danceblock.update(instruction)
        self.setFixedWidth(len(self.danceblock) * 20)

    @staticmethod
    def parse_content(text: str):
        text = text.splitlines(keepends=False)
        out = np.zeros((len(text), 4), dtype=int)
        for i, t in enumerate(text):
            val = t.split(sep=',')
            out[i] = np.array([int(val[0]), int(val[1]), int(val[2]), int(val[3])])
        return out

    def contextMenuEvent(self, ev) -> None:
        self.menu = QMenu(self)
        delete_action = QtGui.QAction('Delete', self)
        delete_action.triggered.connect(lambda: self.delete_callback(ev, self.danceblock))
        self.menu.addAction(delete_action)
        self.menu.popup(QtGui.QCursor.pos())


class Library(QWidget):
    def __init__(self, dances_csv_path):
        super().__init__()
        self.dances_csv_path = dances_csv_path
        self.dances: dict[str:DanceBlock] = self.load_danceblock(dances_csv_path=dances_csv_path)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)
        dances_lbl = QLabel("Dances Library")
        dances_lbl.setContentsMargins(8, 8, 8, 8)
        font = QtGui.QFont()
        font.setBold(True)
        dances_lbl.setFont(font)
        dances_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dances_lbl)

        self.dances_layout = QVBoxLayout()
        self.dances_layout.setContentsMargins(0, 0, 0, 0)
        self.dances_layout.setSpacing(0)
        layout.addLayout(self.dances_layout)

        self.populate_dances()

    @staticmethod
    def load_danceblock(dances_csv_path):
        dances = {}
        for f in glob.glob(os.path.join(dances_csv_path, "*.csv")):
            instructions = np.loadtxt(fname=f, delimiter=',', dtype=int).reshape(-1, 4).tolist()
            name = os.path.splitext(os.path.split(f)[-1])[0]
            dances[name] = DanceBlock(name=name, instructions=InstructionSet(instructions))
        return dances

    def populate_dances(self):
        for i in reversed(range(self.dances_layout.count())):
            self.dances_layout.itemAt(i).widget().setParent(None)
        for name, d in self.dances.items():
            self.dances_layout.addWidget(Gesture(d, delete_callback=self.delete_callback))

    def delete_callback(self, ev, danceblock_ref: DanceBlock):
        os.remove(os.path.join(self.dances_csv_path, f"{danceblock_ref.name}.csv"))
        self.reload_dances()

    def reload_dances(self):
        self.dances = self.load_danceblock(self.dances_csv_path)
        self.populate_dances()


class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        audio, sr = librosa.load(input, mono=True, sr=None)
        tempo = actualtempo.tempo(input)
        waveform_view = WaveformView(mouse_press_callback=self.mouse_callback)
        waveform_view.render(audio, kernel=127)

        self.transport = TransportBar()
        self.transport.set_audio(audio, sr)
        self.transport.set_tempo(tempo)
        self.total_time = len(audio) / sr

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(waveform_view, 1, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(SequenceView(), 1)
        layout.addWidget(self.transport, 0, Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)

        self.transport.position_signal.connect(self.position_callback)
        self.playhead = QWidget(parent=self)
        self.playhead.setFixedWidth(2)
        self.playhead.setFixedHeight(self.height() - self.transport.height())
        self.playhead.setStyleSheet("background-color: white")

    def position_callback(self, position):
        self.playhead.move(int(self.width() * position / self.total_time), 0)

    def mouse_callback(self, position):
        self.playhead.move(int(position), 0)
        self.transport.seek(position / self.width())

    def resizeEvent(self, a0):
        self.playhead.setFixedHeight(self.height() - self.transport.height())
        QWidget.resizeEvent(self, a0)
