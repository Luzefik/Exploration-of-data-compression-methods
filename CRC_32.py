from typing import Union


class CRC32:
    """
    Реалізує 32-бітну перевірку циклічним надлишковим кодом (CRC-32).

    CRC-32 використовується для перевірки цілісності даних у багатьох форматах
    стиснення, включаючи ZIP та формати на основі алгоритму deflate.
    """

    # Попередньо обчислена таблиця CRC для всіх 8-бітних повідомлень
    CRC_TABLE = [0] * 256

    # Ініціалізація таблиці CRC
    for n in range(256):
        c = n
        for _ in range(8):
            if (c & 1) == 1:
                c = (c >> 1) ^ 0xedb88320
            else:
                c >>= 1
        CRC_TABLE[n] = c

    def __init__(self):
        """Створює новий об'єкт перевірки CRC-32."""
        self.crc = 0xffffffff

    def get_value(self) -> int:
        """
        Повертає поточне значення контрольної суми.

        Returns:
            Поточне значення CRC-32
        """
        return ~self.crc & 0xffffffff

    def update(self, b: Union[int, bytes, bytearray], off: int = 0, length: int = None) -> None:
        """
        Оновлює поточну контрольну суму заданими байтами.

        Args:
            b: Байт або масив байтів
            off: Початковий зсув для масиву (ігнорується для одиночного байту)
            length: Кількість байтів для обробки (за замовчуванням - вся довжина масиву)
        """
        if isinstance(b, (bytes, bytearray)):
            if length is None:
                length = len(b) - off

            for i in range(off, off + length):
                self.crc = ((self.crc >> 8) ^
                           self.CRC_TABLE[(self.crc ^ b[i]) & 0xff])
        else:
            # Випадок для одиночного байту
            self.crc = ((self.crc >> 8) ^
                       self.CRC_TABLE[(self.crc ^ b) & 0xff])

    @classmethod
    def calculate(cls, data: Union[bytes, bytearray]) -> int:
        """
        Обчислює CRC-32 для заданих даних.

        Args:
            data: Дані для обчислення контрольної суми

        Returns:
            Значення CRC-32
        """
        crc = cls()
        crc.update(data)
        return crc.get_value()


# Демонстрація використання
if __name__ == "__main__":
    test_data = b"123456789"  # Тестовий рядок для перевірки CRC-32

    # Результат CRC-32 для тестового рядка повинен бути 0xCBF43926
    crc = CRC32()
    crc.update(test_data)
    result = crc.get_value()

    print(f"CRC-32 для '{test_data.decode()}': 0x{result:08X}")
    assert result == 0xCBF43926, "Неправильне значення CRC-32!"

    # Обчислення за допомогою класового методу
    quick_result = CRC32.calculate(test_data)
    print(f"Швидке обчислення CRC-32: 0x{quick_result:08X}")
    assert quick_result == 0xCBF43926, "Неправильне швидке значення CRC-32!"