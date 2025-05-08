# main.py
"""
Main file that controls GUI
"""
import os
import sys

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from algorithms.deflate import Deflate
from algorithms.huffman_coding import HuffmanTree
from algorithms.LZ77 import LZ77
from algorithms.LZ78 import LZ78Compressor
from algorithms.LZW import LZWCompressor
from algorithms.RLE import RLECompressor


class MainWindow(QMainWindow):
    """
    class controls main window
    """

    def __init__(self):
        super().__init__()
        self.setFixedSize(QSize(800, 750))
        self.setWindowTitle("Compression Data Application")

        self.central_widget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(40, 30, 40, 30)
        self.central_widget.setStyleSheet(
            """
            background-color: #E8EEF2;
            """
        )

        self.name = QLabel("Data compressor")
        self.name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name.setStyleSheet(
            """
            font-size: 35px;
            color: #0E103D;
            font-weight: 700;
        """
        )
        self.layout.addWidget(self.name)

        self.caption = QLabel("Choose file for compression:")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setStyleSheet(
            """
            font-size: 25px;
            color: black;"
            font-weight: 600;
            """
        )
        self.layout.addWidget(self.caption)

        self.pick_button = QPushButton("Pick a file")
        self.pick_button.setStyleSheet(
            """
            font-size: 15px;
            color: white;
            font-weight: 500;
            background-color: #0E103D;
            border-radius: 10px;
            """
        )
        self.pick_button.setFixedSize(QSize(400, 60))
        self.pick_button.clicked.connect(self.pick_file)

        pick_button_layout = QHBoxLayout()
        pick_button_layout.addStretch()
        pick_button_layout.addWidget(self.pick_button)
        pick_button_layout.addStretch()
        self.layout.addLayout(pick_button_layout)

        self.selected_file = None
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(
            """
            font-size: 15px;
            color: black;
            font-weight: 500;
            """
        )
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_file_size = None
        self.layout.addWidget(self.file_label)

        self.choose_alg = QLabel("Choose algorithm:")
        self.choose_alg.setStyleSheet(
            """
            font-size: 20px;
            color: black;
            font-weight: 600;
            """
        )
        self.layout.addWidget(self.choose_alg)

        self.algorithms_box = QComboBox()
        self.algorithms_box.addItems(
            ["Huffman", "LZW", "Deflate", "LZ77", "LZ78", "RLE"]
        )

        self.algorithms_box.setStyleSheet(
            """
            QComboBox {
                background-color: white;
                padding: 5px 10px;
                font-size: 15px;
                color: black;
                font-weight: 400;
                border-radius: 10px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                background-color: 'white';
                border-radius: 10px;
            }
        """
        )

        self.algorithms_box.setFixedSize(QSize(720, 40))
        self.layout.addWidget(self.algorithms_box)

        self.compress_button = QPushButton("Compress")
        self.compress_button.setStyleSheet(
            """
            font-size: 15px;
            color: white;
            font-weight: 500;
            background-color: #0E103D;
            border-radius: 10px;
            """
        )
        self.compression_done = False
        self.compress_button.setFixedSize(QSize(200, 60))
        self.compress_button.clicked.connect(self.compress_file)

        self.compress_file_size = 0
        self.compressed_size_label = QLabel("")
        self.compressed_size_label.setStyleSheet(
            """
            font-size: 15px;
            color: black;
            font-weight: 500;
            """
        )
        self.compressed_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.compressed_size_label)

        compress_button_layout = QHBoxLayout()
        compress_button_layout.addStretch()
        compress_button_layout.addWidget(self.compress_button)
        compress_button_layout.addStretch()
        self.layout.addLayout(compress_button_layout)

        self.decompress_button = QPushButton("Decompress")
        self.decompress_button.setStyleSheet(
            """
            font-size: 15px;
            color: white;
            font-weight: 500;
            background-color: #3590F3;
            border-radius: 10px;
            """
        )
        self.decompress_button.setFixedSize(QSize(200, 60))
        self.decompress_button.clicked.connect(self.decompress_file)

        decompress_button_layout = QHBoxLayout()
        decompress_button_layout.addStretch()
        decompress_button_layout.addWidget(self.decompress_button)
        decompress_button_layout.addStretch()
        self.layout.addLayout(decompress_button_layout)

        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

    def pick_file(self):
        """
        function handles picking files
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog.exec():
            files = dialog.selectedFiles()
            if len(files) > 1:
                QMessageBox.warning(
                    self,
                    "Too many files",
                    "Choose only one file at a time for compression.",
                )
                return

            self.selected_file = files[0]
            file_ext = os.path.splitext(self.selected_file)[1].lower()
            self.selected_file_size = os.stat(self.selected_file).st_size

            acceptable_extensions = [
                ".jpg",
                ".tif",
                ".png",
                ".gif",
                ".flac",
                ".mp3",
                ".flac",
                ".wav",
                ".mpeg",
                ".txt",
                ".csv",
                ".json",
                ".jpeg",
                ".bmp",
                ".avi",
                ".mp4",
                ".bin",
                ".gif",
            ]
            if file_ext not in acceptable_extensions:
                QMessageBox.warning(
                    self,
                    "Unsupported File Format",
                    f"This file{file_ext} is not supported.",
                )
                return
            self.file_label.setText(f"Selected: {os.path.basename(self.selected_file)}")

    def compress_file(self):
        """
        function handles file compression
        """
        if not self.selected_file:
            QMessageBox.warning(self, "Error", "No file to compress, select it first")
            return

        algorithms_to_call = {
            "Huffman": HuffmanTree(),
            "LZW": LZWCompressor(),
            "LZ78": LZ78Compressor(),
            "LZ77": LZ77(),
            "RLE": RLECompressor(),
            "Deflate": Deflate(),
        }

        algorithm = self.algorithms_box.currentText()
        if algorithm in algorithms_to_call:
            file_to_encode = algorithms_to_call.get(algorithm)
            file_to_encode.compress_file(self.selected_file)

        self.compression_done = True
        self.compress_file_size = os.stat(f"compressed_{algorithm.lower()}.bin").st_size
        self.compressed_size_label.setText(
            f'Original size was: {\
        round(self.selected_file_size / 1024, 2)} KB, now size is: {\
        round(self.compress_file_size/ 1024, 2)} KB'
        )
        QMessageBox.information(self, "Success", f"File was compressed using {algorithm}!")

    def decompress_file(self):
        """
        function handles file decompression
        """
        if not self.compression_done:
            QMessageBox.warning(self, "Error", "You have not compressed it yet!")
            return
        if not self.selected_file:
            QMessageBox.warning(self, "Error", "No file to compress, select it first")
            return

        algorithms_to_call = {
            "Huffman": HuffmanTree(),
            "LZW": LZWCompressor(),
            "LZ78": LZ78Compressor(),
            "LZ77": LZ77(),
            "RLE": RLECompressor(),
            "Deflate": Deflate(),
        }
        algorithm = self.algorithms_box.currentText()

        if algorithm in algorithms_to_call:
            file_to_encode = algorithms_to_call.get(algorithm)
            file_to_encode.decompress_file()

        QMessageBox.information(self, "Success", "File was decompressed!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
