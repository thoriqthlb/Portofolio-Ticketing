import streamlit as st
import sqlite3
import uuid
from datetime import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash

def buat_tabel():
    '''Membuat tabel databasenya'''

    with sqlite3.connect("tiket_inews.db", timeout= 10) as conn:
        kursor = conn.cursor()
        
        kursor.execute("""
            CREATE TABLE IF NOT EXISTS tiket (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Waktu TEXT,
                Nama TEXT,
                Email TEXT,
                Unit_Kerja TEXT,
                Lantai TEXT,
                Kategori TEXT,
                Detail TEXT,
                Status TEXT DEFAULT 'Open',
                Ditangani_Oleh TEXT DEFAULT '-',
                Closed_At TEXT DEFAULT '-'
            )
        """)

        kursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tiket(Status)")

        kursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        """)

        pass_super = st.secrets.get("admin_setup", {}).get("init_super_pass")
        if not pass_super:
            raise ValueError(":red[:material/error:] FATAL: 'init_super_pass' tidak ditemukan di secrets.toml. Aplikasi dihentikan.")
        
        kursor.execute("SELECT COUNT(*) FROM admin WHERE username = 'superadmin'")
        if kursor.fetchone()[0] == 0:
            hashed_pass_super = generate_password_hash(pass_super)
            kursor.execute("INSERT OR IGNORE INTO admin (username, password, role) VALUES ('superadmin', ?, 'superadmin')", (hashed_pass_super,))

        kursor.execute("""
            CREATE TABLE IF NOT EXISTS sesi (
                token TEXT PRIMARY KEY,
                username TEXT,
                role TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.commit()

# Admin login
def cek_login(username, password):
    '''Validasi login admin'''
    with sqlite3.connect("tiket_inews.db", timeout=10) as conn:
        kursor = conn.cursor()
        
        kursor.execute("SELECT password, role FROM admin WHERE username = ?", (username,))
        hasil = kursor.fetchone()

        if hasil and check_password_hash(hasil[0], password):
            return hasil[1]
        return None

# Admin bisa ubah passnya sendiri
def ubah_password(username, password_baru):
    '''Admin bisa mengubah passwordnya'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10) as conn:
        kursor = conn.cursor()
        hashed_password = generate_password_hash(password_baru)
        
        kursor.execute("UPDATE admin SET password = ? WHERE username = ?", (hashed_password, username))
        kursor.execute("DELETE FROM sesi WHERE username = ?", (username,))
        
        conn.commit()

def tambah_admin(username, password):
    '''Superadmin bisa tambah admin'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10) as conn:
        kursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            kursor.execute("INSERT INTO admin (username, password, role) VALUES (?, ?, 'admin')", (username, hashed_password))
            conn.commit()
            berhasil = True
        except sqlite3.IntegrityError:
            berhasil = False
            
        return berhasil

def ambil_semua_admin():
    '''Superadmin bisa liat daftar admin'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10)as conn:
        kursor = conn.cursor()
        
        kursor.execute("SELECT username, role FROM admin WHERE role = 'admin'")
        hasil = kursor.fetchall()
        
        return hasil

# Simpen data-data untuk tiket
def simpan_tiket(nama, email, unit_kerja, lantai, kategori, detail):
    '''Menerima data dari app.py dan disimpan ke tabel tiket'''

    with sqlite3.connect("tiket_inews.db", timeout= 10)as conn:
        kursor = conn.cursor()

        waktu = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        kursor.execute("""
            INSERT INTO tiket (Waktu, Nama, Email, Unit_Kerja, Lantai, Kategori, Detail)
            VALUES (?,?,?,?,?,?,?)
        """, (waktu, nama, email, unit_kerja, lantai, kategori, detail))

        id_baru = kursor.lastrowid
        conn.commit()
        return id_baru

# User bisa cek status tiketnya sendiri
def cek_status_tiket(id_tiket, email):
    '''Mengambil data tiket dari ID untuk ditampilkan ke user'''

    with sqlite3.connect("tiket_inews.db", timeout=10)as conn:
        kursor = conn.cursor()
        
        kursor.execute("SELECT Waktu, Kategori, Status, Closed_At, Ditangani_Oleh FROM tiket WHERE id = ? AND Email = ?", (id_tiket, email))
        hasil = kursor.fetchone()
        
        return hasil

# Update status tiket
def update_status(id_tiket, status_baru, nama_admin):
    '''Mengubah status tiket di database berdasarkan ID'''

    with sqlite3.connect("tiket_inews.db", timeout= 10)as conn:
        kursor = conn.cursor()

        if status_baru == "Closed":
            waktu_tutup = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            kursor.execute("""
                UPDATE tiket
                SET status = ?, Closed_At = ?, Ditangani_Oleh = ?
                WHERE id = ?
            """, (status_baru, waktu_tutup, nama_admin, id_tiket))
        else:
            kursor.execute("""
                UPDATE tiket
                SET status = ?, Ditangani_Oleh = ?
                WHERE id = ?
            """, (status_baru, nama_admin, id_tiket))

        conn.commit()

# Ambil tiket pelapor
def ambil_email(id_tiket):
    '''Mengambil email pelapor dengan ID tiket di database'''

    with sqlite3.connect("tiket_inews.db", timeout= 10)as conn:
        kursor = conn.cursor()

        kursor.execute("SELECT Email FROM tiket WHERE id = ?", (id_tiket,))
        hasil = kursor.fetchone()

        if hasil:
            return hasil[0]
        return None

# Hapus admin 
def hapus_admin(username):
    '''Menghapus admin dari daftarnya, hanya bisa dilakukan oleh Superadmin'''

    with sqlite3.connect("tiket_inews.db", timeout= 10)as conn:
        kursor = conn.cursor()

        kursor.execute("DELETE FROM admin WHERE username = ? AND role = 'admin'", (username,))
        kursor.execute("DELETE FROM sesi WHERE username = ?", (username,))

        conn.commit()

def buat_sesi(username, role):
    '''Membuat token acak untuk login'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10)as conn:
        kursor = conn.cursor()
        
        token = str(uuid.uuid4())
        kursor.execute("INSERT INTO sesi (token, username, role) VALUES (?, ?, ?)", (token, username, role))
        
        conn.commit()
        return token

def cek_sesi(token):
    '''Mengecek apakah token di URL valid di database'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10) as conn:
        kursor = conn.cursor()
    
        kursor.execute("""
            SELECT username, role FROM sesi 
            WHERE token = ?
            AND created_at > datetime('now', '-8 hours')           
        """, (token,))
        hasil = kursor.fetchone()

        if hasil:
            kursor.execute("DELETE FROM sesi WHERE token = ?", (token,))

            token_baru = str(uuid.uuid4())
            kursor.execute("INSERT INTO sesi (token, username, role) VALUES (?, ?, ?)", (token_baru, hasil[0], hasil[1]))
    
            conn.commit()
            return (hasil[0], hasil[1], token_baru)
        return None

def hapus_sesi(token):
    '''Menghapus token dari database saat logout'''
    
    with sqlite3.connect("tiket_inews.db", timeout=10)as conn:
        kursor = conn.cursor()
        
        kursor.execute("DELETE FROM sesi WHERE token = ?", (token,))
        
        conn.commit()