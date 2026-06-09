from google.colab import files
from google.colab.patches import cv2_imshow

import cv2
import imutils
import numpy as np

from imutils.perspective import four_point_transform
image_path = "/content/WhatsApp Image 2026-05-08 at 09.07.34 (3).jpeg"
image = cv2.imread(image_path)

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
        print("Kertas tidak ditemukan")
        return None

    # PERSPECTIVE TRANSFORM
    paper = four_point_transform(
        image,
        docCnt.reshape(4, 2)
    )

    paper = cv2.resize(
        paper,
        (2000, 2500)
    )

    # =====================
    # KOORDINAT
    # =====================

    nama_y1, nama_y2 = 500, 1828
    nama_x1, nama_x2 = 3, 1000

    nomor_y1, nomor_y2 = 460, 990
    nomor_x1, nomor_x2 = 1820, 1995

    ans_y1, ans_y2 = 1835, 2490
    ans_x1, ans_x2 = 50, 1950

    # =====================
    # PREVIEW AREA
    # =====================

    preview = paper.copy()

    cv2.rectangle(
        preview,
        (nama_x1, nama_y1),
        (nama_x2, nama_y2),
        (0,255,0),
        5
    )

    cv2.rectangle(
        preview,
        (nomor_x1, nomor_y1),
        (nomor_x2, nomor_y2),
        (255,0,0),
        5
    )

    cv2.rectangle(
        preview,
        (ans_x1, ans_y1),
        (ans_x2, ans_y2),
        (0,255,255),
        5
    )

    print("AREA KALIBRASI")
    cv2_imshow(
        cv2.resize(
            preview,
            (700,900)
        )
    )

    # =====================
    # CROP
    # =====================

    nama_crop = paper[
        nama_y1:nama_y2,
        nama_x1:nama_x2
    ]

    nomor_crop = paper[
        nomor_y1:nomor_y2,
        nomor_x1:nomor_x2
    ]

    jawaban_area_crop = paper[
        ans_y1:ans_y2,
        ans_x1:ans_x2
    ]

    print("NAMA CROP")
    cv2_imshow(
        cv2.resize(
            nama_crop,
            (1200,1800)
        )
    )

    print("NOMOR CROP")
    cv2_imshow(nomor_crop)

    print("AREA JAWABAN")
    cv2_imshow(
        cv2.resize(
            jawaban_area_crop,
            (800,300)
        )
    )

    # =====================
    # THRESHOLD NAMA (KEMBALI KE ASLI)
    # =====================
    gray_nama = cv2.cvtColor(nama_crop, cv2.COLOR_BGR2GRAY)
    thresh_nama = cv2.threshold(
        gray_nama, 
        0, 
        255, 
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    # =====================
    # PREVIEW & DETEKSI BUBBLE NAMA 
    # =====================
    nama_preview = nama_crop.copy()
    
    # 1. KEMBALIKAN KE KODE AWAL ANDA YANG SUDAH PAS
    start_x_nama = 18
    start_y_nama = 120
    gap_y_nama = 47     
    radius_nama = 18     
    
    # 2. ARRAY KOORDINAT X MANUAL (Menampung jarak horizontal yang beda-beda ke samping)
    # Jika dihitung dari start_x_nama = 18, ini adalah titik tengah tiap kolom yang fluktuatif
    digit_x_positions_nama = [
        18,  65,  117, 167, 216, 268, 317, 368, 417, 469, 
        521, 569, 619, 670, 719, 769, 819, 870, 921, 972
    ]
    
    huruf_list = [chr(65 + i) for i in range(26)]  # Tepat 26 huruf (A-Z)
    hasil_nama = []

    # jumlah kolom kosong berturut-turut
    kolom_kosong_beruntun = 0

    # berapa kolom kosong dianggap akhir nama
    BATAS_KOSONG = 5

    # Loop menggunakan koordinat X manual yang jaraknya dinamis
    for col_idx, x in enumerate(digit_x_positions_nama):

        if x > nama_crop.shape[1] - 15:
            continue

        skor_huruf_kolom = []

        for row in range(26):

            y = start_y_nama + (row * gap_y_nama)

            if y > nama_crop.shape[0] - 15:
                break

            cv2.circle(
                nama_preview,
                (x, y),
                radius_nama,
                (0, 0, 255),
                2
            )

            mask = np.zeros(
                thresh_nama.shape,
                dtype="uint8"
            )

            cv2.circle(
                mask,
                (x, y),
                radius_nama,
                255,
                -1
            )

            mask_result = cv2.bitwise_and(
                thresh_nama,
                thresh_nama,
                mask=mask
            )

            total_piksel_hitam = cv2.countNonZero(
                mask_result
            )

            skor_huruf_kolom.append(
                total_piksel_hitam
            )

        # ==========================
        # DETEKSI HURUF
        # ==========================
        if len(skor_huruf_kolom) > 0:

            idx_max_nama = np.argmax(
                skor_huruf_kolom
            )

            max_score = skor_huruf_kolom[
                idx_max_nama
            ]

            sorted_scores = sorted(
                skor_huruf_kolom,
                reverse=True
            )

            second_score = (
                sorted_scores[1]
                if len(sorted_scores) > 1
                else 0
            )

            selisih = (
                max_score
                - second_score
            )

            print(
                f"Kolom {col_idx+1}"
                f" | Huruf={huruf_list[idx_max_nama]}"
                f" | Max={max_score}"
                f" | Second={second_score}"
                f" | Selisih={selisih}"
            )

            # ==========================
            # HURUF VALID
            # ==========================
            if (
                max_score > 120
                and selisih > 40
            ):

                huruf_terdeteksi = (
                    huruf_list[idx_max_nama]
                )

                hasil_nama.append(
                    huruf_terdeteksi
                )

                kolom_kosong_beruntun = 0

            # ==========================
            # SPASI / KOSONG
            # ==========================
            else:

                hasil_nama.append(" ")

                kolom_kosong_beruntun += 1

                print(
                    f"Kolom {col_idx+1} dianggap kosong "
                    f"(beruntun={kolom_kosong_beruntun})"
                )

            # ==========================
            # AKHIR NAMA
            # ==========================
            if (
                kolom_kosong_beruntun
                >= BATAS_KOSONG
            ):
                print(
                    "Akhir nama terdeteksi"
                )
                break

    # rapikan spasi ganda
    nama_peserta_final = " ".join(
        "".join(hasil_nama).split()
    )

    print(
        f"\nHasil Ekstraksi Nama: "
        f"{nama_peserta_final}"
    )

    # =====================
    # THRESHOLD JAWABAN
    # =====================

    gray_ans = cv2.cvtColor(
        jawaban_area_crop,
        cv2.COLOR_BGR2GRAY
    )

    thresh_ans = cv2.threshold(
        gray_ans,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    print("THRESHOLD JAWABAN")
    cv2_imshow(
        cv2.resize(
            thresh_ans,
            (1000,400)
        )
    )

    # =====================
    # KONFIG JAWABAN
    # =====================

    start_x = 1788
    start_y = 150
    gap_x = 51
    gap_y = 46
    block_gap_y = 49

    column_x = [
        1788,
        1384,
        993,
        602,
        213
    ]

    radius = 18

    bubble_preview = jawaban_area_crop.copy()

    # =====================
    # DETEKSI JAWABAN
    # =====================

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

            cv2.circle(
                bubble_preview,
                (x,y),
                radius,
                (0,0,255),
                3
            )

            mask = np.zeros(
                thresh_ans.shape,
                dtype="uint8"
            )

            cv2.circle(
                mask,
                (x,y),
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
            hasil = ["A","B","C","D"][idx_max]
        else:
            hasil = "-"

        list_jawaban.append(hasil)

    print("BUBBLE JAWABAN")
    cv2_imshow(
        cv2.resize(
            bubble_preview,
            (1000,600)
        )
    )

    # =====================
    # THRESHOLD NOMOR
    # =====================

    gray_nomor = cv2.cvtColor(
        nomor_crop,
        cv2.COLOR_BGR2GRAY
    )

    thresh_nomor = cv2.threshold(
        gray_nomor,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    print("THRESHOLD NOMOR")
    cv2_imshow(thresh_nomor)

    digit_x_positions = [148, 89, 30]
    digit_start_y = 75
    digit_gap_y = 47
    radius_digit = 18

    nomor_preview = nomor_crop.copy()

    for x in digit_x_positions:
        for angka in range(10):

            y = digit_start_y + (
                angka * digit_gap_y
            )

            cv2.circle(
                nomor_preview,
                (x,y),
                radius_digit,
                (0,0,255),
                2
            )

    print("BUBBLE NOMOR")
    cv2_imshow(
        cv2.resize(
            nomor_preview,
            (300,700)
        )
    )



    # =====================
    # DETEKSI NOMOR
    # =====================

    hasil_nomor = ""

    for x in digit_x_positions:

        angka_score = []

        for angka in range(10):

            y = (
                digit_start_y
                + (angka * digit_gap_y)
            )

            mask = np.zeros(
                thresh_nomor.shape,
                dtype="uint8"
            )

            cv2.circle(
                mask,
                (x,y),
                radius_digit,
                255,
                -1
            )

            masked = cv2.bitwise_and(
                thresh_nomor,
                thresh_nomor,
                mask=mask
            )

            total = cv2.countNonZero(
                masked
            )

            angka_score.append(
                total
            )

        idx = np.argmax(
            angka_score
        )

        if angka_score[idx] > 120:
            hasil_nomor = (
                str(idx)
                + hasil_nomor
            )
        else:
            hasil_nomor = (
                "-"
                + hasil_nomor
            )

    return {
        "jawaban": list_jawaban,
        "nomor": hasil_nomor
    }

hasil = scan_jawaban(image_path)

print("\nHASIL JAWABAN")
print(hasil["jawaban"])

print("\nHASIL NOMOR")
print(hasil["nomor"])