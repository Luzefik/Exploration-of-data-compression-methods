# lz_window.py

from LZ_Pair import LZPair

class LZWindow:
    """
    Реалізує ковзне вікно для LZ77:
    зберігає останні байти в кільцевому буфері,
    дозволяє шукати збіги та копіювати їх.
    """
    MIN_MATCH = 3
    MAX_MATCH = 258

    def __init__(self, size: int):
        """
        :param size: розмір вікна (повинен бути ступенем двійки)
        """
        if size & (size - 1) != 0:
            raise ValueError("Window size must be a power of two")
        self.max_size = size
        self.mask = size - 1
        self.buffer = bytearray(size)
        self.pos = 0      # поточна позиція запису
        self.size = 0     # скільки байт наразі в буфері

    def add(self, data):
        """
        Додає один байт або послідовність байтів у вікно.
        :param data: int (0–255) або bytes/bytearray
        """
        if isinstance(data, int):
            # Додаємо одиничний байт
            self.buffer[self.pos] = data
            self.pos = (self.pos + 1) & self.mask
            if self.size < self.max_size:
                self.size += 1
        else:
            # Додаємо ітерацію байтів
            for b in data:
                self.add(b)

    def find(self, data: bytes, offset: int) -> LZPair | None:
        """
        Шукає найдовший повтор у вікні для data[offset:].
        Повертає LZPair(dist, length) або None, якщо немає збігу ≥ MIN_MATCH.
        """
        if self.size == 0:
            return None

        end = len(data)
        # Ідемо назад по вікну на відстані 1..size
        for dist in range(1, self.size + 1):
            start = (self.pos - dist) & self.mask
            match_len = 0
            x = start
            y = offset
            # рахуємо довжину збігу
            while (match_len < self.MAX_MATCH and
                   y < end and
                   self.buffer[x] == data[y]):
                match_len += 1
                x = (x + 1) & self.mask
                # якщо дійшли до поточної позиції — обертаємося
                if x == self.pos:
                    x = start
                y += 1
            if match_len >= self.MIN_MATCH:
                return LZPair(dist, match_len)
        return None

    def get_bytes(self, dist: int, length: int) -> bytes:
        """
        Витягує з вікна послідовність довжини `length`,
        починаючи `dist` байтів назад від поточної позиції.
        """
        result = bytearray(length)
        start = (self.pos - dist) & self.mask
        x = start
        for i in range(length):
            result[i] = self.buffer[x]
            x = (x + 1) & self.mask
            if x == self.pos:
                x = start
        return bytes(result)

