"""
compression for frames
"""
import os
from algorithms.huffman_coding import HuffmanTree

frames_folder = './res'
compression_folder = './res_compression'
tree = HuffmanTree()

for i, filename in enumerate(os.listdir(frames_folder)):
    file = os.path.join(frames_folder, filename)

    tree.compress_file(
        file,
        os.path.join(compression_folder, f'compressed_{i}.bin'),
        os.path.join(compression_folder, f'compressed_{i}_dict')
        )
