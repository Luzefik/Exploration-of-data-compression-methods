import os
from bitarray import bitarray
from collections import Counter

from LZ77 import LZ77
from huffman_coding import HuffmanTree, BitWriter
class Deflate:
    def __init__(self, window_size=None):
        self.lz77 = LZ77(window_size=window_size)

    def compress(
        self,
        input_file: str,
        output_file: str = None,
        verbose: bool = False,
        bfinal: int = 1
    ) -> bitarray:
        # ... визначення output_file ...

        # 1) Викликаємо LZ77, який ВЖЕ робить мапінг і повертає готові списки
        # УВАГА: Потрібно змінити LZ77.compress, щоб він повертав 4 списки
        # як обговорювалося (або адаптувати HuffmanTree.encode_deflate)
        # Поки що припустимо, що він повертає 3 списки, як у вашому коді LZ77.py
        result_from_lz77 = self.lz77.compress(
            input_file,
            verbose=verbose,
            deflate=True
        )
        # Отримуємо списки (припускаючи, що LZ77.compress повертає кортеж з 3 елементів)
        symbol_list, distance_list, extra_bits_list = result_from_lz77

        if verbose:
            print(f"LZ77+Mapping produced {len(symbol_list)} lit/len symbols and {len(distance_list)} dist symbols.")

        # 2) ВИДАЛЕНО ЦИКЛ МАРІНГУ 'for t in tokens:' - він більше не потрібен тут

        # 3) Build Huffman trees (цей код залишається)
        freq_sym  = Counter(symbol_list)
        freq_dist = Counter(distance_list)
        # ПОПЕРЕДЖЕННЯ: Якщо distance_list порожній (не було жодного match),
        # build_from_freq(freq_dist) може спричинити помилку. Потрібна перевірка.
        if not freq_dist: # Якщо не було збігів
             tree_dist = None # Або створити дерево з одним фіктивним кодом
        else:
             tree_dist = HuffmanTree.build_from_freq(freq_dist)
             tree_dist.make_canonical()

        tree_sym  = HuffmanTree.build_from_freq(freq_sym)
        tree_sym.make_canonical()


        # 4) Emit DEFLATE block (цей код в основному залишається,
        # АЛЕ ПОТРІБНО УЗГОДИТИ обробку extra_bits_list та distance_list!)
        writer = BitWriter()
        # BFINAL + BTYPE=01 (static) - ВИРІШИТИ: СТАТИЧНИЙ чи ДИНАМІЧНИЙ?
        # Якщо статичний, не будуйте дерева вище, а використовуйте фіксовані коди.
        # Якщо динамічний, BTYPE=10 і потрібно закодувати дерева.
        # Припускаємо ПОКИ ЩО динамічний з неправильним BTYPE=01
        writer.write_bits(bfinal, 1)
        writer.write_bits(1, 2) # ПОМИЛКА ЛОГІКИ: BTYPE=01 (статичний) використовується з динамічними деревами

        dist_iter = iter(distance_list)
        # УВАГА: ЛОГІКА ОБРОБКИ extra_bits_list тут, ймовірно, НЕПРАВИЛЬНА
        # через те, як extra_bits_list генерується в LZ77.py (подвійні записи для match)
        for idx, sym in enumerate(symbol_list):
            # write symbol code
            # Перевірка наявності символу в канонічних кодах
            if sym not in tree_sym.canon_codes:
                 raise ValueError(f"Symbol {sym} not found in literal/length Huffman codes!")
            bits, length = tree_sym.canon_codes[sym]
            writer.write_bits(bits, length)

            # write extra bits for this symbol (літерал, довжина або EOB)
            # Потрібна перевірка індексу, якщо структура extra_bits_list інша
            if idx < len(extra_bits_list):
                 eb_cnt, eb_val = extra_bits_list[idx] # Припускаємо, що extra_bits_list відповідає symbol_list
                 writer.write_bits(eb_val, eb_cnt)
            else:
                 print(f"Warning: extra_bits_list index {idx} out of bounds!") # Потрібна відладка

            # if match, write distance
            if sym >= 257: # EOB (256) не є >= 257
                try:
                    dcode = next(dist_iter)
                    # Перевірка наявності коду відстані та дерева
                    if tree_dist is None or dcode not in tree_dist.canon_codes:
                         raise ValueError(f"Distance code {dcode} not found in distance Huffman codes or tree is missing!")
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
                    print(f"Placeholder: Missing correct distance extra bits handling for distance code {dcode}")


                except StopIteration:
                    raise ValueError("Mismatch between number of length codes and distance codes!")


        # flush to file
        writer.flush_to_file(output_file)
        if verbose:
            print(f"Written DEFLATE output to {output_file}")

        return writer.bits

if __name__ == "__main__":
    import time

    start_time = time.perf_counter()

    i_belive_it_works = Deflate()

    i_belive_it_works.compress(
        input_file="customers-100.csv",
        output_file="ЇБАНИЙ_ДІФЛЕЙТ.deflate",
        verbose=True,
        bfinal=1
    )

    i_belive_it_works.compress("pidmohylnyy-valerian-petrovych-misto76.txt",
        output_file="output-file-2.deflate",
        verbose=True,
        bfinal=1
    )
    i_belive_it_works.compress("biblija.txt",
        output_file="output-file-3.deflate",
        verbose=True,
        bfinal=1
    )
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.6f} seconds")

