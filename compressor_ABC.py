from abc import ABC, abstractmethod
import io
from typing import BinaryIO, Union, Tuple


class Compressor(ABC):
    """
    Інтерфейс, що описує операції стиснення та розпакування файлів
    з використанням різних алгоритмів.
    """

    @abstractmethod
    def compress(self, input_stream: BinaryIO, output_stream: BinaryIO) -> str:
        """
        Читає серію байтів з вхідного потоку та виконує алгоритм стиснення
        над цими байтами, записуючи стиснені дані у вказаний вихідний потік.

        Args:
            input_stream: Вхідний потік для даних
            output_stream: Вихідний потік для запису стиснених даних

        Returns:
            Рядок з інформацією для логування
        """
        pass

    @abstractmethod
    def decompress(self, input_stream: BinaryIO, output_stream: BinaryIO) -> str:
        """
        Читає серію байтів зі стисненого потоку та виконує алгоритм розпакування
        над цими байтами, записуючи розпаковані дані у вказаний вихідний потік.

        Args:
            input_stream: Вхідний потік для стиснених даних
            output_stream: Вихідний потік для запису розпакованих даних

        Returns:
            Рядок з інформацією для логування
        """
        pass

    @classmethod
    def compress_file(cls, input_file: str, output_file: str) -> str:
        """
        Допоміжний метод для стиснення файлу.

        Args:
            input_file: Шлях до вхідного файлу
            output_file: Шлях до вихідного файлу

        Returns:
            Інформація про стиснення
        """
        compressor = cls()
        with open(input_file, 'rb') as in_file, open(output_file, 'wb') as out_file:
            return compressor.compress(in_file, out_file)

    @classmethod
    def decompress_file(cls, input_file: str, output_file: str) -> str:
        """
        Допоміжний метод для розпакування файлу.

        Args:
            input_file: Шлях до стисненого файлу
            output_file: Шлях до вихідного файлу

        Returns:
            Інформація про розпакування
        """
        compressor = cls()
        with open(input_file, 'rb') as in_file, open(output_file, 'wb') as out_file:
            return compressor.decompress(in_file, out_file)

    @classmethod
    def compress_bytes(cls, data: bytes) -> Tuple[bytes, str]:
        """
        Допоміжний метод для стиснення байтів.

        Args:
            data: Вхідні дані для стиснення

        Returns:
            Кортеж (стиснені дані, інформація про стиснення)
        """
        compressor = cls()
        in_buffer = io.BytesIO(data)
        out_buffer = io.BytesIO()
        log_info = compressor.compress(in_buffer, out_buffer)
        return out_buffer.getvalue(), log_info

    @classmethod
    def decompress_bytes(cls, data: bytes) -> Tuple[bytes, str]:
        """
        Допоміжний метод для розпакування байтів.

        Args:
            data: Стиснені дані для розпакування

        Returns:
            Кортеж (розпаковані дані, інформація про розпакування)
        """
        compressor = cls()
        in_buffer = io.BytesIO(data)
        out_buffer = io.BytesIO()
        log_info = compressor.decompress(in_buffer, out_buffer)
        return out_buffer.getvalue(), log_info