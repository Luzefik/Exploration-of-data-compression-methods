from bitarray import bitarray


class BitWriter:
    """
    Простий записувач бітів у потік bitarray з вирівнюванням до байта.
    """

    def __init__(self):
        self.bits = bitarray(endian="big")  # endian='big' важливий для tofile()

    def write_bits_msb(self, value: int, length: int):
        """
        Записує length бітів зі значення value (старший біт першим, MSB first).
        Використовується для кодів Хаффмана.
        """
        if length < 0:
            raise ValueError("Довжина не може бути негативною")
        if length == 0:
            return
        # Переконуємось, що value не виходить за межі length біт
        # value &= (1 << length) - 1
        for i in range(length - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def write_bits_lsb(self, value: int, length: int):
        """
        Записує length бітів зі значення value (молодший біт першим, LSB first).
        Використовується для заголовків, дод. бітів та інших полів.
        """
        if length < 0:
            raise ValueError("Довжина не може бути негативною")
        if length == 0:
            return
        # Переконуємось, що value не виходить за межі length біт
        # value &= (1 << length) - 1
        for i in range(length):
            self.bits.append((value >> i) & 1)

    # Можна залишити старий метод як псевдонім для MSB, якщо зручно,
    # або використовувати тільки нові два методи.
    # def write_bits(self, value: int, length: int):
    #     self.write_bits_msb(value, length)

    def flush_to_file(self, filename: str):
        """
        Додає нулі для вирівнювання до байта та записує у файл.
        """
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
        with open(filename, "wb") as f:
            self.bits.tofile(f)

    def get_bitarray(self) -> bitarray:
        """
        Повертає поточний стан бітового масиву (без вирівнювання).
        """
        return self.bits

    def byte_align(self):
        """
        Додає нулі до вирівнювання в байт (без запису в файл).
        """
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
