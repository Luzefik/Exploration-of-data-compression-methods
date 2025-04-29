# lz_pair.py

class LZPair:
    """
    Представляє пару (distance, length) для алгоритму DEFLATE:
    - dist: реальне зміщення назад у буфері
    - length: довжина збігу
    Перетворює їх у символи та додаткові біти за RFC 1951.
    """
    # Згенеровані таблиці за RFC 1951 §3.2.5
    LEN_BASE = [0] * 29
    LEN_BITS = [0] * 29
    DIST_BASE = [0] * 30
    DIST_BITS = [0] * 30

    # Ініціалізуємо таблиці один раз при завантаженні модуля
    # LEN_BASE — найменше значення довжини для кожного символу (257…285)
    # LEN_BITS — кількість додаткових бітів для коду довжини
    # DIST_BASE — найменше значення відстані для кожного символу (0…29)
    # DIST_BITS — кількість дод. бітів для коду відстані
    for i in range(0, 8):
        LEN_BASE[i] = 3 + i
        LEN_BITS[i] = 0
    for i in range(8, 28):
        j = (i - 8) % 4
        k = (i - 8) // 4
        base = ((4 + j) << (k + 1)) + 3
        LEN_BASE[i] = base
        LEN_BITS[i] = k + 1
    # коригування по специфікації
    LEN_BASE[28] = 258
    LEN_BITS[28] = 0

    for i in range(0, 4):
        DIST_BASE[i] = 1 + i
        DIST_BITS[i] = 0
    for i in range(4, 30):
        j = (i - 4) % 2
        k = (i - 4) // 2
        base = ((2 + j) << (k + 1)) + 1
        DIST_BASE[i] = base
        DIST_BITS[i] = k + 1

    def __init__(self, dist: int, length: int):
        """
        :param dist: відстань назад у вікні (>=1)
        :param length: довжина збігу (>=3, <=258)
        """
        self.dist = dist
        self.length = length

        # Знаходимо символ довжини (257…285) та extra-біти
        self.lenSymbol = None
        for i in range(29):
            # верхнє значення довжини символу = LEN_BASE[i] + (1<<LEN_BITS[i]) - 1,
            # але явну таблицю верхніх меж можна вивести за LEN_BASE та LEN_BITS
            max_len = (LZPair.LEN_BASE[i] + (1 << LZPair.LEN_BITS[i]) - 1
                       if i < 28 else 258)
            if length >= LZPair.LEN_BASE[i] and length <= max_len:
                self.lenSymbol = 257 + i
                self.lenNumBits = LZPair.LEN_BITS[i]
                self.lenBits = length - LZPair.LEN_BASE[i]
                break

        # Знаходимо символ відстані (0…29) та extra-біти
        self.distSymbol = None
        for i in range(30):
            max_dist = LZPair.DIST_BASE[i] + (1 << LZPair.DIST_BITS[i]) - 1
            if dist >= LZPair.DIST_BASE[i] and dist <= max_dist:
                self.distSymbol = i
                self.distNumBits = LZPair.DIST_BITS[i]
                self.distBits = dist - LZPair.DIST_BASE[i]
                break

        if self.lenSymbol is None or self.distSymbol is None:
            raise ValueError(f"Cannot encode pair (dist={dist}, length={length})")

    def __repr__(self):
        return (f"<LZPair dist={self.dist}→sym{self.distSymbol}"
                f"+bits({self.distBits},{self.distNumBits})  "
                f"len={self.length}→sym{self.lenSymbol}"
                f"+bits({self.lenBits},{self.lenNumBits})>")

if __name__ == "__main__":
    # Друк таблиці символів довжини
    print("LenCode\tExtraBits\tRange")
    for i in range(29):
        lo = LZPair.LEN_BASE[i]
        hi = lo + ((1 << LZPair.LEN_BITS[i]) - 1) if i < 28 else 258
        bits = LZPair.LEN_BITS[i]
        code = 257 + i
        print(f"{code}\t{bits}\t\t{lo}{'-'+str(hi) if hi!=lo else ''}")

    # Друк таблиці символів відстані
    print("\nDistCode\tExtraBits\tRange")
    for i in range(30):
        lo = LZPair.DIST_BASE[i]
        hi = lo + ((1 << LZPair.DIST_BITS[i]) - 1)
        bits = LZPair.DIST_BITS[i]
        print(f"{i}\t\t{bits}\t\t{lo}{'-'+str(hi) if hi!=lo else ''}")
