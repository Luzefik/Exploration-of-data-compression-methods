from bitarray import bitarray


class BitWriter:
    """
    Простий записувач бітів у потік bitarray з вирівнюванням до байта.
    """

    def __init__(self):
        self.bits = bitarray(endian="big")

    def write_bits(self, value: int, length: int):
        # Записує length бітів зі значення value (старший біт першим)
        for i in range(length - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def flush_to_file(self, filename: str):
        # Додати нулі до вирівнювання в байт
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
        with open(filename, "wb") as f:
            self.bits.tofile(f)
