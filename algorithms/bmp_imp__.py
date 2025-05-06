import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import pickle
import os

def dpcm_encoder(img, levels):
    """
    Perform Differential Pulse Code Modulation encoding

    Parameters:
    -----------
    img : numpy.ndarray
        Input image array
    levels : int
        Number of quantization levels

    Returns:
    --------
    quantized_error : numpy.ndarray
        Quantized prediction error
    """
    N = img.shape[0]
    predictor = np.zeros((N, N))
    quantized_error = np.zeros((N, N))

    # We read the image row1, column1, row2, column2, row3, ... because the
    # predictor uses the adjacent elements in the previous row and column
    for i in range(N):
        # Read row i
        for j in range(i, N):
            if i == 0:
                if j == 0:
                    predicted = 0
                else:
                    predicted = 0.95 * predictor[i, j-1]
            else:
                predicted = 0.95 * predictor[i-1, j] + 0.95 * predictor[i, j-1] - 0.95**2 * predictor[i-1, j-1]

            error = img[i, j] - predicted
            quantized_error[i, j] = quantize_error(error, levels)
            predictor[i, j] = predicted + quantized_error[i, j]

        # Read column i
        for j in range(i+1, N):
            if i == 0:
                predicted = 0.95 * predictor[j-1, i]
            else:
                predicted = 0.95 * predictor[j-1, i] + 0.95 * predictor[j, i-1] - 0.95**2 * predictor[j-1, i-1]

            error = img[j, i] - predicted
            quantized_error[j, i] = quantize_error(error, levels)
            predictor[j, i] = predicted + quantized_error[j, i]

    return quantized_error

def quantize_error(error, levels):
    """
    Perform uniform quantization of the error

    Parameters:
    -----------
    error : float
        Prediction error
    levels : int
        Number of quantization levels

    Returns:
    --------
    quantized_error : float
        Quantized error value
    """
    max_val = 255
    min_val = -255

    q = (max_val - min_val) / levels

    i = 1
    while error >= min_val + q * i:
        i += 1

    quantized_error = min_val + q * (i-1) + q/2

    return quantized_error

def dpcm_decoder(error):
    """
    Perform Differential Pulse Code Modulation decoding

    Parameters:
    -----------
    error : numpy.ndarray
        Quantized prediction error

    Returns:
    --------
    img : numpy.ndarray
        Reconstructed image
    """
    N = error.shape[0]
    img = np.zeros((N, N))
    predictor = np.zeros((N, N))

    # We read the image row1, column1, row2, column2, row3, ... because the
    # predictor uses the adjacent elements in the previous row and column
    for i in range(N):
        # Read row i
        for j in range(i, N):
            if i == 0:
                if j == 0:
                    predicted = 0
                else:
                    predicted = 0.95 * predictor[i, j-1]
            else:
                predicted = 0.95 * predictor[i-1, j] + 0.95 * predictor[i, j-1] - 0.95**2 * predictor[i-1, j-1]

            img[i, j] = predicted + error[i, j]
            predictor[i, j] = predicted + error[i, j]

        # Read column i
        for j in range(i+1, N):
            if i == 0:
                predicted = 0.95 * predictor[j-1, i]
            else:
                predicted = 0.95 * predictor[j-1, i] + 0.95 * predictor[j, i-1] - 0.95**2 * predictor[j-1, i-1]

            img[j, i] = predicted + error[j, i]
            predictor[j, i] = predicted + error[j, i]

    return img

def save_compressed_image(error_red, error_green, error_blue, filename):
    """
    Save compressed image data to a file

    Parameters:
    -----------
    error_red, error_green, error_blue : numpy.ndarray
        Quantized prediction errors for each color channel
    filename : str
        Output filename
    """
    compressed_data = {
        'error_red': error_red,
        'error_green': error_green,
        'error_blue': error_blue
    }

    with open(filename, 'wb') as f:
        pickle.dump(compressed_data, f)

def load_compressed_image(filename):
    """
    Load compressed image data from a file

    Parameters:
    -----------
    filename : str
        Input filename

    Returns:
    --------
    error_red, error_green, error_blue : numpy.ndarray
        Quantized prediction errors for each color channel
    """
    with open(filename, 'rb') as f:
        compressed_data = pickle.load(f)

    return compressed_data['error_red'], compressed_data['error_green'], compressed_data['error_blue']

# Example usage
if __name__ == "__main__":
    # Load test image (replace 'lena.jpg' with your image path)
    try:
        input_image = 'SamplePNGImage_10mbmb.png'
        compressed_file = 'compressed_image.pkl'

        lena = np.array(Image.open(input_image))

        # Extract color components
        lena_red = lena[:, :, 0].astype(float)
        lena_green = lena[:, :, 1].astype(float)
        lena_blue = lena[:, :, 2].astype(float)

        # Make sure the image is square (for this implementation)
        N = min(lena_red.shape)
        lena_red = lena_red[:N, :N]
        lena_green = lena_green[:N, :N]
        lena_blue = lena_blue[:N, :N]

        # Display original image
        plt.figure()
        plt.imshow(lena[:N, :N])
        plt.title('Original Image')
        plt.axis('off')

        # Compress and save the image
        qp = 16  # Quantization parameter
        error_red = dpcm_encoder(lena_red, qp)
        error_green = dpcm_encoder(lena_green, qp)
        error_blue = dpcm_encoder(lena_blue, qp)

        # Save compressed data
        save_compressed_image(error_red, error_green, error_blue, compressed_file)
        print(f"Compressed image saved to {compressed_file}")

        # Load and reconstruct the image
        loaded_error_red, loaded_error_green, loaded_error_blue = load_compressed_image(compressed_file)

        recon_red = dpcm_decoder(loaded_error_red)
        recon_green = dpcm_decoder(loaded_error_green)
        recon_blue = dpcm_decoder(loaded_error_blue)

        # Combine three color channels
        recon_color = np.stack((recon_red, recon_green, recon_blue), axis=2)
        recon_color = np.clip(recon_color, 0, 255).astype(np.uint8)

        plt.figure()
        plt.imshow(recon_color)
        plt.title(f'Reconstructed Color Image QP={qp}')
        plt.axis('off')

        # Calculate compression ratio
        original_size = os.path.getsize(input_image)
        compressed_size = os.path.getsize(compressed_file)
        compression_ratio = original_size / compressed_size
        print(f"Compression ratio: {compression_ratio:.2f}x")

        plt.show()

    except FileNotFoundError:
        print("Please provide a valid image path.")