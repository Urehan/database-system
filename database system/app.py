from flask import Flask, request, send_file
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        mdb_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(mdb_path)

        schema_path = os.path.join(OUTPUT_FOLDER, "schema.sql")
        data_path = os.path.join(OUTPUT_FOLDER, "data.sql")

        # Convert schema
        subprocess.run(f"mdb-schema {mdb_path} mysql > {schema_path}", shell=True)

        # Convert data (example table, baad mein dynamic karenge)
        subprocess.run(f"mdb-export {mdb_path} KAA > {data_path}", shell=True)

        return f"""
        <h3>Conversion Complete ✅</h3>
        <a href="/download/schema">Download Schema SQL</a><br>
        <a href="/download/data">Download Data SQL</a>
        """

    return """
    <h2>Upload KAA MDB File</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <button type="submit">Upload & Convert</button>
    </form>
    """

@app.route("/download/<filetype>")
def download_file(filetype):
    if filetype == "schema":
        return send_file("output/schema.sql", as_attachment=True)
    elif filetype == "data":
        return send_file("output/data.sql", as_attachment=True)

    return "Invalid file"

app.run(host="0.0.0.0", port=5000)
