"""
Huffman coding algorithm -
data compression algorithm
"""
import json
import os
import base64
import mmap
import heapq
from collections import defaultdict
from collections import deque
from bitarray import bitarray


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
    def __init__(self, data = None):
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

    def codes_generation(self, node = None, curr_code = ''):
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

        self.codes_generation(node.left, curr_code + '0')
        self.codes_generation(node.right, curr_code + '1')

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
            new_merged_node = Node('', l.val_freq + r.val_freq)
            new_merged_node.left, new_merged_node.right = l, r
            heapq.heappush(nodes, new_merged_node)

        self.root = nodes[0]


    def compress_file(self, input_f: str, output_f="compressed_huffman.bin",\
        output_dict_f='compressed_huffman_dict.json'):
        """
        Function encodes data from given file using Huffman algorithm.

        :param input_f: str, file given by user
        :param output_f: str, file to write encoded data to
        :param output_dict_f: str, file to write encoded data dictionary to
        """
        f_extension = os.path.splitext(input_f)[1]

        with open(input_f, 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
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

        with open(output_dict_f, 'w', encoding='utf-8') as f:
            final_codes = {v: k for k, v in self.res_codes.items()}
            final_data = {
                "file_extension": f_extension,
                "bit_lengths": bit_lengths,
                "codes_dict": {k: base64.b64encode(bytes([v])).decode('ascii') for k, v in final_codes.items()}
            }
            json.dump(final_data, f)

        with open(output_f, 'wb') as f:
            res.tofile(f)

        return output_f

    @staticmethod
    def decompress_file(input_f="compressed_huffman.bin",\
        input_dict_f='compressed_huffman_dict.json'):
        """
        Function decodes data from given files using Huffman algorithm.

        :param input_f: str, file given by user.
        :param input_dict_f: str, file with dictionary given by user.
        :param output_f: str, file to write decoded data to
        """
        with open(input_f, 'rb') as f:
            data = bitarray()
            data.fromfile(f)

        with open(input_dict_f, 'r', encoding='utf-8') as f:
            res_dict = json.load(f)

        real_bits = res_dict['bit_lengths']
        data = data.to01()[:real_bits]
        data = deque(data)
        f_extension = res_dict['file_extension']
        res_dict = {k: int.from_bytes(base64.b64decode(v), 'big') \
        for k, v in res_dict['codes_dict'].items()}


        output_f = f"decompressed{f_extension}"
        decoded_data = []
        curr_code = ''

        while data:
            curr_el = data.popleft()
            curr_code += str(curr_el)
            if curr_code in res_dict:
                decoded_data.append(res_dict[curr_code])
                curr_code = ''

        with open(output_f, 'wb') as f:
            f.write(bytes(decoded_data))
