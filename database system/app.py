from flask import Flask, request, send_file
import os
import subprocess
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from email.message import EmailMessage
import smtplib

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Table mapping for reports
table_mapping = {
    "customer": ["customer", "customers", "client", "clients"],
    "ledger": ["ledger", "transactions", "accounts"],
    "cashbook": ["cashbook", "cash", "daily_cash", "cashbook_daily"],
    "stock": ["stock", "inventory", "items", "product_stock"]
}

# Generate Excel
def generate_excel(df, file_path):
    df.to_excel(file_path, index=False)

# Generate PDF
def generate_pdf(df, file_path):
    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.gray),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))
    pdf.build([table])

# Generate reports from SQL files
def generate_reports(sql_file_path):
    reports = []
    # First, get tables from SQL file (simple approach)
    with open(sql_file_path,'r',encoding='utf-8', errors='ignore') as f:
        content = f.read()
    detected_tables = []
    for key, aliases in table_mapping.items():
        for t in aliases:
            if f"CREATE TABLE `{t}`" in content or f"CREATE TABLE {t}" in content:
                detected_tables.append((key,t))
    for alias, table_name in detected_tables:
        try:
            import sqlite3
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            cursor.executescript(content)
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            excel_file = os.path.join(OUTPUT_FOLDER, f"{alias}.xlsx")
            pdf_file = os.path.join(OUTPUT_FOLDER, f"{alias}.pdf")
            generate_excel(df, excel_file)
            generate_pdf(df, pdf_file)
            reports.append((excel_file,pdf_file))
            conn.close()
        except Exception as e:
            print(f"Error generating report for {table_name}: {e}")
    return reports

# Send Email
def send_email(reports, recipient):
    msg = EmailMessage()
    msg['Subject'] = 'Your Reports from Access DB'
    msg['From'] = 'noreply@database-system.com'
    msg['To'] = recipient
    msg.set_content('Attached are your requested reports.')

    for excel_file, pdf_file in reports:
        for f in [excel_file, pdf_file]:
            with open(f,'rb') as file:
                msg.add_attachment(file.read(), maintype='application', subtype='octet-stream', filename=os.path.basename(f))

    with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
        smtp.login("your@gmail.com","app-password")
        smtp.send_message(msg)

# Flask routes
@app.route("/", methods=["GET","POST"])
def home():
    if request.method == "POST":
        file = request.files['file']
        email = request.form.get("email")
        mdb_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(mdb_path)

        # Convert MDB → SQL (MySQL format)
        sql_path = os.path.join(OUTPUT_FOLDER, "database.sql")
        subprocess.run(f"mdb-schema {mdb_path} mysql > {sql_path}", shell=True)

        # Generate reports
        reports = generate_reports(sql_path)

        # Send email if provided
        if email:
            send_email(reports, email)

        download_links = "".join([f'<a href="/download/{os.path.basename(f)}">{os.path.basename(f)}</a><br>'
                                  for r in reports for f in r])
        return f"<h3>Reports Generated ✅</h3>{download_links}<br>Email sent to: {email if email else 'N/A'}"

    return """
    <h2>Upload Access 1998 MDB File</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" required><br><br>
        <input type="email" name="email" placeholder="Enter email to receive reports"><br><br>
        <button type="submit">Upload & Generate Reports</button>
    </form>
    """

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port, debug=True)
