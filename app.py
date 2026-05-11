import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import io
from database import buat_tabel, simpan_tiket, update_status, ambil_email, cek_status_tiket, cek_login, ubah_password, tambah_admin, ambil_semua_admin, hapus_admin, buat_sesi, cek_sesi, hapus_sesi

# Setup layout
st.set_page_config(
    page_title= "iNews IT Ticketing",
    page_icon= "logo_app.png",
    layout= "wide"
)

if "db_ready" not in st.session_state:
    buat_tabel()
    st.session_state["db_ready"] = True

@st.cache_data
def generate_excel(df_input):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_input.to_excel(writer, index=False)
    return output.getvalue()

# Halaman utama tiket aduan
def halaman_tiket():
    '''Tampilan halaman utama ticketing'''

    st.title("PUSAT ADUAN TICKETING")

    nama = st.text_input("Nama Lengkap").title()
    email = st.text_input("Alamat Email")
    
    col1, col2 = st.columns(2)
    with col1:
        unit_kerja = st.text_input("Unit Kerja (misal: Okezone)").capitalize()
    with col2:
        lantai = st.text_input("Lantai (misal: 12)")
    
    kategori = st.selectbox(
        "Kategori Masalah", # Sementara, kalo better hardware/software doang yaudah ikutin
        ["Internet", "Email", "Printer", "Perangkat Lemot", "Perangkat Mati", "Lupa Password", "Lainnya"],
        index=None,
        placeholder= "pilih kategori masalah"
    )
    
    detail = st.text_area("Detail Keluhan (sebutkan sedetail mungkin)")

    if st.button("Kirim Tiket"):
        if nama == "" or email == "" or unit_kerja == "" or lantai == "" or kategori == None or detail == "":
            st.error(":red[:material/error:] Mohon lengkapi data sebelum mengirim.")

        elif "@" not in email:
            st.error(":red[:material/error:] Format email tidak valid, sertakan '@'.")
        
        else:
            id_baru = simpan_tiket(nama, email, unit_kerja, lantai, kategori, detail)
            st.success(f":green[:material/check_circle:] Tiket berhasil dikirim! **Nomor ID** tiket Anda: **{id_baru}**")
            st.warning(":orange[:material/warning:] Harap simpan **Nomor ID** tersebut untuk mengecek progres perbaikan.")
            st.info(f":blue[:material/info:] Rangkuman laporan: {nama} ({unit_kerja} - Lantai {lantai}) - Masalah {kategori}")

# Halaman cek status tiket
def halaman_status():
    '''Halaman untuk user cek status tiket'''
    
    st.title("Cek Status Perbaikan")

    col_cek1, col_cek2 = st.columns(2)
    with col_cek1:
        id_cek = st.number_input("Masukkan Nomor ID Tiket Anda", min_value=1, step=1)
    with col_cek2:
        email = st.text_input("Alamat Email").strip()  

    st.write("")
    tombol_cek = st.button("Cek Status")

    if tombol_cek:
        if email == "":
            st.error(":red[:material/error:] Alamat email tidak boleh kosong!")
        else:
            hasil = cek_status_tiket(id_cek, email)

            if hasil:
                waktu, kat, stat, closed, admin = hasil
                st.markdown(f"**Waktu Lapor:** {waktu} | **Kendala:** {kat}")

                if stat == "Open":
                    st.info(":material/schedule: Status saat ini: **Menunggu Antrean (Open)**")
                elif stat == "In Progress":
                    st.warning(f":material/work_history: Status saat ini: **Sedang Dikerjakan (In Progress)** oleh admin **{admin}**")
                elif stat == "Closed":
                    st.success(f":material/check_circle: Status saat ini: **Selesai (Closed)** pada {closed} oleh admin **{admin}**")
            else:
                st.error(f":red[:material/error:] Tiket dengan ID {id_cek} tidak ditemukan. Pastikan nomor ID benar.")

# Halaman Admin
def halaman_admin():
    '''Tampilan halaman admin dengan metrik, filter, dan unduh rekap'''

    st.title("Dashboard Admin IT")

    with sqlite3.connect("tiket_inews.db", timeout= 10) as conn:
        kursor = conn.cursor()

        kursor.execute("""
            SELECT 
                COUNT(*),
                SUM(CASE WHEN Status = 'Open' THEN 1 ELSE 0 END),
                SUM(CASE WHEN Status = 'In Progress' THEN 1 ELSE 0 END)
            FROM tiket
        """)
        total_tiket, tiket_open, tiket_progress = kursor.fetchone()

        df_tampil_db = pd.read_sql_query("SELECT * FROM tiket ORDER BY id DESC LIMIT 100", conn)
        df_export = pd.read_sql_query("SELECT * FROM tiket ORDER BY id DESC", conn)
        
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Tiket Masuk", total_tiket)
    col_b.metric("Menunggu (Open)", tiket_open)
    col_c.metric("Dikerjakan (In Progress)", tiket_progress)

    st.divider()

    filter_status = st.radio(
        "Filter Status (Menampilkan 100 Tiket Terbaru):", 
        ["Semua", "Open", "In Progress", "Closed"], 
        horizontal=True
    )

    if filter_status == "Semua":
        df_tampil = df_tampil_db
    else:
        df_tampil = df_tampil_db[df_tampil_db["Status"] == filter_status]

    st.dataframe(df_tampil.head(15), width="stretch")

    data_excel = generate_excel(df_export)

    st.download_button(
        label="Unduh rekap tiket (excel)",
        data = data_excel,
        file_name="rekap_tiket_inews.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()
    st.subheader("Ubah Status Tiket")

    col1, col2 = st.columns(2)
    with col1:
        id_tiket = st.number_input("Masukkan ID tiket", min_value= 1, step= 1)
    with col2:
        status_baru = st.selectbox("Status Baru", ["Open", "In Progress", "Closed"])
    
    # Admin yang mengubah tiket sesuai sesi
    nama_admin = st.session_state["username_aktif"]
    
    # Kondisi tiket saat ditekan tombol "Update Status"
    if st.button("Update Status"):
        email_pelapor = ambil_email(id_tiket)
        hasil_cek = cek_status_tiket(id_tiket, email_pelapor or "")

        if not hasil_cek:
            st.error(f":red[:material/error:] Tiket dengan ID {id_tiket} tidak ditemukan.")
        else:
            status_database = hasil_cek[2]
            admin_sekarang = hasil_cek[4]

            if status_database == "Closed":
                st.error(":material/block: Ditolak! Tiket ini sudah ditutup (Closed).")

            elif status_database == "In Progress" and status_baru == "Open":
                st.error(":material/block: Ditolak! Tiket yang dipilih sedang dikerjakan")
            
            elif status_database == "In Progress" and admin_sekarang != nama_admin:
                st.session_state["pesan_peringatan"] = ":orange[:material/warning:] Tiket ini sedang dikerjakan oleh admin lain."
                st.rerun()
                
            else:
                update_status(id_tiket, status_baru, nama_admin)
                st.session_state["pesan_sukses"] = f":green[:material/check_circle:] Status tiket ID {id_tiket} sukses diperbarui!"
        
                if status_baru == "Closed" and email_pelapor:
                    subjek = urllib.parse.quote(f"Update Status Tiket iNews #{id_tiket}")
                    pesan = urllib.parse.quote(f"Halo,\n\nTiket aduan Anda dengan ID {id_tiket} telah selesai ditangani (Closed).\n\nTerima kasih,\nIT Operations iNews")
                    tautan_email = f"mailto:{email_pelapor}?subject={subjek}&body={pesan}"
                    st.session_state["notif_email"] = tautan_email
                
                st.rerun()
    
    if "pesan_sukses" in st.session_state:
        st.success(st.session_state["pesan_sukses"])
        del st.session_state["pesan_sukses"]

    if "pesan_peringatan" in st.session_state:
        st.warning(st.session_state["pesan_peringatan"])
        del st.session_state["pesan_peringatan"]

    if "notif_email" in st.session_state:
        st.info(":blue[:material/info:] Tiket ditutup. Klik tombol di bawah untuk membuka aplikasi email Anda:")
        st.link_button("Kirim Notifikasi Email", st.session_state["notif_email"])
        del st.session_state["notif_email"]

    st.divider()
    st.subheader(":grey[:material/settings:] Pengaturan Akun")

    # Posisi di Superadmin
    if st.session_state["role_aktif"] == "superadmin":
        
        # Tampilkan daftar admin
        st.markdown("**Daftar Tim IT (Admin):**")
        data_admin = ambil_semua_admin()
        if data_admin:
            df_admin = pd.DataFrame(data_admin, columns=["Username", "Jabatan"])
            st.dataframe(df_admin, hide_index=True)
        else:
            st.info(":material/info: Belum ada admin lain yang terdaftar.")

        col_admin1, col_admin2, col_admin3 = st.columns(3)
        
        # Form Tambah Admin Baru
        with col_admin1:
            with st.expander("Tambah Admin Baru"):
                user_baru = st.text_input("Username Baru")
                pass_baru = st.text_input("Password Baru", type="password")
                if st.button("Daftarkan Admin"):
                    if user_baru == "" or pass_baru == "":
                        st.error(":red[:material/error:] Data tidak boleh kosong!")
                    else:
                        sukses = tambah_admin(user_baru, pass_baru)
                        if sukses:
                            st.success(f"Admin {user_baru} berhasil ditambah!")
                            st.rerun()
                        else:
                            st.error(":red[:material/error:] Username sudah terdaftar!")

        # Form Ubah Password Superadmin
        with col_admin2:
            with st.expander("Hapus Admin"):
                daftar_admin = ambil_semua_admin()

                if daftar_admin:
                    pilihan_username = [admin[0] for admin in daftar_admin] 
                    target_hapus = st.selectbox("Pilih Admin", pilihan_username, index=None, placeholder= "Pilih Admin yang Akan Dihapus", label_visibility="collapsed")
                    if st.button("Hapus Akun"):
                        if target_hapus:
                            hapus_admin(target_hapus)
                            st.success(f":material/delete: Akun admin {target_hapus} berhasil dihapus permanen.")
                            st.rerun()
                else:
                    st.info(":material/info: Tidak ada admin.")

        with col_admin3:
            with st.expander("Ubah Password"):
                daftar_admin = ambil_semua_admin()

                if daftar_admin:
                    pilihan_username = [admin[0] for admin in daftar_admin]
                    target_ubah = st.selectbox("Pilih Admin", pilihan_username, key="reset_admin", index=None, placeholder="Pilih Admin", label_visibility="collapsed")
                    pass_darurat = st.text_input("Password Darurat", type="password")

                    if st.button("Ubah Password"):
                        if target_ubah and pass_darurat != "":
                            ubah_password(target_ubah, pass_darurat)
                            st.success(f":green[:material/check_circle:] Password admin {target_ubah} sukses diubah!")
                            st.rerun()
                        else:
                            st.error(":red[:material/error:] Pilih admin dan isi password darurat!")

                else:
                    st.info(":material/info: Tidak ada admin.")

    elif st.session_state["role_aktif"] == "admin":
        with st.expander(":orange[:material/key:] Ubah Password Saya"):
            pass_admin = st.text_input("Password Baru", type="password")
            if st.button("Simpan Password"):
                if pass_admin != "":
                    ubah_password(st.session_state["username_aktif"], pass_admin)
                    st.success(":green[:material/check_circle:] Password berhasil diubah!")
                else:
                    st.error(":red[:material/error:] Password tidak boleh kosong!")

# Aplikasi
# Menentukan default halaman dari URL saat layar direfresh
index_halaman = 0
halaman_sekarang = st.query_params.get("halaman")

if halaman_sekarang == "cek_status":
    index_halaman = 1
elif halaman_sekarang == "admin":
    index_halaman = 2

# Tab menu navigasi halaman
halaman = st.radio(
    "Navigasi", 
    ["Formulir Pelaporan", "Cek Status Tiket", "Dashboard Admin"], 
    horizontal=True,
    index=index_halaman,
    label_visibility="collapsed" 
)

st.divider()

# Menyimpan pilihan halaman ke URL agar tidak hilang saat direfresh
if halaman == "Formulir Pelaporan":
    st.query_params["halaman"] = "user"
    halaman_tiket()

elif halaman == "Cek Status Tiket":
    st.query_params["halaman"] = "cek_status"
    halaman_status()

elif halaman == "Dashboard Admin":
    st.query_params["halaman"] = "admin"
    
    if "sudah_login" not in st.session_state:
        token_aktif = st.query_params.get("token")
        if token_aktif:
            data_sesi = cek_sesi(token_aktif)
            if data_sesi:
                st.session_state["sudah_login"] = True
                st.session_state["username_aktif"] = data_sesi[0]
                st.session_state["role_aktif"] = data_sesi[1]
                st.query_params["token"] = data_sesi[2]
            else:
                st.session_state["sudah_login"] = False
        else:
            st.session_state["sudah_login"] = False

    # Jika belum login
    if not st.session_state["sudah_login"]:
        st.subheader(":material/login: Login Akses Admin")
        username = st.text_input("Masukkan username:")
        password = st.text_input("Masukkan password:", type="password")

        if "login_attempts" not in st.session_state:
            st.session_state["login_attempts"] = 0
        
        if st.button("Masuk"):
            # Blokir jika mencoba masuk saat jatah sudah habis
            if st.session_state["login_attempts"] >= 5:
                st.error(":red[:material/block:] Terlalu banyak percobaan. Muat ulang halaman.")
                st.stop()
            
            peran = cek_login(username, password)
            if peran:
                st.session_state["login_attempts"] = 0
                st.session_state["sudah_login"] = True
                st.session_state["username_aktif"] = username
                st.session_state["role_aktif"] = peran

                token_baru = buat_sesi(username, peran)
                st.query_params["token"] = token_baru
                st.rerun()
            else:
                st.session_state["login_attempts"] += 1
                sisa_percobaan = 5 - st.session_state["login_attempts"]

                if sisa_percobaan > 0:
                    st.error(f":red[:material/error:] Username atau password salah! Sisa percobaan: {sisa_percobaan}")
                else:
                    st.error(":red[:material/block:] Percobaan habis. Akses diblokir sementara, silakan muat ulang halaman.")
                    st.stop()

    # Jika sudah login
    else:
        col1, col2 = st.columns([8, 2])
        with col2:
            if st.button(":material/logout: Logout"):
                token_hapus = st.query_params.get("token")
                if token_hapus:
                    hapus_sesi(token_hapus)
                
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
        
        halaman_admin()