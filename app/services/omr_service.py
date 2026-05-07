import cv2
import imutils
import numpy as np

from imutils.perspective import four_point_transform


def scan_jawaban(image_path):

    # LOAD IMAGE
    image = cv2.imread(image_path)

    if image is None:
        return None

    image = imutils.resize(image, width=1200)

    # PREPROCESS
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 30, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    edged = cv2.morphologyEx(
        edged,
        cv2.MORPH_CLOSE,
        kernel
    )

    # FIND PAPER
    cnts = cv2.findContours(
        edged.copy(),
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    cnts = imutils.grab_contours(cnts)
    cnts = sorted(
        cnts,
        key=cv2.contourArea,
        reverse=True
    )

    docCnt = None

    for c in cnts:
        if cv2.contourArea(c) < 100000:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(
            c,
            0.02 * peri,
            True
        )

        if len(approx) == 4:
            docCnt = approx
            break

    if docCnt is None:
        return None

    # PERSPECTIVE TRANSFORM
    paper = four_point_transform(image, docCnt.reshape(4, 2))
    paper = cv2.resize(paper, (2000, 2500))

    # KOORDINAT AREA
    nomor_y1, nomor_y2 = 460, 990
    nomor_x1, nomor_x2 = 1820, 1995

    ans_y1, ans_y2 = 1835, 2490
    ans_x1, ans_x2 = 50, 1950

    # CROP AREA
    nomor_crop = paper[
        nomor_y1:nomor_y2,
        nomor_x1:nomor_x2
    ]

    jawaban_area_crop = paper[
        ans_y1:ans_y2,
        ans_x1:ans_x2
    ]

    # THRESHOLD JAWABAN
    gray_ans = cv2.cvtColor(jawaban_area_crop, cv2.COLOR_BGR2GRAY)
    thresh_ans = cv2.threshold(
        gray_ans,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    # KONFIGURASI JAWABAN
    start_x = 1788
    start_y = 150
    gap_x = 51
    gap_y = 46
    block_gap_y = 49
    column_x = [1788, 1384, 993, 602, 213]
    radius = 18

    # DETEKSI JAWABAN
    list_jawaban = []

    for nomor in range(50):
        col_index = nomor // 10
        local_no = nomor % 10
        base_x = column_x[col_index]

        if local_no < 5:
            y = start_y + (
                local_no * gap_y
            )
        else:
            y = (
                start_y
                + (5 * gap_y)
                + block_gap_y
                + ((local_no - 5) * gap_y)
            )

        pilihan_scores = []

        for j in range(4):
            x = base_x - (
                j * gap_x
            )
            mask = np.zeros(
                thresh_ans.shape,
                dtype="uint8"
            )
            cv2.circle(
                mask,
                (x, y),
                radius,
                255,
                -1
            )
            mask_result = cv2.bitwise_and(
                thresh_ans,
                thresh_ans,
                mask=mask
            )
            pilihan_scores.append(
                cv2.countNonZero(mask_result)
            )

        idx_max = np.argmax(
            pilihan_scores
        )

        if pilihan_scores[idx_max] > 120:
            hasil = ["A", "B", "C", "D"][idx_max]
        else:
            hasil = "-"

        list_jawaban.append(hasil)

    # THRESHOLD NOMOR
    gray_nomor = cv2.cvtColor(nomor_crop, cv2.COLOR_BGR2GRAY)
    thresh_nomor = cv2.threshold(gray_nomor, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # KONFIG NOMOR
    digit_x_positions = [148, 89, 30] 
    digit_start_y = 75
    digit_gap_y = 47
    radius_digit = 18

    # DETEKSI NOMOR
    hasil_nomor = ""

    for x in digit_x_positions:
        angka_score = []

        for angka in range(10):
            y = (digit_start_y + (angka * digit_gap_y))
            mask = np.zeros(thresh_nomor.shape, dtype="uint8")
            cv2.circle(mask, (x, y), radius_digit, 255, -1)
            masked = cv2.bitwise_and(thresh_nomor, thresh_nomor, mask=mask)
            total = cv2.countNonZero(masked)
            angka_score.append(total)

        idx = np.argmax(angka_score)

        if angka_score[idx] > 120:
            hasil_nomor = (str(idx) + hasil_nomor
            )
        else:
            hasil_nomor = "-" + hasil_nomor

    # RETURN
    return {
        "jawaban": list_jawaban,
        "nomor": hasil_nomor
    }