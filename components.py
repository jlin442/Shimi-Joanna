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
import json_handling

# handles all display elements 

input = 'Closer.wav'
path = 'Closer.json'

class TransportBar(QFrame):
    position_signal = pyqtSignal(float)
    stream_ended_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.play_btn = QPushButton(text="Play")
        self.play_btn.clicked.connect(self.play_pause)
        self.file_btn = QPushButton(text = "Open File")
        self.file_btn.clicked.connect(self.open_file)
        self.time_lbl = QLabel(self.format_seconds(0))
        self.tempo_lbl = QLabel()
        
        self.beat_lbl = QLabel("Beat:")
        self.delete_btn = QPushButton(text="Delete All Gestures")
        self.save_btn = QPushButton(text="Save All Gestures")

        layout = QHBoxLayout()
        layout.addWidget(self.play_btn, 0)
        layout.addWidget(self.file_btn,0)
        layout.addWidget(self.time_lbl, 1)
        layout.addWidget(self.beat_lbl,1)
        layout.addWidget(self.tempo_lbl, 1)
        layout.addWidget(self.delete_btn,0)
        layout.addWidget(self.save_btn,0)
        self.setLayout(layout)

        self.is_playing = False
        self.audio, self.fs = None, None
        self.currentPosition = 0

        self.p = pyaudio.PyAudio()
        self.stream = None

        self.stream_ended_signal.connect(self.stream_ended_callback)

        # self.path = path

    def __del__(self):
        if self.stream is not None:
            self.stream.close()
        self.p.terminate()

    def seek(self, percentage):
        self.currentPosition = int(percentage * len(self.audio))
        self.time_lbl.setText(self.format_seconds(self.currentPosition / self.fs))
        self.beat_define(self.currentPosition)

    def beat_define(self,position):
        beat_number = json_handling.beatseek(position, path, self.fs)
        self.beat_lbl.setText(f"Beat: {beat_number}")
       
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

    def open_file(self):
        path = QFileDialog.getOpenFileName(self, 'Open file')
        path = path[0]
        return path

    def set_audio(self, audio, fs):
        self.audio = audio
        self.fs = fs

    def set_tempo(self, tempo):
        self.tempo = json_handling.tempo(path)
        self.tempo_lbl.setText("BPM: " f"{self.tempo}")

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
        self.beat_define(self.currentPosition)
        self.time_lbl.setText(self.format_seconds(sec))
        return data, pyaudio.paContinue
      
    def stream_ended_callback(self):
        self.pause()
        self.seek(0)
        self.position_signal.emit(0) 


class WaveformView(PlotWidget):
    def __init__(self, mouse_press_callback):
        super().__init__()
        self.mouse_press_callback = mouse_press_callback
        self.getPlotItem().hideAxis('left')

        self.setMouseEnabled(x=True, y=False)
        self.setYRange(-1.2, 1, padding=0)
    
        self.setContentsMargins(0, 0, 0, 0)
        self.hideButtons()
        self.setAcceptDrops(False)

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
        self.length = len(x)
        self.ticks(self.length,kernel)
        self.setXRange(0,len(x),padding=0)
        self.plot(x)

    def mousePressEvent(self, ev):
        self.mouse_press_callback(ev.position().x())

    def mouseDoubleClickEvent(self,ev):
        mouse_position = ev.position().x()
        print(mouse_position)
        # self.setXRange()

    def ticks(self, length, kernel):
        ax = self.getAxis('bottom')
        audio, sr = librosa.load(input, mono=True, sr=None)
        seg_values = json_handling.plot_segmentation(path,sr,kernel)
        array = [(int(x), '') for x in seg_values]
        ax.setTicks([array])
    
    def reset(self):
        self.setXRange(0,self.length,padding=0)
    
class  SequenceView(QWidget):
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
        self.dance_length = 0.0
                
    def dragEnterEvent(self, ev) -> None:
        if isinstance(ev.mimeData().parent(), Library):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        data = ev.mimeData()
        instructions = np.frombuffer(data.data("application/octet-stream")).reshape(-1, 4).tolist()
        danceblock = DanceBlock(name=data.text(), instructions=InstructionSet(instructions), color=data.colorData())     
        self.dance_length += danceblock.display_width
        if self.dance_length < self.width():
            self.sequence.append(danceblock)
            self.populate_layout()
            
        else:
            self.dance_length -= danceblock.display_width
            dlg = QMessageBox()
            dlg.setText('Gesture is too long for this section. :/')
            dlg.exec()
        
    def populate_layout(self):
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        for d in self.sequence:
            new_gesture = Gesture(d, delete_callback=self.delete_callback)
            self.layout().addWidget(new_gesture)  
        
    def delete_callback(self, ev, danceblock_ref: DanceBlock):
        self.dance_length -= danceblock_ref.display_width
        self.sequence.remove(danceblock_ref)
        self.populate_layout()

    def reload_dances(self):
        self.populate_layout()

class SequenceLayout(QWidget): # handles the layout of multiple SequenceViews in 1 widget
    def __init__(self):
        super().__init__()
        self.width = 700
        segmentation_closest_beats,self.indexes = json_handling.segmentation_beats(path)
        widths_array_beats = []
        for i in np.arange(1,len(self.indexes)):
            widths_array_beats = np.append(widths_array_beats,self.indexes[i]-self.indexes[i-1])

        sequence_layout = QHBoxLayout() 
        sequence_layout.setContentsMargins(0, 0, 0, 0)
        sequence_layout.setSpacing(0)
        positions, widths = self.find_seq_positions()
        self.sequence_array = []
        for i in positions:
           self.sequence_array = np.append(self.sequence_array, SequenceView())
        for i in np.arange(len(self.sequence_array)):
            self.sequence_array[i].setFixedWidth(int(widths[i]))
            sequence_layout.addWidget(self.sequence_array[i],1)
            self.sequence_array[i].move(positions[i],0)
            self.sequence_array[i].setToolTip(f'{widths_array_beats[i]} beats')

            testwidget = QWidget(parent=self)
            testwidget.setFixedWidth(1)
            testwidget.setStyleSheet("background-color: black")
            sequence_layout.addWidget(testwidget)
            testwidget.move(positions[i],0)

        self.setLayout(sequence_layout)

    def find_seq_positions(self):
        audio, sr = librosa.load(input, mono=True, sr=None)
        segments = [int(i * sr) for i in json_handling.segmentation(path)]
        audio_length = len(audio)
        percentages = np.asarray(segments)/audio_length
        positions = [int(j * self.width) for j in percentages[0:len(percentages)-1]]
        widths = []
        for i in np.arange(1,len(positions)):
            widths = np.append(widths,positions[i]-positions[i-1])
        widths = np.append(widths,self.width-positions[len(positions)-1])
        return positions, widths

    def save_dances(self):
        str = 'Please enter a name for the dance you have just created (Example: groovy).'
        text, confirmation = QInputDialog.getText(self, 'Save Dances', str)
        if confirmation:
            gesture_total_lengths = []
            beats_to_add = []
            instruction_objects_list = []            
            for index in np.arange(len(self.sequence_array)):
                beat_to_add = self.indexes[index]
                for j in self.sequence_array[index].sequence.dances:
                    gesture_total_lengths = np.append(gesture_total_lengths,j.length_accurate())
                    instruction_objects_list = np.append(instruction_objects_list,j.instructions)
                    beats_to_add = np.append(beats_to_add, self.indexes[index])
            
            length_array = np.arange(len(instruction_objects_list))
            with open("newdances/"f"{text}"".csv",'w',newline='') as csvfile:
                writer_object = csv.writer(csvfile)
                for i in length_array:
                    instruction_set = instruction_objects_list[i].instructions
                    instructions_iter = np.arange(len(instruction_set))
                    for j in instructions_iter:
                        length_to_add = sum(gesture_total_lengths[0:i]) + beats_to_add[i]
                        instruction_array = instruction_set[j]
                        instruction_array[1] = instruction_set[j][1] + length_to_add
                        writer_object.writerow(instruction_array)

    def delete_all_dances(self):
        for sequence_view in self.sequence_array:
            for each_dance in sequence_view.sequence.dances:
                sequence_view.dance_length = 0.0
                sequence_view.sequence.remove(each_dance)
                sequence_view.populate_layout()        

class TextEdit(QDialog):
    def __init__(self, name, parent, content: InstructionSet = None, callback=None):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.resize(500, 300)
        self.new_gesture = content is None
        self.table_view = QTableView(self)
        if content is None:
            content = InstructionSet([[0.0, 0.0, 0.0, 20.0]])
        self.table_view.setModel(content)

        self.callback = callback

        # newrow_btn = QPushButton(text = "New Row")
        # newrow_btn.clicked.connect(self.newrow)

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
        # layout.addWidget(newrow_btn)
        btn_layout = QHBoxLayout()

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)

    def newrow(self): # unused function
        content.instructions.append([[0.0, 0.0, 0.0, 20.0]])

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
        self.setFixedHeight(40)
        self.setAlignment(Qt.AlignmentFlag.AlignLeading)
        self.setStyleSheet(f"background-color: {danceblock.color}")
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setToolTip(f'{self.text()} ' f'({self.danceblock.length_accurate()} beats)')

        self.delete_callback = delete_callback
        
        self.setFixedWidth(self.danceblock.display_width)  

    def mouseDoubleClickEvent(self, ev: typing.Optional[QtGui.QMouseEvent]):
        self.launch_popup(self.text())
    
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

    def launch_popup(self, name):
        pop = TextEdit(name, self, content=self.danceblock.instructions, callback=self.text_callback)
        pop.show()

    def text_callback(self, name, instruction: InstructionSet):
        # self.danceblock.update(self.parse_content(text))
        self.danceblock.update(instruction)
        self.setFixedWidth(self.width_finder(700))

    @staticmethod
    def parse_content(text: str):
        text = text.splitlines(keepends=False)
        out = np.zeros((len(text), 4), dtype=int)
        for i, t in enumerate(text):
            val = t.split(sep=',')
            out[i] = np.array([int(val[0]), int(val[1]), int(val[2]), int(val[3])])
        return out
        
    def contextMenuEvent(self, ev) -> None: # delete menu when right click
        self.menu = QMenu(self)
        delete_action = QtGui.QAction('Delete', self)
        delete_action.triggered.connect(lambda: self.delete_callback(ev, self.danceblock))
        self.menu.addAction(delete_action)
        self.menu.popup(QtGui.QCursor.pos())


class Library(QWidget):
    new_gesture_signal = pyqtSignal(DanceBlock)
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

        self.new_gesture_btn = QPushButton(text="New Gesture")
        self.new_gesture_btn.clicked.connect(lambda: self.launch_popup())
        layout.addWidget(self.new_gesture_btn, 0)

        self.dances_layout = QVBoxLayout()
        self.dances_layout.setContentsMargins(0, 0, 0, 0)
        self.dances_layout.setSpacing(0)
        layout.addLayout(self.dances_layout)

        self.populate_dances()

    @staticmethod
    def load_danceblock(dances_csv_path):
        dances = {}
        for f in glob.glob(os.path.join(dances_csv_path, "*.csv")):
            instructions = np.loadtxt(fname=f, delimiter=',').reshape(-1, 4).tolist()
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

    def launch_popup(self, name="Untitled"):
        pop = TextEdit(name, self, content=None, callback=self.text_callback)
        pop.show()

    def text_callback(self, name, instruction: InstructionSet):
        d = DanceBlock(name, instruction)
        self.new_gesture_signal.emit(d)
      

# Canvas = WaveformView + SequenceView + TransportBar

class Canvas(QWidget):
    def __init__(self,complete_csv_path):
        super().__init__()
        self.complete_csv_path = complete_csv_path
        audio, sr = librosa.load(input, mono=True, sr=None)
        tempo = json_handling.tempo(path)
        self.waveform_view = WaveformView(mouse_press_callback=self.mouse_callback)
        self.waveform_view.render(audio, kernel=127)
        waveform_scroll = QScrollArea()
        waveform_scroll.setWidgetResizable(True)
        waveform_scroll.setWidget(self.waveform_view)

        self.transport = TransportBar()
        self.transport.set_audio(audio, sr)
        self.transport.set_tempo(tempo)
        self.total_time = len(audio) / sr

        self.sequence_layout = SequenceLayout()

        self.reset_btn = QPushButton(text="Reset Waveform View") 
        self.reset_btn.clicked.connect(self.waveform_view.reset)
  
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(waveform_scroll, 1, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.reset_btn,0)
        layout.addWidget(self.sequence_layout,1)
        layout.addWidget(self.transport, 0, Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)

        self.transport.position_signal.connect(self.position_callback)
        self.playhead = QWidget(parent=self)
        self.playhead.setFixedWidth(1)
        self.playhead.setFixedHeight(self.height() - self.transport.height())
        self.playhead.setStyleSheet("background-color: white")

    def position_callback(self, position):
        self.playhead.move(int(self.width() * position / self.total_time), 0)
    
    def mouse_callback(self, position):
        audio, sr = librosa.load(input, mono=True, sr=None)
        song_length = len(audio)/sr
        position = json_handling.mouse_quantizetobeats(path, position, song_length, self.width())
        self.playhead.move(int(position), 0)
        self.transport.seek(position / self.width())

    def resizeEvent(self, a0):
        self.playhead.setFixedHeight(self.height() - self.transport.height())
        QWidget.resizeEvent(self, a0)

    