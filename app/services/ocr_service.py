import cv2
import numpy as np
import os

def preprocessing(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # Resize & Contrast Enhancement (CLAHE)
    width, height = 1500, 2000
    img_resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
    lab = cv2.cvtColor(img_resized, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    img_final = cv2.merge((cl, a, b))
    im_final = cv2.cvtColor(img_final, cv2.COLOR_LAB2BGR)

    # Cara aman ganti nama file apapun ekstensinya
    base_name = os.path.splitext(image_path)[0] 
    processed_path = f"{base_name}_cleaned.jpg" # simpan semua jadi .jpg agar Gemini nyaman
    
    cv2.imwrite(processed_path, im_final)
    return processed_path