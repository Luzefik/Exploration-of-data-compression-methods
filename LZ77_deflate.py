"""
Implementation of the LZ77 compression algorithm with DEFLATE-specific optimizations.
"""

import mmap
import os
import struct
from typing import Dict, List, Optional, Tuple, Union

from bitarray import bitarray


class LZ77:
    """
    LZ77 compression algorithm implementation with DEFLATE-specific optimizations.
    Provides methods for compressing and decompressing data using the LZ77 algorithm.
    """

    MAX_WINDOW_SIZE = 32768
    _length_table = [
        (257, 3, 0),
        (258, 4, 0),
        (259, 5, 0),
        (260, 6, 0),
        (261, 7, 0),
        (262, 8, 0),
        (263, 9, 0),
        (264, 10, 0),
        (265, 11, 1),
        (266, 13, 1),
        (267, 15, 1),
        (268, 17, 1),
        (269, 19, 2),
        (270, 23, 2),
        (271, 27, 2),
        (272, 31, 2),
        (273, 35, 3),
        (274, 43, 3),
        (275, 51, 3),
        (276, 59, 3),
        (277, 67, 4),
        (278, 83, 4),
        (279, 99, 4),
        (280, 115, 4),
        (281, 131, 5),
        (282, 163, 5),
        (283, 195, 5),
        (284, 227, 5),
        (285, 258, 0),
    ]

    _distance_table = [
        (0, 1, 0),
        (1, 2, 0),
        (2, 3, 0),
        (3, 4, 0),
        (4, 5, 1),
        (5, 7, 1),
        (6, 9, 2),
        (7, 13, 2),
        (8, 17, 3),
        (9, 25, 3),
        (10, 33, 4),
        (11, 49, 4),
        (12, 65, 5),
        (13, 97, 5),
        (14, 129, 6),
        (15, 193, 6),
        (16, 257, 7),
        (17, 385, 7),
        (18, 513, 8),
        (19, 769, 8),
        (20, 1025, 9),
        (21, 1537, 9),
        (22, 2049, 10),
        (23, 3073, 10),
        (24, 4097, 11),
        (25, 6145, 11),
        (26, 8193, 12),
        (27, 12289, 12),
        (28, 16385, 13),
        (29, 24577, 13),
    ]

    def __init__(self, window_size: Optional[int] = None) -> None:
        """
        Initialize LZ77 compressor with specified window size.

        Args:
            window_size: Optional window size for the sliding window
        """
        if window_size is None:
            window_size = self.MAX_WINDOW_SIZE
        self.window_size = min(window_size, self.MAX_WINDOW_SIZE)
        self.lookahead_buffer_size = 258

    def find_match(
        self, data: bytes, current_position: int, hash_table: Dict[int, List[int]]
    ) -> Optional[Tuple[int, int]]:
        """
        Find the longest match in the search window using a hash table.

        Args:
            data: Input data to search in
            current_position: Current position in the data
            hash_table: Hash table for quick match lookup

        Returns:
            Tuple of (distance, length) if a match is found, None otherwise
        """
        end_of_buffer = min(current_position + self.lookahead_buffer_size, len(data))

        if current_position >= len(data):
            return None

        best_match_distance = 0
        best_match_length = 0

        if current_position >= 2:
            substring = data[current_position - 2 : current_position + 1]
            hash_key_to_add = hash(substring)
            if hash_key_to_add not in hash_table:
                hash_table[hash_key_to_add] = []
            hash_table[hash_key_to_add].append(current_position - 2)

        if current_position + 2 < len(data):
            current_substring = data[current_position : current_position + 3]
            hash_key_to_find = hash(current_substring)

            if hash_key_to_find in hash_table:
                min_valid_candidate_pos = max(
                    0, current_position - (self.window_size - 1)
                )
                candidate_list = hash_table[hash_key_to_find]
                valid_candidates = [
                    pos for pos in candidate_list if pos >= min_valid_candidate_pos
                ]

                if not valid_candidates:
                    del hash_table[hash_key_to_find]
                else:
                    hash_table[hash_key_to_find] = valid_candidates

                    for candidate_position in valid_candidates:
                        distance = current_position - candidate_position

                        if distance < 1:
                            continue

                        match_length = 0
                        while (
                            current_position + match_length < len(data)
                            and candidate_position + match_length < current_position
                            and match_length < self.lookahead_buffer_size
                            and data[candidate_position + match_length]
                            == data[current_position + match_length]
                        ):
                            match_length += 1

                        if match_length > best_match_length:
                            best_match_distance = distance
                            best_match_length = match_length
                            if best_match_length == self.lookahead_buffer_size:
                                break

        if best_match_length >= 3:
            return (best_match_distance, best_match_length)
        return None

    def compress(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        verbose: bool = False,
        deflate: bool = False,
    ) -> Union[
        bitarray,
        Tuple[List[int], List[Tuple[int, int]], List[int], List[Tuple[int, int]]],
    ]:
        """
        Compress input file using LZ77 algorithm with hash-based indexing.

        Args:
            input_file: Path to input file
            output_file: Optional path to output file
            verbose: Whether to print debug information
            deflate: Whether to output in DEFLATE format

        Returns:
            Either a bitarray (if deflate=False) or a tuple of (symbol_list, length_extra_bits, distance_list, distance_extra_bits)
        """
        _, ext = os.path.splitext(input_file)
        ext = ext.lstrip(".")
        ext_bytes = ext.encode("utf-8")
        ext_len = len(ext_bytes)

        with open(input_file, "r+b") as f:
            buf = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)
            data = buf[:]

        if deflate:
            tokens = []
            hash_table = {}
            i = 0
            if verbose:
                print(f"Tokenizing {input_file} ({len(data)} bytes)")

            while i < len(data):
                match = self.find_match(data, i, hash_table)
                if match:
                    dist, length = match
                    if dist > self.window_size:
                        byte = data[i]
                        tokens.append(("lit", byte))
                        if verbose:
                            print(f"  Lit   @ {i}: {byte} (distance {dist} too large)")
                        i += 1
                        continue
                    if dist > 0 and dist <= i:
                        tokens.append(("match", dist, length))
                        if verbose:
                            print(f"  Match @ {i}: dist={dist}, len={length}")
                        i += length
                        continue
                byte = data[i]
                tokens.append(("lit", byte))
                if verbose:
                    print(f"  Lit   @ {i}: {byte}")
                i += 1

            if verbose:
                print(
                    f"Tokenized {len(data)} bytes into {len(tokens)} tokens: {tokens[:20]}"
                )
                if any(t[0] == "match" and t[1] > tokens.index(t) for t in tokens[:20]):
                    print(
                        "[DEBUG] WARNING: Early match with distance greater than current position detected!"
                    )

            symbol_list = []
            distance_list = []
            length_extra_bits = []
            distance_extra_bits = []

            for t in tokens:
                if t[0] == "lit":
                    symbol_list.append(t[1])
                    length_extra_bits.append((0, 0))
                else:
                    dist, length = t[1], t[2]

                    len_code, len_bits, len_val = self.map_length(length)
                    symbol_list.append(len_code)
                    length_extra_bits.append((len_bits, len_val))

                    dist_code, dist_bits, dist_val = self.map_distance(dist)
                    distance_list.append(dist_code)
                    distance_extra_bits.append((dist_bits, dist_val))

            return symbol_list, length_extra_bits, distance_list, distance_extra_bits

        # Non-DEFLATE compression implementation
        result = bitarray(endian="big")
        result.frombytes(struct.pack(">B", ext_len))
        result.frombytes(ext_bytes)

        # Implementation for non-DEFLATE compression...
        # (Add implementation here if needed)

        return result

    @staticmethod
    def map_distance(dist: int) -> Tuple[int, int, int]:
        """
        Map a distance value to its DEFLATE code and extra bits.

        Args:
            dist: Distance value to map

        Returns:
            Tuple of (code, extra_bits, extra_value)
        """
        for code, base_dist, extra_bits in LZ77._distance_table:
            if dist <= base_dist + (1 << extra_bits) - 1:
                extra_val = dist - base_dist
                return code, extra_bits, extra_val
        return 29, 13, dist - 24577

    @staticmethod
    def map_length(length: int) -> Tuple[int, int, int]:
        """
        Map a length value to its DEFLATE code and extra bits.

        Args:
            length: Length value to map

        Returns:
            Tuple of (code, extra_bits, extra_value)
        """
        for code, base_len, extra_bits in LZ77._length_table:
            if length <= base_len + (1 << extra_bits) - 1:
                extra_val = length - base_len
                return code, extra_bits, extra_val
        return 285, 0, 0
