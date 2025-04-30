"""
This class implements the LZ77 compression algorithm.
It compresses data by finding repeated sequences and encoding them.
"""

from bitarray import bitarray


class LZ77:
    """
    LZ77 compression algorithm implementation.
    This class provides methods to compress and decompress data using the LZ77 algorithm.
    """

    MAX_WINDOW_SIZE = 400

    def __init__(self, window_size=None):
        if window_size is None:
            window_size = self.MAX_WINDOW_SIZE
        self.window_size = min(window_size, self.MAX_WINDOW_SIZE)
        self.lookahead_buffer_size = 15

    def find_match(self, data: bytes, current_position: int) -> tuple[int, int] | None:
        """
        Find the longest match in the search window.
        """
        end_of_buffer = min(current_position + self.lookahead_buffer_size, len(data))

        # If we're at the end of the data, there's no match
        if current_position >= len(data):
            return None

        best_match_distance = 0
        best_match_length = 0

        # Search window starts
        search_start = max(0, current_position - self.window_size)

        # For each possible starting position in the window
        for i in range(search_start, current_position):
            # Current match length
            match_length = 0
            # How far can we match from this position?
            while (
                current_position + match_length < len(data)
                and match_length < self.lookahead_buffer_size
                and data[i + match_length % (current_position - i)]
                == data[current_position + match_length]
            ):
                match_length += 1

            if match_length > best_match_length:
                best_match_length = match_length
                best_match_distance = current_position - i

        if best_match_length >= 3:  # Only encode matches of length 3 or more
            return (best_match_distance, best_match_length)
        return None

    def compress(
        self, input_file: str, output_file: str = None, verbose: bool = False
    ) -> bitarray:
        """
        Compresses the input file using the LZ77 algorithm.
        """
        try:
            with open(input_file, "rb") as fd:
                data = fd.read()
        except UnicodeDecodeError:
            # If it fails as text, read as binary
            with open(input_file, "rb") as fd:
                data = fd.read()

        output_buffer = bitarray(endian="big")
        i = 0

        if verbose:
            print(f"Compressing {input_file} ({len(data)} bytes)")

        while i < len(data):
            max_match = self.find_match(data, i)

            if max_match:
                (distance, length) = max_match
                if verbose:
                    print(
                        f"Match at position {i}: distance={distance}, length={length}"
                    )

                output_buffer.append(True)  # Flag for match

                # Store distance (12 bits) and length (4 bits)
                distance_bits = bitarray(endian="big")
                distance_bits.frombytes(bytes([distance >> 4]))
                output_buffer.extend(distance_bits[-8:])  # Take last 8 bits

                mixed_byte = ((distance & 0xF) << 4) | (length & 0xF)
                mixed_bits = bitarray(endian="big")
                mixed_bits.frombytes(bytes([mixed_byte]))
                output_buffer.extend(mixed_bits[-8:])  # Take last 8 bits

                i += length
            else:
                if verbose:
                    print(f"Literal at position {i}: {data[i]}")

                output_buffer.append(False)  # Flag for literal
                char_bits = bitarray(endian="big")
                char_bits.frombytes(bytes([data[i]]))
                output_buffer.extend(char_bits[-8:])  # Take last 8 bits

                i += 1

        # Ensure byte-alignment by padding
        while len(output_buffer) % 8 != 0:
            output_buffer.append(False)

        if output_file:
            with open(output_file, "wb") as fd:
                output_buffer.tofile(fd)

            if verbose:
                compression_ratio = (len(data) / (len(output_buffer) / 8)) * 100
                print(f"Compressed size: {len(output_buffer) / 8} bytes")
                print(f"Compression ratio: {compression_ratio:.2f}%")

        return output_buffer

    def decompress(self, input_file: str, output_file: str = None) -> bytearray | None:
        """
        Decompresses the input file using the LZ77 algorithm.
        """
        with open(input_file, "rb") as fd:
            data = bitarray(endian="big")
            data.fromfile(fd)

        output_buffer = bytearray()
        i = 0

        while i < len(data):
            if i + 8 >= len(data):  # Check if we have at least 9 bits left
                break

            flag = data[i]
            i += 1

            if not flag:  # Literal
                if i + 8 > len(data):
                    break

                # Extract 8 bits for the character
                char_bits = data[i : i + 8]
                i += 8

                # Convert to byte and append to output
                char_byte = int(char_bits.to01(), 2)
                output_buffer.append(char_byte)
            else:  # Match
                if i + 16 > len(data):
                    break

                # Extract distance (12 bits) and length (4 bits)
                dist_high_bits = data[i : i + 8]
                i += 8
                mixed_bits = data[i : i + 8]
                i += 8

                dist_high = int(dist_high_bits.to01(), 2)
                mixed_byte = int(mixed_bits.to01(), 2)

                distance = (dist_high << 4) | (mixed_byte >> 4)
                length = mixed_byte & 0xF

                # Copy from the already decompressed data
                for j in range(length):
                    if len(output_buffer) - distance >= 0:
                        output_buffer.append(
                            output_buffer[len(output_buffer) - distance]
                        )
                    else:
                        # Handle case where distance points before start of buffer
                        output_buffer.append(0)

        with open(output_file, "wb") as fd:
            fd.write(output_buffer)

        return output_buffer


if __name__ == "__main__":
    lz77 = LZ77()
    lz77.compress("test.txt", "compressed.bin", verbose=True)
    lz77.decompress("compressed.bin", "decompressed.txt")
