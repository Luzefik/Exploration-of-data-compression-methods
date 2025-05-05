"""RLE Compression and Decompression"""


class RLECompressor:
    """A class for RLE compression and decompression on binary data."""

    @staticmethod
    def compress(data: bytes) -> list[tuple[int, bytes]]:
        """
        Compresses bytes using RLE.
        Returns a list of (count, byte) tuples.
        """
        runs = []
        current = data[0]
        count = 1

        for b in data[1:]:
            if b == current:
                count += 1
            else:
                runs.append((count, bytes([current])))
                current = b
                count = 1

        runs.append((count, bytes([current])))

        return runs

    @staticmethod
    def decompress(runs: list[tuple[int, bytes]]) -> bytes:
        """
        Decompresses a list of (count, byte) tuples.
        Returns the reconstructed bytes.
        """
        result = bytearray()

        for count, byte in runs:
            result.extend(byte * count)

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
