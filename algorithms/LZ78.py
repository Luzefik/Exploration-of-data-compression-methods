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
        current = b''
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
                current = b''

        if current:
            result.append((dictionary[current], b''))

        return result

    @staticmethod
    def decompress(pairs: list[tuple[int, bytes]]) -> bytes:
        """
        Decompresses a list of (index, byte) pairs using the LZ78 algorithm.
        Returns the reconstructed bytes.
        """
        dictionary = {0: b''}
        result = bytearray()
        dict_size = 1

        for index, byte in pairs:
            entry = dictionary[index] + byte
            result.extend(entry)
            dictionary[dict_size] = entry
            dict_size += 1

        return bytes(result)

    @staticmethod
    def compress_file(input_path: str, output_path: str):
        """
        Reads a file as binary, compresses with LZ78, and writes a binary stream.
        """
        with open(input_path, 'rb') as f:
            data = f.read()

        pairs = LZ78Compressor.compress(data)

        with open(output_path, 'wb') as f:
            for idx, byte in pairs:
                f.write(idx.to_bytes(4, 'big'))
                length = len(byte)
                f.write(length.to_bytes(1, 'big'))
                f.write(byte)

    @staticmethod
    def decompress_file(input_path: str, output_path: str):
        """
        Reads a binary LZ78 stream, decompresses to bytes, and writes to file.
        """
        pairs = []

        with open(input_path, 'rb') as f:
            blob = f.read()

        pos = 0
        n = len(blob)

        while pos < n:
            idx = int.from_bytes(blob[pos:pos+4], 'big')
            pos += 4
            length = blob[pos]
            pos += 1
            byte = blob[pos:pos+length]
            pos += length
            pairs.append((idx, byte))

        data = LZ78Compressor.decompress(pairs)

        with open(output_path, 'wb') as f:
            f.write(data)

if __name__ == '__main__':
    LZ78Compressor.compress_file('./compression/pidmohylnyy-valerian-petrovych-misto76.txt', './compression/compressed_misto_lz78.bin')
    LZ78Compressor.decompress_file('./compression/compressed_misto_lz78.bin', './compression/test1.txt')
    LZ78Compressor.compress_file('./compression/large-file.json', './compression/compressed_json_lz78.bin')
    LZ78Compressor.decompress_file('./compression/compressed_json_lz78.bin', './compression/test2.json')
    LZ78Compressor.compress_file('./compression/customers-100000.csv', './compression/compressed_customers_100000_lz78.bin')
    LZ78Compressor.decompress_file('./compression/compressed_customers_100000_lz78.bin', './compression/test3.csv')
