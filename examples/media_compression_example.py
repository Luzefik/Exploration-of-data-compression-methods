"""
Example script demonstrating media compression using DPCM + other algorithms.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from algorithms.media_compression import MediaCompressor

def main():
    # Create compressor instance
    compressor = MediaCompressor()

    # Example 1: Compress BMP image
    bmp_input = "input.bmp"
    bmp_output = "compressed_bmp.bin"

    if os.path.exists(bmp_input):
        print(f"\nCompressing BMP image: {bmp_input}")

        # Try different compression methods
        methods = ["dpcm+rle", "dpcm+huffman", "dpcm+deflate"]
        for method in methods:
            output = f"{bmp_output}.{method}"
            print(f"\nUsing method: {method}")

            # Compress
            compressor.compress_bmp(
                input_path=bmp_input,
                output_path=output,
                method=method,
                verbose=True
            )

            # Get compression ratio
            original_size = os.path.getsize(bmp_input)
            compressed_size = os.path.getsize(output)
            ratio = original_size / compressed_size

            print(f"Original size: {original_size} bytes")
            print(f"Compressed size: {compressed_size} bytes")
            print(f"Compression ratio: {ratio:.2f}x")

            # Decompress
            decompressed = f"decompressed_{method}.bmp"
            compressor.decompress_bmp(
                input_path=output,
                output_path=decompressed,
                method=method,
                verbose=True
            )

            # Clean up
            os.remove(output)
            if method == "dpcm+huffman":
                os.remove(f"{output}.dict")

    # Example 2: Compress WAV audio
    wav_input = "input.wav"
    wav_output = "compressed_wav.bin"

    if os.path.exists(wav_input):
        print(f"\nCompressing WAV audio: {wav_input}")

        # Try different compression methods
        methods = ["dpcm+rle", "dpcm+huffman", "dpcm+deflate"]
        for method in methods:
            output = f"{wav_output}.{method}"
            print(f"\nUsing method: {method}")

            # Compress
            compressor.compress_wav(
                input_path=wav_input,
                output_path=output,
                method=method,
                verbose=True
            )

            # Get compression ratio
            original_size = os.path.getsize(wav_input)
            compressed_size = os.path.getsize(output)
            ratio = original_size / compressed_size

            print(f"Original size: {original_size} bytes")
            print(f"Compressed size: {compressed_size} bytes")
            print(f"Compression ratio: {ratio:.2f}x")

            # Decompress
            decompressed = f"decompressed_{method}.wav"
            compressor.decompress_wav(
                input_path=output,
                output_path=decompressed,
                original_wav_path=wav_input,
                method=method,
                verbose=True
            )

            # Clean up
            os.remove(output)
            if method == "dpcm+huffman":
                os.remove(f"{output}.dict")

if __name__ == "__main__":
    main()