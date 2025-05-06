"""
Media compression module that integrates DPCM with existing compression algorithms.
Supports BMP images and WAV audio files.
"""

import os
import numpy as np
from typing import Tuple, Optional

from dpcm import (
    DPCMImageCompressor,
    DPCMAudioCompressor,
    compress_bmp_file,
    compress_wav_file,
    decompress_bmp_file,
    decompress_wav_file,
)
from RLE import RLECompressor
from huffman_coding import HuffmanTree
from deflate import Deflate

class MediaCompressor:
    """Class for compressing media files using DPCM + other algorithms"""

    def __init__(self):
        self.huffman = HuffmanTree()
        self.deflate = Deflate()

    def compress_bmp(
        self,
        input_path: str,
        output_path: str,
        method: str = "dpcm+deflate",
        verbose: bool = False
    ) -> None:
        """
        Compress BMP file using DPCM + chosen compression method.

        Args:
            input_path: Path to input BMP file
            output_path: Path to save compressed data
            method: Compression method to use after DPCM ("dpcm+rle", "dpcm+huffman", "dpcm+deflate")
            verbose: Whether to print debug information
        """
        # First apply DPCM
        dpcm_output = f"{output_path}.dpcm.npy"
        compress_bmp_file(input_path, dpcm_output)

        if verbose:
            print(f"DPCM compression completed, saved to {dpcm_output}")

        # Then apply chosen compression method
        if method == "dpcm+rle":
            # Convert numpy array to bytes for RLE
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Apply RLE
            runs = RLECompressor.compress(dpcm_bytes)

            # Save runs
            with open(output_path, "wb") as f:
                for count, byte in runs:
                    f.write(count.to_bytes(4, "big"))
                    f.write(byte)

        elif method == "dpcm+huffman":
            # Convert numpy array to bytes for Huffman
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Apply Huffman
            self.huffman.compress_file(
                input_f=dpcm_output,
                output_f=output_path,
                output_dict_f=f"{output_path}.dict"
            )

        elif method == "dpcm+deflate":
            # Convert numpy array to bytes for Deflate
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Save as temporary file for Deflate
            temp_file = f"{output_path}.temp"
            with open(temp_file, "wb") as f:
                f.write(dpcm_bytes)

            # Apply Deflate
            self.deflate.compress_file(
                input_file=temp_file,
                output_file=output_path,
                verbose=verbose
            )

            # Clean up temporary file
            os.remove(temp_file)

        else:
            raise ValueError(f"Unknown compression method: {method}")

        # Clean up DPCM file
        os.remove(dpcm_output)

    def decompress_bmp(
        self,
        input_path: str,
        output_path: str,
        method: str = "dpcm+deflate",
        verbose: bool = False
    ) -> None:
        """
        Decompress BMP file using chosen method + DPCM.

        Args:
            input_path: Path to compressed data
            output_path: Path to save decompressed BMP
            method: Compression method used ("dpcm+rle", "dpcm+huffman", "dpcm+deflate")
            verbose: Whether to print debug information
        """
        # First decompress using chosen method
        if method == "dpcm+rle":
            # Read runs
            runs = []
            with open(input_path, "rb") as f:
                blob = f.read()

            pos = 0
            n = len(blob)
            while pos < n:
                count = int.from_bytes(blob[pos:pos+4], "big")
                pos += 4
                byte = blob[pos:pos+1]
                pos += 1
                runs.append((count, byte))

            # Decompress RLE
            dpcm_bytes = RLECompressor.decompress(runs)

            # Save as numpy array
            dpcm_output = f"{output_path}.dpcm.npy"
            dpcm_data = np.frombuffer(dpcm_bytes, dtype=np.int16)
            np.save(dpcm_output, dpcm_data)

        elif method == "dpcm+huffman":
            # Decompress Huffman
            dpcm_output = f"{output_path}.dpcm.npy"
            HuffmanTree.decompress_file(
                input_f=input_path,
                input_dict_f=f"{input_path}.dict"
            )

        elif method == "dpcm+deflate":
            # Decompress Deflate
            dpcm_output = f"{output_path}.dpcm.npy"
            self.deflate.decompress_file(
                input_file=input_path,
                output_file=dpcm_output,
                verbose=verbose
            )

        else:
            raise ValueError(f"Unknown compression method: {method}")

        # Then decompress DPCM
        decompress_bmp_file(dpcm_output, output_path)

        # Clean up temporary file
        os.remove(dpcm_output)

    def compress_wav(
        self,
        input_path: str,
        output_path: str,
        method: str = "dpcm+deflate",
        verbose: bool = False
    ) -> None:
        """
        Compress WAV file using DPCM + chosen compression method.

        Args:
            input_path: Path to input WAV file
            output_path: Path to save compressed data
            method: Compression method to use after DPCM ("dpcm+rle", "dpcm+huffman", "dpcm+deflate")
            verbose: Whether to print debug information
        """
        # First apply DPCM
        dpcm_output = f"{output_path}.dpcm.npy"
        compress_wav_file(input_path, dpcm_output)

        if verbose:
            print(f"DPCM compression completed, saved to {dpcm_output}")

        # Then apply chosen compression method
        if method == "dpcm+rle":
            # Convert numpy array to bytes for RLE
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Apply RLE
            runs = RLECompressor.compress(dpcm_bytes)

            # Save runs
            with open(output_path, "wb") as f:
                for count, byte in runs:
                    f.write(count.to_bytes(4, "big"))
                    f.write(byte)

        elif method == "dpcm+huffman":
            # Convert numpy array to bytes for Huffman
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Apply Huffman
            self.huffman.compress_file(
                input_f=dpcm_output,
                output_f=output_path,
                output_dict_f=f"{output_path}.dict"
            )

        elif method == "dpcm+deflate":
            # Convert numpy array to bytes for Deflate
            dpcm_data = np.load(dpcm_output)
            dpcm_bytes = dpcm_data.tobytes()

            # Save as temporary file for Deflate
            temp_file = f"{output_path}.temp"
            with open(temp_file, "wb") as f:
                f.write(dpcm_bytes)

            # Apply Deflate
            self.deflate.compress_file(
                input_file=temp_file,
                output_file=output_path,
                verbose=verbose
            )

            # Clean up temporary file
            os.remove(temp_file)

        else:
            raise ValueError(f"Unknown compression method: {method}")

        # Clean up DPCM file
        os.remove(dpcm_output)

    def decompress_wav(
        self,
        input_path: str,
        output_path: str,
        original_wav_path: str,
        method: str = "dpcm+deflate",
        verbose: bool = False
    ) -> None:
        """
        Decompress WAV file using chosen method + DPCM.

        Args:
            input_path: Path to compressed data
            output_path: Path to save decompressed WAV
            original_wav_path: Path to original WAV file (for metadata)
            method: Compression method used ("dpcm+rle", "dpcm+huffman", "dpcm+deflate")
            verbose: Whether to print debug information
        """
        # First decompress using chosen method
        if method == "dpcm+rle":
            # Read runs
            runs = []
            with open(input_path, "rb") as f:
                blob = f.read()

            pos = 0
            n = len(blob)
            while pos < n:
                count = int.from_bytes(blob[pos:pos+4], "big")
                pos += 4
                byte = blob[pos:pos+1]
                pos += 1
                runs.append((count, byte))

            # Decompress RLE
            dpcm_bytes = RLECompressor.decompress(runs)

            # Save as numpy array
            dpcm_output = f"{output_path}.dpcm.npy"
            dpcm_data = np.frombuffer(dpcm_bytes, dtype=np.int16)
            np.save(dpcm_output, dpcm_data)

        elif method == "dpcm+huffman":
            # Decompress Huffman
            dpcm_output = f"{output_path}.dpcm.npy"
            HuffmanTree.decompress_file(
                input_f=input_path,
                input_dict_f=f"{input_path}.dict"
            )

        elif method == "dpcm+deflate":
            # Decompress Deflate
            dpcm_output = f"{output_path}.dpcm.npy"
            self.deflate.decompress_file(
                input_file=input_path,
                output_file=dpcm_output,
                verbose=verbose
            )

        else:
            raise ValueError(f"Unknown compression method: {method}")

        # Then decompress DPCM
        decompress_wav_file(dpcm_output, output_path, original_wav_path)

        # Clean up temporary file
        os.remove(dpcm_output)

if __name__ == "__main__":
    # Example usage
    compressor = MediaCompressor()
    compressor.compress_bmp("img.bmp", "output.bmp", method="dpcm+deflate", verbose=True)
    compressor.decompress_bmp("output.bmp", "decompressed.bmp", method="dpcm+deflate", verbose=True)

    compressor.compress_wav("Ouch-1.wav", "output.wav", method="dpcm+deflate", verbose=True)
    compressor.decompress_wav("output.wav", "decompressed.wav", "input.wav", method="dpcm+deflate", verbose=True)