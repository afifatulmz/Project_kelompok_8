import warnings
warnings.filterwarnings("ignore", category=UserWarning) #pandasny maunya sama sqlalchemy
import psycopg2
import pandas as pd
from datetime import datetime

#Buat connect ke database
def connectDB():
    try:
        conn = psycopg2.connect(host="localhost", user="postgres", password="baru123", dbname="Projekan")
        cur = conn.cursor()
        print('koneksi berhasil')
        return conn, cur
    except Exception as e:
        print('koneksi gagal, silahkan perbaiki!', e)
        return None, None
 
def get_connection():
    """Membuat koneksi ke database PostgreSQL"""
    result = connectDB()
    if result:
        return result[0]  #Return connection aja
    return None

def get_petani_id(username):
    """
    Mendapatkan id_users untuk username yang sudah terdaftar.
    Jika username tidak ditemukan, mengembalikan None (tanpa membuat user otomatis).
    """
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_users FROM users WHERE username = %s", (username,))
        res = cursor.fetchone()
        
        if res:
            return res[0]
        else:
            return None 
            
    except Exception as e:
        print(f"Error get petani ID: {e}")
        return None
    finally:
        # Pastikan koneksi ditutup
        cursor.close()
        conn.close()

def get_petani_lahan_ids(id_petani):
    """Mendapatkan semua ID lahan milik petani (users.id_users)"""
    conn = get_connection()
    if not conn:
        return []
    try:
        query = "SELECT id_lahan FROM lahan WHERE id_users = %s"
        df = pd.read_sql(query, conn, params=(id_petani,))
        return df['id_lahan'].tolist()
    except Exception as e:
        print(f"Error get lahan IDs: {e}")
        return []
    finally:
        conn.close()


#Evaluasi otomatis
def buat_evaluasi_otomatis(id_pemeriksaan, tinggi, warna, lebar, tekstur, lembab, kadar):
    # Konversi input
    try:
        tinggi_val = float(tinggi)
        lebar_val = float(lebar)
        lembab_val = float(lembab) if lembab not in [None, ""] else 0
        kadar_val = float(kadar)
    except:
        tinggi_val = lebar_val = lembab_val = kadar_val = 0

    skor = 0
    catatan_detail = []

    # 1. Tinggi (30)
    if 80 <= tinggi_val <= 120:
        skor += 30; catatan_detail.append("✓ Tinggi optimal")
    elif 50 <= tinggi_val < 80:
        skor += 20; catatan_detail.append("⚠ Tinggi kurang optimal, pertimbangkan pemupukan")
    elif tinggi_val > 120:
        skor += 15; catatan_detail.append("⚠ Tinggi berlebih, waspadai kerebahan")
    else:
        skor += 5; catatan_detail.append("✗ Tinggi terlalu rendah, periksa nutrisi tanah")

    # 2. Lebar daun (25)
    if 30 <= lebar_val <= 60:
        skor += 25; catatan_detail.append("✓ Lebar daun sempurna")
    elif 20 <= lebar_val < 30:
        skor += 15; catatan_detail.append("⚠ Daun agak kecil")
    else:
        skor += 5; catatan_detail.append("✗ Lebar daun tidak ideal")

    # 3. Kelembapan (20)
    if 50 <= lembab_val <= 70:
        skor += 20; catatan_detail.append("✓ Kelembapan ideal")
    elif 40 <= lembab_val < 50 or 70 < lembab_val <= 80:
        skor += 12; catatan_detail.append("⚠ Kelembapan perlu dipantau")
    else:
        skor += 5; catatan_detail.append("✗ Kelembapan tidak sesuai standar")

    # 4. Kadar air (25)
    if 70 <= kadar_val <= 90:
        skor += 25; catatan_detail.append("✓ Kadar air sangat baik")
    elif 60 <= kadar_val < 70 or 90 < kadar_val <= 95:
        skor += 15; catatan_detail.append("⚠ Kadar air perlu penyesuaian")
    else:
        skor += 5; catatan_detail.append("✗ Kadar air bermasalah")

    # Warna & Tekstur
    warna_lower = (warna or "").lower()
    if "tua" in warna_lower:
        catatan_detail.append("✓ Warna daun menunjukkan kesehatan baik")
    elif "kuning" in warna_lower:
        skor -= 5; catatan_detail.append("⚠ Warna kekuningan - cek kekurangan nitrogen")
    elif "coklat" in warna_lower or "kering" in warna_lower:
        skor -= 10; catatan_detail.append("✗ Daun kecoklatan - kemungkinan stres atau penyakit")

    tekstur_lower = (tekstur or "").lower()
    if "halus" in tekstur_lower:
        catatan_detail.append("✓ Tekstur daun baik")
    elif "kasar" in tekstur_lower:
        catatan_detail.append("⚠ Tekstur kasar - perhatikan irigasi")

    # Tentukan grade & hasil
    if skor >= 85:
        grade_label = "A"; hasil_label = "SANGAT LAYAK"
    elif skor >= 70:
        grade_label = "B"; hasil_label = "LAYAK"
    elif skor >= 50:
        grade_label = "C"; hasil_label = "KURANG LAYAK"
    else:
        grade_label = "D"; hasil_label = "TIDAK LAYAK"

    rekomendasi = {
        "A": "Tembakau siap untuk penjualan premium.",
        "B": "Kualitas baik, tingkatkan sedikit lagi.",
        "C": "Perlu perbaikan signifikan.",
        "D": "Evaluasi ulang metode budidaya."
    }[grade_label]

    catatan_lengkap = " | ".join(catatan_detail) + f" || Rekomendasi: {rekomendasi}"

    # Simpan ke DB
    conn = get_connection()
    if not conn:
        print("Gagal menyimpan evaluasi.")
        return

    try:
        cur = conn.cursor()

        # ambil id_users pemeriksaan
        cur.execute("SELECT id_users FROM pemeriksaan WHERE id_pemeriksaan = %s", (id_pemeriksaan,))
        id_owner = cur.fetchone()[0]

        # Ambil ID grade_evaluasi
        cur.execute("SELECT id_grade_evaluasi FROM grade_evaluasi WHERE grade_evaluasi = %s", (grade_label,))
        grade_row = cur.fetchone()
        id_grade = grade_row[0] if grade_row else None

        # Ambil ID hasil_evaluasi
        cur.execute("SELECT id_hasil_evaluasi FROM hasil_evaluasi WHERE hasil_evaluasi = %s", (hasil_label,))
        hasil_row = cur.fetchone()
        id_hasil = hasil_row[0] if hasil_row else None


        cur.execute(
        """INSERT INTO evaluasi 
        (tanggal_evaluasi, skor_evaluasi, catatan, id_pemeriksaan, id_users,
        id_grade_evaluasi, id_hasil_evaluasi)
        VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (datetime.now(), float(skor), catatan_lengkap, id_pemeriksaan,
         id_owner, id_grade, id_hasil)
        )



        conn.commit()
    except Exception as e:
        print("Error simpan evaluasi:", e)
    finally:
        cur.close()
        conn.close()

# ==========================
# REGISTRASI & LOGIN
# ==========================
def register_manual():
  while True:
    username = input("Username: ")
    if not username.strip():
        print("username tidak boleh kosong!")
        continue
    if not username.isalnum():
        print("tidak boleh selain huruf dan angka!")
        continue
    print(f"username berhasil disimpan ✓: '{username}'")
    break
  
  while True:
    password = input("Password: ")
    if not password.strip():
        print("tidak boleh kosong!")
        continue
    print(f"password berhasil disimpan ✓")
    break
  
  print("\nPilih Jenis Pengguna:")
  print("1. Petani")
  print("2. Pabrik")
  pilihan = input("Jenis (1/2): ").strip()
  role_name = "petani" if pilihan == "1" else "pabrik" if pilihan == "2" else None

  if not role_name:
        print("Pilihan tidak valid!")
        return

  conn = get_connection()
  if not conn:
        return

  try:
        cur = conn.cursor()
        # cek username
        cur.execute("SELECT id_users FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            print("Username sudah digunakan!")
            cur.close()
            conn.close()
            return

        # cari id_role
        cur.execute("SELECT id_role FROM role WHERE nama_role ILIKE %s", (role_name,))
        role_row = cur.fetchone()
        id_role = role_row[0] if role_row else None

        # insert user minimal (sesuai tabel users)
        cur.execute(
            "INSERT INTO users (nama, no_kontak, email, username, password, id_alamat, id_role) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            ('', '', '', username, password, id_alamat, id_role)
        )
        conn.commit()
        print("Registrasi berhasil!")
  except Exception as e:
        print(f"Error registrasi: {e}")
  finally:
        cur.close()
        conn.close()

def login():
   while True:
    username = input("Username: ")
    if not username.strip():
        print("username tidak boleh kosong!")
        continue
    if not username.isalnum():
        print("username hanya boleh angka dan huruf!")
        continue
    break 
   
   while True:
    password = input("Password: ")
    if not password.strip():
        print("password tidak boleh kosong!")
        continue
    break
   
   if username == "admin" and password == "admin123":
        print("Login sebagai Admin")
        dashboard_admin()
        return

   conn = get_connection()
   if not conn:
        return

   try:
        cur = conn.cursor()
        # ambil role name via join untuk memudahkan cek
        cur.execute("""
            SELECT u.id_users, r.nama_role
            FROM users u
            LEFT JOIN role r ON u.id_role = r.id_role
            WHERE u.username = %s AND u.password = %s
        """, (username, password))
        row = cur.fetchone()
        if row:
            id_user, role_name = row
            print(f"Login berhasil sebagai {role_name}!")
            if role_name and role_name.lower() == "petani":
                dashboard_petani(username)
            elif role_name and role_name.lower() == "pabrik":
                dashboard_pabrik(username)
            else:
                input("Menu untuk role ini belum dibuat. Tekan Enter untuk kembali...")
        else:
            print("Username atau password salah!")
   except Exception as e:
        print(f"Error login: {e}")
   finally:
        cur.close()
        conn.close()

def pilih_alamat():
    conn = get_connection()
    if not conn:
        return None
    cur = conn.cursor()

    cur.execute("SELECT id_kabupaten, nama_kabupaten FROM kabupaten ORDER BY nama_kabupaten")
    kab = cur.fetchall()
    print("\nPilih Kabupaten:")
    for k in kab:
        print(f"{k[0]}. {k[1]}")
    pilih_kab = input("ID Kabupaten: ")

    cur.execute("SELECT id_kecamatan, nama_kecamatan FROM kecamatan WHERE id_kabupaten=%s ORDER BY nama_kecamatan",
                (pilih_kab,))
    kec = cur.fetchall()
    print("\nPilih Kecamatan:")
    for c in kec:
        print(f"{c[0]}. {c[1]}")
    pilih_kec = input("ID Kecamatan: ")

    cur.execute("SELECT id_desa, nama_desa FROM desa WHERE id_kecamatan=%s ORDER BY nama_desa",
                (pilih_kec,))
    des = cur.fetchall()
    print("\nPilih Desa:")
    for d in des:
        print(f"{d[0]}. {d[1]}")
    pilih_des = input("ID Desa: ")

    nama_jalan = input("Nama Jalan: ")

    cur.execute("INSERT INTO alamat (nama_jalan, id_desa) VALUES (%s,%s) RETURNING id_alamat",
                (nama_jalan, pilih_des))
    id_alamat = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()
    return id_alamat

# ==========================
# FITUR PETANI (sesuaikan dg schema)
# ==========================
def input_data_petani(username):
    """
    Update profil user di tabel users (nama, no_kontak, email ...).
    """
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_users, nama, no_kontak, email FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            print("User tidak ditemukan.")
            cur.close(); conn.close(); return
        id_user = row[0]
        print("\n--- Update Profil ---")
        while True:
            nama = input(f"Nama ({row[1] or ''}): ") or row[1]
            if not nama.isalpha():
                print("nama tidak boleh selain huruf!")
            if not nama.strip():
                print("nama tidak boleh kosong!")
            break
        while True:
            telp = input(f"No Telepon ({row[2] or ''}): ") or row[2]
            if not telp.isdigit():
                print("no telp tidak boleh selain angka!")
            if not telp.strip():
                print("no telp tidak boleh kosong!")
            break
        while True:
            email = input(f"Email({row[3] or ''}):") or row[3]
            if not email.strip():
                print("email tidak boleh kosong!")
            break
        cur.execute("UPDATE users SET nama=%s, no_kontak=%s, email=%s WHERE id_users=%s", (nama, telp, email, id_user))
        conn.commit()
        print("Profil berhasil diperbarui!")
    except Exception as e:
        print(f"Error update profil: {e}")
    finally:
        cur.close(); conn.close()

def input_data_lahan(id_petani):

    id_alamat = pilih_alamat()        # << TAMBAHKAN INI
    if not id_alamat:
        print("Gagal menyimpan alamat!")
        return

    luas = input("Luas Lahan (M²): ")
    print("\nPilihan Jenis Tanah:")
    print("1. Tanah Aluvial")
    print("2. Tanah Andosol")
    pilih = input("Jenis Tanah (1/2): ")
    jenis = "Aluvial" if pilih == "1" else "Andosol" if pilih == "2" else None

    if not jenis:
        print("Pilihan tidak valid!")
        return

    conn = get_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lahan (luas_lahan, ketinggian_lahan, jenis_tanah, id_users, id_alamat) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING id_lahan",
            (float(luas), 0.0, jenis, id_petani, id_alamat)
        )
        id_lahan = cur.fetchone()[0]
        conn.commit()
        print(f"Data lahan disimpan! ID Lahan = {id_lahan}")
    except Exception as e:
        print(f"Error simpan lahan: {e}")
    finally:
        cur.close(); conn.close()


def input_data_pertumbuhan(id_petani):
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Belum ada lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    try:
        query = "SELECT id_lahan, luas_lahan FROM lahan WHERE id_users = %s"
        df = pd.read_sql(query, conn, params=(id_petani,))
        for _, row in df.iterrows():
            print(f"{row['id_lahan']} - Luas: {row['luas_lahan']}")
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return

    pilih = input("ID Lahan: ")
    if int(pilih) not in lahan_ids:
        print("ID lahan bukan milik Anda.")
        conn.close()
        return

    tanggal = input(f"Tanggal (Enter = {datetime.now().strftime('%Y-%m-%d')}): ") or datetime.now().strftime("%Y-%m-%d")

    # validasi angka
    while True:
        tinggi = input("Tinggi (cm): ")
        if tinggi.replace(".", "", 1).isdigit():
            break
        print("❌ Tinggi harus angka!")

    warna = input("Warna Daun: ")

    while True:
        lebar = input("Lebar Daun (cm): ")
        if lebar.replace(".", "", 1).isdigit():
            break
        print("❌ Lebar harus angka!")

    tekstur = input("Tekstur Daun: ")

    while True:
        lembab = input("Kelembapan (%): ")
        if lembab.replace(".", "", 1).isdigit():
            break
        print("❌ Kelembapan harus angka!")

    while True:
        kadar = input("Kadar Air (%): ")
        if kadar.replace(".", "", 1).isdigit():
            break
        print("❌ Kadar air harus angka!")

    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO pemeriksaan (tanggal_pemeriksaan, tinggi_tembakau, tekstur_daun, lebar_daun, warna_daun, kadar_air, keterangan, id_lahan, id_users)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_pemeriksaan""",
            (tanggal, float(tinggi), tekstur, float(lebar), warna, float(kadar), '', int(pilih), id_petani)
        )
        id_pemeriksaan = cur.fetchone()[0]
        conn.commit()
        print("✔ Data pemeriksaan tersimpan!")
        buat_evaluasi_otomatis(id_pemeriksaan, tinggi, warna, lebar, tekstur, lembab, kadar)
    except Exception as e:
        print(f"Error simpan pemeriksaan: {e}")
    finally:
        cur.close(); conn.close()

def edit_data_pertumbuhan(id_petani):
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Belum ada lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    try:
        print("\n===== DATA PEMERIKSAAN =====")
        query = """
            SELECT p.id_pemeriksaan, p.id_lahan, p.tanggal_pemeriksaan, p.tinggi_tembakau,
                   p.warna_daun, p.lebar_daun, p.tekstur_daun, p.kadar_air
            FROM pemeriksaan p
            WHERE p.id_lahan = ANY(%s)
            ORDER BY p.id_pemeriksaan DESC
        """
        df = pd.read_sql(query, conn, params=(lahan_ids,))
        if df.empty:
            print("Belum ada data pemeriksaan.")
            return
        for _, row in df.iterrows():
            print(f"ID: {row['id_pemeriksaan']} | Lahan: {row['id_lahan']} | Tgl: {row['tanggal_pemeriksaan']} | Tinggi: {row['tinggi_tembakau']} | Warna: {row['warna_daun']}")

        id_edit = input("\nMasukkan ID Pemeriksaan yang ingin diedit: ")
        cur = conn.cursor()
        cur.execute("SELECT id_lahan FROM pemeriksaan WHERE id_pemeriksaan = %s", (id_edit,))
        cek = cur.fetchone()
        if not cek or cek[0] not in lahan_ids:
            print("ID tidak valid atau bukan milik Anda!")
            cur.close(); conn.close(); return

        # ambil data lama
        cur.execute("""SELECT tanggal_pemeriksaan, tinggi_tembakau, warna_daun, lebar_daun, tekstur_daun, kadar_air
                       FROM pemeriksaan WHERE id_pemeriksaan = %s""", (id_edit,))
        old = cur.fetchone()

        print("\n--- Masukkan data baru (Enter untuk tetap pakai data lama) ---")
        tanggal = input(f"Tanggal ({old[0]}): ") or old[0]

        # validasi angka untuk tinggi
        while True:
            tinggi = input(f"Tinggi ({old[1]}): ") or old[1]
            if str(tinggi).replace(".", "", 1).isdigit():
                break
            print("❌ Tinggi harus angka!")

        warna = input(f"Warna Daun ({old[2]}): ") or old[2]

        # validasi angka untuk lebar
        while True:
            lebar = input(f"Lebar Daun ({old[3]}): ") or old[3]
            if str(lebar).replace(".", "", 1).isdigit():
                break
            print("❌ Lebar harus angka!")

        tekstur = input(f"Tekstur Daun ({old[4]}): ") or old[4]

        # validasi angka untuk kadar air
        while True:
            kadar = input(f"Kadar Air ({old[5]}): ") or old[5]
            if str(kadar).replace(".", "", 1).isdigit():
                break
            print("❌ Kadar air harus angka!")

        # update pemeriksaan
        cur.execute(
            """UPDATE pemeriksaan SET tanggal_pemeriksaan=%s, tinggi_tembakau=%s, warna_daun=%s,
               lebar_daun=%s, tekstur_daun=%s, kadar_air=%s WHERE id_pemeriksaan=%s""",
            (tanggal, float(tinggi), warna, float(lebar), tekstur, float(kadar), id_edit)
        )
        conn.commit()
        print("✔ Data pemeriksaan berhasil diperbarui!")

        # update evaluasi lama (tidak delete, langsung update)
        buat_evaluasi_otomatis(id_edit, tinggi, warna, lebar, tekstur, None, kadar)

    except Exception as e:
        print(f"Error edit: {e}")
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def hapus_data_pertumbuhan(id_petani):
    print("\n===== HAPUS DATA PEMERIKSAAN =====")
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Anda belum memiliki lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    try:
        query = """
            SELECT p.id_pemeriksaan, p.tanggal_pemeriksaan, p.tinggi_tembakau, p.warna_daun, p.id_lahan
            FROM pemeriksaan p
            WHERE p.id_lahan = ANY(%s)
            ORDER BY p.tanggal_pemeriksaan DESC
        """
        df = pd.read_sql(query, conn, params=(lahan_ids,))
        if df.empty:
            print("Belum ada data pemeriksaan.")
            return

        print("\nDaftar Pemeriksaan:")
        for _, row in df.iterrows():
            print(f"ID: {row['id_pemeriksaan']} | Tanggal: {row['tanggal_pemeriksaan']} | Tinggi: {row['tinggi_tembakau']} cm | Warna: {row['warna_daun']} | Lahan: {row['id_lahan']}")

        id_hapus = input("\nMasukkan ID Pemeriksaan yang ingin dihapus: ")
        if int(id_hapus) not in df['id_pemeriksaan'].values:
            print("❌ ID tidak ditemukan atau bukan milik Anda!")
            return

        yakin = input(f"Yakin ingin menghapus ID {id_hapus}? (y/n): ")
        if yakin.lower() != "y":
            print("Dibatalkan.")
            return

        cur = conn.cursor()

        # cek apakah evaluasi pemeriksaan ini dipakai di pengajuan
        cur.execute("""
            SELECT COUNT(*) FROM pengajuan 
            WHERE id_evaluasi IN (SELECT id_evaluasi FROM evaluasi WHERE id_pemeriksaan=%s)
        """, (id_hapus,))
        if cur.fetchone()[0] > 0:
            print("❌ Data pemeriksaan tidak bisa dihapus karena evaluasi sudah dipakai di pengajuan!")
            return

        # kalau aman, hapus evaluasi & hama lalu pemeriksaan
        cur.execute("DELETE FROM evaluasi WHERE id_pemeriksaan = %s", (id_hapus,))
        cur.execute("DELETE FROM hama WHERE id_pemeriksaan = %s", (id_hapus,))
        cur.execute("DELETE FROM pemeriksaan WHERE id_pemeriksaan = %s", (id_hapus,))
        conn.commit()
        print("✔ Data pemeriksaan berhasil dihapus!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def lihat_riwayat_pertumbuhan(id_petani):
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Belum ada lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    print("\n===== RIWAYAT PEMERIKSAAN =====")
    try:
        query = """
            SELECT id_pemeriksaan, tanggal_pemeriksaan, tinggi_tembakau, warna_daun
            FROM pemeriksaan
            WHERE id_lahan = ANY(%s)
            ORDER BY tanggal_pemeriksaan DESC
        """
        df = pd.read_sql(query, conn, params=(lahan_ids,))
        if df.empty:
            print("Belum ada data.")
        else:
            for _, row in df.iterrows():
                print(f"ID: {row['id_pemeriksaan']} | {row['tanggal_pemeriksaan']} | Tinggi: {row['tinggi_tembakau']} cm | Warna: {row['warna_daun']}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def input_data_hama(id_petani):
    lihat_riwayat_pertumbuhan(id_petani)
    id_pemeriksaan = input("\nID Pemeriksaan terkena hama: ")
    lahan_ids = get_petani_lahan_ids(id_petani)
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT id_lahan FROM pemeriksaan WHERE id_pemeriksaan = %s", (id_pemeriksaan,))
        result = cur.fetchone()
        if not result or result[0] not in lahan_ids:
            print("ID tidak valid atau bukan milik Anda!")
            cur.close(); conn.close(); return
        nama_hama = input("Nama Hama: ").strip()
        jenis = input("Jenis Hama (nama jenis): ").strip()
        tingkat = input("Tingkat Serangan (nama tingkat): ").strip()
        # pastikan jenis_hama ada
        id_jenis = None
        if jenis:
            cur.execute("SELECT id_jenis_hama FROM jenis_hama WHERE jenis_hama ILIKE %s", (jenis,))
            r = cur.fetchone()
            if r:
                id_jenis = r[0]
            else:
                cur.execute("INSERT INTO jenis_hama (jenis_hama) VALUES (%s) RETURNING id_jenis_hama", (jenis,))
                id_jenis = cur.fetchone()[0]
        # pastikan tingkat_serangan ada
        id_tingkat = None
        if tingkat:
            cur.execute("SELECT id_tingkat_serangan FROM tingkat_serangan WHERE tingkat_serangan ILIKE %s", (tingkat,))
            r = cur.fetchone()
            if r:
                id_tingkat = r[0]
            else:
                cur.execute("INSERT INTO tingkat_serangan (tingkat_serangan) VALUES (%s) RETURNING id_tingkat_serangan", (tingkat,))
                id_tingkat = cur.fetchone()[0]
        # insert hama
        cur.execute(
            "INSERT INTO hama (nama_hama, id_jenis_hama, id_tingkat_serangan, id_pemeriksaan) VALUES (%s,%s,%s,%s)",
            (nama_hama, id_jenis, id_tingkat, id_pemeriksaan)
        )
        conn.commit()
        print("Data hama tersimpan!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def lihat_hasil_evaluasi(id_petani):
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Belum ada lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    print("\n" + "="*70)
    print("           HASIL EVALUASI KELAYAKAN TEMBAKAU")
    print("="*70)
    try:
        # join ke pemeriksaan supaya batasi hanya milik lahan petani
        query = """
            SELECT ev.id_evaluasi, ev.tanggal_evaluasi, ev.skor_evaluasi, ev.catatan,
                   ge.grade_evaluasi, he.hasil_evaluasi, ev.id_pemeriksaan
            FROM evaluasi ev
            LEFT JOIN grade_evaluasi ge ON ev.id_grade_evaluasi = ge.id_grade_evaluasi
            LEFT JOIN hasil_evaluasi he ON ev.id_hasil_evaluasi = he.id_hasil_evaluasi
            JOIN pemeriksaan p ON ev.id_pemeriksaan = p.id_pemeriksaan
            WHERE p.id_lahan = ANY(%s)
            ORDER BY ev.tanggal_evaluasi DESC
        """
        df = pd.read_sql(query, conn, params=(lahan_ids,))
        if df.empty:
            print("   Belum ada evaluasi.")
        else:
            for _, row in df.iterrows():
                print(f"\nID Evaluasi    : {row['id_evaluasi']}")
                print(f"ID Pemeriksaan : {row['id_pemeriksaan']}")
                print(f"Tanggal        : {row['tanggal_evaluasi']}")
                print(f"Skor           : {row['skor_evaluasi']}")
                print(f"Grade          : {row.get('grade_evaluasi')}")
                print(f"Hasil          : {row.get('hasil_evaluasi')}")
                catatan = row['catatan'] or ''
                if " || Rekomendasi: " in catatan:
                    detail, rekom = catatan.split(" || Rekomendasi: ", 1)
                    items = detail.split(" | ")
                    print("\nDetail Penilaian:")
                    for it in items:
                        if it.strip():
                            print("  " + it)
                    print(f"\nRekomendasi    : {rekom}")
                else:
                    print(f"Catatan        : {catatan}")
                print("-" * 70)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def pengajuan_penjualan(id_petani):
    lahan_ids = get_petani_lahan_ids(id_petani)
    if not lahan_ids:
        print("Belum ada lahan.")
        return
    conn = get_connection()
    if not conn:
        return
    try:
        query = "SELECT id_lahan, luas_lahan FROM lahan WHERE id_users = %s"
        df = pd.read_sql(query, conn, params=(id_petani,))
        for _, row in df.iterrows():
            print(f"{row['id_lahan']} - Luas: {row['luas_lahan']} m²")

        pilih = input("ID Lahan: ")
        if int(pilih) not in lahan_ids:
            print("❌ Lahan tidak valid!")
            return

        # validasi angka untuk jumlah
        while True:
            jumlah = input("Jumlah (kg): ")
            if jumlah.replace(".", "", 1).isdigit():
                break
            print("❌ Jumlah harus angka!")

        # validasi angka untuk harga
        while True:
            harga = input("Harga per kg: ")
            if harga.replace(".", "", 1).isdigit():
                break
            print("❌ Harga harus angka!")

        cur = conn.cursor()
        # ambil evaluasi terbaru untuk lahan tsb
        cur.execute("""
            SELECT ev.id_evaluasi FROM evaluasi ev
            JOIN pemeriksaan p ON ev.id_pemeriksaan = p.id_pemeriksaan
            WHERE p.id_lahan = %s
            ORDER BY ev.tanggal_evaluasi DESC LIMIT 1
        """, (pilih,))
        ev = cur.fetchone()
        id_evaluasi = ev[0] if ev else None

        cur.execute(
            "INSERT INTO pengajuan (tanggal_pengajuan, pengajuan_harga, id_status_pengajuan, id_evaluasi, id_users) VALUES (%s,%s,%s,%s,%s)",
            (datetime.now(), float(harga), None, id_evaluasi, id_petani)
        )
        conn.commit()
        print("✔ Pengajuan berhasil dikirim!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def lihat_transaksi_penjualan(id_petani):
    print("\n===== RIWAYAT TRANSAKSI =====")
    conn = get_connection()
    if not conn:
        print("Tidak dapat menampilkan transaksi: koneksi DB bermasalah.")
        return
    try:
        df = pd.read_sql(
            "SELECT id_transaksi, tanggal_transaksi, jumlah_kg, harga_sepakat FROM transaksi WHERE id_users = %s ORDER BY tanggal_transaksi DESC",
            conn, params=(id_petani,)
        )
        if df.empty:
            print("Belum ada transaksi.")
        else:
            for _, r in df.iterrows():
                # format tanggal lebih ringkas
                tgl_fmt = r['tanggal_transaksi'].strftime("%d-%m-%Y %H:%M")
                # format angka
                jumlah_fmt = f"{float(r['jumlah_kg']):,.2f}".rstrip("0").rstrip(".")
                harga_fmt = f"{float(r['harga_sepakat']):,.0f}"
                total = float(r['jumlah_kg']) * float(r['harga_sepakat'])
                total_fmt = f"{total:,.0f}"

                print(f"ID: {r['id_transaksi']} | Tgl: {tgl_fmt} | Jumlah: {jumlah_fmt} kg | Harga: Rp {harga_fmt} | Total: Rp {total_fmt}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

# ==========================
# DASHBOARD PETANI
# ==========================
def dashboard_petani(username):
    id_petani = get_petani_id(username)
    if not id_petani:
        print("Gagal ambil ID petani.")
        return
    while True:
        print(f"\n{'='*22} MENU PETANI {'='*22}")
        print("1. Input Data Profil")
        print("2. Input Data Lahan")
        print("3. Input Data Pemeriksaan (Pertumbuhan)")
        print("4. Edit Data Pemeriksaan")
        print("5. Hapus Data Pemeriksaan")
        print("6. Lihat Riwayat Pemeriksaan")
        print("7. Input Data Hama")
        print("8. Lihat Hasil Evaluasi")
        print("9. Pengajuan Penjualan")
        print("10. Lihat Transaksi")
        print("11. Logout")
        p = input("\nPilih (1-11): ")
        if p == "1": input_data_petani(username)
        elif p == "2": input_data_lahan(id_petani)
        elif p == "3": input_data_pertumbuhan(id_petani)
        elif p == "4": edit_data_pertumbuhan(id_petani)
        elif p == "5": hapus_data_pertumbuhan(id_petani)
        elif p == "6": lihat_riwayat_pertumbuhan(id_petani)
        elif p == "7": input_data_hama(id_petani)
        elif p == "8": lihat_hasil_evaluasi(id_petani)
        elif p == "9": pengajuan_penjualan(id_petani)
        elif p == "10": lihat_transaksi_penjualan(id_petani)
        elif p == "11":
            print("Logout berhasil! Terima kasih.")
            break
        else:
            print("Pilihan tidak valid!")

# ==========================
# FITUR PABRIK
# ==========================
def lihat_pengajuan_pabrik(username):
    conn = get_connection()
    if not conn:
        return
    try:
        df = pd.read_sql("""
            SELECT pg.id_pengajuan, pg.tanggal_pengajuan, pg.pengajuan_harga, u.username, ev.skor_evaluasi, he.hasil_evaluasi
            FROM pengajuan pg
            LEFT JOIN users u ON pg.id_users = u.id_users
            LEFT JOIN evaluasi ev ON pg.id_evaluasi = ev.id_evaluasi
            LEFT JOIN hasil_evaluasi he ON ev.id_hasil_evaluasi = he.id_hasil_evaluasi
            ORDER BY pg.tanggal_pengajuan DESC
        """, conn)
        if df.empty:
            print("Belum ada pengajuan dari petani.")
        else:
            print("\n===== DAFTAR PENGAJUAN =====")
            for _, r in df.iterrows():
                harga_fmt = f"{float(r['pengajuan_harga']):,.0f}"
                print(f"ID: {r['id_pengajuan']} | Petani: {r['username']} | Harga: Rp {harga_fmt} | Skor: {r['skor_evaluasi']} | Hasil: {r['hasil_evaluasi']}")
    except Exception as e:
        print("Error lihat pengajuan:", e)
    finally:
        conn.close()

def putuskan_pengajuan(username):
    conn = get_connection()
    if not conn:
        return
    try:
        id_pengajuan = input("Masukkan ID Pengajuan yang ingin diputuskan: ")
        keputusan = input("Keputusan (setuju/tolak): ").lower()

        cur = conn.cursor()
        # sesuaikan dengan nama kolom di tabel status_pengajuan
        cur.execute("SELECT id_status_pengajuan FROM status_pengajuan WHERE status_pengajuan ILIKE %s", (keputusan,))
        status_row = cur.fetchone()
        if not status_row:
            print("❌ Status tidak valid! Harus 'setuju' atau 'tolak'.")
            return
        id_status = status_row[0]

        cur.execute("UPDATE pengajuan SET id_status_pengajuan=%s WHERE id_pengajuan=%s", (id_status, id_pengajuan))
        conn.commit()
        print(f"✔ Pengajuan {id_pengajuan} berhasil di-{keputusan}.")
    except Exception as e:
        print("Error putuskan pengajuan:", e)
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def transaksi_pembelian(username):
    conn = get_connection()
    if not conn:
        return
    try:
        id_pengajuan = input("ID Pengajuan yang disetujui: ")

        # validasi angka jumlah
        while True:
            jumlah = input("Jumlah (kg): ")
            if jumlah.replace(".", "", 1).isdigit():
                break
            print("❌ Jumlah harus angka!")

        # validasi angka harga
        while True:
            harga = input("Harga sepakat per kg: ")
            if harga.replace(".", "", 1).isdigit():
                break
            print("❌ Harga harus angka!")

        total = float(jumlah) * float(harga)

        cur = conn.cursor()
        # ambil id_users petani dari pengajuan
        cur.execute("SELECT id_users FROM pengajuan WHERE id_pengajuan=%s", (id_pengajuan,))
        petani_row = cur.fetchone()
        id_petani = petani_row[0] if petani_row else None


        # simpan transaksi dengan id_users petani
        cur.execute("""
            INSERT INTO transaksi (tanggal_transaksi, jumlah_kg, harga_sepakat, id_pengajuan, id_users)
            VALUES (%s,%s,%s,%s,%s)
        """, (datetime.now(), float(jumlah), float(harga), id_pengajuan, id_petani))
        conn.commit()
        print(f"✔ Transaksi pembelian tercatat untuk petani {id_petani}. Total: Rp {total:,.0f}")
    except Exception as e:
        print("Error transaksi:", e)
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()

def riwayat_transaksi_pabrik(username):
    conn = get_connection()
    if not conn:
        return
    try:
        df = pd.read_sql("SELECT id_transaksi, tanggal_transaksi, jumlah_kg, harga_sepakat FROM transaksi ORDER BY tanggal_transaksi DESC", conn)
        if df.empty:
            print("Belum ada transaksi.")
        else:
            print("\n===== RIWAYAT TRANSAKSI PABRIK =====")
            for _, r in df.iterrows():
                jumlah_fmt = f"{float(r['jumlah_kg']):,.2f}".rstrip("0").rstrip(".")
                harga_fmt = f"{float(r['harga_sepakat']):,.0f}"
                total = float(r['jumlah_kg']) * float(r['harga_sepakat'])
                total_fmt = f"{total:,.0f}"
                print(f"ID: {r['id_transaksi']} | Tgl: {r['tanggal_transaksi']} | Jumlah: {jumlah_fmt} kg | Harga: Rp {harga_fmt} | Total: Rp {total_fmt}")
    except Exception as e:
        print("Error riwayat transaksi:", e)
    finally:
        conn.close()

# ==========================
# DASHBOARD PABRIK
# ==========================
def dashboard_pabrik(username):
    while True:
        print(f"\n{'='*22} MENU PABRIK {'='*22}")
        print("1. Lihat Pengajuan Penjualan")
        print("2. Putuskan Pengajuan")
        print("3. Transaksi Pembelian")
        print("4. Riwayat Transaksi")
        print("5. Logout")
        p = input("\nPilih (1-5): ")
        if p == "1": lihat_pengajuan_pabrik(username)
        elif p == "2": putuskan_pengajuan(username)
        elif p == "3": transaksi_pembelian(username)
        elif p == "4": riwayat_transaksi_pabrik(username)
        elif p == "5":
            print("Logout berhasil dari menu Pabrik.")
            break
        else:
            print("Pilihan tidak valid!")

# ==========================
# DASHBOARD ADMIN
# ==========================
def dashboard_admin():
    while True:
        print(f"\n{'='*22} MENU ADMIN {'='*22}")
        print("1. Lihat Semua User")
        print("2. Hapus User")
        print("3. Lihat Semua Pengajuan")
        print("4. Lihat Semua Transaksi")
        print("5. Logout")
        p = input("\nPilih (1-5): ")

        if p == "1": lihat_semua_user()
        elif p == "2": hapus_user()
        elif p == "3": lihat_semua_pengajuan()
        elif p == "4": lihat_semua_transaksi()
        elif p == "5":
            print("Logout berhasil dari menu Admin.")
            break
        else:
            print("Pilihan tidak valid!")

def lihat_semua_user():
    conn = get_connection()
    if not conn: return
    try:
        df = pd.read_sql("SELECT id_users, username, id_role FROM users ORDER BY id_users", conn)
        print("\n===== DAFTAR USER =====")
        for _, r in df.iterrows():
            print(f"ID: {r['id_users']} | Username: {r['username']} | Role: {r['id_role']}")
    except Exception as e:
        print("Error lihat user:", e)
    finally:
        conn.close()

def hapus_user():
    conn = get_connection()
    if not conn: return
    try:
        id_user = input("Masukkan ID User yang ingin dihapus: ")
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id_users=%s", (id_user,))
        conn.commit()
        print(f"✔ User {id_user} berhasil dihapus.")
    except Exception as e:
        print("Error hapus user:", e)
    finally:
        cur.close(); conn.close()

def lihat_semua_pengajuan():
    conn = get_connection()
    if not conn: return
    try:
        df = pd.read_sql("SELECT * FROM pengajuan ORDER BY tanggal_pengajuan DESC", conn)
        print("\n===== SEMUA PENGAJUAN =====")
        for _, r in df.iterrows():
            print(f"ID: {r['id_pengajuan']} | User: {r['id_users']} | Harga: Rp {r['pengajuan_harga']} | Status: {r['id_status_pengajuan']}")
    except Exception as e:
        print("Error lihat pengajuan:", e)
    finally:
        conn.close()

def lihat_semua_transaksi():
    conn = get_connection()
    if not conn: return
    try:
        df = pd.read_sql("SELECT * FROM transaksi ORDER BY tanggal_transaksi DESC", conn)
        print("\n===== SEMUA TRANSAKSI =====")
        for _, r in df.iterrows():
            total = float(r['jumlah_kg']) * float(r['harga_sepakat'])
            print(f"ID: {r['id_transaksi']} | User: {r['id_users']} | Jumlah: {r['jumlah_kg']} kg | Harga: Rp {r['harga_sepakat']} | Total: Rp {total:,.0f}")
    except Exception as e:
        print("Error lihat transaksi:", e)
    finally:
        conn.close()

# ==========================
# MAIN
# ==========================
def main():
    while True:
        print("\n===== SISTEM INFORMASI PEMANTAUAN TEMBAKAU =====")
        print("1. Registrasi")
        print("2. Login")
        print("3. Keluar")
        p = input("Pilih: ")
        if p == "1":
            register_manual()
        elif p == "2":
            login()
        elif p == "3":
            print("Sampai jumpa!")
            break

if __name__ == "__main__":
    main()
