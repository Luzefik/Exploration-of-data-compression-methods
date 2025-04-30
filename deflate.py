import os
from collections import Counter

from bitarray import bitarray

from huffman_coding import BitWriter, HuffmanTree
from LZ77 import LZ77


class Deflate:
    _FIXED_LIT_LEN_CODES = {}
    for symbol in range(0, 144):
        _FIXED_LIT_LEN_CODES[symbol] = (0b00110000 + symbol, 8)
    for symbol in range(144, 256):
        _FIXED_LIT_LEN_CODES[symbol] = (0b110010000 + (symbol - 144), 9)
    for symbol in range(256, 280):
        _FIXED_LIT_LEN_CODES[symbol] = (0b0000000 + (symbol - 256), 7)
    for symbol in range(280, 286):
        _FIXED_LIT_LEN_CODES[symbol] = (0b11000000 + (symbol - 280), 8)
    _FIXED_DIST_CODES = {}
    for dist_code in range(0, 30):
        _FIXED_DIST_CODES[dist_code] = (dist_code, 5)

    def __init__(self, window_size=None):
        self.lz77 = LZ77(window_size=window_size)

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
        writer.write_bits(bfinal, 1)
        writer.write_bits(1, 2)

        # 4) Емітувати всі символи + додбіт + коди відстаней
        dist_iter = iter(distance_list)
        for idx, sym in enumerate(symbol_list):
            # Літерал чи length/EOB
            bits, length = tree_sym.canon_codes[sym]
            writer.write_bits(bits, length)

            # Додаткові біти літералу/length чи EOB
            eb_cnt, eb_val = extra_bits_list[idx]
            writer.write_bits(eb_val, eb_cnt)

            # Якщо це код довжини матчу, пишемо ще відстань
            if sym >= 257 and sym != 256:
                dcode = next(dist_iter)
                dbits, dlen = tree_dist.canon_codes[dcode]
                writer.write_bits(dbits, dlen)
                # додаткові біти відстані
                eb_cnt_d, eb_val_d = extra_bits_list[idx + 1]
                writer.write_bits(eb_val_d, eb_cnt_d)

        # 5) Записати в файл
        writer.flush_to_file(output_f)

    def compress(
        self,
        input_file: str,
        output_file: str = None,
        verbose: bool = False,
        bfinal: int = 1,
    ) -> bitarray:
        # ... визначення output_file ...

        # 1) Викликаємо LZ77, який ВЖЕ робить мапінг і повертає готові списки
        # УВАГА: Потрібно змінити LZ77.compress, щоб він повертав 4 списки
        # як обговорювалося (або адаптувати HuffmanTree.encode_deflate)
        # Поки що припустимо, що він повертає 3 списки, як у вашому коді LZ77.py
        result_from_lz77 = self.lz77.compress(input_file, verbose=verbose, deflate=True)
        # Отримуємо списки (припускаючи, що LZ77.compress повертає кортеж з 4 елементів)
        symbol_list, symbol_extra_bits, distance_list, distance_extra_bits = (
            result_from_lz77
        )

        if verbose:
            print(
                f"LZ77+Mapping produced {len(symbol_list)} lit/len symbols and {len(distance_list)} dist symbols."
            )

        # 2) ВИДАЛЕНО ЦИКЛ МАРІНГУ 'for t in tokens:' - він більше не потрібен тут

        # 3) Build Huffman trees (цей код залишається)
        freq_sym = Counter(symbol_list)
        freq_dist = Counter(distance_list)
        # ПОПЕРЕДЖЕННЯ: Якщо distance_list порожній (не було жодного match),
        # build_from_freq(freq_dist) може спричинити помилку. Потрібна перевірка.
        if not freq_dist:  # Якщо не було збігів
            tree_dist = None  # Або створити дерево з одним фіктивним кодом
        else:
            tree_dist = HuffmanTree.build_from_freq(freq_dist)
            tree_dist.make_canonical()

        tree_sym = HuffmanTree.build_from_freq(freq_sym)
        tree_sym.make_canonical()

        # 4) Emit DEFLATE block (цей код в основному залишається,
        # АЛЕ ПОТРІБНО УЗГОДИТИ обробку extra_bits_list та distance_list!)
        writer = BitWriter()
        # BFINAL + BTYPE=01 (static) - ВИРІШИТИ: СТАТИЧНИЙ чи ДИНАМІЧНИЙ?
        # Якщо статичний, не будуйте дерева вище, а використовуйте фіксовані коди.
        # Якщо динамічний, BTYPE=10 і потрібно закодувати дерева.
        # Припускаємо ПОКИ ЩО динамічний з неправильним BTYPE=01
        writer.write_bits(bfinal, 1)
        writer.write_bits(
            1, 2
        )  # ПОМИЛКА ЛОГІКИ: BTYPE=01 (статичний) використовується з динамічними деревами

        dist_iter = iter(distance_list)
        # УВАГА: ЛОГІКА ОБРОБКИ extra_bits_list тут, ймовірно, НЕПРАВИЛЬНА
        # через те, як extra_bits_list генерується в LZ77.py (подвійні записи для match)
        for idx, sym in enumerate(symbol_list):
            # write symbol code
            # Перевірка наявності символу в канонічних кодах
            if sym not in tree_sym.canon_codes:
                raise ValueError(
                    f"Symbol {sym} not found in literal/length Huffman codes!"
                )
            bits, length = tree_sym.canon_codes[sym]
            writer.write_bits(bits, length)

            # write extra bits for this symbol (літерал, довжина або EOB)
            # Потрібна перевірка індексу, якщо структура extra_bits_list інша
            if idx < len(symbol_extra_bits):
                eb_cnt, eb_val = symbol_extra_bits[
                    idx
                ]  # Припускаємо, що extra_bits_list відповідає symbol_list
                writer.write_bits(eb_val, eb_cnt)
            else:
                print(
                    f"Warning: symbol_extra_bits index {idx} out of bounds!"
                )  # Потрібна відладка

            # if match, write distance
            if sym >= 257:  # EOB (256) не є >= 257
                try:
                    dcode = next(dist_iter)
                    # Перевірка наявності коду відстані та дерева
                    if tree_dist is None or dcode not in tree_dist.canon_codes:
                        raise ValueError(
                            f"Distance code {dcode} not found in distance Huffman codes or tree is missing!"
                        )
                    dbits, dlen = tree_dist.canon_codes[dcode]
                    writer.write_bits(dbits, dlen)

                    # *** ОСНОВНА ПРОБЛЕМА ЗАЛИШАЄТЬСЯ ТУТ ***
                    # Як отримати ПРАВИЛЬНІ дод. біти для ВІДСТАНІ?
                    # Поточний extra_bits_list[idx+1] НЕПРАВИЛЬНИЙ через генерацію в LZ77.
                    # Потрібно або змінити генерацію в LZ77 (рекомендовано),
                    # або мати окремий список дод. бітів для відстаней.
                    # Припустимо, що ми маємо окремий `dist_extra_bits`, який відповідає `distance_list`
                    # eb_cnt_d, eb_val_d = dist_extra_bits[dist_iter_index] # Потрібно реалізувати
                    # writer.write_bits(eb_val_d, eb_cnt_d)
                    print(
                        f"Placeholder: Missing correct distance extra bits handling for distance code {dcode}"
                    )

                except StopIteration:
                    raise ValueError(
                        "Mismatch between number of length codes and distance codes!"
                    )

        # flush to file
        writer.flush_to_file(output_file)
        if verbose:
            print(f"Written DEFLATE output to {output_file}")

        return writer.bits

    # def read_and_build_dynamic_trees(self, reader):
    #     # Перенесено імпорт сюди
    #     from huffman_coding import HuffmanTree

    #     HLIT = reader.read_bits(5) + 257
    #     HDIST = reader.read_bits(5) + 1
    #     HCLEN = reader.read_bits(4) + 4

    #     # 1) Зчитуємо коди довжин кодів (19 можливих, у певному порядку)
    #     code_length_order = [
    #         16,
    #         17,
    #         18,
    #         0,
    #         8,
    #         7,
    #         9,
    #         6,
    #         10,
    #         5,
    #         11,
    #         4,
    #         12,
    #         3,
    #         13,
    #         2,
    #         14,
    #         1,
    #         15,
    #     ]
    #     clens = [0] * 19
    #     for i in range(HCLEN):
    #         clens[code_length_order[i]] = reader.read_bits(3)

    #     # 2) Побудувати дерево для кодів довжин:
    #     tree_cl = HuffmanTree.build_from_freq(
    #         {sym: clens[sym] for sym in range(19) if clens[sym] > 0}
    #     )
    #     tree_cl.make_canonical()

    #     # 3) Розгорнути HLIT+HDIST довжин кодів для двох дерев за алгоритмом з RFC1951:
    #     lengths = []
    #     total = HLIT + HDIST
    #     while len(lengths) < total:
    #         sym = tree_cl.decode_symbol(reader)
    #         if sym <= 15:
    #             lengths.append(sym)
    #         elif sym == 16:
    #             repeat = reader.read_bits(2) + 3
    #             lengths.extend([lengths[-1]] * repeat)
    #         elif sym == 17:
    #             repeat = reader.read_bits(3) + 3
    #             lengths.extend([0] * repeat)
    #         elif sym == 18:
    #             repeat = reader.read_bits(7) + 11
    #             lengths.extend([0] * repeat)

    #     # 4) Тепер перші HLIT значень → дерево для літераалів/довжин, наступні HDIST → дерево для відстаней
    #     lit_len_freq = Counter({i: lengths[i] for i in range(HLIT) if lengths[i] > 0})
    #     dist_freq = Counter(
    #         {i: lengths[HLIT + i] for i in range(HDIST) if lengths[HLIT + i] > 0}
    #     )

    #     tree_ll = HuffmanTree.build_from_freq(lit_len_freq)
    #     tree_ll.make_canonical()
    #     tree_ds = HuffmanTree.build_from_freq(dist_freq)
    #     tree_ds.make_canonical()

    #     return tree_ll, tree_ds


if __name__ == "__main__":
    import time

    start_time = time.perf_counter()

    i_belive_it_works = Deflate()

    i_belive_it_works.compress(
        "pidmohylnyy-valerian-petrovych-misto76.txt",
        output_file="output-file-2.deflate",
        verbose=True,
        bfinal=1,
    )
    # i_belive_it_works.compress(
    #     "biblija.txt", output_file="output-file-3.deflate", verbose=True, bfinal=1
    # )
    # end_time = time.perf_counter()
    # elapsed_time = end_time - start_time
    # print(f"Elapsed time: {elapsed_time:.6f} seconds")
