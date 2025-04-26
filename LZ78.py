"""LZ78"""

import struct

def lz78_compress(data):
    """
    Compresses a string using the LZ78 algorithm.
    Returns a list of (index, char) pairs.
    """
    dictionary = {}
    result = []
    current = ''
    dict_size = 1

    for char in data:
        next_seq = current + char

        if next_seq in dictionary:
            current = next_seq
        else:
            index = dictionary.get(current, 0)
            result.append((index, char))
            dictionary[next_seq] = dict_size
            dict_size += 1
            current = ''

    if current:
        result.append((dictionary[current], ''))

    return result

def lz78_decompress(pairs):
    """
    Decompresses a list of (index, char) pairs using the LZ78 algorithm.
    Returns the reconstructed string.
    """
    dictionary = {0: ''}
    result = []
    dict_size = 1

    for index, char in pairs:
        entry = dictionary[index] + char
        result.append(entry)
        dictionary[dict_size] = entry
        dict_size += 1

    return ''.join(result)

def compress_file(input_txt, output_bin):
    """
    Reads a UTF-8 text file, compresses its contents using LZ78,
    and writes the compressed data to a binary file.
    """
    with open(input_txt, encoding='utf-8') as f:
        data = f.read()

    pairs = lz78_compress(data)

    with open(output_bin, 'wb') as f:
        for idx, ch in pairs:
            f.write(struct.pack('>I', idx))
            b = ch.encode('utf-8')
            f.write(struct.pack('B', len(b)))
            f.write(b)

def decompress_file(input_bin, output_txt):
    """
    Reads a binary LZ78 stream, decompresses to a string,
    and writes it out as UTF-8 text.
    """
    pairs = []

    with open(input_bin, 'rb') as f:
        data = f.read()
        pos = 0

        while pos < len(data):
            idx = struct.unpack_from('>I', data, pos)[0]
            pos += 4
            length = struct.unpack_from('B', data, pos)[0]
            pos += 1
            b = data[pos:pos + length]
            pos += length
            ch = b.decode('utf-8')
            pairs.append((idx, ch))

    decompressed = lz78_decompress(pairs)

    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(decompressed)

if __name__ == '__main__':
    compress_file('input.txt', 'compressed.bin')
    decompress_file('compressed.bin', 'output.txt')
