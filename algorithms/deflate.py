import os

from bitarray import bitarray

from deflate_utils.bit_reader import BitReader
from deflate_utils.bit_writer import BitWriter
from deflate_utils.LZ77_deflate import LZ77


class Deflate:
    def __init__(self, window_size=None):
        self.lz77 = LZ77(window_size=window_size)
        # Initialize static Huffman encoding maps
        self._fixed_lit_len_codes = self._get_fixed_lit_len_encoding_map()
        self._fixed_dist_codes = self._get_fixed_dist_encoding_map()

    @staticmethod
    def _get_fixed_lit_len_encoding_map() -> dict[int, tuple[int, int]]:
        """
        Generates canonical Huffman codes for fixed literal/length tree.
        Returns dictionary {symbol: (code, code_length)}.
        """
        # Lengths from RFC 1951
        # 0-143: 8 bits
        # 144-255: 9 bits
        # 256-279: 7 bits
        # 280-287: 8 bits
        lengths = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
        # Add EOB symbol 256 with length 7
        full_lengths = {}
        for i, length in enumerate(lengths):
            full_lengths[i] = length
        full_lengths[256] = 7  # EOB symbol

        # Convert lengths to canonical codes
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
        Generates canonical Huffman codes for fixed distance tree.
        Returns dictionary {symbol: (code, code_length)}.
        """
        # All distance codes (0-29) have length 5
        lengths = [5] * 32
        full_lengths = {}
        for i, length in enumerate(lengths):
            full_lengths[i] = length

        # Convert lengths to canonical codes
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
        output_file: str = 'compressed_deflate.deflate',
        verbose: bool = False,
        bfinal: int = 1,
    ) -> bitarray:
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + ".deflate"

        # Get file extension and prepare header
        _, ext = os.path.splitext(input_file)
        ext = ext.lstrip(".")  # Remove the dot from the extension
        ext_bytes = ext.encode("utf-8")
        ext_len = len(ext_bytes)

        # 1) Get lists from LZ77
        symbol_list, length_extra_bits, distance_list, distance_extra_bits = (
            self.lz77.compress(input_file, verbose=verbose, deflate=True)
        )

        # Debug print: show the first 20 tuples after LZ77 mapping
        debug_tuples = []
        dist_idx = 0
        dist_extra_idx = 0
        for i in range(20):
            if i < len(symbol_list):
                sym = symbol_list[i]
                len_extra = length_extra_bits[i] if i < len(length_extra_bits) else None
                if 257 <= sym <= 285:
                    # This is a match, so show distance and distance_extra
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
                    # Literal, only show symbol and length_extra
                    debug_tuples.append((sym, len_extra))
            else:
                debug_tuples.append(None)
        print(f"[DEBUG] First 20 LZ77->DEFLATE tuples: {debug_tuples}")

        if verbose:
            print(f"LZ77+Mapping produced:")
            print(f"  {len(symbol_list)} lit/len symbols")
            print(f"  {len(length_extra_bits)} corresponding length extra bits")
            print(f"  {len(distance_list)} dist symbols")
            print(f"  {len(distance_extra_bits)} corresponding distance extra bits")

        # 2) Split data into blocks
        BLOCK_SIZE = 16384  # Maximum block size
        blocks = []
        current_block = {
            "symbols": [],
            "length_extra": [],
            "distances": [],
            "dist_extra": [],
        }
        # Indexes for tracking distances and extra bits
        dist_list_idx = 0
        dist_extra_idx = 0

        # Process all symbols from LZ77
        for i in range(len(symbol_list)):
            sym = symbol_list[i]
            len_extra = length_extra_bits[i]

            # Add symbol and its length extra bits to current block
            current_block["symbols"].append(sym)
            current_block["length_extra"].append(len_extra)

            # If it's a length code (match), add distance and its extra bits
            if 257 <= sym <= 285:
                # Ensure indices don't exceed list lengths
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

            # Check if block is full or if this is the last symbol
            # Important: condition `i == len(symbol_list) - 1` ensures we process the last symbol
            if len(current_block["symbols"]) >= BLOCK_SIZE or i == len(symbol_list) - 1:
                # >>> Important change: Add EOB (256) to the end of current block <<<
                current_block["symbols"].append(256)  # EOB symbol
                current_block["length_extra"].append((0, 0))  # EOB has no extra bits
                # >>> End of important change <<<

                # Add complete block to blocks list
                blocks.append(current_block)

                # Create new empty block for next symbols
                # (if this wasn't the last input symbol)
                if i < len(symbol_list) - 1:
                    current_block = {
                        "symbols": [],
                        "length_extra": [],
                        "distances": [],
                        "dist_extra": [],
                    }
                else:
                    # If this was the last symbol, no more blocks needed
                    current_block = None

        # 3) Process each block
        writer = BitWriter()

        # Write file extension header
        writer.write_bits_lsb(ext_len, 8)  # Write extension length
        for byte in ext_bytes:
            writer.write_bits_lsb(byte, 8)  # Write extension bytes

        for block_index, block in enumerate(blocks):
            # Determine if this is the final block
            is_final = bfinal == 1 and block_index == len(blocks) - 1

            # Write block header
            writer.write_bits_lsb(is_final, 1)  # BFINAL
            writer.write_bits_lsb(1, 2)  # BTYPE=01 (static)

            # Write block data
            dist_iter = iter(block["distances"])
            len_eb_iter = iter(block["length_extra"])
            dist_eb_iter = iter(block["dist_extra"])

            # Process symbols in block (including added EOB)
            for sym in block["symbols"]:
                # Write Huffman code for symbol/length
                if sym not in self._fixed_lit_len_codes:
                    raise ValueError(
                        f"Symbol {sym} not found in FIXED Huffman lit/len tree"
                    )
                bits, length = self._fixed_lit_len_codes[sym]
                writer.write_bits_msb(bits, length)

                # Write extra bits for length/literal
                eb_cnt, eb_val = next(len_eb_iter)
                if eb_cnt > 0:
                    writer.write_bits_lsb(eb_val, eb_cnt)

                # If it's a length code, write distance
                if 257 <= sym <= 285:
                    dcode = next(dist_iter)
                    if dcode not in self._fixed_dist_codes:
                        raise ValueError(
                            f"Distance code {dcode} not found in FIXED Huffman dist tree"
                        )
                    dbits, dlen = self._fixed_dist_codes[dcode]
                    writer.write_bits_msb(dbits, dlen)

                    # Write distance extra bits
                    eb_cnt_d, eb_val_d = next(dist_eb_iter)
                    if eb_cnt_d > 0:
                        writer.write_bits_lsb(eb_val_d, eb_cnt_d)

        # Write result to file
        writer.flush_to_file(output_file)
        if verbose:
            print(f"Written DEFLATE output (using fixed trees) to {output_file}")

        return writer.get_bitarray()

    def decompress_file(
        self, input_file: 'compressed_deflate.deflate', output_file = None, verbose: bool = False
    ) -> bytes:
        """
        Декомпресує файл у форматі DEFLATE.

        :param input_file: шлях до вхідного .deflate файлу
        :param output_file: шлях до вихідного файлу
        :param verbose: виводити додаткову інформацію
        :return: розпаковані байти
        """
        # if output_file is None:
        #     output_file = os.path.splitext(input_file)[0] + ".decoded"

        reader = BitReader(input_file)
        decoded_data = bytearray()

        # Read file extension header
        try:
            ext_len = reader.read_bits_lsb(8)
            ext_bytes = bytearray()
            for _ in range(ext_len):
                ext_bytes.append(reader.read_bits_lsb(8))
            ext = ext_bytes.decode('utf-8')

            if verbose:
                print(f"Read file extension: {ext}")
        except Exception as e:
            raise ValueError(f"Failed to read file extension header: {str(e)}")

        # Декодування буде відбуватися доки не дійдемо до кінця файлу або до останнього блоку
        is_final_block = False
        while not is_final_block:
            try:
                # Зчитуємо заголовок блоку
                bfinal = reader.read_bit()
                is_final_block = bfinal == 1

                btype = reader.read_bits_lsb(2)

                if verbose:
                    print(f"Block: BFINAL={bfinal}, BTYPE={btype}")

                if btype == 0:
                    # Нестиснутий блок - пропускаємо, оскільки ми не використовуємо їх при стисненні
                    if verbose:
                        print(
                            "Skipping uncompressed block (BTYPE=00) as we don't use them in compression"
                        )
                    reader.byte_align()
                    len_bytes = reader.read_bits_lsb(16)
                    nlen_bytes = reader.read_bits_lsb(16)
                    # Пропускаємо дані блоку
                    for _ in range(len_bytes):
                        reader.read_bits_lsb(8)
                elif btype == 1:
                    # Блок із фіксованим кодуванням Хаффмана
                    self._decompress_fixed_huffman_block(reader, decoded_data, verbose)
                elif btype == 2:
                    # Блок із динамічним кодуванням Хаффмана - пропускаємо, оскільки ми не використовуємо їх
                    if verbose:
                        print(
                            "Skipping dynamic Huffman block (BTYPE=10) as we don't use them in compression"
                        )
                    raise ValueError(
                        "Dynamic Huffman blocks (BTYPE=10) are not supported"
                    )
                else:
                    raise ValueError(f"Невідомий тип блоку: {btype}")
            except EOFError:
                # Якщо досягли кінця файлу, виходимо з циклу
                break

        # Записуємо результат у файл з правильною розширенням
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + f".{ext}"
        else:
            # Ensure output file has correct extension
            base, _ = os.path.splitext(output_file)
            output_file = f"{base}.{ext}"

        with open(output_file, "wb") as f:
            f.write(decoded_data)

        if verbose:
            print(f"Декомпресовано {len(decoded_data)} байтів у файл {output_file}")

        return decoded_data

    def _decompress_fixed_huffman_block(
        self, reader: BitReader, output_buffer: bytearray, verbose: bool
    ):
        """
        Декомпресує блок із фіксованим кодуванням Хаффмана (BTYPE=1).
        """
        # Створюємо фіксовані дерева Хаффмана
        lit_len_tree = self._create_fixed_huffman_lit_len_tree()
        dist_tree = self._create_fixed_huffman_dist_tree()

        # Декодуємо дані
        self._decode_huffman_data(
            reader, lit_len_tree, dist_tree, output_buffer, verbose
        )

    def _decompress_32kb_block(
        self, reader: BitReader, output_buffer: bytearray, verbose: bool
    ):
        """
        Декомпресує блок розміром 32KB з використанням динамічного кодування Хаффмана.
        """
        try:
            # Зчитуємо параметри з заголовка
            hlit = reader.read_bits_lsb(5) + 257
            hdist = reader.read_bits_lsb(5) + 1
            hclen = reader.read_bits_lsb(4) + 4

            # Перевіряємо валідність параметрів
            if hlit > 286 or hdist > 30 or hclen > 19:
                raise ValueError(
                    f"Invalid block parameters: HLIT={hlit}, HDIST={hdist}, HCLEN={hclen}"
                )

            if verbose:
                print(
                    f"32KB Dynamic Huffman block: HLIT={hlit}, HDIST={hdist}, HCLEN={hclen}"
                )

            # Порядок кодів для дерева кодів довжин
            code_length_order = [
                16,
                17,
                18,
                0,
                8,
                7,
                9,
                6,
                10,
                5,
                11,
                4,
                12,
                3,
                13,
                2,
                14,
                1,
                15,
            ]

            # Зчитуємо довжини кодів для дерева кодів довжин
            cl_lengths = [0] * 19
            for i in range(hclen):
                length = reader.read_bits_lsb(3)
                if length > 7:
                    raise ValueError(f"Invalid code length: {length}")
                cl_lengths[code_length_order[i]] = length

            # Будуємо дерево кодів довжин
            cl_tree = self._build_huffman_tree_from_lengths(cl_lengths)
            if not cl_tree:
                raise ValueError("Failed to build code length tree")

            # Зчитуємо довжини кодів для літералів/довжин та відстаней
            code_lengths = []
            i = 0
            while i < hlit + hdist:
                try:
                    code = self._decode_huffman_symbol(reader, cl_tree)

                    if code <= 15:
                        # Звичайна довжина коду
                        code_lengths.append(code)
                        i += 1
                    elif code == 16:
                        # Повторення попереднього коду
                        if not code_lengths:
                            raise ValueError("No previous code to repeat")
                        repeat_count = reader.read_bits_lsb(2) + 3
                        code_lengths.extend([code_lengths[-1]] * repeat_count)
                        i += repeat_count
                    elif code == 17:
                        # Повторення 0 (3-10 разів)
                        repeat_count = reader.read_bits_lsb(3) + 3
                        code_lengths.extend([0] * repeat_count)
                        i += repeat_count
                    elif code == 18:
                        # Повторення 0 (11-138 разів)
                        repeat_count = reader.read_bits_lsb(7) + 11
                        code_lengths.extend([0] * repeat_count)
                        i += repeat_count
                    else:
                        raise ValueError(f"Invalid RLE code: {code}")
                except EOFError:
                    raise ValueError(
                        "Unexpected end of compressed data while reading code lengths"
                    )

            # Розділяємо довжини кодів
            lit_len_lengths = code_lengths[:hlit]
            dist_lengths = code_lengths[hlit : hlit + hdist]

            # Будуємо дерева Хаффмана
            lit_len_tree = self._build_huffman_tree_from_lengths(lit_len_lengths)
            if not lit_len_tree:
                raise ValueError("Failed to build literal/length tree")

            dist_tree = self._build_huffman_tree_from_lengths(
                dist_lengths, is_distance_tree=True
            )
            if not dist_tree:
                raise ValueError("Failed to build distance tree")

            # Декодуємо дані
            self._decode_huffman_data(
                reader, lit_len_tree, dist_tree, output_buffer, verbose
            )

        except Exception as e:
            raise ValueError(f"Error in 32KB dynamic Huffman block: {str(e)}")

    def _decode_huffman_data(
        self,
        reader: BitReader,
        lit_len_tree: dict,
        dist_tree: dict,
        output_buffer: bytearray,
        verbose: bool,
    ):
        """
        Декодує дані з використанням дерев Хаффмана для літералів/довжин та відстаней.
        """
        while True:
            # Декодуємо наступний символ
            symbol = self._decode_huffman_symbol(reader, lit_len_tree)
            if symbol is None:
                if verbose:
                    print("End of block reached")
                break

            if symbol < 256:
                # Літерал - додаємо його до вихідного буфера
                output_buffer.append(symbol)
                if verbose:
                    print(f"Literal: {symbol} ({chr(symbol)})")
            elif symbol == 256:
                # Кінець блоку
                if verbose:
                    print("End of block marker found")
                break
            else:
                # Довжина коду - декодуємо відстань
                length = self._decode_length(reader, symbol)
                if length is None:
                    raise ValueError("Invalid length code")

                distance_code = self._decode_huffman_symbol(reader, dist_tree)
                if distance_code is None:
                    raise ValueError("Missing distance code")

                distance = self._decode_distance(reader, distance_code)
                if distance is None:
                    raise ValueError("Invalid distance code")

                # Перевіряємо, чи відстань не перевищує розмір буфера
                if distance > len(output_buffer):
                    raise ValueError(
                        f"Invalid distance {distance} exceeds buffer size {len(output_buffer)}"
                    )

                if verbose:
                    print(f"Match: length={length}, distance={distance}")

                # Копіюємо дані з попередньої позиції
                for i in range(length):
                    if distance > len(output_buffer):
                        raise ValueError(
                            f"Distance {distance} exceeds buffer size {len(output_buffer)}"
                        )
                    output_buffer.append(output_buffer[-distance])

    def _decode_huffman_symbol(self, reader: BitReader, tree: dict) -> int | None:
        """
        Декодує один символ за допомогою дерева Хаффмана.
        """
        # Зчитуємо біти, поки не знайдемо символ
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

            # Перевіряємо чи код існує для даної довжини
            if (code_len, code) in tree:
                return tree[(code_len, code)]

            # Якщо досягли максимальної довжини і не знайшли код,
            # повертаємо None
            if code_len == max_code_len:
                return None

        return None

    def _decode_length(self, reader: BitReader, length_code: int) -> int | None:
        """
        Декодує довжину збігу за кодом довжини.
        Використовує таблицю _length_table з LZ77.
        """
        if length_code < 257 or length_code > 285:
            return None

        # Знаходимо відповідну довжину в таблиці
        for code, base_len, extra_bits in LZ77._length_table:
            if code == length_code:
                # Додаємо додаткові біти, якщо є
                if extra_bits > 0:
                    extra = reader.read_bits_lsb(extra_bits)
                    return base_len + extra
                return base_len

        return None

    def _decode_distance(self, reader: BitReader, distance_code: int) -> int | None:
        """
        Декодує відстань за кодом відстані.
        Використовує таблицю _distance_table з LZ77.
        """
        if distance_code < 0 or distance_code > 29:
            return None

        # Знаходимо відповідну відстань в таблиці
        for code, base_dist, extra_bits in LZ77._distance_table:
            if code == distance_code:
                # Додаємо додаткові біти, якщо є
                if extra_bits > 0:
                    try:
                        extra = reader.read_bits_lsb(extra_bits)
                        distance = base_dist + extra
                        # Перевіряємо чи відстань не перевищує максимальну
                        if distance > LZ77.MAX_WINDOW_SIZE:
                            raise ValueError(
                                f"Distance {distance} exceeds maximum window size {LZ77.MAX_WINDOW_SIZE}"
                            )
                        return distance
                    except EOFError:
                        # Якщо не вистачає бітів для додаткових бітів,
                        # повертаємо базову відстань
                        return base_dist
                return base_dist

        return None

    def _create_fixed_huffman_lit_len_tree(self) -> dict:
        """
        Створює дерево Хаффмана для літералів/довжин із фіксованими довжинами.
        """
        # Довжини кодів для фіксованого дерева літералів/довжин
        lengths = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8

        # Будуємо дерево з довжин
        return self._build_huffman_tree_from_lengths(lengths)

    def _create_fixed_huffman_dist_tree(self) -> dict:
        """
        Створює дерево Хаффмана для відстаней із фіксованими довжинами.
        """
        # Довжини кодів для фіксованого дерева відстаней
        lengths = [5] * 32

        # Будуємо дерево з довжин
        return self._build_huffman_tree_from_lengths(lengths)

    def _build_huffman_tree_from_lengths(
        self, lengths: list[int], is_distance_tree: bool = False
    ) -> dict[tuple[int, int], int]:
        """
        Будує дерево Хаффмана за списком довжин кодів та повертає словник для декодування.
        Словник має формат {(довжина_коду, значення_коду): символ}.
        """
        # Filter out symbols with code length 0
        symbols_with_lengths = [
            (length, symbol) for symbol, length in enumerate(lengths) if length > 0
        ]

        if not symbols_with_lengths:
            # If no symbols have length > 0, return an empty tree
            # This is valid for distance trees if no matches occur
            return {}

        # Sort by length, then by symbol for canonical ordering
        symbols_with_lengths.sort()

        decode_tree = {}
        current_code = 0
        current_length = symbols_with_lengths[0][0]

        for length, symbol in symbols_with_lengths:
            # Pad with zeros if length increased
            current_code <<= length - current_length

            # Add the current symbol to the decode tree
            decode_tree[(length, current_code)] = symbol

            # Prepare for the next code
            current_code += 1
            current_length = length

        return decode_tree

