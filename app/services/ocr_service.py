import cv2
import numpy as np
import os

def preprocessing(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Gambar tidak ditemukan.")
        return None
    
    # 1. Original RGB (untuk display)
    img_original_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 2. Resize menggunakan INTER_AREA
    width, height = 1500, 2000
    img_resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
    
    # 3. Grayscale
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    
    # 4. Gaussian Blur(untuk menghilangkan noise serat kertas sebelum thresholding)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 5. Adaptive Thresholding (Mengubah menjadi Hitam-Putih Mutlak/Biner)
    # Block size 21 dan C=10 bisa disesuaikan. Semakin besar C, kertas semakin putih bersih.
    im_final = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 21, 11
    )

    # Save hasil
    base_name = os.path.splitext(image_path)[0] 
    processed_path = f"{base_name}_v5_final.jpg" 
    
    cv2.imwrite(processed_path, im_final)
    return processed_path