import warnings
import struct
import binascii
from collections import deque
from huffman_coding import LIT, DIST
from huffman_coding import HuffmanTable
from LZ_Pair import LZPair


class Inflater:
    """
    Inflates DEFLATE-compressed data blocks from a bit stream.
    """
    END_OF_BLOCK = 256
    LEN_ORDER = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
    N_LITERALS = 286
    N_DISTANCES = 30
    N_LENGTHS = 19
    WINDOW_SIZE = 32768

    def __init__(self, bit_in, bit_out, update_progress=None):
        self.in_stream = bit_in
        self.out_stream = bit_out
        self.update_progress = update_progress or (lambda count: None)
        self.crc = 0
        self.window = deque(maxlen=self.WINDOW_SIZE)
        # code tables
        self.lit_codes = []
        self.lit_map = {}
        self.dist_codes = []
        self.dist_map = {}
        self.len_codes = []
        self.len_map = {}

    def process(self):
        """Process all blocks; return total output byte count."""
        total = 0
        while True:
            bfinal = self.in_stream.read_bits(1)
            btype  = self.in_stream.read_bits(2)
            if btype == 0:
                self.in_stream.align_byte()
                total += self._process_uncompressed()
            elif btype == 1:
                self._load_static_codes()
                total += self._process_huffman()
            elif btype == 2:
                self._read_dynamic_codes()
                total += self._process_huffman()
            else:
                raise ValueError("Invalid block type")
            self.update_progress(self.in_stream.bit_count)
            if bfinal:
                break
        return total

    def _process_uncompressed(self):
        # read LEN and NLEN
        len_lo = self.in_stream.read_bits(16)
        nlen   = self.in_stream.read_bits(16) ^ 0xFFFF
        if nlen != len_lo:
            raise ValueError("Invalid uncompressed block lengths")
        data = self.in_stream.read_bytes(len_lo)
        self._write_bytes(data)
        return len_lo

    def _load_static_codes(self):
        # static tables from RFC1951
        self.lit_codes = LIT.code
        self.lit_map   = self._build_map(LIT.code, LIT.code_len)
        self.dist_codes= DIST.code
        self.dist_map  = self._build_map(DIST.code, DIST.code_len)

    def _read_dynamic_codes(self):
        hlit = 257 + self.in_stream.read_bits(5)
        hdist= 1   + self.in_stream.read_bits(5)
        hclen= 4   + self.in_stream.read_bits(4)
        # read code length code lengths
        clens = [0]*self.N_LENGTHS
        for i in range(hclen):
            clens[self.LEN_ORDER[i]] = self.in_stream.read_bits(3)
        # build length code tree

        table = HuffmanTable(self.N_LENGTHS)
        table.code_len = clens
        self.len_codes = table.pack_code_lengths([], [])  # placeholder to generate codes
        self.len_map = self._build_map(self.len_codes, clens)
        # read lit+dist code lengths
        lengths = []
        i = 0
        total = hlit + hdist
        while i < total:
            sym = self._read_symbol(self.len_codes, self.len_map)
            if sym == 16:
                count = 3 + self.in_stream.read_bits(2)
                lengths.extend([lengths[-1]]*count)
                i += count
            elif sym == 17:
                count = 3 + self.in_stream.read_bits(3)
                lengths.extend([0]*count)
                i += count
            elif sym == 18:
                count = 11 + self.in_stream.read_bits(7)
                lengths.extend([0]*count)
                i += count
            else:
                lengths.append(sym)
                i += 1
        # split
        lit_lens  = lengths[:hlit]
        dist_lens = lengths[hlit:]
        # build tables
        lit_table  = HuffmanTable(len(lit_lens))
        lit_table.code_len = lit_lens
        self.lit_codes = lit_table.code
        self.lit_map   = self._build_map(lit_table.code, lit_lens)
        dist_table = HuffmanTable(len(dist_lens))
        dist_table.code_len = dist_lens
        self.dist_codes= dist_table.code
        self.dist_map  = self._build_map(dist_table.code, dist_lens)

    def _process_huffman(self):
        count = 0
        while True:
            sym = self._read_symbol(self.lit_codes, self.lit_map)
            if sym < self.END_OF_BLOCK:
                b = sym
                self._write_bytes(bytes([b]))
                count += 1
            elif sym == self.END_OF_BLOCK:
                break
            else:
                # length/distance pair
                length, dist = self._decode_pair(sym)
                chunk = self._copy_window(dist, length)
                self._write_bytes(chunk)
                count += len(chunk)
        return count

    def _decode_pair(self, sym):
        # length
        # tables below LZPair.len_lower etc must be defined
        idx = sym - 257
        extra = self.in_stream.read_bits(LZPair.LEN_BITS[idx])
        length = LZPair.LEN_BASE[idx] + extra
        # distance
        dsym = self._read_symbol(self.dist_codes, self.dist_map)
        extra = self.in_stream.read_bits(LZPair.DIST_BITS[dsym])
        dist  = LZPair.DIST_BASE[dsym] + extra
        return length, dist

    def _read_symbol(self, codes, cmap):
        code = 0
        length = 0
        while True:
            code = (code << 1) | self.in_stream.read_bits(1)
            length += 1
            if length > max(cmap):
                raise ValueError("No matching code")
            if code in cmap.get(length, []):
                return codes.index(code)

    def _build_map(self, codes, lengths):
        cmap = {}
        for sym, length in enumerate(lengths):
            if length > 0:
                cmap.setdefault(length, []).append(codes[sym])
        return cmap

    def _write_bytes(self, data: bytes):
        # update crc and window, write out
        self.crc = binascii.crc32(data, self.crc)
        for b in data:
            self.window.append(b)
        self.out_stream.write(data)

    def _copy_window(self, dist, length):
        buf = []
        for _ in range(length):
            b = self.window[-dist]
            buf.append(b)
            self.window.append(b)
        return bytes(buf)
