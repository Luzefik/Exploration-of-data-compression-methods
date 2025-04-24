"""
Huffman coding algorithm -
data compression algorithm
"""
from collections import defaultdict

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
        while len(nodes) != 1:
            # sorting nodes, because we always need to extract with the smallest freq
            nodes.sort(key = lambda x: x.val_freq)

            # left smallest node
            l = nodes.pop(0)
            # rigth smallest node
            r = nodes.pop(0)

            # creating new merged node from the smallest left and right
            new_merged_node = Node('', l.val_freq + r.val_freq)
            new_merged_node.left, new_merged_node.right = l, r

            nodes.append(new_merged_node)

        self.root = nodes[0]
