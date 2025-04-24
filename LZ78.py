"""LZ78"""

def lz78_compress(data):
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
    dictionary = {0: ''}
    result = []
    dict_size = 1

    for index, char in pairs:
        entry = dictionary[index] + char
        result.append(entry)
        dictionary[dict_size] = entry
        dict_size += 1

    return ''.join(result)

if __name__ == '__main__':
    text = 'abacabacabadaca'
    compressed = lz78_compress(text)
    decompressed = lz78_decompress(compressed)

    print(f'Original text: {text}')
    print(f'Compressed: {compressed}')
    print(f'Decompressed: {decompressed}')
