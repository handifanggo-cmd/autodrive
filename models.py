import psycopg2
import psycopg2.extras
import os
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

def get_db_connection():
    try:
        connection_url = os.getenv('DATABASE_URL')
        if connection_url:
            return psycopg2.connect(connection_url, cursor_factory=psycopg2.extras.DictCursor)
        
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'db.soebeuvybyupvorxaqkr.supabase.co'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASS', '@fanggo081121'),
            port=os.getenv('DB_PORT', '6543'),
            cursor_factory=psycopg2.extras.DictCursor,
            connect_timeout=10
        )
    except Exception as e:
        print(f"LOG: Koneksi Gagal: {e}")
        return None

class User:
    @staticmethod
    def register(username, password):
        conn = get_db_connection()
        if not conn: return "Koneksi ke database gagal!"
        try:
            cur = conn.cursor()
            u_name = username.strip()
            cur.execute("SELECT username FROM users WHERE username = %s", (u_name,))
            if cur.fetchone(): return "Username sudah ada!"
            
            hash_pw = generate_password_hash(password.strip())
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                       (u_name, hash_pw, 'customer'))
            conn.commit()
            return True
        except Exception as e: return f"Error Database: {str(e)}"
        finally: conn.close()

    @staticmethod
    def check_login(username, password):
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            u_name = username.strip()
            u_pass = password.strip()
            
            cur.execute("SELECT * FROM users WHERE username = %s", (u_name,))
            user = cur.fetchone()
            cur.close()
            
            if user:
                if str(user['password']).strip() == u_pass:
                    return user
                
                try:
                    if check_password_hash(user['password'], u_pass):
                        return user
                except:
                    pass
            return None
        finally: 
            conn.close()

class Mobil:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM mobil ORDER BY id_mobil DESC")
            return cur.fetchall()
        finally: conn.close()

class Sewa:
    @staticmethod
    def create(id_mobil, nama, telp, tgl_p, tgl_k, warna):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT harga_sewa, stok FROM mobil WHERE id_mobil = %s", (id_mobil,))
            mobil = cur.fetchone()
            
            if not mobil or mobil['stok'] <= 0:
                print("LOG: Stok habis!")
                return False

            harga_per_hari = mobil['harga_sewa']
            d1 = datetime.strptime(tgl_p, '%Y-%m-%d')
            d2 = datetime.strptime(tgl_k, '%Y-%m-%d')
            jumlah_hari = (d2 - d1).days
            if jumlah_hari <= 0: jumlah_hari = 1 
            
            total_bayar = jumlah_hari * harga_per_hari
            

            cur.execute("""
                INSERT INTO sewa (id_mobil, nama_penyewa, no_telp, warna_pilihan, tgl_pesan, tgl_kembali, total_harga, status_sewa) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Proses')
            """, (id_mobil, nama.strip(), telp.strip(), warna, tgl_p, tgl_k, total_bayar))

            cur.execute("UPDATE mobil SET stok = stok - 1 WHERE id_mobil = %s", (id_mobil,))
            conn.commit()
            return True
        except Exception as e:
            print(f"LOG: Error create sewa: {e}")
            return False
        finally: conn.close()

    @staticmethod
    def selesaikan_sewa(id_sewa):
        conn = get_db_connection()
        if not conn: return False
        try:
            cur = conn.cursor()
            cur.execute("SELECT id_mobil, status_sewa FROM sewa WHERE id_sewa = %s", (id_sewa,))
            data = cur.fetchone()
            
            if data and data['status_sewa'] == 'Proses':
            
                cur.execute("UPDATE sewa SET status_sewa = 'Selesai' WHERE id_sewa = %s", (id_sewa,))
                cur.execute("UPDATE mobil SET stok = stok + 1 WHERE id_mobil = %s", (data['id_mobil'],))
                conn.commit()
                return True
            return False
        finally: conn.close()