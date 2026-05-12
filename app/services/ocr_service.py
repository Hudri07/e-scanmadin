import cv2
import numpy as np
import os

def preprocessing(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # Resize pakai Lanczos4
    width, height = 1500, 2000
    img_resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
    
    # Bilateral Filter
    denoised = cv2.bilateralFilter(img_resized, 7, 50, 50)

    # LAB Space
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    img_final = cv2.merge((cl, a, b))
    im_final = cv2.cvtColor(img_final, cv2.COLOR_LAB2BGR)

    gaussian = cv2.GaussianBlur(im_final, (0, 0), 2.0)
    # Rumus: Result = Original + (Original - Blurred) * Amount
    im_final = cv2.addWeighted(im_final, 1.5, gaussian, -0.5, 0)

    # Save hasil
    base_name = os.path.splitext(image_path)[0] 
    processed_path = f"{base_name}_v5_final.jpg" 
    
    cv2.imwrite(processed_path, im_final)
    return processed_path