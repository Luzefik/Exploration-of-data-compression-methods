"""
DPCM (Differential Pulse-Code Modulation) compression module.
Supports both image and audio compression.
"""

import numpy as np
from typing import Tuple, Union, List
import wave
import struct

class DPCMImageCompressor:
    """DPCM compression for BMP images"""

    @staticmethod
    def compress_image(image_data: np.ndarray) -> np.ndarray:
        """
        Compress image using DPCM by encoding differences between adjacent pixels.

        Args:
            image_data: Input image as numpy array (height, width, channels)

        Returns:
            Compressed image data as differences
        """
        height, width, channels = image_data.shape
        compressed = np.zeros_like(image_data)

        # First pixel/row remains unchanged
        compressed[0, 0] = image_data[0, 0]

        # Encode differences for first row
        for x in range(1, width):
            compressed[0, x] = image_data[0, x] - image_data[0, x-1]

        # Encode differences for first column
        for y in range(1, height):
            compressed[y, 0] = image_data[y, 0] - image_data[y-1, 0]

        # Encode differences for rest of the image
        for y in range(1, height):
            for x in range(1, width):
                # Use average of left and top pixels as predictor
                predictor = (image_data[y, x-1] + image_data[y-1, x]) // 2
                compressed[y, x] = image_data[y, x] - predictor

        return compressed

    @staticmethod
    def decompress_image(compressed_data: np.ndarray) -> np.ndarray:
        """
        Decompress image from DPCM differences.

        Args:
            compressed_data: Compressed image data as differences

        Returns:
            Decompressed image data
        """
        height, width, channels = compressed_data.shape
        decompressed = np.zeros_like(compressed_data)

        # First pixel remains unchanged
        decompressed[0, 0] = compressed_data[0, 0]

        # Decode first row
        for x in range(1, width):
            decompressed[0, x] = compressed_data[0, x] + decompressed[0, x-1]

        # Decode first column
        for y in range(1, height):
            decompressed[y, 0] = compressed_data[y, 0] + decompressed[y-1, 0]

        # Decode rest of the image
        for y in range(1, height):
            for x in range(1, width):
                predictor = (decompressed[y, x-1] + decompressed[y-1, x]) // 2
                decompressed[y, x] = compressed_data[y, x] + predictor

        return decompressed

class DPCMAudioCompressor:
    """DPCM compression for WAV audio"""

    @staticmethod
    def compress_audio(audio_data: np.ndarray) -> np.ndarray:
        """
        Compress audio using DPCM by encoding differences between adjacent samples.

        Args:
            audio_data: Input audio samples as numpy array

        Returns:
            Compressed audio data as differences
        """
        compressed = np.zeros_like(audio_data)
        compressed[0] = audio_data[0]  # First sample remains unchanged

        # Encode differences for rest of the samples
        for i in range(1, len(audio_data)):
            compressed[i] = audio_data[i] - audio_data[i-1]

        return compressed

    @staticmethod
    def decompress_audio(compressed_data: np.ndarray) -> np.ndarray:
        """
        Decompress audio from DPCM differences.

        Args:
            compressed_data: Compressed audio data as differences

        Returns:
            Decompressed audio data
        """
        decompressed = np.zeros_like(compressed_data)
        decompressed[0] = compressed_data[0]  # First sample remains unchanged

        # Decode rest of the samples
        for i in range(1, len(compressed_data)):
            decompressed[i] = compressed_data[i] + decompressed[i-1]

        return decompressed

def compress_bmp_file(input_path: str, output_path: str) -> None:
    """
    Compress BMP file using DPCM and save the compressed data.

    Args:
        input_path: Path to input BMP file
        output_path: Path to save compressed data
    """
    from PIL import Image
    import numpy as np

    # Read BMP file
    img = Image.open(input_path)
    img_data = np.array(img)

    # Compress using DPCM
    compressed = DPCMImageCompressor.compress_image(img_data)

    # Save compressed data
    np.save(output_path, compressed)

def decompress_bmp_file(input_path: str, output_path: str) -> None:
    """
    Decompress BMP file from DPCM data and save as BMP.

    Args:
        input_path: Path to compressed data file
        output_path: Path to save decompressed BMP
    """
    from PIL import Image
    import numpy as np

    # Load compressed data
    compressed = np.load(input_path)

    # Decompress using DPCM
    decompressed = DPCMImageCompressor.decompress_image(compressed)

    # Convert to image and save
    img = Image.fromarray(decompressed.astype(np.uint8))
    img.save(output_path)

def compress_wav_file(input_path: str, output_path: str) -> None:
    """
    Compress WAV file using DPCM and save the compressed data.

    Args:
        input_path: Path to input WAV file
        output_path: Path to save compressed data
    """
    import wave
    import numpy as np

    # Read WAV file
    with wave.open(input_path, 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        n_frames = wav_file.getnframes()
        frames = wav_file.readframes(n_frames)

    # Convert to numpy array
    audio_data = np.frombuffer(frames, dtype=np.int16)

    # Reshape for stereo
    if n_channels == 2:
        audio_data = audio_data.reshape(-1, 2)

    # Compress using DPCM
    compressed = DPCMAudioCompressor.compress_audio(audio_data)

    # Save compressed data
    np.save(output_path, compressed)

def decompress_wav_file(input_path: str, output_path: str, original_wav_path: str) -> None:
    """
    Decompress WAV file from DPCM data and save as WAV.

    Args:
        input_path: Path to compressed data file
        output_path: Path to save decompressed WAV
        original_wav_path: Path to original WAV file (for metadata)
    """
    import wave
    import numpy as np

    # Load compressed data
    compressed = np.load(input_path)

    # Decompress using DPCM
    decompressed = DPCMAudioCompressor.decompress_audio(compressed)

    # Get original WAV metadata
    with wave.open(original_wav_path, 'rb') as wav_file:
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()

    # Convert to bytes
    if n_channels == 2:
        decompressed = decompressed.reshape(-1)
    audio_bytes = decompressed.astype(np.int16).tobytes()

    # Save as WAV
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(n_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(framerate)
        wav_file.writeframes(audio_bytes)