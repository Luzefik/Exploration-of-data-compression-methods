import os

from bitarray import bitarray

from algorithms.deflate_utils.bit_reader import BitReader
from algorithms.deflate_utils.bit_writer import BitWriter
from algorithms.deflate_utils.LZ77_deflate import LZ77


class Deflate:
    def __init__(self, window_size: int | None = None) -> None:
        """
        Initialize the Deflate compression algorithm.

        Args:
            window_size: Optional window size for LZ77 compression
        """
        self.lz77 = LZ77(window_size=window_size)
        # Initialize static Huffman encoding maps
        self._fixed_lit_len_codes = self._get_fixed_lit_len_encoding_map()
        self._fixed_dist_codes = self._get_fixed_dist_encoding_map()

    @staticmethod
    def _get_fixed_lit_len_encoding_map() -> dict[int, tuple[int, int]]:
        """
        Generate canonical Huffman codes for fixed literal/length tree.

        Returns:
            Dictionary mapping symbols to their (code, code_length) tuples
        """
        lengths = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
        full_lengths = {i: length for i, length in enumerate(lengths)}
        full_lengths[256] = 7

        symbols_with_lengths = sorted(
            [(symbol, length) for symbol, length in full_lengths.items() if length > 0],
            key=lambda x: (x[1], x[0]),
        )

        encoding_map = {}
        current_code = 0
        current_length = symbols_with_lengths[0][1] if symbols_with_lengths else 0

        for symbol, length in symbols_with_lengths:
            current_code <<= length - current_length
            encoding_map[symbol] = (current_code, length)
            current_code += 1
            current_length = length

        return encoding_map

    @staticmethod
    def _get_fixed_dist_encoding_map() -> dict[int, tuple[int, int]]:
        """
        Generate canonical Huffman codes for fixed distance tree.

        Returns:
            Dictionary mapping symbols to their (code, code_length) tuples
        """
        lengths = [5] * 32
        full_lengths = {i: length for i, length in enumerate(lengths)}

        symbols_with_lengths = sorted(
            [(symbol, length) for symbol, length in full_lengths.items() if length > 0],
            key=lambda x: (x[1], x[0]),
        )

        encoding_map = {}
        current_code = 0
        current_length = symbols_with_lengths[0][1] if symbols_with_lengths else 0

        for symbol, length in symbols_with_lengths:
            current_code <<= length - current_length
            encoding_map[symbol] = (current_code, length)
            current_code += 1
            current_length = length

        return encoding_map

    def compress_file(
        self,
        input_file: str,
        output_file: str = "compressed_deflate.bin",
        verbose: bool = False,
        bfinal: int = 1,
    ) -> bitarray:
        """
        Compress a file using the DEFLATE algorithm.

        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            verbose: Whether to print debug information
            bfinal: Whether this is the final block

        Returns:
            The compressed data as a bitarray
        """
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + ".bin"

        # Get file extension and encode it
        _, ext = os.path.splitext(input_file)
        ext = ext.lstrip(".")
        ext_bytes = ext.encode("utf-8")
        ext_len = len(ext_bytes)

        symbol_list, length_extra_bits, distance_list, distance_extra_bits = (
            self.lz77.compress(input_file, verbose=verbose, deflate=True)
        )

        debug_tuples = []
        dist_idx = 0
        dist_extra_idx = 0
        for i in range(20):
            if i < len(symbol_list):
                sym = symbol_list[i]
                len_extra = length_extra_bits[i] if i < len(length_extra_bits) else None
                if 257 <= sym <= 285:
                    dist = (
                        distance_list[dist_idx]
                        if dist_idx < len(distance_list)
                        else None
                    )
                    dist_extra = (
                        distance_extra_bits[dist_extra_idx]
                        if dist_extra_idx < len(distance_extra_bits)
                        else None
                    )
                    debug_tuples.append((sym, len_extra, dist, dist_extra))
                    dist_idx += 1
                    dist_extra_idx += 1
                else:
                    debug_tuples.append((sym, len_extra))
            else:
                debug_tuples.append(None)

        if verbose:
            print(f"LZ77+Mapping produced:")
            print(f"  {len(symbol_list)} lit/len symbols")
            print(f"  {len(length_extra_bits)} corresponding length extra bits")
            print(f"  {len(distance_list)} dist symbols")
            print(f"  {len(distance_extra_bits)} corresponding distance extra bits")

        BLOCK_SIZE = 16384
        blocks = []
        current_block = {
            "symbols": [],
            "length_extra": [],
            "distances": [],
            "dist_extra": [],
        }
        dist_list_idx = 0
        dist_extra_idx = 0

        for i in range(len(symbol_list)):
            sym = symbol_list[i]
            len_extra = length_extra_bits[i]

            current_block["symbols"].append(sym)
            current_block["length_extra"].append(len_extra)

            if 257 <= sym <= 285:
                if dist_list_idx < len(distance_list):
                    current_block["distances"].append(distance_list[dist_list_idx])
                    dist_list_idx += 1
                else:
                    raise IndexError(
                        "Mismatch between length codes and distance list length"
                    )

                if dist_extra_idx < len(distance_extra_bits):
                    current_block["dist_extra"].append(
                        distance_extra_bits[dist_extra_idx]
                    )
                    dist_extra_idx += 1
                else:
                    raise IndexError(
                        "Mismatch between length codes and distance extra bits length"
                    )

            if len(current_block["symbols"]) >= BLOCK_SIZE or i == len(symbol_list) - 1:
                current_block["symbols"].append(256)
                current_block["length_extra"].append((0, 0))

                blocks.append(current_block)

                if i < len(symbol_list) - 1:
                    current_block = {
                        "symbols": [],
                        "length_extra": [],
                        "distances": [],
                        "dist_extra": [],
                    }
                else:
                    current_block = None

        writer = BitWriter()

        # Write file extension header
        writer.write_bits_lsb(ext_len, 8)  # Write extension length
        for byte in ext_bytes:
            writer.write_bits_lsb(byte, 8)  # Write extension bytes

        for block_index, block in enumerate(blocks):
            is_final = bfinal == 1 and block_index == len(blocks) - 1

            writer.write_bits_lsb(is_final, 1)
            writer.write_bits_lsb(1, 2)

            dist_iter = iter(block["distances"])
            len_eb_iter = iter(block["length_extra"])
            dist_eb_iter = iter(block["dist_extra"])

            for sym in block["symbols"]:
                if sym not in self._fixed_lit_len_codes:
                    raise ValueError(
                        f"Symbol {sym} not found in FIXED Huffman lit/len tree"
                    )
                bits, length = self._fixed_lit_len_codes[sym]
                writer.write_bits_msb(bits, length)

                eb_cnt, eb_val = next(len_eb_iter)
                if eb_cnt > 0:
                    writer.write_bits_lsb(eb_val, eb_cnt)

                if 257 <= sym <= 285:
                    dcode = next(dist_iter)
                    if dcode not in self._fixed_dist_codes:
                        raise ValueError(
                            f"Distance code {dcode} not found in FIXED Huffman dist tree"
                        )
                    dbits, dlen = self._fixed_dist_codes[dcode]
                    writer.write_bits_msb(dbits, dlen)

                    eb_cnt_d, eb_val_d = next(dist_eb_iter)
                    if eb_cnt_d > 0:
                        writer.write_bits_lsb(eb_val_d, eb_cnt_d)

        writer.flush_to_file(output_file)
        if verbose:
            print(f"Written DEFLATE output (using fixed trees) to {output_file}")

        return writer.get_bitarray()

    def decompress_file(
        self,
        input_file: str = "compressed_deflate.bin",
        output_file: str | None = None,
        verbose: bool = False,
    ) -> bytes:
        """
        Decompress a DEFLATE compressed file.

        Args:
            input_file: Path to the input compressed file
            output_file: Path to the output decompressed file
            verbose: Whether to print debug information

        Returns:
            The decompressed data as bytes
        """
        reader = BitReader(input_file)
        decoded_data = bytearray()

        try:
            ext_len = reader.read_bits_lsb(8)
            ext_bytes = bytearray()
            for _ in range(ext_len):
                ext_bytes.append(reader.read_bits_lsb(8))
            ext = ext_bytes.decode("utf-8")

            if verbose:
                print(f"Read file extension: {ext}")
        except Exception as e:
            raise ValueError(f"Failed to read file extension header: {str(e)}")

        is_final_block = False
        while not is_final_block:
            try:
                bfinal = reader.read_bit()
                is_final_block = bfinal == 1

                btype = reader.read_bits_lsb(2)

                if verbose:
                    print(f"Block: BFINAL={bfinal}, BTYPE={btype}")

                if btype == 0:
                    if verbose:
                        print("Skipping uncompressed block (BTYPE=00)")
                    reader.byte_align()
                    len_bytes = reader.read_bits_lsb(16)
                    nlen_bytes = reader.read_bits_lsb(16)
                    for _ in range(len_bytes):
                        reader.read_bits_lsb(8)
                elif btype == 1:
                    self._decompress_fixed_huffman_block(reader, decoded_data, verbose)
                elif btype == 2:
                    if verbose:
                        print("Skipping dynamic Huffman block (BTYPE=10)")
                    raise ValueError(
                        "Dynamic Huffman blocks (BTYPE=10) are not supported"
                    )
                else:
                    raise ValueError(f"Unknown block type: {btype}")
            except EOFError:
                break

        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + f".{ext}"
        else:
            base, _ = os.path.splitext(output_file)
            output_file = f"{base}.{ext}"

        with open(output_file, "wb") as f:
            f.write(decoded_data)

        if verbose:
            print(f"Decompressed {len(decoded_data)} bytes to file {output_file}")

        return decoded_data

    def _decompress_fixed_huffman_block(
        self, reader: BitReader, output_buffer: bytearray, verbose: bool
    ) -> None:
        """
        Decompress a block using fixed Huffman encoding.

        Args:
            reader: BitReader instance for reading compressed data
            output_buffer: Buffer to store decompressed data
            verbose: Whether to print debug information
        """
        lit_len_tree = self._create_fixed_huffman_lit_len_tree()
        dist_tree = self._create_fixed_huffman_dist_tree()

        self._decode_huffman_data(
            reader, lit_len_tree, dist_tree, output_buffer, verbose
        )

    def _decode_huffman_data(
        self,
        reader: BitReader,
        lit_len_tree: dict,
        dist_tree: dict,
        output_buffer: bytearray,
        verbose: bool,
    ) -> None:
        """
        Decode data using Huffman trees for literals/lengths and distances.

        Args:
            reader: BitReader instance for reading compressed data
            lit_len_tree: Huffman tree for literals and lengths
            dist_tree: Huffman tree for distances
            output_buffer: Buffer to store decompressed data
            verbose: Whether to print debug information
        """
        while True:
            symbol = self._decode_huffman_symbol(reader, lit_len_tree)
            if symbol is None:
                if verbose:
                    print("End of block reached")
                break

            if symbol < 256:
                output_buffer.append(symbol)
                if verbose:
                    print(f"Literal: {symbol} ({chr(symbol)})")
            elif symbol == 256:
                if verbose:
                    print("End of block marker found")
                break
            else:
                length = self._decode_length(reader, symbol)
                if length is None:
                    raise ValueError("Invalid length code")

                distance_code = self._decode_huffman_symbol(reader, dist_tree)
                if distance_code is None:
                    raise ValueError("Missing distance code")

                distance = self._decode_distance(reader, distance_code)
                if distance is None:
                    raise ValueError("Invalid distance code")

                if distance > len(output_buffer):
                    raise ValueError(
                        f"Invalid distance {distance} exceeds buffer size {len(output_buffer)}"
                    )

                if verbose:
                    print(f"Match: length={length}, distance={distance}")

                for i in range(length):
                    if distance > len(output_buffer):
                        raise ValueError(
                            f"Distance {distance} exceeds buffer size {len(output_buffer)}"
                        )
                    output_buffer.append(output_buffer[-distance])

    def _decode_huffman_symbol(self, reader: BitReader, tree: dict) -> int | None:
        """
        Decode a single symbol using a Huffman tree.

        Args:
            reader: BitReader instance for reading compressed data
            tree: Huffman tree for decoding

        Returns:
            Decoded symbol or None if end of data
        """
        code = 0
        code_len = 0
        max_code_len = max(length for length, _ in tree.keys()) if tree else 0

        while code_len <= max_code_len:
            try:
                bit = reader.read_bit()
            except EOFError:
                return None

            code = (code << 1) | bit
            code_len += 1

            if (code_len, code) in tree:
                return tree[(code_len, code)]

            if code_len == max_code_len:
                return None

        return None

    def _decode_length(self, reader: BitReader, length_code: int) -> int | None:
        """
        Decode a match length from a length code.

        Args:
            reader: BitReader instance for reading compressed data
            length_code: The length code to decode

        Returns:
            Decoded length or None if invalid code
        """
        if length_code < 257 or length_code > 285:
            return None

        for code, base_len, extra_bits in LZ77._length_table:
            if code == length_code:
                if extra_bits > 0:
                    extra = reader.read_bits_lsb(extra_bits)
                    return base_len + extra
                return base_len

        return None

    def _decode_distance(self, reader: BitReader, distance_code: int) -> int | None:
        """
        Decode a match distance from a distance code.

        Args:
            reader: BitReader instance for reading compressed data
            distance_code: The distance code to decode

        Returns:
            Decoded distance or None if invalid code
        """
        if distance_code < 0 or distance_code > 29:
            return None

        for code, base_dist, extra_bits in LZ77._distance_table:
            if code == distance_code:
                if extra_bits > 0:
                    try:
                        extra = reader.read_bits_lsb(extra_bits)
                        distance = base_dist + extra
                        if distance > LZ77.MAX_WINDOW_SIZE:
                            raise ValueError(
                                f"Distance {distance} exceeds maximum window size {LZ77.MAX_WINDOW_SIZE}"
                            )
                        return distance
                    except EOFError:
                        return base_dist
                return base_dist

        return None

    def _create_fixed_huffman_lit_len_tree(self) -> dict:
        """
        Create a fixed Huffman tree for literals and lengths.

        Returns:
            Dictionary representing the Huffman tree
        """
        lengths = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
        return self._build_huffman_tree_from_lengths(lengths)

    def _create_fixed_huffman_dist_tree(self) -> dict:
        """
        Create a fixed Huffman tree for distances.

        Returns:
            Dictionary representing the Huffman tree
        """
        lengths = [5] * 32
        return self._build_huffman_tree_from_lengths(lengths)

    def _build_huffman_tree_from_lengths(
        self, lengths: list[int], is_distance_tree: bool = False
    ) -> dict[tuple[int, int], int]:
        """
        Build a Huffman tree from a list of code lengths.

        Args:
            lengths: List of code lengths
            is_distance_tree: Whether this is a distance tree

        Returns:
            Dictionary mapping (length, code) tuples to symbols
        """
        symbols_with_lengths = [
            (length, symbol) for symbol, length in enumerate(lengths) if length > 0
        ]

        if not symbols_with_lengths:
            return {}

        symbols_with_lengths.sort()

        decode_tree = {}
        current_code = 0
        current_length = symbols_with_lengths[0][0]

        for length, symbol in symbols_with_lengths:
            current_code <<= length - current_length
            decode_tree[(length, current_code)] = symbol
            current_code += 1
            current_length = length

        return decode_tree


if __name__ == "__main__":
    deflate = Deflate()
    input_file = (
        "pidmohylnyy-valerian-petrovych-misto76.txt"  # Replace with your input file
    )

    # compressed_data = deflate.compress_file(input_file, verbose=True)

    decompressed_data = deflate.decompress_file("compressed_deflate.bin")
