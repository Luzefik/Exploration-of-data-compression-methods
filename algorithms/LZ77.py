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

    MAX_WINDOW_SIZE = 4096  # Maximum size of the search window

    def __init__(self, window_size=None):
        if window_size is None:
            window_size = self.MAX_WINDOW_SIZE
        self.window_size = min(window_size, self.MAX_WINDOW_SIZE)
        self.lookahead_buffer_size = 15

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
                candidate_list = hash_table[hash_key_to_find]

                # Determine the minimum valid candidate position
                min_valid_candidate_pos = current_position - (self.window_size - 1)

                # Create a new list containing only valid candidates
                valid_candidates = [
                    pos for pos in candidate_list if pos >= min_valid_candidate_pos
                ]

                # Update the entry in the hash table
                if not valid_candidates:
                    # If after cleaning the list is empty, delete the key
                    del hash_table[hash_key_to_find]
                else:
                    # Otherwise replace the old list with the cleaned one
                    hash_table[hash_key_to_find] = valid_candidates

                    # Iterate over the cleaned list of valid candidates
                    for candidate_position in valid_candidates:
                        distance = current_position - candidate_position

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
                            best_match_length = match_length
                            best_match_distance = distance
                            # Early exit if maximum length is found
                            if best_match_length == self.lookahead_buffer_size:
                                break

        if best_match_length >= 3:  # Only encode matches of length 3 or more
            return (best_match_distance, best_match_length)
        return None

    def compress_file(
        self,
        input_file: str,
        verbose: bool = False,
        output_file: str = "compressed_lz77.bin",
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
            data = memoryview(
                buf
            )  # Use memoryview instead of copying the entire buffer

        output_buffer = bitarray(endian="big")
        i = 0
        hash_table = {}

        if verbose:
            print(f"Compressing {input_file} ({len(data)} bytes)")

        while i < len(data):
            max_match = self.find_match(data, i, hash_table)

            if max_match:
                (distance, length) = max_match

                if distance > 4095:
                    raise ValueError(
                        f"Distance {distance} exceeds the maximum allowable value (4095)."
                    )

                if verbose:
                    print(
                        f"Match at position {i}: distance={distance}, length={length}"
                    )

                output_buffer.append(True)

                distance_bits = bitarray(endian="big")
                distance_bits.frombytes(bytes([(distance >> 4) & 0xFF]))
                output_buffer.extend(distance_bits[-8:])

                mixed_byte = ((distance & 0xF) << 4) | (length & 0xF)
                mixed_bits = bitarray(endian="big")
                mixed_bits.frombytes(bytes([mixed_byte]))
                output_buffer.extend(mixed_bits[-8:])

                i += length
            else:
                if verbose:
                    print(f"Literal at position {i}: {data[i]}")

                output_buffer.append(False)
                char_bits = bitarray(endian="big")
                char_bits.frombytes(bytes([data[i]]))
                output_buffer.extend(char_bits[-8:])

                i += 1

        while len(output_buffer) % 8 != 0:
            output_buffer.append(False)

        with open(output_file, "wb") as fd:
            fd.write(struct.pack("!B", ext_len))
            fd.write(ext_bytes)
            output_buffer.tofile(fd)

        return output_buffer

    def decompress_file(
        self, input_file: str = "compressed_lz77.bin", output_file: str = None
    ) -> bytearray:
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

            if not flag:
                if i + 8 > len(data):
                    break

                char_bits = data[i : i + 8]
                i += 8

                char_byte = int(char_bits.to01(), 2)
                output_buffer.append(char_byte)
            else:
                if i + 16 > len(data):
                    break

                dist_high_bits = data[i : i + 8]
                i += 8
                mixed_bits = data[i : i + 8]
                i += 8

                dist_high = int(dist_high_bits.to01(), 2)
                mixed_byte = int(mixed_bits.to01(), 2)

                distance = (dist_high << 4) | (mixed_byte >> 4)
                length = mixed_byte & 0xF

                for j in range(length):
                    if len(output_buffer) - distance >= 0:
                        output_buffer.append(
                            output_buffer[len(output_buffer) - distance]
                        )
                    else:
                        output_buffer.append(0)

        if output_file is None:
            base = os.path.splitext(input_file)[0]
            output_file = f"{base}_decompressed.{ext}"

        with open(output_file, "wb") as fd:
            fd.write(output_buffer)

        return output_buffer
