# IT Ticketing System

Sistem manajemen tiket aduan IT internal yang dirancang untuk efisiensi pelaporan kendala teknis dan pemantauan progres perbaikan secara real-time. Dibangun menggunakan **Streamlit** dan didukung oleh **SQLite** untuk performa yang ringan namun tangguh.

## 🚀 Fitur Utama

### 🛠️ Untuk Pengguna (Pelapor)
* **Formulir Pelaporan Cepat**: Input data pelapor (Nama, Unit Kerja, Lantai) dan detail keluhan dengan kategori masalah.
* **Cek Status Tiket**: Pantau progres perbaikan menggunakan Nomor ID Tiket secara transparan.

### 🔐 Untuk Admin & Superadmin
* **Dashboard Metrik**: Visualisasi jumlah tiket (Open, In Progress, Closed) untuk pemantauan beban kerja.
* **Manajemen Status**: Update status tiket dengan alur logika yang ketat (Conflict Guard).
* **Sistem Keamanan Tinggi**:
    * **Brute Force Protection**: Pembatasan 5 kali percobaan login.
    * **Session Management**: Rotasi token sesi dan validasi durasi (8 jam).
    * **Role-Based Access Control (RBAC)**: Perbedaan akses antara Admin biasa dan Superadmin.
* **Ekspor Data**: Fitur unduh rekap seluruh data tiket dalam format Excel.

## 💻 Teknologi yang Digunakan

* **Frontend & UI**: [Streamlit](https://streamlit.io/)
* **Backend & Logic**: Python 3.12
* **Database**: SQLite3 (dengan optimasi index pada kolom status)
* **Security**: Werkzeug (Password Hashing)
* **Containerization**: Docker

## 📦 Instalasi & Deployment (Docker)

Pastikan Anda sudah menginstal Docker di sistem Anda.

1.  **Build Image**:
    ```bash
    docker build -t nama-image .
    ```

2.  **Jalankan Container (Production Mode - Port 80)**:
    ```bash
    docker run -d -p 80:8501 --name nama-container nama-image
    ```

3.  **Akses Aplikasi**:
    Buka browser dan akses melalui IP PC Statis Anda (misal: `http://192.168.1.1`) atau `http://localhost`.

## 📂 Struktur Proyek

```text
.
├── app.py              # File utama aplikasi Streamlit (UI Logic)
├── database.py         # Logika Database (CRUD, Auth, Session)
├── Dockerfile          # Instruksi pembuatan image Docker
├── requirements.txt    # Daftar dependensi Python
└── logo_app.png        # Aset visual aplikasi
