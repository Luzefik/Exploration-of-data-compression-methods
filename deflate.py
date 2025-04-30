import os
from collections import Counter

from bitarray import bitarray

from bit_reader import BitReader
from bit_writer import BitWriter
from huffman_coding import HuffmanTree
from LZ77 import LZ77


class Deflate:
    def __init__(self, window_size=None):
        self.lz77 = LZ77(window_size=window_size)

    def compress(
        self,
        input_file: str,
        output_file: str = None,
        verbose: bool = False,
        bfinal: int = 1,
    ) -> bitarray:
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + ".deflate"

        # 1) Отримуємо 4 списки від LZ77 (після змін у LZ77.py)
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
                    dist = distance_list[dist_idx] if dist_idx < len(distance_list) else None
                    dist_extra = distance_extra_bits[dist_extra_idx] if dist_extra_idx < len(distance_extra_bits) else None
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

        # 2) Розділяємо дані на блоки розумного розміру
        BLOCK_SIZE = 16384  # Розумний розмір блоку
        blocks = []
        current_block = {
            'symbols': [],
            'length_extra': [],
            'distances': [],
            'dist_extra': []
        }

        for i in range(len(symbol_list)):
            current_block['symbols'].append(symbol_list[i])
            current_block['length_extra'].append(length_extra_bits[i])

            if 257 <= symbol_list[i] <= 285:  # Якщо це код довжини
                current_block['distances'].append(distance_list[len(current_block['distances'])])
                current_block['dist_extra'].append(distance_extra_bits[len(current_block['dist_extra'])])

            # Якщо блок досяг максимального розміру або це останній символ
            if len(current_block['symbols']) >= BLOCK_SIZE or i == len(symbol_list) - 1:
                blocks.append(current_block)
                current_block = {
                    'symbols': [],
                    'length_extra': [],
                    'distances': [],
                    'dist_extra': []
                }

        # 3) Обробляємо кожен блок окремо
        writer = BitWriter()
        for i, block in enumerate(blocks):
            # Визначаємо чи це останній блок
            is_final = bfinal == 1 and i == len(blocks) - 1

            # Будуємо дерева Хаффмана для блоку
            freq_sym = Counter(block['symbols'])
            tree_sym = HuffmanTree.build_from_freq(freq_sym)
            tree_sym.make_canonical()

            freq_dist = Counter(block['distances'])
            tree_dist = None
            if freq_dist:
                tree_dist = HuffmanTree.build_from_freq(freq_dist)
                tree_dist.make_canonical()

            # Записуємо заголовок блоку
            writer.write_bits_lsb(is_final, 1)  # BFINAL
            writer.write_bits_lsb(2, 2)  # BTYPE=10 (динамічний)

            # Записуємо опис дерев
            self.write_tree_description(writer, tree_sym, tree_dist)

            # Записуємо дані блоку
            dist_iter = iter(block['distances'])
            len_eb_iter = iter(block['length_extra'])
            dist_eb_iter = iter(block['dist_extra'])

            for sym in block['symbols']:
                # Запис коду Хаффмана для символу/довжини
                if sym not in tree_sym.canon_codes:
                    raise ValueError(f"Symbol {sym} not found in Huffman tree")
                bits, length = tree_sym.canon_codes[sym]
                writer.write_bits_msb(bits, length)

                # Запис додаткових бітів
                eb_cnt, eb_val = next(len_eb_iter)
                if eb_cnt > 0:
                    writer.write_bits_lsb(eb_val, eb_cnt)

                # Обробка збігу
                if 257 <= sym <= 285:
                    dcode = next(dist_iter)
                    if tree_dist is None or dcode not in tree_dist.canon_codes:
                        raise ValueError(f"Distance code {dcode} not found in Huffman tree")
                    dbits, dlen = tree_dist.canon_codes[dcode]
                    writer.write_bits_msb(dbits, dlen)

                    eb_cnt_d, eb_val_d = next(dist_eb_iter)
                    if eb_cnt_d > 0:
                        writer.write_bits_lsb(eb_val_d, eb_cnt_d)

        # Записуємо результат у файл
        writer.flush_to_file(output_file)
        if verbose:
            print(f"Written DEFLATE output to {output_file}")

        return writer.get_bitarray()

    def encode_deflate(
        self,
        symbol_list: list[int],
        distance_list: list[int],
        extra_bits_list: list[tuple[int, int]],
        output_f: str,
        bfinal: int = 0,
    ):
        """
        Створює один DEFLATE-блок з статичним Huffman-кодуванням.

        :param symbol_list: список кодів літералів/довжин/256
        :param distance_list: список кодів відстаней для кожного матчу
        :param extra_bits_list: список (count, value) додаткових бітів
        :param output_f: ім'я вихідного файлу
        :param bfinal: чи це останній блок (0 або 1)
        """
        # 1) Розрахувати частоти
        freq_sym = Counter(symbol_list)
        freq_dist = Counter(distance_list)

        # 2) Побудувати Huffman-дерева
        tree_sym = HuffmanTree.build_from_freq(freq_sym)
        tree_sym.codes_generation()
        tree_sym.make_canonical()

        tree_dist = HuffmanTree.build_from_freq(freq_dist)
        tree_dist.codes_generation()
        tree_dist.make_canonical()

        # 3) Підготувати записувач бітів
        writer = BitWriter()
        # Заголовок: BFINAL (1 біт) + BTYPE=01 (статичний)
        writer.write_bits_lsb(bfinal, 1)  # BFINAL повинен бути в LSB порядку
        writer.write_bits_lsb(1, 2)  # BTYPE повинен бути в LSB порядку

        # 4) Емітувати всі символи + додбіт + коди відстаней
        dist_iter = iter(distance_list)
        for idx, sym in enumerate(symbol_list):
            # Літерал чи length/EOB
            bits, length = tree_sym.canon_codes[sym]
            writer.write_bits_msb(bits, length)  # Коди Хаффмана в MSB порядку

            # Додаткові біти літералу/length чи EOB
            eb_cnt, eb_val = extra_bits_list[idx]
            if eb_cnt > 0:
                writer.write_bits_lsb(eb_val, eb_cnt)  # Додаткові біти в LSB порядку

            # Якщо це код довжини матчу, пишемо ще відстань
            if sym >= 257 and sym != 256:
                dcode = next(dist_iter)
                dbits, dlen = tree_dist.canon_codes[dcode]
                writer.write_bits_msb(dbits, dlen)  # Коди Хаффмана в MSB порядку

                # додаткові біти відстані
                eb_cnt_d, eb_val_d = extra_bits_list[idx + 1]
                if eb_cnt_d > 0:
                    writer.write_bits_lsb(
                        eb_val_d, eb_cnt_d
                    )  # Додаткові біти в LSB порядку

        # 5) Записати в файл
        writer.flush_to_file(output_f)

    def write_tree_description(
        self,
        writer: BitWriter,
        tree_lit_len: HuffmanTree,
        tree_dist: HuffmanTree | None,
    ):
        """
        Записує опис динамічних дерев Хаффмана у DEFLATE потік (для BTYPE=10).
        Реалізує RLE та третє дерево для довжин кодів.
        """
        # --- Крок А: Визначення HLIT, HDIST ---
        # Кількість кодів літералів/довжин (мінімум 257)
        hlit = (
            max(tree_lit_len.canon_codes.keys() if tree_lit_len.canon_codes else [256])
            + 1
        )
        if hlit < 257:
            hlit = 257  # За стандартом мінімум 257
        if hlit > 286:  # Максимальне значення за стандартом
            hlit = 286

        # Кількість кодів відстаней (мінімум 1)
        hdist = 1
        if tree_dist and tree_dist.canon_codes:
            hdist = max(tree_dist.canon_codes.keys()) + 1
        if hdist < 1:
            hdist = 1  # За стандартом мінімум 1
        if hdist > 30:  # Максимальне значення за стандартом
            hdist = 30

        # --- Крок Б: Створення списку довжин кодів ---
        lit_len_lengths = [
            tree_lit_len.canon_codes.get(i, (0, 0))[1] for i in range(hlit)
        ]
        dist_lengths = []
        if tree_dist and tree_dist.canon_codes:
            dist_lengths = [
                tree_dist.canon_codes.get(i, (0, 0))[1] for i in range(hdist)
            ]
        else:  # Якщо дерева відстаней немає, але hdist=1, потрібна довжина 0
            dist_lengths = [0] * hdist

        all_code_lengths = lit_len_lengths + dist_lengths

        # --- Крок В: Run-Length Encoding (RLE) ---
        rle_encoded_lengths = []  # Список значень 0-18
        rle_extra_bits = []  # Список дод. бітів для 16, 17, 18

        i = 0
        while i < len(all_code_lengths):
            length = all_code_lengths[i]
            # Рахуємо повтори поточної довжини
            count = 1
            j = i + 1
            while j < len(all_code_lengths) and all_code_lengths[j] == length:
                count += 1
                j += 1

            if length == 0:  # Кодування послідовностей нулів
                if count >= 11:
                    # Використовуємо код 18 (11-138 нулів)
                    while count >= 11:
                        num_zeros = min(count, 138)
                        rle_encoded_lengths.append(18)
                        rle_extra_bits.append((7, num_zeros - 11))  # 7 дод. біт
                        count -= num_zeros
                if count >= 3:
                    # Використовуємо код 17 (3-10 нулів)
                    while count >= 3:
                        num_zeros = min(count, 10)
                        rle_encoded_lengths.append(17)
                        rle_extra_bits.append((3, num_zeros - 3))  # 3 дод. біти
                        count -= num_zeros
                # Залишок нулів (0, 1 або 2) записуємо як є
                rle_encoded_lengths.extend([0] * count)
                rle_extra_bits.extend([(0, 0)] * count)

            else:  # Кодування ненульової довжини та її повторів
                rle_encoded_lengths.append(length)  # Записуємо саму довжину
                rle_extra_bits.append((0, 0))
                count -= 1  # Один раз вже записали

                if count >= 3:
                    # Використовуємо код 16 (повтор попереднього 3-6 разів)
                    while count >= 3:
                        num_repeats = min(count, 6)
                        rle_encoded_lengths.append(16)
                        rle_extra_bits.append((2, num_repeats - 3))  # 2 дод. біти
                        count -= num_repeats
                # Залишок повторів (0, 1 або 2) записуємо як є
                rle_encoded_lengths.extend([length] * count)
                rle_extra_bits.extend([(0, 0)] * count)

            i += j - i  # Пересуваємо індекс на оброблену послідовність

        # --- Крок Г: Побудова дерева для довжин кодів (tree_cl) ---
        cl_freqs = Counter(rle_encoded_lengths)
        if not cl_freqs:  # Повинно бути хоча б щось
            raise ValueError(
                "Cannot build Code Length Huffman tree from empty frequencies"
            )
        tree_cl = HuffmanTree.build_from_freq(cl_freqs)
        tree_cl.make_canonical()

        # --- Крок Д: Визначення HCLEN ---
        # Порядок перевірки символів для HCLEN
        cl_order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        hclen = 19  # Максимальна можлива кількість
        for k in range(18, -1, -1):
            if cl_order[k] in tree_cl.canon_codes:
                hclen = k + 1
                break
        # Мінімальне значення HCLEN - 4
        if hclen < 4:
            hclen = 4

        # --- Крок Е: Запис заголовка опису дерев (HLIT, HDIST, HCLEN) ---
        writer.write_bits_lsb(hlit - 257, 5)
        writer.write_bits_lsb(hdist - 1, 5)
        writer.write_bits_lsb(hclen - 4, 4)

        # --- Крок Є: Запис дерева tree_cl ---
        for k in range(hclen):
            symbol_in_order = cl_order[k]
            cl_code_len = tree_cl.canon_codes.get(symbol_in_order, (0, 0))[1]
            writer.write_bits_lsb(cl_code_len, 3)  # 3 біти LSB first

        # --- Крок Ж: Запис RLE-закодованих даних ---
        rle_extra_iter = iter(rle_extra_bits)
        for rle_sym in rle_encoded_lengths:
            if rle_sym not in tree_cl.canon_codes:
                raise ValueError(
                    f"RLE symbol {rle_sym} not found in Code Length Huffman tree!"
                )

            # Отримуємо код Хаффмана для RLE-символу
            bits, length = tree_cl.canon_codes[rle_sym]
            # Записуємо код: MSB first
            writer.write_bits_msb(bits, length)

            # Отримуємо та записуємо додаткові біти для кодів 16, 17, 18
            extra_cnt, extra_val = next(rle_extra_iter)
            if extra_cnt > 0:
                # Записуємо додаткові біти: LSB first
                writer.write_bits_lsb(extra_val, extra_cnt)

    def decompress(
        self, input_file: str, output_file: str = None, verbose: bool = False
    ) -> bytes:
        """
        Декомпресує файл у форматі DEFLATE.

        :param input_file: шлях до вхідного .deflate файлу
        :param output_file: шлях до вихідного файлу
        :param verbose: виводити додаткову інформацію
        :return: розпаковані байти
        """
        if output_file is None:
            output_file = os.path.splitext(input_file)[0] + ".decoded"

        reader = BitReader(input_file)
        decoded_data = bytearray()

        # Декодування буде відбуватися доки не дійдемо до кінця файлу або до останнього блоку
        is_final_block = False
        while not is_final_block:
            # Зчитуємо заголовок блоку
            bfinal = reader.read_bit()
            is_final_block = bfinal == 1

            btype = reader.read_bits_lsb(2)

            if verbose:
                print(f"Block: BFINAL={bfinal}, BTYPE={btype}")

            if btype == 0:
                # Нестиснутий блок
                self._decompress_uncompressed_block(reader, decoded_data, verbose)
            elif btype == 1:
                # Блок із фіксованим кодуванням Хаффмана
                self._decompress_fixed_huffman_block(reader, decoded_data, verbose)
            elif btype == 2:
                # Блок із динамічним кодуванням Хаффмана
                self._decompress_32kb_block(reader, decoded_data, verbose)
            else:
                raise ValueError(f"Невідомий тип блоку: {btype}")

        # Записуємо результат у файл
        with open(output_file, "wb") as f:
            f.write(decoded_data)

        if verbose:
            print(f"Декомпресовано {len(decoded_data)} байтів у файл {output_file}")

        return decoded_data

    def _decompress_uncompressed_block(
        self, reader: BitReader, output_buffer: bytearray, verbose: bool
    ):
        """
        Декомпресує нестиснутий блок (BTYPE=0).
        """
        # Вирівнюємо до байта
        reader.byte_align()

        # Зчитуємо довжину та інверсію довжини
        len_bytes = reader.read_bits_lsb(16)
        nlen_bytes = reader.read_bits_lsb(16)

        # Перевіряємо, чи доповнення правильне
        if (len_bytes + nlen_bytes) != 0xFFFF:
            raise ValueError(
                f"Неправильне доповнення для нестиснутого блоку: LEN={len_bytes}, NLEN={nlen_bytes}"
            )

        if verbose:
            print(f"Uncompressed block: {len_bytes} bytes")

        # Зчитуємо безпосередньо байти
        for _ in range(len_bytes):
            byte = reader.read_bits_lsb(8)
            output_buffer.append(byte)

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
                raise ValueError(f"Invalid block parameters: HLIT={hlit}, HDIST={hdist}, HCLEN={hclen}")

            if verbose:
                print(f"32KB Dynamic Huffman block: HLIT={hlit}, HDIST={hdist}, HCLEN={hclen}")

            # Порядок кодів для дерева кодів довжин
            code_length_order = [
                16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15,
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
                    raise ValueError("Unexpected end of compressed data while reading code lengths")

            # Розділяємо довжини кодів
            lit_len_lengths = code_lengths[:hlit]
            dist_lengths = code_lengths[hlit : hlit + hdist]

            # Будуємо дерева Хаффмана
            lit_len_tree = self._build_huffman_tree_from_lengths(lit_len_lengths)
            if not lit_len_tree:
                raise ValueError("Failed to build literal/length tree")

            dist_tree = self._build_huffman_tree_from_lengths(dist_lengths, is_distance_tree=True)
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
                    raise ValueError(f"Invalid distance {distance} exceeds buffer size {len(output_buffer)}")

                if verbose:
                    print(f"Match: length={length}, distance={distance}")

                # Копіюємо дані з попередньої позиції
                for i in range(length):
                    if distance > len(output_buffer):
                        raise ValueError(f"Distance {distance} exceeds buffer size {len(output_buffer)}")
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
                symbol = tree[(code_len, code)]
                # Додаткова валідація для кодів відстаней
                if symbol > 29 and (0, 0) in tree:
                    return tree[(0, 0)]
                return symbol

            # Якщо досягли максимальної довжини і не знайшли код,
            # перевіряємо чи є код довжини 0
            if code_len == max_code_len and (0, 0) in tree:
                return tree[(0, 0)]

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
                            raise ValueError(f"Distance {distance} exceeds maximum window size {LZ77.MAX_WINDOW_SIZE}")
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

    def _build_huffman_tree_from_lengths(self, lengths: list[int], is_distance_tree: bool = False) -> dict[tuple[int, int], int]:
        """
        Будує дерево Хаффмана за списком довжин кодів та повертає словник для декодування.
        Словник має формат {(довжина_коду, значення_коду): символ}.
        """
        # Filter out symbols with code length 0
        symbols_with_lengths = [(length, symbol) for symbol, length in enumerate(lengths) if length > 0]

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
            current_code <<= (length - current_length)

            # Add the current symbol to the decode tree
            decode_tree[(length, current_code)] = symbol

            # Prepare for the next code
            current_code += 1
            current_length = length

        return decode_tree


if __name__ == "__main__":
    import time

    start_time = time.perf_counter()

    i_belive_it_works = Deflate()


    # i_belive_it_works.compress(
    #     "customers-100.csv",
    #     output_file="output-file-CSV.deflate",
    #     verbose=True,
    #     bfinal=1,
    # )
    # i_belive_it_works.decompress(
    #     "output-file-CSV.deflate",
    #     output_file="ТИЗМОЖЕШ-file-CSV.csv",
    #     verbose=True,
    # )


    i_belive_it_works.compress(
        "pidmohylnyy-valerian-petrovych-misto76.txt",
        output_file="output-file-2.deflate",
        verbose=True,
        bfinal=1,
    )
    i_belive_it_works.decompress(
        "output-file-2.deflate",
        output_file="БУДЬЛАСКА_____output-file-2.txt",
        verbose=True,
    )

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.6f} seconds")
