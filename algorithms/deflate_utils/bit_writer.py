from bitarray import bitarray

class BitWriter:
    """
    A class for writing bits to a bitarray stream with byte alignment support.
    Provides methods for writing bits in both MSB and LSB order.
    """

    def __init__(self) -> None:
        """Initialize a new BitWriter instance with an empty bitarray."""
        self.bits = bitarray(endian="big")

    def write_bits_msb(self, value: int, length: int) -> None:
        """
        Write bits in MSB-first order (most significant bit first).
        Used for Huffman codes.

        Args:
            value: Integer value to write
            length: Number of bits to write

        Raises:
            ValueError: If length is negative
        """
        if length < 0:
            raise ValueError("Length cannot be negative")
        if length == 0:
            return
        for i in range(length - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def write_bits_lsb(self, value: int, length: int) -> None:
        """
        Write bits in LSB-first order (least significant bit first).
        Used for headers, extra bits, and other fields.

        Args:
            value: Integer value to write
            length: Number of bits to write

        Raises:
            ValueError: If length is negative
        """
        if length < 0:
            raise ValueError("Length cannot be negative")
        if length == 0:
            return
        for i in range(length):
            self.bits.append((value >> i) & 1)

    def flush_to_file(self, filename: str) -> None:
        """
        Write the bitarray to a file with byte alignment.

        Args:
            filename: Path to the output file
        """
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
        with open(filename, "wb") as f:
            self.bits.tofile(f)

    def get_bitarray(self) -> bitarray:
        """
        Get the current state of the bit array without alignment.

        Returns:
            The current bit array
        """
        return self.bits

    def byte_align(self) -> None:
        """Add padding bits to achieve byte alignment."""
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
