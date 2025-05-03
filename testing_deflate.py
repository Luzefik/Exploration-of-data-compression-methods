import os
import time
from pathlib import Path

from deflate import Deflate


class TestDeflate:
    def __init__(self):
        self.deflate = Deflate()
        self.test_dir = Path("test")
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)
        self.comparison_dir = self.results_dir / "comparisons"
        self.comparison_dir.mkdir(exist_ok=True)

    def _compare_files(
        self, original_path: Path, decompressed_path: Path, test_name: str
    ):
        """Compare original and decompressed files and save results"""
        comparison_file = self.comparison_dir / f"{test_name}_comparison.txt"

        with open(comparison_file, "w", encoding="utf-8") as f:
            f.write(f"Comparison Results for {test_name}\n")
            f.write("=" * 50 + "\n\n")

            # Basic file info
            f.write("File Information:\n")
            f.write(f"Original size: {os.path.getsize(original_path) / 1024:.2f} KB\n")
            f.write(
                f"Decompressed size: {os.path.getsize(decompressed_path) / 1024:.2f} KB\n\n"
            )

            # Compare first 1000 lines
            f.write("First 1000 lines comparison:\n")
            f.write("-" * 50 + "\n")

            with open(
                original_path, "r", encoding="utf-8", errors="ignore"
            ) as orig, open(
                decompressed_path, "r", encoding="utf-8", errors="ignore"
            ) as decomp:

                for i, (orig_line, decomp_line) in enumerate(zip(orig, decomp)):
                    if i >= 1000:
                        break

                    if orig_line != decomp_line:
                        f.write(f"\nDifference found at line {i+1}:\n")
                        f.write(f"Original: {orig_line.strip()}\n")
                        f.write(f"Decompressed: {decomp_line.strip()}\n")
                        f.write("-" * 30 + "\n")
                    elif i < 5:  # Show first 5 matching lines
                        f.write(f"Line {i+1} matches: {orig_line.strip()}\n")

                # Check if one file has more lines than the other
                orig_remaining = sum(1 for _ in orig)
                decomp_remaining = sum(1 for _ in decomp)

                if orig_remaining > 0 or decomp_remaining > 0:
                    f.write(f"\nAdditional lines in original: {orig_remaining}\n")
                    f.write(f"Additional lines in decompressed: {decomp_remaining}\n")

            # Add hash comparison
            orig_hash = self._calculate_file_hash(original_path)
            decomp_hash = self._calculate_file_hash(decompressed_path)

            f.write("\nHash Comparison:\n")
            f.write(f"Original SHA-256: {orig_hash}\n")
            f.write(f"Decompressed SHA-256: {decomp_hash}\n")
            f.write(f"Files match: {orig_hash == decomp_hash}\n")

    def run_test(self, input_file: str, verbose: bool = False):
        """Run compression and decompression test on a single file"""
        input_path = self.test_dir / input_file
        compressed_path = self.results_dir / f"{input_file}.deflate"
        decompressed_path = self.results_dir / f"decompressed_{input_file}"

        print(f"\nTesting file: {input_file}")
        print(f"Original size: {os.path.getsize(input_path) / 1024:.2f} KB")

        # Compression
        start_time = time.time()
        self.deflate.compress_file(
            str(input_path), output_file=str(compressed_path), verbose=verbose, bfinal=1
        )
        compress_time = time.time() - start_time
        compressed_size = os.path.getsize(compressed_path)
        compression_ratio = (1 - compressed_size / os.path.getsize(input_path)) * 100

        print(f"Compressed size: {compressed_size / 1024:.2f} KB")
        print(f"Compression ratio: {compression_ratio:.2f}%")
        print(f"Compression time: {compress_time:.2f} seconds")

        # Decompression
        start_time = time.time()
        self.deflate.decompress_file(
            str(compressed_path), output_file=str(decompressed_path), verbose=verbose
        )
        decompress_time = time.time() - start_time

        print(f"Decompression time: {decompress_time:.2f} seconds")

        # Compare files and save results
        self._compare_files(input_path, decompressed_path, input_file)

        # Verify file integrity
        original_hash = self._calculate_file_hash(input_path)
        decompressed_hash = self._calculate_file_hash(decompressed_path)
        success = original_hash == decompressed_hash

        if success:
            print("✅ Test passed: Files match")
        else:
            print("❌ Test failed: Files don't match")
            print(
                f"See comparison results in: {self.comparison_dir / f'{input_file}_comparison.txt'}"
            )

        return {
            "file": input_file,
            "original_size": os.path.getsize(input_path),
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "compress_time": compress_time,
            "decompress_time": decompress_time,
            "success": success,
        }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        import hashlib

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def run_all_tests(self, verbose: bool = False):
        """Run tests on different file types"""
        test_files = {
            "Text files": [
                "pidmohylnyy-valerian-petrovych-misto76.txt",
                "biblija.txt",
                "CSB_Pew_Bible_2nd_Printing.txt"
            ],
            "CSV files": [
                "customers-100000.csv",
            ],
            "JSON files": [
                "large-file.json"
            ]
        }

        results = []
        for category, files in test_files.items():
            print(f"\n{'='*50}")
            print(f"Testing {category}")
            print(f"{'='*50}")

            for file in files:
                if (self.test_dir / file).exists():
                    result = self.run_test(file, verbose)
                    results.append(result)
                else:
                    print(f"File not found: {file}")

        # Print summary
        print("\nTest Summary:")
        print("=" * 50)
        for result in results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['file']}:")
            print(f"  Original: {result['original_size']/1024:.2f} KB")
            print(f"  Compressed: {result['compressed_size']/1024:.2f} KB")
            print(f"  Ratio: {result['compression_ratio']:.2f}%")
            print(f"  Compress time: {result['compress_time']:.2f}s")
            print(f"  Decompress time: {result['decompress_time']:.2f}s")
            if not result["success"]:
                print(
                    f"  Comparison file: {self.comparison_dir / f'{result['file']}_comparison.txt'}"
                )
            print("-" * 50)


if __name__ == "__main__":
    tester = TestDeflate()
    tester.run_all_tests(verbose=False)
