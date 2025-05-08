"""
WAV Compression Module using Huffman Coding

This module provides functionality to compress and decompress WAV files
using Huffman coding with delta coding preprocessing.
"""

import json
import os
import wave

from algorithms.audio_utils.audio_transforms import AudioTransforms
from algorithms.huffman_coding import HuffmanTree


class WAVCompressor:
    """Class for compressing and decompressing WAV files using Huffman coding"""

    @staticmethod
    def compress_file(
        input_file: str, output_file: str = "compressed_dpcm.bin"
    ) -> None:
        """
        Compress a WAV file using Huffman coding with delta coding.

        Args:
            input_file: Path to the input WAV file
            output_file: Path to save the compressed file
        """
        try:
            # Read the WAV file
            with wave.open(input_file, "rb") as wav_file:
                # Get WAV parameters
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()

                # Read all frames
                frames = wav_file.readframes(n_frames)

            # Convert bytes to samples
            samples = AudioTransforms.bytes_to_samples(
                frames, sample_width * 8, n_channels  # Convert bytes to bits
            )

            # Apply delta encoding
            deltas, first_sample = AudioTransforms.delta_encode(
                samples, sample_width * 8
            )

            # Convert deltas to bytes for Huffman compression
            delta_bytes = AudioTransforms.samples_to_bytes(
                deltas, sample_width * 8, n_channels
            )

            # Create a temporary file for Huffman compression
            temp_file = "temp_delta.bin"
            with open(temp_file, "wb") as f:
                f.write(delta_bytes)

            # Prepare metadata for storage
            metadata = {
                "n_channels": n_channels,
                "sample_width": sample_width,
                "frame_rate": frame_rate,
                "n_frames": n_frames,
                "original_size": len(frames),
                "first_sample": first_sample,
                "use_delta": True,
            }

            # Convert metadata to bytes
            metadata_bytes = json.dumps(metadata).encode("utf-8")

            # First compress the data using Huffman coding
            huffman = HuffmanTree()
            compressed_file = "temp_compressed.bin"
            huffman.compress_file(
                input_f=temp_file,
                output_f=compressed_file,
                output_dict_f="compressed_dpcm.json",
            )

            # Clean up temporary delta file
            os.remove(temp_file)

            # Now combine metadata and compressed data
            with open(output_file, "wb") as f:
                # Write metadata length (4 bytes)
                f.write(len(metadata_bytes).to_bytes(4, "big"))
                # Write metadata
                f.write(metadata_bytes)
                # Write compressed data
                with open(compressed_file, "rb") as cf:
                    f.write(cf.read())

            # Clean up temporary compressed file
            os.remove(compressed_file)

            # Get the final compressed size
            compressed_size = os.path.getsize(output_file)
            dict_size = os.path.getsize("compressed_dpcm.json")
            total_compressed_size = compressed_size + dict_size

            # Check if compression is effective
            if total_compressed_size >= len(frames):
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except OSError:
                        pass
                if os.path.exists("compressed_dpcm.json"):
                    try:
                        os.remove("compressed_dpcm.json")
                    except OSError:
                        pass
                return

        except Exception as e:
            raise Exception(f"Error during compression: {e}")

    @staticmethod
    def decompress_file(
        input_file: str = "compressed_dpcm.bin",
        output_file: str = "decompressed_dpcm.wav",
    ) -> None:
        """
        Decompress a Huffman-compressed WAV file.

        Args:
            input_file: Path to the compressed file
            output_file: Path to save the decompressed WAV file
        """
        try:
            with open(input_file, "rb") as f:
                # Read metadata length
                metadata_len = int.from_bytes(f.read(4), "big")

                # Read metadata
                metadata_bytes = f.read(metadata_len)
                metadata = json.loads(metadata_bytes.decode("utf-8"))

                # Create a temporary file for the compressed data
                compressed_file = "temp_compressed.bin"
                with open(compressed_file, "wb") as cf:
                    # Write the remaining data (compressed audio)
                    cf.write(f.read())

            # Decompress using Huffman coding
            HuffmanTree.decompress_file(
                input_f=compressed_file, input_dict_f="compressed_dpcm.json"
            )

            # Clean up temporary compressed file
            os.remove(compressed_file)

            # The decompressed file will be named "decompressed.bin"
            decompressed_file = "decompressed.bin"

            # Read the decompressed data
            with open(decompressed_file, "rb") as f:
                decompressed_delta_bytes = f.read()

            if metadata.get("use_delta", False):
                # Convert bytes back to delta values
                deltas = AudioTransforms.bytes_to_samples(
                    decompressed_delta_bytes,
                    metadata["sample_width"] * 8,
                    metadata["n_channels"],
                )

                # Apply delta decoding
                samples = AudioTransforms.delta_decode(deltas, metadata["first_sample"])

                # Convert samples back to bytes
                decompressed_data = AudioTransforms.samples_to_bytes(
                    samples,
                    metadata["sample_width"] * 8,
                    metadata["n_channels"],
                )
            else:
                decompressed_data = decompressed_delta_bytes

            # Write WAV file
            with wave.open(output_file, "wb") as wav_file:
                wav_file.setnchannels(metadata["n_channels"])
                wav_file.setsampwidth(metadata["sample_width"])
                wav_file.setframerate(metadata["frame_rate"])
                wav_file.writeframes(decompressed_data)

            # Clean up temporary files
            if os.path.exists(decompressed_file):
                os.remove(decompressed_file)

        except Exception as e:
            raise Exception(f"Error during decompression: {e}")
