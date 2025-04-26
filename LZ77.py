"""
This class implements the LZ77 compression algorithm.
It compresses data by finding repeated sequences and encoding them.
"""

import mmap
from pathlib import Path

from bitarray import bitarray


class LZ77:
    """
    LZ77 compression algorithm implementation.
    This class provides methods to compress and decompress data using the LZ77 algorithm.
    """

    MAX_CHAIN = 64

    def __init__(self, window_size=4096, lookahead_buffer_size=18, hash_bits=16):
        """Initialize the LZ77 compressor with given parameters."""
        self.window_size = window_size
        self.lookahead_buffer_size = lookahead_buffer_size
        self.hsize = 1 << hash_bits
        self.head = [-1] * self.hsize
        self.prev = [-1] * (window_size + 1)

    def compute_hash(self, data: memoryview, pos: int) -> int:
        """Compute a hash value for the data starting at the given position."""
        h = 0
        end = min(len(data), pos + 3)
        for i in range(pos, end):
            h = ((h << 5) ^ data[i]) & (self.hsize - 1)
        return h

    def roll_hash(self, old_hash: int, new_byte: int) -> int:
        """Update the hash value by rolling in a new byte."""
        return ((old_hash << 5) ^ new_byte) & (self.hsize - 1)

    def insert_position(self, data: memoryview, pos: int, cur_hash: int):
        """Insert the current position into the hash table."""
        idx = pos & self.window_size
        self.prev[idx] = self.head[cur_hash]
        self.head[cur_hash] = pos

    def find_match(
        self, data: memoryview, pos: int, cur_hash: int
    ) -> tuple[int, int] | None:
        """Find the longest match for the current position in the sliding window."""
        best_len = 0
        best_dist = 0
        limit = max(0, pos - self.window_size)
        count = 0
        candidate = self.head[cur_hash]
        max_look = min(self.lookahead_buffer_size, len(data) - pos)

        while candidate >= limit and count < self.MAX_CHAIN:
            length = best_len
            for l in range(max_look, best_len, -1):
                if data[candidate : candidate + l] == data[pos : pos + l]:
                    length = l
                    break
            if length > best_len:
                best_len = length
                best_dist = pos - candidate
                if best_len == max_look:
                    break
            candidate = self.prev[candidate & self.window_size]
            count += 1

        if best_len >= 3:
            return best_dist, best_len
        return None

    def compress(self, infile: str, outfile: str = None) -> bitarray:
        """Compress the input file and optionally write the output to a file."""
        with open(infile, "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            data = memoryview(mm)
            n = len(data)

            output = bitarray(endian="big")
            pos = 0
            cur_hash = self.compute_hash(data, pos)

            while pos < n:
                self.insert_position(data, pos, cur_hash)
                match = self.find_match(data, pos, cur_hash)
                if match:
                    dist, length = match
                    output.append(True)
                    output.extend(bitarray(f"{dist:012b}"))
                    output.extend(bitarray(f"{length:04b}"))
                    for i in range(length):
                        if pos + i + 3 < n:
                            cur_hash = self.roll_hash(cur_hash, data[pos + i + 3])
                        self.insert_position(data, pos + i + 1, cur_hash)
                    pos += length
                else:
                    output.append(False)
                    output.extend(bitarray(f"{data[pos]:08b}"))
                    if pos + 3 < n:
                        cur_hash = self.roll_hash(cur_hash, data[pos + 3])
                    pos += 1

            while len(output) % 8:
                output.append(False)

            if outfile:
                with open(outfile, "wb") as out:
                    output.tofile(out)
            return output

    def decompress(self, infile: str, outfile: str = None) -> bytearray:
        """Decompress the input file and optionally write the output to a file."""
        with open(infile, "rb") as f:
            bits = bitarray(endian="big")
            bits.fromfile(f)

        out = bytearray()
        i = 0
        n = len(bits)
        while i + 1 <= n:
            flag = bits[i]
            i += 1
            if not flag:
                byte = int(bits[i : i + 8].to01(), 2)
                i += 8
                out.append(byte)
            else:
                dist = int(bits[i : i + 12].to01(), 2)
                i += 12
                length = int(bits[i : i + 4].to01(), 2)
                i += 4
                for _ in range(length):
                    out.append(out[-dist])
        if outfile:
            Path(outfile).write_bytes(out)
        return out


if __name__ == "__main__":
    lz77 = LZ77()
    lz77.compress("biblija.txt", "biblija.bin")
    lz77.compress("CSB_Pew_Bible_2nd_Printing.txt", "CSB_Pew_Bible_2nd_Printing.bin")
    lz77.compress(
        "ivanychuk-roman-ivanovych-malvy1004.txt",
        "ivanychuk-roman-ivanovych-malvy1004.bin",
    )
    lz77.compress(
        "pidmohylnyy-valerian-petrovych-misto76.txt",
        "after_change_pidmohylnyy-valerian-petrovych-misto76.bin",
    )
