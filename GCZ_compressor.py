import os
import struct
import binascii
import zlib


# GZIP/DEFLATE constants
M_DEFLATE = 8
F_TEXT    = 1
F_HCRC    = 2
F_EXTRA   = 4
F_NAME    = 8
F_COMMENT = 16

class GZCompressor:
    """
    Implements the gzip file format for DEFLATE-compressed streams.
    """
    def __init__(self, file_name: str, show_progress: bool = False):
        self.file_name = file_name
        self.file_size = os.path.getsize(file_name)
        self.show_progress = show_progress
        self.last_percent = -1
        self.log = []

    def update_progress(self, read_bytes: int):
        if self.show_progress:
            percent = read_bytes * 100 // self.file_size
            if percent != self.last_percent:
                print(f"{percent}%")
                self.last_percent = percent

    def compress(self, input_path: str, output_path: str) -> str:
        """
        Compresses input_path into gzip format, writes to output_path.
        Returns log information.
        """
        self.log.clear()
        print(f"Compressing {self.file_name} ({self.file_size} bytes)")

        # Prepare header
        flags = F_NAME
        # MTIME = 0, XFL = 0, OS = 255 (unknown)
        header = bytearray()
        header.extend(b"\x1f\x8b")               # ID1, ID2
        header.append(M_DEFLATE)                     # CM
        header.append(flags)                         # FLG
        header.extend(struct.pack('<I', 0))          # MTIME
        header.append(0)                             # XFL
        header.append(255)                           # OS
        header.extend(self.file_name.encode())       # original filename
        header.append(0)                             # zero terminator

        compressor = zlib.compressobj(
            level=zlib.Z_DEFAULT_COMPRESSION,
            wbits=-zlib.MAX_WBITS
        )

        crc = 0
        total_read = 0

        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            # Write header
            fout.write(header)
            # Compress data in chunks
            while True:
                chunk = fin.read(8192)
                if not chunk:
                    break
                total_read += len(chunk)
                self.update_progress(total_read)
                crc = binascii.crc32(chunk, crc)
                comp = compressor.compress(chunk)
                if comp:
                    fout.write(comp)
            # Flush remaining
            fout.write(compressor.flush())
            # Write CRC32 and ISIZE (little-endian)
            fout.write(struct.pack('<I', crc & 0xffffffff))
            fout.write(struct.pack('<I', total_read & 0xffffffff))

        # Log statistics
        final_size = os.path.getsize(output_path)
        diff = self.file_size - final_size
        ratio = (1 - (final_size / self.file_size)) * 100
        if diff > 0:
            self.log.append(f"Size reduced by {diff} bytes ({ratio:.1f}% total saving)")
        else:
            self.log.append(f"Size increased by {-diff} bytes")

        return '\n'.join(self.log)

    def decompress(self, input_path: str, output_path: str) -> str:
        """
        Decompresses a gzip file at input_path, writes raw output to output_path.
        Returns log information.
        """
        self.log.clear()
        print(f"Decompressing {self.file_name} ({self.file_size} bytes)")

        with open(input_path, 'rb') as fin, open(output_path, 'wb') as fout:
            # Read and validate header
            id1, id2 = fin.read(1), fin.read(1)
            if id1 != b'\x1f' or id2 != b'\x8b':
                raise ValueError("Invalid magic number")
            method = ord(fin.read(1))
            flags = ord(fin.read(1))
            if method != M_DEFLATE:
                raise ValueError("Unsupported compression method")
            if flags & (F_HCRC | F_EXTRA | F_COMMENT):
                raise ValueError("Unsupported flags set in header")
            fin.read(6)  # MTIME, XFL, OS
            if flags & F_NAME:
                # skip original filename
                while True:
                    if fin.read(1) == b'\x00':
                        break

            # Read all remaining data
            data = fin.read()
            if len(data) < 8:
                raise ValueError("Incomplete gzip trailer")
            comp_data = data[:-8]
            crc_expected, isize = struct.unpack('<II', data[-8:])

            # Decompress raw DEFLATE
            decompressor = zlib.decompressobj(wbits=-zlib.MAX_WBITS)
            out_bytes = decompressor.decompress(comp_data)
            fout.write(out_bytes)

        # Verify CRC and size
        crc_actual = binascii.crc32(out_bytes) & 0xffffffff
        size_actual = len(out_bytes)
        if size_actual != isize:
            raise ValueError(f"Size mismatch: expected {isize}, got {size_actual}")
        if crc_actual != crc_expected:
            raise ValueError(f"CRC mismatch: expected {crc_expected:08X}, got {crc_actual:08X}")

        # Log statistics
        diff = size_actual - self.file_size
        ratio = (1 - (self.file_size / size_actual)) * 100 if size_actual else 0
        if diff > 0:
            self.log.append(f"Size increased by {diff} bytes ({ratio:.1f}% space saving)")
        else:
            self.log.append(f"Size reduced by {-diff} bytes")

        return '\n'.join(self.log)
