"""
Audio Transformations Module

This module provides functionality for audio data transformations,
including delta encoding/decoding and byte/sample conversions.
"""

import struct
from typing import List, Tuple


class AudioTransforms:
    """Class for audio data transformations"""

    @staticmethod
    def bytes_to_samples(
        data: bytes, bits_per_sample: int, n_channels: int
    ) -> List[int]:
        """
        Convert bytes to audio samples.

        Args:
            data: Raw audio data in bytes
            bits_per_sample: Number of bits per sample
            n_channels: Number of audio channels

        Returns:
            List of audio samples
        """
        samples = []
        bytes_per_sample = bits_per_sample // 8
        total_samples = len(data) // bytes_per_sample

        for i in range(0, total_samples, n_channels):
            for channel in range(n_channels):
                if i + channel < total_samples:
                    start = (i + channel) * bytes_per_sample
                    end = start + bytes_per_sample
                    sample_bytes = data[start:end]
                    if bytes_per_sample == 1:
                        sample = struct.unpack("b", sample_bytes)[0]
                    elif bytes_per_sample == 2:
                        sample = struct.unpack("<h", sample_bytes)[0]
                    elif bytes_per_sample == 4:
                        sample = struct.unpack("<i", sample_bytes)[0]
                    else:
                        raise ValueError(
                            f"Unsupported sample width: {bytes_per_sample} bytes"
                        )
                    samples.append(sample)

        return samples

    @staticmethod
    def samples_to_bytes(
        samples: List[int], bits_per_sample: int, n_channels: int
    ) -> bytes:
        """
        Convert audio samples to bytes.

        Args:
            samples: List of audio samples
            bits_per_sample: Number of bits per sample
            n_channels: Number of audio channels

        Returns:
            Raw audio data in bytes
        """
        bytes_per_sample = bits_per_sample // 8
        result = bytearray()

        for i in range(0, len(samples), n_channels):
            for channel in range(n_channels):
                if i + channel < len(samples):
                    sample = samples[i + channel]
                    if bytes_per_sample == 1:
                        result.extend(struct.pack("b", sample))
                    elif bytes_per_sample == 2:
                        result.extend(struct.pack("<h", sample))
                    elif bytes_per_sample == 4:
                        result.extend(struct.pack("<i", sample))
                    else:
                        raise ValueError(
                            f"Unsupported sample width: {bytes_per_sample} bytes"
                        )

        return bytes(result)

    @staticmethod
    def delta_encode(samples: List[int], bits_per_sample: int) -> Tuple[List[int], int]:
        """
        Apply delta encoding to audio samples.

        Args:
            samples: List of audio samples
            bits_per_sample: Number of bits per sample

        Returns:
            Tuple of (delta values, first sample)
        """
        if not samples:
            return [], 0

        first_sample = samples[0]
        deltas = [0] * len(samples)
        max_delta = (1 << (bits_per_sample - 1)) - 1
        min_delta = -(1 << (bits_per_sample - 1))

        for i in range(1, len(samples)):
            delta = samples[i] - samples[i - 1]
            if delta > max_delta:
                delta = max_delta
            elif delta < min_delta:
                delta = min_delta
            deltas[i] = delta

        return deltas, first_sample

    @staticmethod
    def delta_decode(deltas: List[int], first_sample: int) -> List[int]:
        """
        Apply delta decoding to audio samples.

        Args:
            deltas: List of delta values
            first_sample: First sample value

        Returns:
            List of decoded audio samples
        """
        if not deltas:
            return []

        samples = [first_sample]
        for delta in deltas[1:]:
            samples.append(samples[-1] + delta)

        return samples
