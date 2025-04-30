"""
Huffman coding algorithm -
data compression algorithm
"""

import heapq
import json
import mmap
import os
from collections import Counter, defaultdict, deque

from bitarray import bitarray

from bit_writer import BitWriter


class Node:
    """
    Class object for Node in Huffman's Tree
    """

    def __init__(self, value, val_freq: int):
        """
        Function initializes the structure of a node.

        :param value: value held by node
        :val_freq: int, the frequency in our data for this value
        """
        self.left = None
        self.right = None
        self.value = value
        self.val_freq = val_freq

    def __lt__(self, val):
        return self.val_freq < val.val_freq


class HuffmanTree:
    """
    Class object for Huffman Tree - main structure used
    in Huffman coding algorithm. Object includes encoding
    and decoding.
    """

    def __init__(self, data=None):
        """
        Function initializes the structure of Huffman Tree.
        """
        self.res_codes = {}
        self.root = None
        if data:
            self.char_frequency_dict = self.char_frequency(data)
            self.nodes = []
            for val, val_freq in self.char_frequency_dict.items():
                self.nodes.append(Node(val, val_freq))

    @classmethod
    def build_from_freq(cls, freq_dict: dict[int, int]) -> "HuffmanTree":
        """
        Статичний конструктор: будує Huffman-дерево із зовнішнього словника частот,
        генерує префіксні коди та повертає інстанс.
        :param freq_dict: словник {symbol: frequency}
        :return: готовий обʼєкт HuffmanTree з заповненими res_codes
        """
        # 1) Створюємо порожній обʼєкт
        tree = cls(data=None)

        # 2) Наповнюємо частоти й вузли
        tree.char_frequency_dict = freq_dict
        tree.nodes = [Node(val, freq) for val, freq in freq_dict.items()]

        # 3) Будуємо дерево
        heapq.heapify(tree.nodes)
        while len(tree.nodes) > 1:
            l = heapq.heappop(tree.nodes)
            r = heapq.heappop(tree.nodes)
            parent = Node(None, l.val_freq + r.val_freq)
            parent.left, parent.right = l, r
            heapq.heappush(tree.nodes, parent)
        tree.root = tree.nodes[0]

        # 4) Генеруємо префіксні коди (res_codes)
        tree.res_codes = {}
        tree.codes_generation()

        return tree

    def make_canonical(self):
        """
        Перетворює self.res_codes (рядкові префіксні коди)
        в канонічні біти+довжини й зберігає у self.canon_codes.
        """
        # 1) Збираємо (symbol, length) пари
        lengths = [(sym, len(code)) for sym, code in self.res_codes.items()]
        # 2) Сортуємо за length asc, а потім за sym asc
        lengths.sort(key=lambda x: (x[1], x[0]))

        canon_codes: dict[int, tuple[int, int]] = {}
        code = 0
        prev_len = lengths[0][1]

        for sym, length in lengths:
            # зсунути вліво, якщо довжина збільшилась
            code <<= length - prev_len
            # призначити код цьому символу
            canon_codes[sym] = (code, length)
            # і перейти до наступного
            code += 1
            prev_len = length

        self.canon_codes = canon_codes

    def char_frequency(self, data) -> dict:
        """
        Function builds dictionary with frequency
        of each symbol for given data.

        :param data: data to count symbol frequency for
        :return: dict, dictionary with symbol frequency
        """
        char_frequency_dict = defaultdict(int)
        for el in data:
            char_frequency_dict[el] += 1

        return char_frequency_dict

    def codes_generation(self, node=None, curr_code=""):
        """
        Recursive function that generates
        code for each symbol, preoder traversal of Huffman's tree

        :param node: node to start traversal from
        :param curr_code: str, current code of a symbol
        """

        # if node is not passed, we start traversal from the root
        if node is None:
            node = self.root

        # if our node is a leaf than we write the code for it
        if node.left is None and node.right is None:
            self.res_codes.setdefault(node.value, curr_code)
            return

        self.codes_generation(node.left, curr_code + "0")
        self.codes_generation(node.right, curr_code + "1")

    def tree(self):
        """
        Function builds Huffman Tree.
        """
        nodes = self.nodes[:]
        heapq.heapify(nodes)
        while len(nodes) != 1:
            # left smallest node
            l = heapq.heappop(nodes)
            # rigth smallest node
            r = heapq.heappop(nodes)

            # creating new merged node from the smallest left and right
            new_merged_node = Node("", l.val_freq + r.val_freq)
            new_merged_node.left, new_merged_node.right = l, r
            heapq.heappush(nodes, new_merged_node)

        self.root = nodes[0]

    def encoding(
        self,
        input_f: str,
        output_f="compressed.bin",
        output_dict_f="compressed_dict.json",
    ):
        """
        Function encodes data from given file using Huffman algorithm.

        :param input_f: str, file given by user
        :param output_f: str, file to write encoded data to
        :param output_dict_f: str, file to write encoded data dictionary to
        """
        f_extension = os.path.splitext(input_f)[1]

        with open(input_f, "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                data = mm[:].decode("utf-8")
            except UnicodeDecodeError:
                data = mm[:]

        if not self.root:
            self.char_frequency_dict = self.char_frequency(data)
            self.nodes = []
            for val, val_freq in self.char_frequency_dict.items():
                self.nodes.append(Node(val, val_freq))
            self.tree()
            self.codes_generation()

        res = bitarray()
        for char in data:
            res.extend(self.res_codes[char])
        bit_lengths = len(res)

        with open(output_dict_f, "w", encoding="utf-8") as f:
            final_codes = defaultdict(str)
            for k, v in self.res_codes.items():
                final_codes[v] = k
            final_data = {
                "file_extension": f_extension,
                "bit_lengths": bit_lengths,
                "codes_dict": final_codes,
            }
            json.dump(final_data, f)

        with open(output_f, "wb") as f:
            res.tofile(f)

    def decoding(self, input_f: str, input_dict_f: str):
        """
        Function decodes data from given files using Huffman algorithm.

        :param input_f: str, file given by user.
        :param input_dict_f: str, file with dictionary given by user.
        :param output_f: str, file to write decoded data to
        """
        with open(input_f, "rb") as f:
            data = bitarray()
            data.fromfile(f)

        with open(input_dict_f, "r", encoding="utf-8") as f:
            res_dict = json.load(f)

        real_bits = res_dict["bit_lengths"]
        data = data.to01()[:real_bits]
        data = deque(data)
        f_extension = res_dict["file_extension"]
        res_dict = res_dict["codes_dict"]
        output_f = f"decompressed{f_extension}"
        decoded_data = []
        curr_code = ""

        while data:
            curr_el = data.popleft()
            curr_code += str(curr_el)
            if curr_code in res_dict:
                decoded_data.append(res_dict[curr_code])
                curr_code = ""

        if f_extension not in [".jpg", ".bin", ".png"]:
            with open(output_f, "w", encoding="utf-8") as f:
                f.write("".join(c for c in decoded_data))
        else:
            with open(output_f, "wb") as f:
                f.write(bytes(decoded_data))
