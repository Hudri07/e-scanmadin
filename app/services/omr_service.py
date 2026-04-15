import cv2
import numpy as np
import imutils
from imutils.perspective import four_point_transform

def scan_jawaban(image_path):
    # Load image
    image = cv2.imread(image_path)

    if image is None:
        return None

    # Preprocessing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # DETEKSI KERTAS
    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    docCnt = None

    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            docCnt = approx
            break

    if docCnt is None:
        return None

    # Perspective transform
    paper = four_point_transform(image, docCnt.reshape(4, 2))
    paper = cv2.resize(paper, (1000, 1500))

    warped_gray = cv2.cvtColor(paper, cv2.COLOR_BGR2GRAY)

    # Threshold (bulatan hitam jadi putih)
    thresh = cv2.threshold(
        warped_gray,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    # Konfigurasi Koordinat (hasil kalibrasi)
    col_x_list = [902, 699, 503, 308, 113]
    start_y = 313
    gap_x = 25
    gap_y = 107.5
    box_size = 32
    block_spacing = 90

    axes = (
        int((box_size * 0.68) // 2),
        int((box_size * 2.5) // 2)
    )

    list_jawaban = []

    # Iterasi 5 Kolom x 10 Soal
    for col_idx, start_x_col in enumerate(col_x_list):
        y_fix = [0, 4, 6, 4, 4][col_idx]
        for i in range(10):
            pilihan_scores = []
            y_base = int(start_y + y_fix + (i * gap_y))
            if i >= 5:
                y_base += block_spacing
            for j in range(4):
                x = start_x_col - (j * gap_x)
                center = (
                    x + (box_size // 2),
                    y_base + (box_size // 2)
                )
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.ellipse(
                    mask,
                    center,
                    axes,
                    0,
                    0,
                    360,
                    255,
                    -1
                )
                mask_result = cv2.bitwise_and(
                    thresh,
                    thresh,
                    mask=mask
                )
                pilihan_scores.append(
                    cv2.countNonZero(mask_result)
                )
            # Penentuan jawaban
            idx_max = np.argmax(pilihan_scores)

            if pilihan_scores[idx_max] > 120:
                list_jawaban.append(["A", "B", "C", "D"][idx_max])
            else:
                list_jawaban.append("-")

    return list_jawaban