"""
Run-Length Encoding (RLE) Compression Module
"""


class RLECompressor:
    """Class for RLE compression and decompression"""

    @staticmethod
    def compress(data: bytes) -> list[tuple[int, bytes]]:
        """
        Compress data using RLE.

        Args:
            data: Input data as bytes

        Returns:
            List of (count, value) tuples
        """
        if not data:
            return []

        result = []
        current_byte = data[0]
        count = 1

        for byte in data[1:]:
            if byte == current_byte and count < 255:
                count += 1
            else:
                result.append((count, bytes([current_byte])))
                current_byte = byte
                count = 1

        # Add the last run
        result.append((count, bytes([current_byte])))

        return result

    @staticmethod
    def decompress(runs: list[tuple[int, bytes]]) -> bytes:
        """
        Decompress RLE data.

        Args:
            runs: List of (count, value) tuples

        Returns:
            Decompressed data as bytes
        """
        result = bytearray()
        for count, byte_val in runs:
            result.extend(byte_val * count)
        return bytes(result)

    @staticmethod
    def compress_file(input_path: str, output_path: str = "compressed_rle.bin"):
        """
        Reads a file as binary, compresses with RLE, and writes a binary stream.
        """
        with open(input_path, "rb") as f:
            data = f.read()
        runs = RLECompressor.compress(data)
        with open(output_path, "wb") as f:
            for count, byte in runs:
                f.write(count.to_bytes(4, "big"))
                f.write(byte)

    @staticmethod
    def decompress_file(
        input_path: str = "compressed_rle.bin", output_path: str = "decompressed_rle"
    ):
        """
        Reads a binary RLE stream, decompresses to bytes, and writes to file.
        """
        runs = []

        with open(input_path, "rb") as f:
            blob = f.read()

        pos = 0
        n = len(blob)

        while pos < n:
            count = int.from_bytes(blob[pos : pos + 4], "big")
            pos += 4
            byte = blob[pos : pos + 1]
            pos += 1
            runs.append((count, byte))

        data = RLECompressor.decompress(runs)

        with open(output_path, "wb") as f:
            f.write(data)
