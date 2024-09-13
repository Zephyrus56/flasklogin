from flask import Flask, render_template, request, redirect, url_for, make_response
import os
import MySQLdb
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Connect to the MySQL database
db = MySQLdb.connect("localhost", "newuser", "password", "testdb")
cursor = db.cursor()

# Utility function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route for the index page
@app.route('/')
def index():
    return redirect(url_for('show_anggota'))

# Route to display the anggota (anggota) page
@app.route('/anggota')
def show_anggota():
    cursor.execute("SELECT * FROM members")
    data = cursor.fetchall()
    return render_template('index.html', members=data, table_type="Anggota")

# Route to display the admin page
@app.route('/admin')
def show_admin():
    cursor.execute("SELECT * FROM admin")
    data = cursor.fetchall()
    return render_template('index.html', members=data, table_type="Admin")

# Route to display the transaksi page
@app.route('/transaksi')
def show_transaksi():
    cursor.execute("""
        SELECT transaksi.id, COALESCE(members.name, admin.name) AS nama, transaksi.nama_barang, transaksi.quantity, transaksi.harga, transaksi.total, transaksi.image_path
        FROM transaksi
        LEFT JOIN members ON transaksi.anggota_id = members.id
        LEFT JOIN admin ON transaksi.admin_id = admin.id
    """)
    data = cursor.fetchall()
    return render_template('transaksi.html', transaksi=data)

@app.route('/save_transaksi', methods=['POST'])
def save_transaksi():
    role = request.form['role']  # Role: 'anggota' atau 'admin'
    anggota_admin_id = request.form['id']  # ID anggota atau admin
    nama_barang = request.form['nama_barang']
    quantity = request.form['quantity']
    harga = request.form['harga']
    image = request.files['file']

    # Validasi role untuk memeriksa apakah ID ada di tabel yang sesuai
    if role == 'anggota':
        cursor.execute("SELECT * FROM members WHERE id = %s", (anggota_admin_id,))
    else:
        cursor.execute("SELECT * FROM admin WHERE id = %s", (anggota_admin_id,))
    
    id_check = cursor.fetchone()

    # Jika ID tidak ditemukan, return error
    if not id_check:
        return "Error: The ID does not exist in the selected role's table.", 400
    
    # Hitung total sebagai quantity * harga
    total = float(quantity) * float(harga)

    # Simpan file image jika ada
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        filename = None

    # Simpan transaksi dengan validasi anggota_id atau admin_id
    cursor.execute("""
        INSERT INTO transaksi (anggota_id, admin_id, nama_barang, quantity, harga, total, image_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (anggota_admin_id if role == 'anggota' else None,
         None if role == 'anggota' else anggota_admin_id,
         nama_barang, quantity, harga, total, filename))
    
    db.commit()

    return redirect(url_for('show_transaksi'))

@app.route('/update_transaksi', methods=['POST'])
def update_transaksi():
    transaksi_id = request.form['transaksi_id']
    nama_barang = request.form['nama_barang']
    quantity = request.form['quantity']
    harga = request.form['harga']
    
    # Hitung ulang total berdasarkan quantity dan harga
    total = float(quantity) * float(harga)
    
    # Pastikan transaksi_id valid
    cursor.execute("SELECT * FROM transaksi WHERE id = %s", (transaksi_id,))
    existing_transaksi = cursor.fetchone()
    
    if not existing_transaksi:
        return "Error: Transaksi tidak ditemukan.", 400

    # Lakukan update pada transaksi
    cursor.execute("""
        UPDATE transaksi 
        SET nama_barang = %s, quantity = %s, harga = %s, total = %s
        WHERE id = %s
    """, (nama_barang, quantity, harga, total, transaksi_id))
    
    db.commit()
    return redirect(url_for('show_transaksi'))

@app.route('/delete_transaksi', methods=['POST'])
def delete_transaksi():
    transaksi_id = request.form['transaksi_id']
    
    # Pastikan transaksi_id valid
    cursor.execute("SELECT * FROM transaksi WHERE id = %s", (transaksi_id,))
    existing_transaksi = cursor.fetchone()

    if not existing_transaksi:
        return "Error: Transaksi tidak ditemukan.", 400

    # Hapus transaksi dari tabel
    cursor.execute("DELETE FROM transaksi WHERE id = %s", (transaksi_id,))
    
    db.commit()
    return redirect(url_for('show_transaksi'))

@app.route('/report', methods=['GET', 'POST'])
def report_page():
    if request.method == 'POST':
        num_records = request.form['num_records']
        # Fetch the required number of records from the transaksi table
        cursor.execute("SELECT * FROM transaksi LIMIT %s", (num_records,))
        transaksi_list = cursor.fetchall()

        # Render the report HTML page with the data
        return render_template('report.html', transaksi_list=transaksi_list)
    
    # Display the report page with a form to choose the number of records
    return render_template('report.html')

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # Query data dari database
    cursor.execute("""
        SELECT COALESCE(members.name, admin.name) AS nama, transaksi.nama_barang, transaksi.quantity, transaksi.harga, transaksi.total
        FROM transaksi
        LEFT JOIN members ON transaksi.anggota_id = members.id
        LEFT JOIN admin ON transaksi.admin_id = admin.id
    """)
    data = cursor.fetchall()

    # Render template HTML untuk PDF
    html = render_template('report.html', transaksi_list=data)

    # Generate PDF menggunakan xhtml2pdf
    response = make_response()
    pdf = pisa.CreatePDF(html, dest=response)

    if not pdf.err:
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=transaction_report.pdf'
        return response
    else:
        return "Error creating PDF", 500

def pdf_from_html(html_content):
    pdf = pisa.pisaDocument(html_content)
    return pdf.dest.getvalue()

@app.route('/report', methods=['GET'])
def report():
    # Get the current page number from query parameters (default to page 1)
    page = int(request.args.get('page', 1))
    per_page = 15
    offset = (page - 1) * per_page

    # Fetch 15 records at a time using LIMIT and OFFSET
    cursor.execute("SELECT * FROM transaksi LIMIT %s OFFSET %s", (per_page, offset))
    transaksi_list = cursor.fetchall()

    return render_template('report.html', transaksi_list=transaksi_list, page=page)

@app.route('/save_user', methods=['POST'])
def save_user():
    user_type = request.form['user_type']  # 'anggota' or 'admin'
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    if user_type == 'anggota':
        cursor.execute("INSERT INTO members (name, email, phone) VALUES (%s, %s, %s)", (name, email, phone))
    elif user_type == 'admin':
        cursor.execute("INSERT INTO admin (name, email, phone) VALUES (%s, %s, %s)", (name, email, phone))
    
    db.commit()
    return redirect(url_for('show_anggota') if user_type == 'anggota' else url_for('show_admin'))

@app.route('/update_user', methods=['POST'])
def update_user():
    user_type = request.form['user_type']  # 'anggota' or 'admin'
    user_id = request.form['user_id']
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    if user_type == 'anggota':
        cursor.execute("""
            UPDATE members SET name = %s, email = %s, phone = %s WHERE id = %s
        """, (name, email, phone, user_id))
    elif user_type == 'admin':
        cursor.execute("""
            UPDATE admin SET name = %s, email = %s, phone = %s WHERE id = %s
        """, (name, email, phone, user_id))
    
    db.commit()
    return redirect(url_for('show_anggota') if user_type == 'anggota' else url_for('show_admin'))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_type = request.form['user_type']  # 'anggota' or 'admin'
    user_id = request.form['user_id']

    if user_type == 'anggota':
        cursor.execute("DELETE FROM members WHERE id = %s", (user_id,))
    elif user_type == 'admin':
        cursor.execute("DELETE FROM admin WHERE id = %s", (user_id,))
    
    db.commit()
    return redirect(url_for('show_anggota') if user_type == 'anggota' else url_for('show_admin'))



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
