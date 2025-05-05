from collections import Counter

from bitarray import bitarray


class BitReader:
    """
    A class for reading bits from a file according to the DEFLATE format.
    Provides methods for reading individual bits and multi-bit values in both MSB and LSB order.
    """

    def __init__(self, filename: str) -> None:
        """
        Initialize BitReader by reading the entire file into a bitarray.

        Args:
            filename: Path to the binary file containing the bit stream
        """
        self.bits = bitarray(endian="big")
        with open(filename, "rb") as f:
            self.bits.fromfile(f)
        self.pos = 0

    def read_bit(self) -> int:
        """
        Read one bit from the stream.

        Returns:
            The bit value (0 or 1)

        Raises:
            EOFError: If the bit stream is exhausted
        """
        if self.pos >= len(self.bits):
            raise EOFError("Bit stream length exceeded")
        val = self.bits[self.pos]
        self.pos += 1
        return val

    def read_bits_lsb(self, n: int) -> int:
        """
        Read n bits in LSB-first order and return as an integer.

        Args:
            n: Number of bits to read

        Returns:
            The value as an integer

        Raises:
            EOFError: If there are not enough bits to read
        """
        if self.pos + n > len(self.bits):
            raise EOFError("Not enough bits to read (LSB)")
        val = 0
        for i in range(n):
            bit = self.read_bit()
            val |= bit << i
        return val

    def read_bits_msb(self, n: int) -> int:
        """
        Read n bits in MSB-first order and return as an integer.

        Args:
            n: Number of bits to read

        Returns:
            The value as an integer

        Raises:
            EOFError: If there are not enough bits to read
        """
        if self.pos + n > len(self.bits):
            raise EOFError("Not enough bits to read (MSB)")
        val = 0
        for _ in range(n):
            val = (val << 1) | self.read_bit()
        return val

    def byte_align(self) -> None:
        """
        Move the position to the start of the next byte.
        Used for processing uncompressed blocks (BTYPE=00).
        """
        offset = self.pos % 8
        if offset != 0:
            skip = 8 - offset
            self.pos += skip
