import cv2
import imutils
import numpy as np
import base64
from imutils.perspective import four_point_transform

def scan_jawaban(image_bytes: bytes):
    """
    Memproses OMR, menggambar bulatan hasil bidikan, 
    dan mengembalikan data teks + gambar bukti dalam format Base64.
    """
    # Convert bytes ke OpenCV Image (In-Memory)
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        return None

    image = imutils.resize(image, width=1200)

    # PREPROCESS
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 30, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # FIND PAPER
    cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    docCnt = None
    for c in cnts:
        if cv2.contourArea(c) < 100000:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            docCnt = approx
            break

    if docCnt is None:
        return None

    # PERSPECTIVE TRANSFORM
    paper = four_point_transform(image, docCnt.reshape(4, 2))
    paper = cv2.resize(paper, (1000, 1250)) 

    gambar_bukti = paper.copy()

    # KOORDINAT KROP
    nama_y1, nama_y2 = 250, 914
    nama_x1, nama_x2 = 1, 500
    nomor_y1, nomor_y2 = 230, 495
    nomor_x1, nomor_x2 = 910, 998
    ans_y1, ans_y2 = 918, 1245
    ans_x1, ans_x2 = 25, 975

    # CROP AREA
    nama_crop = paper[nama_y1:nama_y2, nama_x1:nama_x2]
    nomor_crop = paper[nomor_y1:nomor_y2, nomor_x1:nomor_x2]
    jawaban_area_crop = paper[ans_y1:ans_y2, ans_x1:ans_x2]

    
    # DETEKSI NAMA
    gray_nama = cv2.cvtColor(nama_crop, cv2.COLOR_BGR2GRAY)
    thresh_nama = cv2.threshold(gray_nama, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    start_x_nama = 9
    start_y_nama = 60
    gap_y_nama = 23.5     
    radius_nama = 9  

    digit_x_positions_nama = [
        9,  32,  58,  83,  108, 134, 158, 184, 208, 234, 
        260, 285, 310, 335, 360, 385, 410, 435, 460, 486
    ]
    
    huruf_list = [chr(65 + i) for i in range(26)]
    hasil_nama = []
    blank_mask = np.zeros(thresh_nama.shape, dtype="uint8")

    for col_idx, x in enumerate(digit_x_positions_nama):
        if x > nama_crop.shape[1] - 8:
            continue
            
        skor_huruf_kolom = []
        for row in range(26):
            y = int(start_y_nama + (row * gap_y_nama))
            if y > nama_crop.shape[0] - 8:
                break
            
            # Gambar bulatan MERAH langsung di gambar kertas utuh (bukan di hasil crop)
            cv2.circle(gambar_bukti, (x + nama_x1, y + nama_y1), radius_nama, (0, 0, 255), 1)
            
            mask = blank_mask.copy()
            cv2.circle(mask, (x, y), radius_nama, 255, -1)
            mask_result = cv2.bitwise_and(thresh_nama, thresh_nama, mask=mask)
            skor_huruf_kolom.append(cv2.countNonZero(mask_result) * 4) 
            
        if len(skor_huruf_kolom) > 0:
            idx_max_nama = np.argmax(skor_huruf_kolom)
            skor_tertinggi = skor_huruf_kolom[idx_max_nama]
            skor_terendah = np.min(skor_huruf_kolom)
            is_huruf = False
            
            if skor_tertinggi - skor_terendah > 394 and skor_tertinggi > 750:
                is_huruf = True
            elif skor_terendah > 500 and skor_tertinggi - skor_terendah > 350 and skor_tertinggi > 950:
                is_huruf = True
                
            hasil_nama.append(huruf_list[idx_max_nama] if is_huruf else " ")
    
    nama_peserta_final = " ".join("".join(hasil_nama).strip().split())

    # DETEKSI JAWABAN & GAMBAR BULATAN HIJAU
    gray_ans = cv2.cvtColor(jawaban_area_crop, cv2.COLOR_BGR2GRAY)
    thresh_ans = cv2.threshold(gray_ans, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    start_x = 894
    start_y = 75
    gap_x = 25.5
    gap_y = 23
    block_gap_y = 24.5
    column_x = [894, 692, 496, 301, 106]
    radius = 9

    list_jawaban = []
    blank_mask_ans = np.zeros(thresh_ans.shape, dtype="uint8")

    for nomor in range(50):
        col_index = nomor // 10
        local_no = nomor % 10
        base_x = column_x[col_index]

        if local_no < 5:
            y = int(start_y + (local_no * gap_y))
        else:
            y = int(start_y + (5 * gap_y) + block_gap_y + ((local_no - 5) * gap_y))

        pilihan_scores = []
        for j in range(4):
            x = int(base_x - (j * gap_x))
            
            # 🟢 Gambar bulatan HIJAU di gambar kertas utuh (+ ans_x1, + ans_y1)
            cv2.circle(gambar_bukti, (x + ans_x1, y + ans_y1), radius, (0, 255, 0), 1)
            
            mask = blank_mask_ans.copy()
            cv2.circle(mask, (x, y), radius, 255, -1)
            mask_result = cv2.bitwise_and(thresh_ans, thresh_ans, mask=mask)
            pilihan_scores.append(cv2.countNonZero(mask_result))

        idx_max = np.argmax(pilihan_scores)
        list_jawaban.append(["A", "B", "C", "D"][idx_max] if pilihan_scores[idx_max] > 30 else "-")

    # ==================================================
    # DETEKSI NOMOR UJIAN & GAMBAR BULATAN BIRU
    
    gray_nomor = cv2.cvtColor(nomor_crop, cv2.COLOR_BGR2GRAY)
    thresh_nomor = cv2.threshold(gray_nomor, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    digit_x_positions = [77, 47, 17] 
    digit_start_y = 37
    digit_gap_y = 23.5
    radius_digit = 9

    hasil_nomor = ""
    blank_mask_num = np.zeros(thresh_nomor.shape, dtype="uint8")

    for x in digit_x_positions:
        angka_score = []
        for angka in range(10):
            y = int(digit_start_y + (angka * digit_gap_y))
            
            # Gambar bulatan BIRU di gambar kertas utuh (+ nomor_x1, + nomor_y1)
            cv2.circle(gambar_bukti, (x + nomor_x1, y + nomor_y1), radius_digit, (255, 0, 0), 1)
            
            mask = blank_mask_num.copy()
            cv2.circle(mask, (x, y), radius_digit, 255, -1)
            masked = cv2.bitwise_and(thresh_nomor, thresh_nomor, mask=mask)
            angka_score.append(cv2.countNonZero(masked))

        idx = np.argmax(angka_score)
        hasil_nomor = (str(idx) if angka_score[idx] > 30 else "-") + hasil_nomor

    # ENCODE GAMBAR PREVIEW BUKTI KE BASE64
    _, buffer = cv2.imencode('.jpg', gambar_bukti)
    gambar_base64 = base64.b64encode(buffer).decode('utf-8')
    data_uri_gambar = f"data:image/jpeg;base64,{gambar_base64}"

    return {
        "nama": nama_peserta_final,
        "nomor": hasil_nomor,
        "jawaban": list_jawaban,
        "gambar_bukti": data_uri_gambar 
    }