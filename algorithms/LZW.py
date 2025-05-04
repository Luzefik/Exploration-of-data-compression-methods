"""
LZW Compression and Decompression
"""


class LZWCompressor:
    """
    A class for LZW compression and decompression.
    """

    @staticmethod
    def compress(data: bytes):
        """LZW compression for bytes."""
        dict_size = 256
        dictionary = {bytes([i]): i for i in range(dict_size)}
        w = b""
        result = []

        for c in data:
            wc = w + bytes([c])
            if wc in dictionary:
                w = wc
            else:
                result.append(dictionary[w])
                dictionary[wc] = dict_size
                dict_size += 1
                w = bytes([c])

        if w:
            result.append(dictionary[w])
        return result

    @staticmethod
    def decompress(compressed_data):
        """LZW decompression for bytes."""
        dict_size = 256
        dictionary = {i: bytes([i]) for i in range(dict_size)}
        result = bytearray()

        w = bytes([compressed_data[0]])
        result += w

        for k in compressed_data[1:]:
            if k in dictionary:
                entry = dictionary[k]
            elif k == dict_size:
                entry = w + w[:1]
            else:
                raise ValueError("Bad compressed k: %s" % k)

            result += entry
            dictionary[dict_size] = w + entry[:1]
            dict_size += 1
            w = entry

        return bytes(result)

    @staticmethod
    def compress_file(input_path, output_path: str = "compressed_lzw.bin"):
        """Compress a file using LZW and save it in binary format."""
        with open(input_path, "rb") as f:
            data = f.read()
        compressed = LZWCompressor.compress(data)
        with open(output_path, "wb") as f:
            for num in compressed:
                f.write(num.to_bytes(4, byteorder="big"))

    @staticmethod
    def decompress_file(
        input_path: str = "compressed_lzw.bin", output_path: str = "decompressed_lzw"
    ):
        """Decompress a binary file using LZW and save it."""
        with open(input_path, "rb") as f:
            compressed = []
            while byte := f.read(4):
                compressed.append(int.from_bytes(byte, byteorder="big"))
        decompressed = LZWCompressor.decompress(compressed)
        with open(output_path, "wb") as f:
            f.write(decompressed)


# Example usage:
# LZWCompressor.compress_file('pidmohylnyy-valerian-petrovych-misto76.docx', 'compressed.bin')
# LZWCompressor.decompress_file('compressed.bin', 'decompressed.docx')
