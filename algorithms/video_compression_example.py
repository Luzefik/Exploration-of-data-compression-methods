import os

import cv2


# Функція для витягання кадрів з відео
def extract_frames(video_path, output_folder="frames"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Не вдалося відкрити відео. Перевір шлях або формат.")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Загальна кількість кадрів: {total_frames}")

    for i in range(total_frames):
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"{output_folder}/frame_{i:04d}.bmp", frame)

    cap.release()
    print(f"[✓] Витягнуто {total_frames} кадрів до папки {output_folder}/")


# Алгоритм стиснення LZW
def lzw_compress(data):
    dictionary = {bytes([i]): i for i in range(256)}
    current_code = 256
    result = []
    w = bytes()

    for byte in data:
        wc = w + bytes([byte])
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            if current_code < 4096:
                dictionary[wc] = current_code
                current_code += 1
            w = bytes([byte])

    if w:
        result.append(dictionary[w])

    return result


# Функція для стиснення всіх кадрів
def compress_all_frames(folder="frames"):
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".bmp"):
            with open(os.path.join(folder, fname), "rb") as f:
                data = f.read()

            compressed = lzw_compress(data)

            with open(os.path.join(folder, fname + ".lzw"), "wb") as f:
                for code in compressed:
                    # Записуємо код в 3 байти
                    f.write(code.to_bytes(3, "big"))

    print("[✓] Всі кадри стиснуті за допомогою LZW.")


# Функція для декомпресії LZW
def decompress_all_frames(folder="frames"):
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".lzw"):
            with open(os.path.join(folder, fname), "rb") as f:
                data = f.read()

            # Розбити на коди по 3 байти
            codes = [
                int.from_bytes(data[i : i + 3], "big") for i in range(0, len(data), 3)
            ]

            # LZW декомпресія
            dictionary = {i: bytes([i]) for i in range(256)}
            result = bytearray()

            prev_code = codes[0]
            result += dictionary[prev_code]
            next_code = 256

            for code in codes[1:]:
                if code in dictionary:
                    entry = dictionary[code]
                elif code == next_code:
                    entry = dictionary[prev_code] + dictionary[prev_code][:1]
                else:
                    raise ValueError("Bad LZW code")

                result += entry
                dictionary[next_code] = dictionary[prev_code] + entry[:1]
                next_code += 1
                prev_code = code

            # Зберегти відновлені кадри як .bmp
            out_name = fname.replace(".bmp.lzw", ".bmp").replace(".lzw", "")
            with open(os.path.join(folder, "decompressed_" + out_name), "wb") as f:
                f.write(result)

    print("[✓] Всі .lzw файли розпаковані до .bmp")


# Функція для відновлення відео з кадрів
def recreate_video_from_frames(
    input_folder="frames",
    output_video="output_video.mp4",
    fps=30,
    resolution=(1920, 1080),
):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video, fourcc, fps, resolution)

    for fname in sorted(os.listdir(input_folder)):
        if fname.endswith(".bmp"):
            img = cv2.imread(os.path.join(input_folder, fname))
            out.write(img)

    out.release()
    print(f"[✓] Відео відновлене до {output_video}")


# Основна частина коду
if __name__ == "__main__":
    video_path = "example.mp4"  # Шлях до відео
    frames_folder = "frames"  # Папка для кадрів

    # 1. Витягуємо кадри з відео
    extract_frames(video_path, frames_folder)

    # 2. Стискаємо кадри
    compress_all_frames(frames_folder)

    # 3. Розпаковуємо стиснуті кадри
    decompress_all_frames(frames_folder)

    # 4. Відновлюємо відео з розпакованих кадрів
    recreate_video_from_frames(
        input_folder=frames_folder,
        output_video="restored_video.mp4",
        fps=30,
        resolution=(1920, 1080),
    )
