"""
This class implements the LZ77 compression algorithm.
It compresses data by finding repeated sequences and encoding them.
"""

import mmap
import os
import struct

from bitarray import bitarray


class LZ77:
    """
    LZ77 compression algorithm implementation.
    This class provides methods to compress and decompress data using the LZ77 algorithm.
    """

    MAX_WINDOW_SIZE = 32768  # Maximum size of the search window
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

    def __init__(self, window_size=None):
        if window_size is None:
            window_size = self.MAX_WINDOW_SIZE
        self.window_size = min(window_size, self.MAX_WINDOW_SIZE)
        self.lookahead_buffer_size = 258  # Maximum match length

    def find_match(
        self, data: bytes, current_position: int, hash_table: dict
    ) -> tuple[int, int] | None:
        """
        Find the longest match in the search window using a hash table,
        with integrated cleanup of stale candidate positions.
        """
        end_of_buffer = min(current_position + self.lookahead_buffer_size, len(data))

        # If we're at the end of the data, there's no match
        if current_position >= len(data):
            return None

        best_match_distance = 0
        best_match_length = 0

        # Update hash table with the current substring
        if current_position >= 2:  # Ensure we have at least 3 bytes to hash
            substring = data[current_position - 2 : current_position + 1]
            hash_key_to_add = hash(substring)
            if hash_key_to_add not in hash_table:
                hash_table[hash_key_to_add] = []
            hash_table[hash_key_to_add].append(current_position - 2)

        # Get the current substring to match
        if current_position + 2 < len(data):
            current_substring = data[current_position : current_position + 3]
            hash_key_to_find = hash(current_substring)

            # Check candidate positions from the hash table
            if hash_key_to_find in hash_table:
                # Determine the minimum valid candidate position
                min_valid_candidate_pos = current_position - (self.window_size - 1)
                if min_valid_candidate_pos < 0:
                    min_valid_candidate_pos = 0

                # Get the list of candidates and filter out stale positions
                candidate_list = hash_table[hash_key_to_find]
                valid_candidates = [pos for pos in candidate_list if pos >= min_valid_candidate_pos]

                # Update the hash table entry
                if not valid_candidates:
                    del hash_table[hash_key_to_find]
                else:
                    hash_table[hash_key_to_find] = valid_candidates

                    # Iterate over valid candidates to find the best match
                    for candidate_position in valid_candidates:
                        distance = current_position - candidate_position

                        # Check if distance is valid
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
                            # Early exit if maximum length is found
                            if best_match_length == self.lookahead_buffer_size:
                                break

        if best_match_length >= 3:  # Only encode matches of length 3 or more
            return (best_match_distance, best_match_length)
        return None

    def compress(
        self,
        input_file: str,
        output_file: str = None,
        verbose: bool = False,
        deflate=False,
    ) -> bitarray:
        """
        Compresses the input file using the LZ77 algorithm with hash-based indexing.
        """
        _, ext = os.path.splitext(input_file)
        ext = ext.lstrip(".")  # Remove the dot from the extension
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
                    # Validate distance and length
                    if dist > self.window_size:
                        # If distance is too large, treat as literal
                        byte = data[i]
                        tokens.append(("lit", byte))
                        if verbose:
                            print(f"  Lit   @ {i}: {byte} (distance {dist} too large)")
                        i += 1
                        continue
                    # Only emit match if distance is valid
                    if dist > 0 and dist <= i:
                        tokens.append(("match", dist, length))
                        if verbose:
                            print(f"  Match @ {i}: dist={dist}, len={length}")
                        i += length
                        continue  # skip to next iteration
                    # Otherwise, treat as literal
                byte = data[i]
                tokens.append(("lit", byte))
                if verbose:
                    print(f"  Lit   @ {i}: {byte}")
                i += 1

            print(
                f"Tokenized {len(data)} bytes into {len(tokens)} tokens: {tokens[:20]}"
            )
            if any(t[0] == "match" and t[1] > tokens.index(t) for t in tokens[:20]):
                print(
                    "[DEBUG] WARNING: Early match with distance greater than current position detected!"
                )

            symbol_list = []
            distance_list = []
            length_extra_bits = []  # Новий список для дод. бітів довжин/літералів
            distance_extra_bits = []  # Новий список для дод. бітів відстаней

            for t in tokens:
                if t[0] == "lit":
                    symbol_list.append(t[1])
                    # Літерал не має дод. бітів довжини
                    length_extra_bits.append((0, 0))
                    # І не має відстані/дод. бітів відстані
                else:  # t[0] == "match"
                    dist, length = t[1], t[2]

                    # Мапінг довжини
                    len_code, len_bits, len_val = self.map_length(length)
                    symbol_list.append(len_code)
                    length_extra_bits.append((len_bits, len_val))

                    # Мапінг відстані
                    dist_code, dist_bits, dist_val = self.map_distance(dist)
                    distance_list.append(dist_code)
                    distance_extra_bits.append((dist_bits, dist_val))

            # Додати код кінця блоку
            symbol_list.append(256)
            length_extra_bits.append((0, 0))  # EOB теж не має дод. бітів довжини

            # Повертаємо 4 списки
            return (symbol_list, length_extra_bits, distance_list, distance_extra_bits)

    @staticmethod
    def map_distance(dist: int) -> tuple[int, int, int]:
        """
        Повертає (distance_code, extra_bits_count, extra_bits_value)
        """
        for code, base, bits in reversed(LZ77._distance_table):
            if dist >= base:
                extra = dist - base
                return code, bits, extra
        raise ValueError(f"Distance {dist} out of range (min 1)")

    @staticmethod
    def map_length(length: int) -> tuple[int, int, int]:
        """
        Повертає (length_code, extra_bits_count, extra_bits_value)
        """
        for code, base, bits in reversed(LZ77._length_table):
            if length >= base:
                extra = length - base
                return code, bits, extra
        raise ValueError(f"Length {length} out of range (min 3)")

    def decompress(self, input_file: str, output_file: str = None) -> bytearray:
        """
        Decompresses the input file using the LZ77 algorithm.
        """
        with open(input_file, "rb") as fd:
            header = fd.read(1)
            if not header:
                raise ValueError("File is corrupted or empty")
            ext_len = struct.unpack("!B", header)[0]
            ext = fd.read(ext_len).decode("utf-8")

            data = bitarray(endian="big")
            data.fromfile(fd)

        output_buffer = bytearray()
        i = 0

        while i < len(data):
            if i + 8 >= len(data):
                break

            flag = data[i]
            i += 1

            if not flag:  # Literal
                if i + 8 > len(data):
                    break

                char_bits = data[i : i + 8]
                i += 8

                char_byte = int(char_bits.to01(), 2)
                output_buffer.append(char_byte)
            else:  # Match
                if i + 16 > len(data):
                    break

                dist_high_bits = data[i : i + 8]
                i += 8
                mixed_bits = data[i : i + 8]
                i += 8

                dist_high = int(dist_high_bits.to01(), 2)
                mixed_byte = int(mixed_bits.to01(), 2)

                distance = (dist_high << 4) | (mixed_byte >> 4)
                length = (mixed_byte & 0xF) + 3  # Add minimum match length

                # Validate distance
                if distance == 0 or distance > len(output_buffer):
                    raise ValueError(f"Invalid distance {distance} at position {i}")

                # Copy match
                for j in range(length):
                    if len(output_buffer) - distance >= 0:
                        output_buffer.append(
                            output_buffer[len(output_buffer) - distance]
                        )
                    else:
                        raise ValueError(f"Invalid match reference at position {i}")

        if output_file is None:
            base = os.path.splitext(input_file)[0]
            output_file = f"{base}_decompressed.{ext}"

        with open(output_file, "wb") as fd:
            fd.write(output_buffer)

        return output_buffer
