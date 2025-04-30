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

    def read_bits_lsb(self, n: int) -> int:
        """
        Зчитує n бітів та повертає ціле число.
        Біти читаються від молодшого до старшого (LSB first).
        :param n: кількість біт
        :return: значення як int
        """
        if self.pos + n > len(self.bits):
            raise EOFError("Недостатньо біт для зчитування (LSB)")
        val = 0
        for i in range(n):
            bit = self.read_bit()  # read_bit читає наступний доступний біт
            val |= bit << i  # Зсуваємо прочитаний біт на відповідну позицію
            # і додаємо до результату
        return val

    # Ваш існуючий метод для MSB first (можливо, перейменувати для ясності)
    def read_bits_msb(self, n: int) -> int:
        """
        Зчитує n бітів та повертає ціле число.
        Біти читаються від старшого до молодшого (MSB first).
        :param n: кількість біт
        :return: значення як int
        """
        if self.pos + n > len(self.bits):
            raise EOFError("Недостатньо біт для зчитування (MSB)")
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
