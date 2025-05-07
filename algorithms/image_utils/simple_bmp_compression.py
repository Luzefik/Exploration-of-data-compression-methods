"""
Simple BMP Compression Module using Pillow

This module provides functionality to compress and decompress BMP files
using Run-Length Encoding (RLE) compression, with Pillow for BMP handling.
"""

import json
import os

from PIL import Image
from RLE import RLECompressor


class SimpleBMPCompressor:
    """Class for compressing and decompressing BMP files using RLE and Pillow"""

    @staticmethod
    def compress_bmp(input_file: str, output_file: str = "compressed_bmp.bin") -> None:
        """
        Compress a BMP file using RLE compression.

        Args:
            input_file: Path to the input BMP file
            output_file: Path to save the compressed file
        """
        try:
            # Read the BMP file using Pillow
            img = Image.open(input_file)
            img_mode = img.mode
            img_size = img.size

            # Convert to RGB if needed (simplifies handling)
            if img_mode != "RGB":
                img = img.convert("RGB")
                img_mode = "RGB"

            # Get pixel data
            pixel_data = img.tobytes()
            bytes_per_row = img_size[0] * 3  # 3 bytes per pixel in RGB mode

            # Compress the pixel data using RLE
            runs = RLECompressor.compress(pixel_data)

            # Calculate compressed size
            rle_data_size = 0
            for count, _ in runs:
                if count <= 127:
                    rle_data_size += 2  # 1 byte count + 1 byte value
                else:
                    rle_data_size += 3  # 2 bytes count + 1 byte value

            # Prepare metadata for storage
            metadata_json = {
                "width": img_size[0],
                "height": img_size[1],
                "mode": img_mode,
                "bytes_per_row": bytes_per_row,
                "original_size": len(pixel_data),
            }

            # Convert metadata to bytes
            metadata_bytes = json.dumps(metadata_json).encode("utf-8")

            # Calculate total compressed size
            compressed_file_size = len(metadata_bytes) + 4 + rle_data_size

            # Check if compression is effective
            if compressed_file_size >= len(pixel_data):
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except OSError:
                        pass
                return

            # Write the compressed file
            with open(output_file, "wb") as f:
                # Write metadata length (4 bytes)
                f.write(len(metadata_bytes).to_bytes(4, "big"))
                # Write metadata
                f.write(metadata_bytes)
                # Write RLE runs using more efficient encoding
                for count, byte_val in runs:
                    if count <= 127:
                        f.write(bytes([count]))
                        f.write(byte_val)
                    else:
                        f.write(bytes([128 | (count >> 8)]))
                        f.write(bytes([count & 0xFF]))
                        f.write(byte_val)

        except Exception as e:
            raise Exception(f"Error during compression: {e}")

    @staticmethod
    def decompress_bmp(
        input_file: str = "compressed_bmp.bin", output_file: str = "decompressed.bmp"
    ) -> None:
        """
        Decompress a compressed BMP file.

        Args:
            input_file: Path to the compressed file
            output_file: Path to save the decompressed BMP file
        """
        try:
            with open(input_file, "rb") as f:
                # Read metadata length
                metadata_len = int.from_bytes(f.read(4), "big")

                # Read metadata
                metadata_bytes = f.read(metadata_len)
                metadata_json = json.loads(metadata_bytes.decode("utf-8"))

                # Read RLE runs
                runs = []
                while True:
                    count_byte = f.read(1)
                    if not count_byte:
                        break

                    count = count_byte[0]
                    if count & 128:  # If high bit is set, read second byte
                        count = ((count & 0x7F) << 8) | f.read(1)[0]

                    byte_val = f.read(1)
                    if not byte_val:
                        break

                    runs.append((count, byte_val))

            # Decompress the pixel data
            decompressed_data = RLECompressor.decompress(runs)

            # Create image from decompressed data
            img = Image.frombytes(
                metadata_json["mode"],
                (metadata_json["width"], metadata_json["height"]),
                decompressed_data,
            )

            # Save as BMP
            img.save(output_file, "BMP")

        except Exception as e:
            raise Exception(f"Error during decompression: {e}")
