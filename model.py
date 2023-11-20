import numpy as np
import random
import uuid
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
import os
import csv
import librosa
import json_handling

# handles all non-display elements

input = 'Closer.wav'
path = 'Closer.json'

class InstructionSet(QAbstractTableModel): # handles the csv for each gesture that contains instructions
    def __init__(self, instructions: list):
        super().__init__()
        self.instructions = instructions
        self.header = ["Motor ID", "Beat #" , "Position (°)", "Length (beats)"]

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{self.instructions[index.row()][index.column()]}"
        if role == Qt.ItemDataRole.EditRole:
            return self.instructions[index.row()][index.column()]

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.instructions)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.instructions[0])

    def tobytes(self):
        return np.array(self.instructions).tobytes()

    def save(self, file_path):
        np.array(self.instructions).tofile(file_path, sep=',')
                
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.header[section]

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            try:
                value = value
            except ValueError:
                return False
            self.instructions[index.row()][index.column()] = value
            return True


class BaseBlock:
    def __init__(self, name) -> None:
        self.name = name
        self.id = uuid.uuid4()


class DanceBlock(BaseBlock):
    def __init__(self, name, instructions: InstructionSet, color=None):
        assert isinstance(instructions, InstructionSet)
        self.instructions = instructions
        color_range = [128, 255]
        self.color = self.rgb_to_hex(random.randrange(*color_range), random.randrange(*color_range),
                                     random.randrange(*color_range)) if color is None else color
        super(DanceBlock, self).__init__(name=name)

        self.tempo = json_handling.tempo(path)
        self.audio, self.sr = librosa.load(input, mono=True, sr=None)
        self.song_length_seconds = len(self.audio) / self.sr
        self.display_width = self.width_finder(700)

    def length(self):
        length_array = []
        last_row_idx = self.instructions.rowCount()
        for i in np.arange(last_row_idx):
            length_array = np.append(length_array, self.instructions.instructions[i][1])
        return int(max(length_array))

    def length_accurate(self):
        lengths_array = []
        last_row_idx = self.instructions.rowCount()
        for i in np.arange(last_row_idx):
            lengths_array = np.append(lengths_array, self.instructions.instructions[i][1]+self.instructions.instructions[i][3])
        return max(lengths_array)

    def width_finder(self,width):
        beats_to_seconds = self.length_accurate() / self.tempo * 60
        percentage = beats_to_seconds/self.song_length_seconds
        final_width = int(percentage*width)
        return(final_width)

    def __len__(self):
        print("length joke")

    def update(self, instructions: InstructionSet):
        self.instructions = instructions

    def save(self, file_path):
        self.instructions.save(os.path.join(file_path, f"{self.name}.csv"))


    @staticmethod
    def rgb_to_hex(r, g, b):
        """Converts an RGB color to a hex color."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))

        self.instructions.save_to_csv(os.path.join(file_path))

    @staticmethod
    def rgb_to_hex(r, g, b):
        """Converts an RGB color to a hex color."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


class Sequence:
    def __init__(self):
        self.dances: list[BaseBlock] = []
                
    def append(self, dance: BaseBlock):
        self.dances.append(dance)
                                    
    def remove(self, dance: BaseBlock):
        new_dances = []
        for d in self.dances:
            if d.id != dance.id:
                new_dances.append(d)
        self.dances = new_dances
        
    def __iter__(self):
        return self.dances.__iter__()
