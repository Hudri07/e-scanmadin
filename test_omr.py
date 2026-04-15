import cv2
import numpy as np

# Fungsi bantu transformasi (tetap dipakai agar kertas tegak lurus)
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]; rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]; rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl); widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br); heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

def find_four_anchors(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 74, 255, cv2.THRESH_BINARY_INV)[1]

    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Kumpulkan semua calon anchor
    candidates = []
    h, w = img.shape[:2]
    
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area = cv2.contourArea(c)
        
        # Filter: harus 4 titik, luas masuk akal, dan rasio mendekati kotak
        x, y, rect_w, rect_h = cv2.boundingRect(c)
        ratio = float(rect_w) / rect_h
        if len(approx) == 4 and 500 < area < 4000 and 0.5 < ratio < 1:
            cX, cY = x + rect_w//8, y + rect_h//8
            candidates.append([cX, cY])

    # LOGIKA PENTING: Pilih 4 yang paling mendekati sudut gambar
    if len(candidates) >= 4:
        # Urutkan berdasarkan jarak ke sudut (0,0), (w,0), (0,h), (w,h)
        # Atau cara termudah: ambil 4 yang paling mewakili kuadran
        candidates = np.array(candidates)
        # Di sini Anda bisa menyortir agar hanya mengambil yang paling pojok
        return candidates # Untuk testing, kembalikan semua dulu untuk melihat mana yang terdeteksi
    
    return None

def scan_omr_full_page(image_path):
    # 1. Load Gambar
    img = cv2.imread(image_path)

    pts = find_four_anchors(img)

    if pts is not None:
        img = four_point_transform(img, pts)

    if img is None:
        print("Error: Gambar tidak ditemukan.")
        return

    # 2. Crop header atas (160px) untuk membuang area kosong
    h_orig, w_orig = img.shape[:2]
    img = img[160:h_orig, 0:w_orig] 
    
    # 3. Resize Proporsional (Penting agar tidak terpotong)
    target_width = 1000
    aspect_ratio = img.shape[0] / img.shape[1]
    target_height = int(target_width * aspect_ratio)
    final = cv2.resize(img, (target_width, target_height))
    
    gray = cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # --- A. SCAN NOMOR PESERTA ---
    col_x_list = [535, 561, 615, 641, 693, 719, 747, 775, 825, 878, 905, 933]
    y_digit_list = [231, 254, 275, 298, 320, 342, 365, 388, 410, 433]
    
    THRESHOLD_HITAM= 100

    # Digit maps untuk membatasi opsi angka per kolom
    digit_maps = [
        [0, 1, 2], [0, 1, 2, 3, 4, 5, 6],
        list(range(10)), list(range(10)), list(range(10)),
        list(range(10)), list(range(10)), list(range(10)),
        [1, 2, 3],
        list(range(10)), list(range(10)), list(range(10))
    ]

    nomor_lengkap = ""
    for col_idx, x in enumerate(col_x_list):

        if col_idx in [2,4,8,9]:
            nomor_lengkap+="-"

        scores = []
        
        for digit in range(len(digit_maps[col_idx])):
            y = y_digit_list[digit] # Ambil Y berdasarkan angka yang diizinkan saja
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.circle(mask, (int(x), int(y)), 8, 255, -1)
            res = cv2.bitwise_and(thresh, thresh, mask=mask)
            scores.append(cv2.countNonZero(res))
            
            # Visualisasi
            cv2.circle(final, (int(x), int(y)), 8, (0, 255, 0), 1)
        
        # Ambil indeks digit dengan skor tertinggi HANYA dari yang diizinkan
        digit_detected = np.argmax(scores)
        nomor_lengkap += str(digit_maps[col_idx][digit_detected]) if scores[digit_detected]>THRESHOLD_HITAM else "0"

    # --- B. SCAN JAWABAN (1-50) ---
    # Koordinat Y untuk 10 baris jawaban per kolom
    y_coords = [920, 943, 965, 987, 1010, 1054, 1075, 1096, 1119, 1143]
    col_x_jawaban = [872, 693, 519, 344, 170] 
    
    jawaban_dict = {}
    for col_idx, start_x in enumerate(col_x_jawaban):
        for i in range(10):
            nomor_soal = (col_idx * 10) + (i + 1)
            y = y_coords[i]
            pilihan_scores = []
            
            for j in range(4):
                # x dikurangi (j*n) untuk menggeser ke opsi A, B, C, D
                x = start_x - (j * 22)
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.circle(mask, (int(x), int(y)), 8,  255, -1)
                res = cv2.bitwise_and(thresh, thresh, mask=mask)
                pilihan_scores.append(cv2.countNonZero(res))
                
                # Visualisasi 
                cv2.circle(final, (int(x), int(y)), 8, (0, 0, 255), 1)

            if max(pilihan_scores) > 150: 
                idx = np.argmax(pilihan_scores)
                jawaban_dict[nomor_soal] = ["A", "B", "C", "D"][idx]
            else:
                jawaban_dict[nomor_soal] = "-"

    # Output
    print(f"Nomor Peserta: {nomor_lengkap}")
    print(f"Hasil Jawaban: {jawaban_dict}")
    
    # Tampilkan hasil
    cv2.imshow("DEBUG FINAL", cv2.resize(final, (800, 580)))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Jalankan fungsi
scan_omr_full_page("data/uploads/jk_akqidah.jfif")