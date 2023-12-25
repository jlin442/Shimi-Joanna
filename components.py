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

class TransportBar(QFrame):
    position_signal = pyqtSignal(float)
    stream_ended_signal = pyqtSignal()

    def __init__(self,json_path):
        super().__init__()
        self.json_path = json_path
        self.input = self.json_path[:-5] + '.wav'

        self.play_btn = QPushButton(text="Play")
        self.play_btn.clicked.connect(self.play_pause)
        self.play_btn.setToolTip('Plays audio through computer.')

        self.send_btn = QPushButton(text="Send")
        self.send_btn.setToolTip('Sends audio and dance data to Shimi.')

        self.file_btn = QPushButton(text = "Open JSON")

        self.time_lbl = QLabel(self.format_seconds(0))
        self.tempo_lbl = QLabel()
        self.beat_lbl = QLabel("Beat: 0")

        self.delete_btn = QPushButton(text="Delete All Gestures")
        self.delete_btn.setToolTip('Deletes ALL gestures in every sequence.')

        layout = QHBoxLayout()
        layout.addWidget(self.play_btn, 0)
        layout.addWidget(self.send_btn,0)
        # layout.addWidget(self.file_btn,0)
        layout.addWidget(self.time_lbl, 1)
        layout.addWidget(self.beat_lbl,1)
        layout.addWidget(self.tempo_lbl, 1)
        layout.addWidget(self.delete_btn,0)
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
        self.currentPosition = int(percentage * len(self.audio))
        self.time_lbl.setText(self.format_seconds(self.currentPosition / self.fs))
        self.beat_define(self.currentPosition)

    def beat_define(self,position):
        self.beat_number = json_handling.beatseek(position, self.json_path, self.fs)
        self.beat_lbl.setText(f"Beat: {self.beat_number}")
       
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
        self.tempo = json_handling.tempo(self.json_path)
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
    def __init__(self, json_path,mouse_press_callback):
        super().__init__()
        self.json_path = json_path
        self.input = self.json_path[:-5] + '.wav'
        self.mouse_press_callback = mouse_press_callback
        self.getPlotItem().hideAxis('left')

        self.setMouseEnabled(x=False, y=False)
        self.setYRange(-1.1, 1, padding=0)
    
        self.setContentsMargins(0, 0, 0, 0)
        self.hideButtons()
        self.setAcceptDrops(False)

        audio, self.sr = librosa.load(self.input, mono=True, sr=None)
        self.bar_height = self.height()/2

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
        self.ticks(kernel)
        self.setXRange(0,len(x),padding=0)
        self.plot(x)

    def mousePressEvent(self, ev):
        self.mouse_press_callback(ev.position().x())

    def mouseDoubleClickEvent(self,ev):
        mouse_position = ev.position().x()

    def mouseHoverEvent(self,ev):
        return ev.position().x()

    def ticks(self, kernel):
        ax = self.getAxis('bottom')
        seg_values = json_handling.plot_segmentation(self.json_path,self.sr,kernel)
        seg_lbls = []
        for i in np.arange(len(seg_values)):
            seg_lbls = np.append(seg_lbls,str(i))
        array = [(seg_values[x], seg_lbls[x]) for x in np.arange(len(seg_values))]
        ax.setTicks([array])
    
    def reset(self):
        self.setXRange(0,self.length,padding=0)
    
class  SequenceView(QWidget):
    valueChanged = pyqtSignal()
    def __init__(self,json_path,length_inbeats):
        super().__init__()
        self.json_path = json_path
        self.input = self.json_path[:-5] + '.wav'
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # seqview_layout.addLayout(layout)
        self.setLayout(layout)
        p = self.palette()
        p.setColor(self.backgroundRole(), 0)

        self.setPalette(p)
        self.setAcceptDrops(True)

        self.sequence = Sequence()

        self.length_inbeats = length_inbeats
        self.dance_length = 0.0
        self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')

        self.tempo = json_handling.tempo(self.json_path)
        self.audio, self.sr = librosa.load(self.input, mono=True, sr=None)
        self.song_length_seconds = len(self.audio) / self.sr
                
    def dragEnterEvent(self, ev) -> None:
        if (isinstance(ev.mimeData().parent(), Library) or isinstance(ev.mimeData().parent(), SequenceView)):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        data = ev.mimeData()
        instructions = np.frombuffer(data.data("application/octet-stream")).reshape(-1, 4).tolist()
        danceblock = DanceBlock(name=data.text(), instructions=InstructionSet(instructions), color=data.colorData())     
        self.dance_length += danceblock.length_accurate()
        self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')
        if self.dance_length <= self.length_inbeats:
            self.sequence.append(danceblock)
            self.populate_layout()            
        else:
            self.dance_length -= danceblock.length_accurate()
            self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')
            dlg = QMessageBox()
            dlg.setText('Gesture is too long for this section. :/' f'\n ({self.length_inbeats - self.dance_length} beats left)')
            dlg.setWindowTitle('Error')
            dlg.exec()
        
    def populate_layout(self):
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        for d in self.sequence:
            new_gesture = Gesture(d, delete_callback=self.delete_callback, duplicate_callback=self.duplicate_callback)
            new_gesture.setFixedWidth(self.width_finder(self.width(),new_gesture.danceblock.length_accurate()))
            self.layout().addWidget(new_gesture)
        
    def delete_callback(self, ev, danceblock_ref: DanceBlock):
        self.dance_length -= danceblock_ref.length_accurate()
        self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')
        self.sequence.remove(danceblock_ref)
        self.populate_layout()

    def duplicate_callback(self, ev, danceblock_ref: DanceBlock):
        duplicate_textbox = QLineEdit()
        # validator = QIntValidator(0,100,self)
        # duplicate_textbox.setValidator(validator)
        duplicate_textbox.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)

        ok_btn = QPushButton(text = 'Ok')
        ok_btn.clicked.connect(self.handle_ok)
        duplicate_textbox.show()
        for i in (np.arange(times)+1):
            self.dance_length += danceblock_ref.length_accurate()
            if self.dance_length <= self.length_inbeats:
                self.sequence.append(danceblock)
                self.populate_layout()            
            else:
                self.dance_length -= danceblock.length_accurate()
                self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')
                dlg = QMessageBox()
                dlg.setText('Gesture is too long for this section. :/')
                dlg.exec()
                self.setToolTip(f'{self.length_inbeats - self.dance_length} beats left')

    def handle_ok(self):
        self.close()

    def reload_dances(self):
        self.populate_layout()

    def width_finder(self,totalwidth,gesturewidth):
        percentage = gesturewidth/self.length_inbeats
        final_width = int(percentage*totalwidth)
        return(final_width)

class SequenceLayout(QWidget): # handles the layout of multiple SequenceViews in 1 widget
    def __init__(self,json_path,sequence_width):
        super().__init__()
        self.json_path = json_path
        self.input = self.json_path[:-5] + '.wav'
        self.width = sequence_width
        segmentation_closest_beats,self.indexes = json_handling.segmentation_beats(self.json_path)
        widths_array_beats = []
        for i in np.arange(1,len(self.indexes)):
            widths_array_beats = np.append(widths_array_beats,self.indexes[i]-self.indexes[i-1])
        self.sequence_layout = QStackedLayout() 
        self.sequence_layout.setContentsMargins(0, 0, 0, 0)
        self.sequence_layout.setSpacing(0)
        positions, widths = self.find_seq_positions()
        self.sequence_array = []
        for i in np.arange(len(positions)):
           self.sequence_array = np.append(self.sequence_array, SequenceView(self.json_path,widths_array_beats[i]))
        for i in np.arange(len(self.sequence_array)):
            self.sequence_layout.addWidget(self.sequence_array[i])
        self.index = 0
        self.setLayout(self.sequence_layout)

    def go_to_start(self):
        self.index = 0
        self.sequence_layout.setCurrentIndex(self.index)

    def next_SequenceView(self):
        self.index = (self.index+1)%len(self.sequence_array)
        self.sequence_layout.setCurrentIndex(self.index)

    def previous_SequenceView(self):
        self.index = (self.index-1)%len(self.sequence_array)
        self.sequence_layout.setCurrentIndex(self.index)

    def find_seq_positions(self):
        audio, sr = librosa.load(self.input, mono=True, sr=None)
        audio_length = len(audio)
        segments = [int(i * sr) for i in json_handling.segmentation(self.json_path)]
        percentages = np.asarray(segments)/audio_length
        positions = [int(j * self.width) for j in percentages[0:len(percentages)-1]]
        widths = []
        for i in np.arange(1,len(positions)):
            widths = np.append(widths,positions[i]-positions[i-1])
        widths = np.append(widths,self.width-positions[len(positions)-1])
        return positions, widths

    def play_dances(self):
        dance_names = []
        start_beats = []
        gesture_lengths = []
        for i in np.arange(len(self.sequence_array)):
            sequence_length = len(self.sequence_array[i].sequence.dances)
            number = 0
            for j in np.arange(sequence_length):
                dance_names = np.append(dance_names,self.sequence_array[i].sequence.dances[j].name.splitlines()[0])
                gesture_lengths = np.append(gesture_lengths,number)
                start_beats = np.append(start_beats,self.indexes[i])
                number += self.sequence_array[i].sequence.dances[j].length_accurate()
        start_beats += gesture_lengths
        final_list = [[dance_names[i], start_beats[i]] for i in np.arange(len(dance_names))]
        # print(final_list)
        return final_list           

    def delete_all_dances(self):
        for sequence_view in self.sequence_array:
            for each_dance in sequence_view.sequence.dances:
                sequence_view.dance_length = 0.0
                sequence_view.sequence.remove(each_dance)
                sequence_view.populate_layout() 
                sequence_view.setToolTip(f'{sequence_view.length_inbeats - sequence_view.dance_length} beats left')

    def delete_segment_dances(self):
        for each_dance in self.sequence_array[self.index].sequence.dances:
                self.sequence_array[self.index].dance_length = 0.0
                self.sequence_array[self.index].sequence.remove(each_dance)
                self.sequence_array[self.index].populate_layout() 
                self.sequence_array[self.index].setToolTip(f'{self.sequence_array[self.index].length_inbeats - self.sequence_array[self.index].dance_length} beats left')

    def contextMenuEvent(self, ev) -> None:
        self.menu = QMenu(self)
        delete_action = QtGui.QAction('Clear Segment', self)
        delete_action.triggered.connect(self.delete_segment_dances)
        self.menu.addAction(delete_action)
        self.menu.popup(QtGui.QCursor.pos())

class TextEdit(QDialog):
    def __init__(self, name, parent, content: InstructionSet = None, callback=None):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.resize(500, 300)
        self.new_gesture = content is None
        self.table_view = QTableView(self)
        if content is None:
            content = InstructionSet([[0.0, 0.0, 0.0, 1.0]])
        self.table_view.setModel(content)

        self.callback = callback

        # newrow_btn = QPushButton(text = "New Row")
        # newrow_btn.clicked.connect(self.newrow)♦

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

    def handle_ok(self, ev):
        self.close()
        if self.callback is not None:
            self.callback(self.name_textbox.text(), self.table_view.model())

    def handle_cancel(self, ev):
        self.close()

class Gesture(QLabel):
    ok_signal = pyqtSignal()
    def __init__(self, danceblock: DanceBlock, delete_callback=None, duplicate_callback = None):
        super().__init__(danceblock.name)
        self.setText(danceblock.name + f'\n({danceblock.length_accurate()} beats)')
        self.danceblock = danceblock
        self.setFixedHeight(40)
        self.setAlignment(Qt.AlignmentFlag.AlignLeading)
        self.setStyleSheet(f"background-color: {danceblock.color}")
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setToolTip(f'{danceblock.name}' + f'\n({danceblock.length_accurate()} beats)')

        self.delete_callback = delete_callback
        self.duplicate_callback = duplicate_callback

    def mouseDoubleClickEvent(self, ev: typing.Optional[QtGui.QMouseEvent]):
        self.launch_popup(self.text())
    
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and (isinstance(self.parent(), Library) or isinstance(self.parent(),SequenceView)):
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.danceblock.name)
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
        new_name = name.splitlines()[0]
        self.setText(new_name + f'\n({self.danceblock.length_accurate()} beats)')
        ok_signal.emit()

    @staticmethod
    def parse_content(text: str):
        text = text.splitlines(keepends=False)
        out = np.zeros((len(text), 4), dtype=int)
        for i, t in enumerate(text):
            val = t.split(sep=',')
            out[i] = np.array([int(val[0]), int(val[1]), int(val[2]), int(val[3])])
        return out
        
    def contextMenuEvent(self, ev) -> None: # delete menu when right click
        if isinstance(self.parent(), Library):
            self.menu = QMenu(self)
            delete_action = QtGui.QAction('Delete', self)
            delete_action.triggered.connect(lambda: self.delete_callback(ev, self.danceblock))
            self.menu.addAction(delete_action)
            self.menu.popup(QtGui.QCursor.pos())
        if isinstance(self.parent(),SequenceView):
            self.menu = QMenu(self)
            delete_action = QtGui.QAction('Delete', self)
            delete_action.triggered.connect(lambda: self.delete_callback(ev, self.danceblock))
            duplicate_action = QtGui.QAction('Duplicate', self)
            duplicate_action.triggered.connect(lambda: self.duplicate_callback(ev, self.danceblock))
            # self.menu.addAction(duplicate_action)
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
        self.reload_gestures_btn = QPushButton(text = 'Reload Gestures')
        self.reload_gestures_btn.clicked.connect(self.reload_dances)
        layout.addWidget(self.new_gesture_btn, 0)
        layout.addWidget(self.reload_gestures_btn,0)       

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
    def __init__(self,json_path):
        super().__init__()
        self.json_path = json_path
        self.input = self.json_path[:-5] + '.wav'
        audio, sr = librosa.load(self.input, mono=True, sr=None)
        tempo = json_handling.tempo(self.json_path)
        self.waveform_view = WaveformView(self.json_path,mouse_press_callback=self.mouse_callback)
        self.waveform_view.render(audio, kernel=127)
        

        self.transport = TransportBar(self.json_path)
        self.transport.set_audio(audio, sr)
        self.transport.set_tempo(tempo)
        self.total_time = len(audio) / sr

        self.sequence_layout = SequenceLayout(self.json_path,self.waveform_view.width())

        # ----------- prev/next segment buttons and segment labels -------------
        self.seg_lbl = QPushButton(text = 'Segment 'f'{self.sequence_layout.index}')
        self.seg_lbl.clicked.connect(self.segment_callback)
        self.seg_lbl.setToolTip('Click to move playhead to start of segment.')
        self.beatlength_lbl = QLabel()
        seq_lengthinbeats = self.sequence_layout.sequence_array[self.sequence_layout.index].length_inbeats
        self.beatlength_lbl.setText('Length (beats): 'f'{seq_lengthinbeats}')
        self.beatlength_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beatlength_lbl.setToolTip('Length of segment in beats.')
        
        start_btn = QPushButton(text = '<<')
        start_btn.setFixedWidth(25)
        start_btn.setToolTip('Jump to Segment 0.')
        start_btn.clicked.connect(self.sequence_layout.go_to_start)
        start_btn.clicked.connect(self.lbl_text)

        previous_btn = QPushButton(text = '<')
        previous_btn.setFixedWidth(25)
        previous_btn.setToolTip('Go to previous segment.')
        previous_btn.clicked.connect(self.sequence_layout.previous_SequenceView)
        previous_btn.clicked.connect(self.lbl_text)

        next_btn = QPushButton(text = '>') 
        next_btn.setFixedWidth(25)
        next_btn.setToolTip('Go to next segment.')
        next_btn.clicked.connect(self.sequence_layout.next_SequenceView)
        next_btn.clicked.connect(self.lbl_text)

        button_layout = QHBoxLayout()
        button_layout.addWidget(start_btn)
        button_layout.addWidget(previous_btn)
        button_layout.addWidget(self.seg_lbl)
        button_layout.addWidget(self.beatlength_lbl)
        button_layout.addWidget(next_btn)
        # --------------
        hover_lbl = QLabel(text='Hover over empty space to see number of beats left in each segment.')
        hover_lbl.setFixedHeight(18)
        hover_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hover_lbl.setStyleSheet("background-color: light gray")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.waveform_view, 1, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.transport, 0) #, Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.sequence_layout,1)
        layout.addLayout(button_layout,0)
        layout.addWidget(hover_lbl,1)
        self.setLayout(layout)

        self.transport.position_signal.connect(self.position_callback)
        self.playhead = QWidget(parent=self)
        self.playhead.setFixedWidth(1)
        self.playhead.setFixedHeight(int(self.waveform_view.height()))
        self.playhead.setStyleSheet("background-color: red")

        previous_btn.clicked.connect(self.segment_callback)
        next_btn.clicked.connect(self.segment_callback)
        start_btn.clicked.connect(self.segment_callback)

        # self.seq_playhead = QWidget(parent=self)
        # self.seq_playhead.setFixedWidth(1)
        # self.seq_playhead.setFixedHeight(int(self.sequence_layout.height()-next_btn.height()))
        # self.seq_playhead.setStyleSheet("background-color: red")

        audio, sr = librosa.load(self.input, mono=True, sr=None)
        self.song_length = len(audio)/sr

    def position_callback(self, position):
        self.playhead.move(int(self.width() * position / self.total_time), 0)

        new_position = json_handling.mouse_quantizetobeats(self.json_path, position, self.song_length, self.width())
        positions = json_handling.segmentation_positions(self.json_path,self.song_length, self.width())
        jump_index = (np.abs(positions - positions[positions < position].max())).argmin()
        self.sequence_layout.index = jump_index
        self.sequence_layout.sequence_layout.setCurrentIndex(self.sequence_layout.index)
        self.lbl_text()
    
    def mouse_callback(self, position):
        new_position = json_handling.mouse_quantizetobeats(self.json_path, position, self.song_length, self.width())
        positions = json_handling.segmentation_positions(self.json_path,self.song_length, self.width())
        jump_index = (np.abs(positions - positions[positions < position].max())).argmin()
        
        self.sequence_layout.index = jump_index
        self.sequence_layout.sequence_layout.setCurrentIndex(self.sequence_layout.index)
        self.lbl_text()
        self.playhead.move(int(new_position), 0)
        self.transport.seek(new_position / self.width())

        subtracted_position = new_position-positions[positions < position].max()
        positions,widths = self.sequence_layout.find_seq_positions()
        percentage = subtracted_position/ widths[jump_index]
        seq_mouse_position = percentage*self.sequence_layout.width
        # self.seq_playhead.move(int(seq_mouse_position),int(self.waveform_view.height()))

    def segment_callback(self):
        positions = json_handling.segmentation_positions(self.json_path,self.song_length, self.width())
        self.playhead.move(int(positions[self.sequence_layout.index]), 0)
        self.transport.seek(positions[self.sequence_layout.index] / self.width())
        # self.seq_playhead.move(0,int(self.waveform_view.height()))

    def resizeEvent(self, a0):
        self.playhead.setFixedHeight(int(self.waveform_view.height()))
        for i in self.sequence_layout.sequence_array:
            i.reload_dances()
        QWidget.resizeEvent(self, a0)

    def lbl_text(self):
        self.seg_lbl.setText('Segment 'f'{self.sequence_layout.index}')
        seq_lengthinbeats = self.sequence_layout.sequence_array[self.sequence_layout.index].length_inbeats
        self.beatlength_lbl.setText('Length(beats): 'f'{seq_lengthinbeats}')
        

    
