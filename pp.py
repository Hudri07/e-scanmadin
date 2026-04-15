import cv2
import numpy as np

def scan_omr_dinamis(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    h, w = gray.shape
    roi_jawaban = gray[int(h*0.7):h, 0:w] # Potong ambil 30% area bawah saja
    
    # 2. DETEKSI ANCHOR HANYA DI AREA JAWABAN
    _, thresh = cv2.threshold(roi_jawaban, 100, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    anchors = []
    for cnt in contours:
        x, y, w_cnt, h_cnt = cv2.boundingRect(cnt)
        # Filter hanya kotak kecil di area kiri
        if 5 < w_cnt < 25 and 5 < h_cnt < 25 and x < (w * 0.2):
            # Tambahkan offset (h*0.7) karena kita tadi melakukan crop
            anchors.append(y + (h_cnt//2) + int(h*0.7)) 
    
    # Urutkan dan filter agar hanya ada 50 (untuk 50 soal)
    anchors = sorted(list(set(anchors)))
    # Ambil 50 anchor terakhir yang paling bawah
    anchors = anchors[-50:] 
    
    print(f"Anchor terdeteksi di area jawaban: {len(anchors)}")
    # 3. SCAN JAWABAN BERDASARKAN POSISI ANCHOR
    jawaban_dict = {}
    col_x_jawaban = [872, 693, 519, 344, 170] # X tetap
    
    for col_idx, start_x in enumerate(col_x_jawaban):
        for i in range(10):
            idx_anchor = (col_idx * 10) + i
            if idx_anchor < len(anchors):
                y = anchors[idx_anchor] # Y sekarang dinamis mengikuti kertas!
                
                nomor_soal = (col_idx * 10) + (i + 1)
                pilihan_scores = []
                
                for j in range(4):
                    x = start_x - (j * 22)
                    mask = np.zeros(gray.shape, dtype="uint8")
                    cv2.circle(mask, (int(x), int(y)), 8, 255, -1)
                    res = cv2.bitwise_and(thresh, thresh, mask=mask)
                    pilihan_scores.append(cv2.countNonZero(res))
                    
                    # Visualisasi deteksi (Merah untuk area deteksi)
                    cv2.circle(img, (int(x), int(y)), 8, (0, 0, 255), 1)

                # Penentuan jawaban
                if max(pilihan_scores) > 150: 
                    idx = np.argmax(pilihan_scores)
                    jawaban_dict[nomor_soal] = ["A", "B", "C", "D"][idx]
                else:
                    jawaban_dict[nomor_soal] = "-"
    
    # Tampilkan hasil untuk verifikasi
    cv2.imshow("Hasil Deteksi Dinamis", cv2.resize(img, (500, 750)))
    cv2.waitKey(0)
    return jawaban_dict

# Jalankan
scan_omr_dinamis("data/uploads/aqidah2.jpg")