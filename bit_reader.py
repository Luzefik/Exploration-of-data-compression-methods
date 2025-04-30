from collections import Counter  # Додано імпорт Counter

from bitarray import bitarray


class BitReader:
    """
    Клас для зчитування бітів з файлу, згідно з форматом DEFLATE.
    """

    def __init__(self, filename: str):
        """
        Ініціалізує BitReader, читаючи весь файл у bitarray.
        :param filename: шлях до бінарного файлу з бітовим потоком
        """
        self.bits = bitarray(endian="big")
        with open(filename, "rb") as f:
            self.bits.fromfile(f)
        self.pos = 0  # поточна позиція в бітовому потоці

    def read_bit(self) -> int:
        """
        Зчитує один біт і повертає його як 0 або 1.
        """
        if self.pos >= len(self.bits):
            raise EOFError("Перевищено довжину бітового потоку")
        val = self.bits[self.pos]
        self.pos += 1
        return val

    def read_bits(self, n: int) -> int:
        """
        Зчитує n бітів та повертає ціле число.
        Біти читаються від старшого до молодшого (big-endian).
        :param n: кількість біт
        :return: значення як int
        """
        if self.pos + n > len(self.bits):
            raise EOFError("Недостатньо біт для зчитування")
        val = 0
        for _ in range(n):
            val = (val << 1) | self.read_bit()
        return val

    def byte_align(self):
        """
        Переміщує позицію до початку наступного байту (вирівнювання вверх).
        Використовується для обробки uncompressed блоків (BTYPE=00).
        """
        # Якщо вже вирівняно, нічого не робимо
        offset = self.pos % 8
        if offset != 0:
            skip = 8 - offset
            self.pos += skip
