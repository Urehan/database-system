from flask import Flask, request, send_file
import pandas as pd
import mysql.connector
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from email.message import EmailMessage
import smtplib
import os

app = Flask(__name__)
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Table mapping for dynamic detection
table_mapping = {
    "customer": ["customer", "customers", "client", "clients"],
    "ledger": ["ledger", "transactions", "accounts"],
    "cashbook": ["cashbook", "cash", "daily_cash", "cashbook_daily"],
    "stock": ["stock", "inventory", "items", "product_stock"]
}

# SQL connection
def connect_sql(host, user, password, database):
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

# Detect required tables dynamically
def detect_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    db_tables = [t[0].lower() for t in cursor.fetchall()]
    detected = {}
    for key, aliases in table_mapping.items():
        for t in db_tables:
            if t in aliases:
                detected[key] = t
    return detected

# Excel & PDF generation
def generate_excel(df, file_path):
    df.to_excel(file_path, index=False)

def generate_pdf(df, file_path):
    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.gray),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    pdf.build([table])

# Generate reports from SQL tables
def generate_reports(conn, detected_tables):
    reports = []
    for alias, table_name in detected_tables.items():
        try:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            excel_file = os.path.join(OUTPUT_FOLDER, f"{alias}.xlsx")
            pdf_file = os.path.join(OUTPUT_FOLDER, f"{alias}.pdf")
            generate_excel(df, excel_file)
            generate_pdf(df, pdf_file)
            reports.append((excel_file, pdf_file))
        except Exception as e:
            print(f"Error generating report for {table_name}: {e}")
    return reports

# Email sending function
def send_email(reports, recipient):
    msg = EmailMessage()
    msg['Subject'] = 'Your SQL Reports'
    msg['From'] = 'noreply@database-system.com'
    msg['To'] = recipient
    msg.set_content('Attached are your requested reports.')

    for excel_file, pdf_file in reports:
        for f in [excel_file, pdf_file]:
            with open(f,'rb') as file:
                msg.add_attachment(file.read(), maintype='application', subtype='octet-stream', filename=os.path.basename(f))

    # Gmail SMTP (use app password)
    with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
        smtp.login("your@gmail.com","app-password")
        smtp.send_message(msg)

# Flask routes
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        host = request.form["host"]
        user = request.form["user"]
        password = request.form["password"]
        database = request.form["database"]
        email = request.form.get("email")

        conn = connect_sql(host, user, password, database)
        detected_tables = detect_tables(conn)

        if not detected_tables:
            return "No required tables found in this database."

        reports = generate_reports(conn, detected_tables)

        if email:
            send_email(reports, email)

        download_links = "".join([f'<a href="/download/{os.path.basename(f)}">{os.path.basename(f)}</a><br>' for r in reports for f in r])
        return f"<h3>Reports Generated ✅</h3>{download_links}<br>Email sent to: {email if email else 'N/A'}"

    return """
    <h2>Connect to SQL Database</h2>
    <form method="POST">
        <input type="text" name="host" placeholder="Host" required><br><br>
        <input type="text" name="user" placeholder="User" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <input type="text" name="database" placeholder="Database Name" required><br><br>
        <input type="email" name="email" placeholder="Enter your email to receive reports"><br><br>
        <button type="submit">Generate Reports</button>
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
