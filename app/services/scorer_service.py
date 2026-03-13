import json

def hitung_skor(jawaban_siswa, kunci_jawaban):
    if not jawaban_siswa or not kunci_jawaban:
        return 0, 0, 0, [] 

    benar = 0
    perbandingan = []
    total_soal = len(kunci_jawaban)

    for i in range(total_soal):
        j_siswa = str(jawaban_siswa[i]).upper() if i < len(jawaban_siswa) else ""
        j_kunci = str(kunci_jawaban[i]).upper()
        
        is_correct = j_siswa == j_kunci
        if is_correct:
            benar += 1
        
        perbandingan.append({
            "no": i + 1,
            "siswa": j_siswa if j_siswa else "-",
            "kunci": j_kunci,
            "status": "correct" if is_correct else "wrong"
        })

    salah = total_soal - benar
    # Rumus: (Benar / Total Soal) * 100
    nilai = (benar / total_soal) * 100 if total_soal > 0 else 0
    
    return round(nilai, 2), benar, salah, perbandingan