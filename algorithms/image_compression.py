"""
Image compression using DPCM + Huffman coding for BMP files.
"""

import os
import struct
from typing import Tuple

from algorithms.huffman_coding import HuffmanTree


class BMPCompressor:
    """A class for compressing BMP files using DPCM + Huffman coding."""

    @staticmethod
    def read_bmp_header(file_path: str) -> Tuple[bytes, int, int, int]:
        """
        Read BMP header and return header bytes and image dimensions.

        Args:
            file_path: Path to BMP file

        Returns:
            Tuple of (header_bytes, width, height, bits_per_pixel)
        """
        with open(file_path, 'rb') as f:
            # Read BMP header (54 bytes)
            header = f.read(54)

            # Get image dimensions from header
            width = struct.unpack('<I', header[18:22])[0]
            height = struct.unpack('<I', header[22:26])[0]
            bits_per_pixel = struct.unpack('<H', header[28:30])[0]

            return header, width, height, bits_per_pixel

    @staticmethod
    def dpcm_encode(pixel_data: bytes) -> bytes:
        """
        Apply DPCM encoding to pixel data.

        Args:
            pixel_data: Raw pixel data bytes

        Returns:
            DPCM encoded bytes
        """
        result = bytearray()
        prev_value = 0

        for byte in pixel_data:
            # Calculate difference and handle overflow
            diff = (byte - prev_value) % 256
            result.append(diff)
            prev_value = byte

        return bytes(result)

    @staticmethod
    def dpcm_decode(encoded_data: bytes) -> bytes:
        """
        Decode DPCM encoded data back to original pixel values.

        Args:
            encoded_data: DPCM encoded bytes

        Returns:
            Original pixel data bytes
        """
        result = bytearray()
        prev_value = 0

        for diff in encoded_data:
            # Reconstruct original value
            value = (prev_value + diff) % 256
            result.append(value)
            prev_value = value

        return bytes(result)

    @staticmethod
    def compress_file(input_path: str, output_path: str = "compressed_bmp.bin"):
        """
        Compress a BMP file using DPCM + Huffman coding.

        Args:
            input_path: Path to input BMP file
            output_path: Path to output compressed file
        """
        # Read BMP header and pixel data
        header, width, height, bits_per_pixel = BMPCompressor.read_bmp_header(input_path)

        with open(input_path, 'rb') as f:
            f.seek(54)  # Skip header
            pixel_data = f.read()

        # Apply DPCM encoding
        dpcm_data = BMPCompressor.dpcm_encode(pixel_data)

        # Apply Huffman coding
        huffman = HuffmanTree(dpcm_data)
        huffman.tree()
        huffman.codes_generation()

        # Save compressed data
        compressed_path = huffman.compress_file(
            input_f=input_path,
            output_f=output_path,
            output_dict_f=output_path + ".dict"
        )

        # Save metadata
        metadata = {
            "header": header.hex(),
            "width": width,
            "height": height,
            "bits_per_pixel": bits_per_pixel
        }

        with open(output_path + ".meta", "w") as f:
            for key, value in metadata.items():
                f.write(f"{key}={value}\n")

        return compressed_path

    @staticmethod
    def decompress_file(
        input_path: str = "compressed_bmp.bin",
        output_path: str = "decompressed.bmp"
    ):
        """
        Decompress a compressed BMP file.

        Args:
            input_path: Path to compressed file
            output_path: Path to output decompressed BMP file
        """
        # Read metadata
        metadata = {}
        with open(input_path + ".meta", "r") as f:
            for line in f:
                key, value = line.strip().split("=")
                metadata[key] = value

        # Decompress using Huffman
        HuffmanTree.decompress_file(
            input_f=input_path,
            input_dict_f=input_path + ".dict"
        )

        # Read decompressed data
        with open("decompressed", "rb") as f:
            dpcm_data = f.read()

        # Apply DPCM decoding
        pixel_data = BMPCompressor.dpcm_decode(dpcm_data)

        # Write final BMP file
        with open(output_path, "wb") as f:
            # Write original header
            f.write(bytes.fromhex(metadata["header"]))
            # Write pixel data
            f.write(pixel_data)

        # Clean up temporary files
        os.remove("decompressed")
        os.remove(input_path + ".dict")
        os.remove(input_path + ".meta")