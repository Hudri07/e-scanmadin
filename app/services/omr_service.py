import cv2
import numpy as np

def grab_contours(cnts):
    """Menggantikan fungsi imutils.grab_contours."""
    if len(cnts) == 2:
        cnts = cnts[0]
    elif len(cnts) == 3:
        cnts = cnts[1]
    return cnts

def order_points(pts):
    """Mengurutkan 4 titik sudut secara konsisten."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # Top-left
    rect[2] = pts[np.argmax(s)] # Bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # Top-right
    rect[3] = pts[np.argmax(diff)] # Bottom-left
    return rect

def four_point_transform(image, pts):
    """Menggantikan fungsi imutils.perspective.four_point_transform."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

def scan_halaman_omr(image_path):
    # Load & Transform
    image = cv2.imread(image_path)
    if image is None: return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # DETEKSI KERTAS
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = grab_contours((contours, _))
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    docCnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            docCnt = approx
            break

    if docCnt is None: return None

    # Transformasi perspektif
    paper = four_point_transform(image, docCnt.reshape(4, 2))
    paper = cv2.resize(paper, (1000, 1500))
    warped_gray = cv2.cvtColor(paper, cv2.COLOR_BGR2GRAY)
    
    # Thresholding
    thresh = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Konfigurasi Koordinat
    col_x_list = [902, 699, 503, 308, 113]
    start_y, gap_x, gap_y = 313, 25, 107.5
    box_size, block_spacing = 32, 90
    axes = (int((box_size * 0.68) // 2), int((box_size * 2.5) // 2))

    list_jawaban = []

    # Iterasi 5 Kolom x 10 Soal
    for col_idx, start_x_col in enumerate(col_x_list):
        y_fix = [0, 4, 6, 4, 4][col_idx]
        for i in range(10):
            pilihan_scores = []
            y_base = int(start_y + y_fix + (i * gap_y))
            if i >= 5: y_base += block_spacing
                
            for j in range(4):
                x = start_x_col - (j * gap_x)
                center = (x + (box_size // 2), y_base + (box_size // 2))

                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
                mask_result = cv2.bitwise_and(thresh, thresh, mask=mask)
                pilihan_scores.append(cv2.countNonZero(mask_result))

            idx_max = np.argmax(pilihan_scores)
            if pilihan_scores[idx_max] > 120:
                list_jawaban.append(["A", "B", "C", "D"][idx_max])
            else:
                list_jawaban.append("-")

    return list_jawaban