import cv2

def test_koordinat(image_path):
    img = cv2.imread(image_path)
    start_y = 422
    gap_y = 25

    # Daftar x_pos untuk 12 kolom (isi angka pastinya dari Paint)
    # Contoh: [603, 634, 685, 716, 747, 778, 830, 882, 913, 965, 996, 1027]
    col_x_list = [603, 634, 693, 724, 783, 815, 845, 873, 932, 993, 1021, 1052]
    
    # Berapa banyak baris di tiap kolom?
    row_counts = [3, 7, 10, 10, 10, 10, 10, 10, 3, 10, 10, 10]

    # LOOPING BERDASARKAN KONFIGURASI
    for col_idx, col_x in enumerate(col_x_list):
        num_rows = row_counts[col_idx]
        
        for i in range(num_rows):
            y_pos = start_y + (i * gap_y)
            
            # Gambar lingkaran
            cv2.circle(img, (col_x, y_pos), 9, (0, 0, 255), 2)
            
            # Text debug
            cv2.putText(img, str(i), (col_x + 15, y_pos + 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    roi = img[300:670, 580:1090] 
    cv2.imshow("Cek Semua Kolom", cv2.resize(roi, (800, 500)))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

test_koordinat("data/uploads/JK_akqidah.jfif")