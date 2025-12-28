from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import User, Mobil, Sewa, get_db_connection
import os

app = Flask(__name__)
app.secret_key = "autodrive_pro_key"

app = app 

@app.template_filter('format_rupiah')
def format_rupiah(value):
    return f"{value:,.0f}".replace(",", ".")

@app.route("/")
def index():
    if "logged_in" in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('customer_dashboard'))
    return render_template("portal.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_pw = request.form.get("confirm_password")
        if password != confirm_pw:
            flash("Password tidak cocok!", "danger")
            return redirect(url_for("register"))
        result = User.register(username, password) 
        if result is True:
            flash("Registrasi Berhasil! Silakan Login.", "success")
            return redirect(url_for("login_customer"))
        else:
            flash(f"Gagal: {result}", "danger")
    return render_template("register.html")

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        user = User.check_login(request.form.get("username"), request.form.get("password"))
        if user and user['role'] == 'admin':
            session.update({"logged_in": True, "username": user["username"], "role": "admin"})
            return redirect(url_for("admin_dashboard"))
        flash("Login Admin Gagal!", "danger")
    return render_template("login_admin.html")

@app.route("/login/customer", methods=["GET", "POST"])
def login_customer():
    if request.method == "POST":
        user = User.check_login(request.form.get("username"), request.form.get("password"))
        if user and user['role'] == 'customer':
            session.update({"logged_in": True, "username": user["username"], "role": "customer"})
            return redirect(url_for("customer_dashboard"))
        flash("Login Customer Gagal!", "danger")
    return render_template("login_customer.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    return render_template("admin_dashboard.html", daftar_mobil=Mobil.get_all())

@app.route("/admin/laporan")
def admin_laporan():
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        query = """
            SELECT s.id_sewa, s.nama_penyewa, s.no_telp, 
                   m.nama_mobil, s.tgl_pesan, s.tgl_kembali, 
                   s.total_harga, s.status_sewa, s.warna_pilihan
            FROM sewa s
            JOIN mobil m ON s.id_mobil = m.id_mobil
            ORDER BY s.id_sewa DESC
        """
        try:
            cur.execute(query)
            laporan = cur.fetchall()
            cur.close(); conn.close()
            return render_template("admin_laporan.html", laporan=laporan)
        except Exception as e:
            if conn: conn.close()
            return f"Detail Error Database: {e}"
    return "Gagal koneksi ke database"

@app.route("/admin/sewa/selesai/<int:id_sewa>", methods=["POST"])
def admin_selesai_sewa(id_sewa):
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    if Sewa.selesaikan_sewa(id_sewa):
        flash("Mobil telah dikembalikan, stok bertambah!", "success")
    else:
        flash("Gagal memproses data.", "danger")
    return redirect(url_for('admin_laporan'))

@app.route("/admin/laporan/hapus/<int:id_sewa>")
def hapus_laporan(id_sewa):
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT id_mobil, status_sewa FROM sewa WHERE id_sewa = %s", (id_sewa,))
        res = cur.fetchone()
        if res:
            id_mobil, status = res
            cur.execute("DELETE FROM sewa WHERE id_sewa = %s", (id_sewa,))
            if status == 'Proses':
                cur.execute("UPDATE mobil SET stok = stok + 1 WHERE id_mobil = %s", (id_mobil,))
            conn.commit()
            flash('Data laporan berhasil dihapus!', 'success')
        cur.close(); conn.close()
    return redirect(url_for('admin_laporan'))

@app.route('/mobil/tambah', methods=['POST'])
def tambah_mobil():
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    nama = request.form.get('nama')
    merk = request.form.get('merk')
    harga = request.form.get('harga')
    stok = request.form.get('stok')
    url_foto = request.form.get('url_foto')
    warna = request.form.get('warna')
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO mobil (nama_mobil, merk, harga_sewa, stok, foto, warna, status) VALUES (%s, %s, %s, %s, %s, %s, 'Tersedia')",
                    (nama, merk, harga, stok, url_foto, warna))
        conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/mobil/edit/<int:id_mobil>', methods=['POST'])
def edit_mobil(id_mobil):
    if session.get('role') != 'admin': return redirect(url_for('login_admin'))
    nama = request.form.get('nama')
    harga = request.form.get('harga')
    stok = request.form.get('stok')
    url_foto = request.form.get('url_foto')
    warna = request.form.get('warna')
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("UPDATE mobil SET nama_mobil=%s, harga_sewa=%s, stok=%s, foto=%s, warna=%s WHERE id_mobil=%s",
                    (nama, harga, stok, url_foto, warna, id_mobil))
        conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/customer/dashboard")
def customer_dashboard():
    if session.get('role') != 'customer': return redirect(url_for('login_customer'))
    return render_template("customer_dashboard.html", daftar_mobil=Mobil.get_all())

@app.route('/sewa/proses/<int:id_mobil>', methods=['POST'])
def proses_sewa(id_mobil):
    if session.get('role') != 'customer': 
        return redirect(url_for('login_customer'))
    nama = request.form.get('nama_penyewa')
    telp = request.form.get('no_telp')
    warna = request.form.get('warna_pilihan')
    tgl_p = request.form.get('tgl_pinjam')
    tgl_k = request.form.get('tgl_kembali')
    if Sewa.create(id_mobil, nama, telp, tgl_p, tgl_k, warna):
        flash(f'Booking Mobil Warna {warna} Berhasil!', 'success')
        return redirect(url_for('customer_dashboard'))
    else:
        flash('Gagal memesan. Mungkin stok habis atau tanggal salah.', 'danger')
        return redirect(url_for('customer_dashboard'))

if __name__ == "__main__":
    app.run()