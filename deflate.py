# deflater.py

import io
import binascii
from LZ_Pair import LZPair
from lz_window import LZWindow
from huffman_coding import HuffmanTree, HuffmanTable
from bit_streaming import BitInputStream, BitOutputStream  # ваші утиліти для бітового I/O

class Deflater:
    """
    Клас для стискання даних у форматі DEFLATE (використовується всередині GZCompressor).
    """
    # режими стиснення
    MODE_NONE    = 0
    MODE_FIXED   = 1
    MODE_DYNAMIC = 2

    END_OF_BLOCK = 256
    LEN_ORDER    = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
    N_LITERALS   = 286
    N_DISTANCES  = 30
    N_LENGTHS    = 19

    def __init__(self, gz, bit_in: BitInputStream, bit_out: BitOutputStream,
                 mode=MODE_DYNAMIC, window_bits=8, buffer_size=32768):
        self.gz = gz                  # посилання на GZCompressor для прогресу
        self.inp = bit_in
        self.out = bit_out
        self.mode = mode
        self.enable_lz77 = True
        self.buffer_size = buffer_size
        # CRC32 так само як у Java CRC32
        self.crc = 0

    def _update_crc(self, data: bytes):
        self.crc = binascii.crc32(data, self.crc) & 0xffffffff

    def get_crc(self) -> int:
        return self.crc

    def process(self) -> int:
        """
        Основний метод: читає вхідний потік, ділить на блоки, стискає і пише у self.out.
        Повертає загальну кількість записаних бітів/байтів.
        """
        block_buffer = io.BytesIO()
        block_bits = BitOutputStream(block_buffer)

        window = LZWindow(1 << 8)  # вікно розміром 256

        while True:
            chunk = self.inp.read(self.buffer_size)
            if not chunk:
                break
            # оновлюємо CRC і показуємо прогрес
            self._update_crc(chunk)
            self.gz.update_progress(self.inp.get_count())

            # Якщо попередній блок не порожній — запишемо його у self.out
            if block_buffer.tell() > 0:
                self._flush_block(block_buffer, block_bits)

            # Якщо режим NONE — пишемо сирі блоки
            if self.mode == self.MODE_NONE:
                block_bits.write_short(len(chunk))
                block_bits.write_short(len(chunk) ^ 0xFFFF)
                block_bits.write(chunk)
                for b in chunk:
                    window.add(b)
                block_bits.flush_bits()
                continue

            # 1) Знаходимо LZ-пари і збираємо частоти
            lit_freq = [0] * self.N_LITERALS
            dist_freq = [0] * self.N_DISTANCES
            pairs = [None] * len(chunk)

            i = 0
            while i < len(chunk):
                pair = None
                if self.enable_lz77:
                    pair = window.find(chunk, i)
                if pair:
                    pairs[i] = pair
                    window.add(chunk[i:i + pair.length])
                    lit_freq[pair.lenSymbol] += 1
                    dist_freq[pair.distSymbol] += 1
                    i += pair.length
                else:
                    byte = chunk[i]
                    window.add(byte)
                    lit_freq[byte] += 1
                    i += 1

            # кінцевий маркер блоку
            lit_freq[self.END_OF_BLOCK] += 1

            # 2) Будуємо Huffman-дерева та таблиці кодів
            if self.mode == self.MODE_DYNAMIC:
                lit_tree = HuffmanTree(lit_freq, 15)
                dist_tree = HuffmanTree(dist_freq, 15)
                lit_tab = lit_tree.get_table()
                dist_tab = dist_tree.get_table()

                # упаковка довжин кодів (для дерев довжин)
                lengths = HuffmanTable.pack_code_lengths(lit_tab.code_len, dist_tab.code_len)

                # частоти для дерев довжин
                len_freq = {}
                for sym in lengths:
                    len_freq[sym] = len_freq.get(sym, 0) + 1

                len_tree = HuffmanTree([len_freq.get(i, 0) for i in range(self.N_LENGTHS)], 7)
                len_tab = len_tree.get_table()
            else:
                # фіксовані коди
                lit_tab, dist_tab = HuffmanTable.LIT, HuffmanTable.DIST
                len_tab = None
                lengths = []

            # 3) Записуємо заголовок блоку (final + type)
            block_bits.write_bits(0, 1)               # bfinal=0 поки не останній
            block_bits.write_bits(self.mode, 2)       # btype

            # якщо динамічний — пишемо дерева довжин
            if self.mode == self.MODE_DYNAMIC:
                block_bits.write_bits(self.N_LITERALS - 257, 5)
                block_bits.write_bits(self.N_DISTANCES - 1, 5)
                block_bits.write_bits(self.N_LENGTHS - 4, 4)
                for idx in self.LEN_ORDER:
                    block_bits.write_bits(len_tab.code_len[idx], 3)
                it = iter(lengths)
                for sym in lengths:
                    block_bits.write_bits(len_tab.code[sym], len_tab.code_len[sym])
                    if sym == 16:
                        extra = next(it)
                        block_bits.write_bits(extra, 2)
                    elif sym == 17:
                        extra = next(it)
                        block_bits.write_bits(extra, 3)
                    elif sym == 18:
                        extra = next(it)
                        block_bits.write_bits(extra, 7)

            # 4) Записуємо власне дані (літерали + length/distance пари)
            i = 0
            while i < len(chunk):
                pair = pairs[i]
                if pair:
                    sym = pair.lenSymbol
                    block_bits.write_bits(lit_tab.code[sym], lit_tab.code_len[sym])
                    block_bits.write_bits(pair.lenBits, pair.lenNumBits)
                    dsym = pair.distSymbol
                    block_bits.write_bits(dist_tab.code[dsym], dist_tab.code_len[dsym])
                    block_bits.write_bits(pair.distBits, pair.distNumBits)
                    i += pair.length
                else:
                    b = chunk[i]
                    block_bits.write_bits(lit_tab.code[b], lit_tab.code_len[b])
                    i += 1

            eob = self.END_OF_BLOCK
            block_bits.write_bits(lit_tab.code[eob], lit_tab.code_len[eob])
            block_bits.flush_bits()

        self._flush_block(block_buffer, block_bits, final=True)
        return self.out.byte_count

    def _flush_block(self, buffer_io: io.BytesIO, block_bits: BitOutputStream, final=False):
        data = buffer_io.getvalue()
        bfinal = 1 if final else 0
        for byte in data:
            self.out.write_bits(byte, 8)
        buffer_io.seek(0)
        buffer_io.truncate(0)
