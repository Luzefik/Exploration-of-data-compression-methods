"""
Utility classes for reading and writing bit streams.
Equivalent to BitInputStream.java and BitOutputStream.java
"""
import struct
from io import BytesIO


class BitInputStream:
    """A utility class for reading bit streams."""

    def __init__(self, in_stream):
        """
        Create a new bit input stream.

        Args:
            in_stream: The input stream
        """
        self.in_stream = in_stream
        self.count = 0
        self.bit_val = 0
        self.bit_pos = 0

    def get_count(self):
        """
        Return the number of bytes read.

        Returns:
            The byte count
        """
        return self.count

    def read(self, b, off=0, length=None):
        """
        Read an array of bytes.

        Args:
            b: The byte array
            off: The starting offset
            length: The number of bytes to read

        Returns:
            The number of bytes read
        """
        if length is None:
            length = len(b) - off

        c = self.in_stream.readinto(memoryview(b)[off:off + length])
        if c > 0:
            self.count += c
        return c

    def read_byte(self):
        """
        Read a single byte.

        Returns:
            The byte value
        """
        b = self.in_stream.read(1)
        if not b:
            raise EOFError("End of file reached")
        self.count += 1
        return b[0]

    def read_short(self):
        """
        Read a two-byte short.

        Returns:
            The short value
        """
        return self.read_byte() | (self.read_byte() << 8)

    def read_int(self):
        """
        Read a four-byte integer.

        Returns:
            The integer value
        """
        return (self.read_byte() |
                (self.read_byte() << 8) |
                (self.read_byte() << 16) |
                (self.read_byte() << 24))

    def read_unsigned_int(self):
        """
        Read a four-byte unsigned integer.

        Returns:
            The long value
        """
        return self.read_int() & 0xffffffff

    def skip_bytes(self, n):
        """
        Skip the next n bytes.

        Args:
            n: The number of bytes to be skipped

        Returns:
            The number of bytes skipped
        """
        skipped = self.in_stream.read(n)
        self.count += len(skipped)
        return len(skipped)

    def read_bits(self, n):
        """
        Read a sequence of bits.

        Args:
            n: The number of bits

        Returns:
            The value
        """
        v = 0
        for m in range(n):
            if self.bit_pos == 0:
                self.bit_val = self.read_byte()
            v |= ((self.bit_val >> self.bit_pos) & 1) << m
            self.bit_pos = (self.bit_pos + 1) & 7
        return v

    def clear_bits(self):
        """Clear the bit queue."""
        self.bit_val = 0
        self.bit_pos = 0


class BitOutputStream:
    """A utility class for writing bit streams."""

    def __init__(self, out_stream):
        """
        Create a new bit output stream.

        Args:
            out_stream: The output stream
        """
        self.out_stream = out_stream
        self.count = 0
        self.bit_val = 0
        self.bit_pos = 0

    def get_count(self):
        """
        Return the number of bytes written.

        Returns:
            The byte count
        """
        return self.count

    def write(self, b, off=0, length=None):
        """
        Write an array of bytes.

        Args:
            b: The byte array
            off: The starting offset
            length: The number of bytes to write
        """
        if length is None:
            length = len(b) - off

        self.out_stream.write(b[off:off + length])
        self.count += length

    def write_byte(self, v):
        """
        Write a single byte.

        Args:
            v: The byte value
        """
        self.out_stream.write(bytes([v & 0xff]))
        self.count += 1

    def write_short(self, v):
        """
        Write a two-byte short.

        Args:
            v: The short value
        """
        self.write_byte(v & 0xff)
        self.write_byte((v >> 8) & 0xff)

    def write_int(self, v):
        """
        Write a four-byte integer.

        Args:
            v: The integer value
        """
        self.write_byte(v & 0xff)
        self.write_byte((v >> 8) & 0xff)
        self.write_byte((v >> 16) & 0xff)
        self.write_byte((v >> 24) & 0xff)

    def write_unsigned_int(self, v):
        """
        Write a four-byte unsigned integer.

        Args:
            v: The long value
        """
        self.write_byte(int(v) & 0xff)
        self.write_byte(int(v >> 8) & 0xff)
        self.write_byte(int(v >> 16) & 0xff)
        self.write_byte(int(v >> 24) & 0xff)

    def write_bits(self, v, n):
        """
        Write the given bit sequence.

        Args:
            v: The value
            n: The number of bits
        """
        for m in range(n):
            self.bit_val |= ((v >> m) & 1) << self.bit_pos
            self.bit_pos += 1
            if self.bit_pos > 7:
                self.write_byte(self.bit_val)
                self.bit_val = 0
                self.bit_pos = 0

    def write_bits_r(self, v, n):
        """
        Write the reverse of the given bit sequence.

        Args:
            v: The value
            n: The number of bits
        """
        for m in range(n - 1, -1, -1):
            self.bit_val |= ((v >> m) & 1) << self.bit_pos
            self.bit_pos += 1
            if self.bit_pos > 7:
                self.write_byte(self.bit_val)
                self.bit_val = 0
                self.bit_pos = 0

    def flush_bits(self):
        """Flush the bit queue."""
        if self.bit_pos > 0:
            self.write_bits(0xff, 8 - self.bit_pos)