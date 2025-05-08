"""LZ78 Compression and Decompression"""

class LZ78Compressor:
    """A class for LZ78 compression and decompression"""

    @staticmethod
    def compress(data: bytes) -> list[tuple[int, bytes]]:
        """
        Compresses bytes using the LZ78 algorithm.
        Returns a list of (index, byte) pairs.
        """
        dictionary = {}
        result = []
        current = b""
        dict_size = 1

        for b in data:
            seq = current + bytes([b])

            if seq in dictionary:
                current = seq
            else:
                index = dictionary.get(current, 0)
                result.append((index, bytes([b])))
                dictionary[seq] = dict_size
                dict_size += 1
                current = b""

        if current:
            result.append((dictionary[current], b""))

        return result

    @staticmethod
    def decompress(pairs: list[tuple[int, bytes]]) -> bytes:
        """
        Decompresses a list of (index, byte) pairs using the LZ78 algorithm.
        Returns the reconstructed bytes.
        """
        dictionary = {0: b""}
        result = bytearray()
        dict_size = 1

        for index, byte in pairs:
            entry = dictionary[index] + byte
            result.extend(entry)
            dictionary[dict_size] = entry
            dict_size += 1

        return bytes(result)

    @staticmethod
    def compress_file(input_path: str, output_path: str = "compressed_lz78.bin"):
        """
        Reads a file as binary, compresses with LZ78, and writes a binary stream.
        """
        with open(input_path, "rb") as f:
            data = f.read()

        ext = input_path.split(".")[-1] if "." in input_path else ""

        with open(output_path, "wb") as f:
            f.write(len(ext).to_bytes(1, "big"))
            f.write(ext.encode())

            for idx, byte in LZ78Compressor.compress(data):
                f.write(idx.to_bytes(4, "big"))
                length = len(byte)
                f.write(length.to_bytes(1, "big"))
                f.write(byte)

    @staticmethod
    def decompress_file(
        input_path: str = "compressed_lz78.bin", output_path: str = None
    ):
        """
        Reads a binary LZ78 stream, decompresses to bytes, and writes to file.
        """
        with open(input_path, "rb") as f:
            blob = f.read()

        pos = 0
        ext_len = blob[pos]
        pos += 1
        ext = blob[pos:pos+ext_len].decode()
        pos += ext_len

        pairs = []
        n = len(blob)

        while pos < n:
            idx = int.from_bytes(blob[pos : pos + 4], "big")
            pos += 4
            length = blob[pos]
            pos += 1
            byte = blob[pos : pos + length]
            pos += length
            pairs.append((idx, byte))

        data = LZ78Compressor.decompress(pairs)

        if output_path is None:
            output_path = f"decompressed_lz78.{ext}"

        with open(output_path, "wb") as f:
            f.write(data)
