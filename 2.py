import cv2
import numpy as np

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]; rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]; rect[3] = pts[np.argmax(diff)]
    return rect

def get_warped_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            rect = order_points(approx.reshape(4, 2))
            w, h = 1000, 1400
            dst = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(img, M, (w, h))

    print("Deteksi otomatis gagal, menggunakan metode hardcoded crop.")
    h_orig, w_orig = img.shape[:2]
    warped = img[20:h_orig-20, 20:w_orig-20] 
    return cv2.resize(warped, (1000, 1400))

def scan_omr(image_path):
    img = cv2.imread(image_path)
    warped = get_warped_image(img)
    
    # Inisialisasi variabel visualisasi
    final = warped.copy()
    
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # --- SCAN NOMOR PESERTA ---
    col_x_peserta = [535, 561, 615, 641, 693, 719, 747, 775, 825, 878, 905, 933]
    y_digit_peserta = [231, 254, 275, 298, 320, 342, 365, 388, 410, 433]

    nomor_lengkap = ""
    for x in col_x_peserta:
        scores = []
        for y in y_digit_peserta:
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.circle(mask, (int(x), int(y)), 8, 255, -1)
            res = cv2.bitwise_and(thresh, thresh, mask=mask)
            scores.append(cv2.countNonZero(res))
            cv2.circle(final, (int(x), int(y)), 8, (0, 255, 0), 1)
        
        nomor_lengkap += str(np.argmax(scores))
    print(f"Nomor Peserta Terdeteksi: {nomor_lengkap}")

    # --- SCAN JAWABAN ---
    y_coords = [920, 943, 965, 987, 1010, 1054, 1075, 1096, 1119, 1143]
    col_x_jawaban = [872, 693, 519, 344, 170] 
    
    for col_idx, start_x in enumerate(col_x_jawaban):
        for i in range(10):
            nomor_soal = (col_idx * 10) + (i + 1)
            y = y_coords[i]
            pilihan_scores = []
            
            for j in range(4):
                x = start_x - (j * 22)
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.circle(mask, (int(x), int(y)), 8, 255, -1)
                res = cv2.bitwise_and(thresh, thresh, mask=mask)
                pilihan_scores.append(cv2.countNonZero(res))
                cv2.circle(final, (int(x), int(y)), 8, (0, 0, 255), 1)

            if max(pilihan_scores) > 100:
                print(f"Soal {nomor_soal}: {['A', 'B', 'C', 'D'][np.argmax(pilihan_scores)]}")

    cv2.imshow("Hasil Scan", cv2.resize(final, (600, 800)))
    cv2.waitKey(0)

scan_omr("data/uploads/jk_akqidah.jfif")