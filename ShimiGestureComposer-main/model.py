import numpy as np
import random
import uuid
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
import os

class InstructionSet(QAbstractTableModel):
    def __init__(self, instructions: list):
        super().__init__()
        self.instructions = instructions
        self.header = ["Beat", "Motor Id", "Position", "Length"]

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
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
                value = int(value)
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
        # shape: (N, beat, motor_id, rotation, length)
        assert isinstance(instructions, InstructionSet)
        self.instructions = instructions
        color_range = [128, 255]
        self.color = self.rgb_to_hex(random.randrange(*color_range), random.randrange(*color_range),
                                     random.randrange(*color_range)) if color is None else color
        super(DanceBlock, self).__init__(name=name)

    def __len__(self):
        last_row_idx = self.instructions.rowCount() - 1
        last_col_idx = self.instructions.columnCount() - 1
        return self.instructions.instructions[last_row_idx][0] + self.instructions.instructions[last_row_idx][last_col_idx]

    def update(self, instructions: InstructionSet):
        self.instructions = instructions

    def save(self, file_path):
        self.instructions.save(os.path.join(file_path, f"{self.name}.csv"))

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

