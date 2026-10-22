from flask import Flask, render_template, request, redirect, session, send_from_directory, jsonify

import mysql.connector

import os

from werkzeug.utils import secure_filename

from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__)

app.secret_key = "secret123"



UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)



# ================= DB CONNECTION =================

def get_db():

    return mysql.connector.connect(

        host="localhost",

        user="root",

        password="2082006",

        database="university_system",

        autocommit=True

    )



# ================= HELPER FUNCTIONS =================

def send_notification(user_id, message):

    """دالة لإرسال إشعار للمستخدم"""

    if user_id is None: return

    db = get_db()

    cur = db.cursor()

    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, message))

    db.close()



# ================= LOGIN & AUTH =================

@app.route("/")

def home():

    return redirect("/login")



@app.route("/register", methods=["GET", "POST"])

def register():

    if request.method == "POST":

        db = get_db()

        cur = db.cursor()

        name = request.form["name"]

        email = request.form["email"]

        password = request.form["password"]

        uni_id = request.form["university_id"]



        hashed_password = generate_password_hash(password)

        try:

            cur.execute("""

                INSERT INTO users (name, email, password, university_id, role, profile_pic)

                VALUES (%s, %s, %s, %s, 'student', 'default_avatar.png')

            """, (name, email, hashed_password, uni_id))

            db.close()

            return redirect("/login")

        except:

            return render_template("register.html", msg="❌ Error: Email or ID might exist")

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])

def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]



        if email == "ahmedmady@gmail.com" and password == "123456":

            session["id"] = 0

            session["name"] = "Ahmed Mady"

            session["role"] = "admin"

            session["profile_pic"] = "default_avatar.png"

            return redirect("/dashboard")



        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))

        user = cur.fetchone()

        db.close()



        if user and check_password_hash(user["password"], password):

            session["id"] = user["id"]

            session["name"] = user["name"]

            session["role"] = user["role"]

            session["profile_pic"] = user["profile_pic"] if user["profile_pic"] else "default_avatar.png"

            return redirect("/dashboard")

        return render_template("login.html", msg="❌ Wrong credentials")

    return render_template("login.html")



# ================= PROFILE & PIC UPLOAD =================

@app.route("/profile")

def profile():

    if "id" not in session: return redirect("/login")

   

    user_id = session["id"]

    db = get_db()

    cur = db.cursor(dictionary=True)

   

    if user_id == 0:

        user_info = {'name': 'Ahmed Mady', 'email': 'ahmedmady@gmail.com', 'university_id': 'Admin', 'role': 'admin', 'profile_pic': 'default_avatar.png'}

    else:

        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))

        user_info = cur.fetchone()



    cur.execute("""

        SELECT

            uploads.*,

            subjects.name as subject_name,

            (SELECT COUNT(*) FROM likes WHERE upload_id = uploads.id) as likes_count

        FROM uploads

        JOIN subjects ON uploads.subject_id = subjects.id

        WHERE uploads.user_id = %s OR (uploads.user_id IS NULL AND %s=0)

        ORDER BY uploads.id DESC

    """, (user_id, user_id))

    user_files = cur.fetchall()

   

    db.close()

    return render_template("profile.html", user=user_info, files=user_files)



@app.route("/upload_profile_pic", methods=["POST"])

def upload_profile_pic():

    if "id" not in session: return redirect("/login")

   

    file = request.files.get("profile_pic")

    if file and file.filename != "":

        filename = f"user_{session['id']}_{secure_filename(file.filename)}"

        file.save(os.path.join(UPLOAD_FOLDER, filename))

       

        db = get_db()

        cur = db.cursor()

        cur.execute("UPDATE users SET profile_pic=%s WHERE id=%s", (filename, session["id"]))

        db.close()

        session["profile_pic"] = filename

       

    return redirect("/profile")



# ================= NOTIFICATIONS =================

@app.route("/notifications")

def notifications():

    if "id" not in session: return redirect("/login")

    db = get_db()

    cur = db.cursor(dictionary=True)

   

    cur.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session["id"],))

    notifs = cur.fetchall()

   

    cur.execute("UPDATE notifications SET is_read=True WHERE user_id=%s", (session["id"],))

    db.close()

    return render_template("notifications.html", notifications=notifs)



# ================= DASHBOARD & SEARCH =================

@app.route("/dashboard")

def dashboard():

    if "id" not in session: return redirect("/login")

   

    search_query = request.args.get('search', '')

    db = get_db()

    cur = db.cursor(dictionary=True)

   

    if search_query:

        cur.execute("SELECT * FROM subjects WHERE name LIKE %s", (f"%{search_query}%",))

    else:

        cur.execute("SELECT * FROM subjects")

       

    subjects = cur.fetchall()

    db.close()

    return render_template("dashboard.html", subjects=subjects, search_query=search_query)



@app.route("/view_level/<int:lvl>/<int:sem>")

def view_level(lvl, sem):

    if "id" not in session: return redirect("/login")

    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM subjects WHERE level=%s AND semester=%s", (lvl, sem))

    subjects = cur.fetchall()

    db.close()

    return render_template("level_subjects.html", subjects=subjects, lvl=lvl, sem=sem)



# ================= SUBJECT PAGE & UPLOADS =================



@app.route("/add_subject", methods=["POST"])

def add_subject():

    """إضافة مادة جديدة - متاحة الآن للأدمن وأي مستخدم مسجل دخول"""

    if "id" not in session:

        return redirect("/login")



    name = request.form.get("name")

    level = request.form.get("level")

    semester = request.form.get("semester")



    if name and level and semester:

        db = get_db()

        cur = db.cursor()

        cur.execute("INSERT INTO subjects (name, level, semester) VALUES (%s, %s, %s)",

                    (name, level, semester))

        db.close()

   

    return redirect(request.referrer)



@app.route("/subject/<int:id>", methods=["GET", "POST"])

def subject(id):

    if "id" not in session: return redirect("/login")

    db = get_db()

   

    uploader_id = session.get("id")

    if uploader_id == 0: uploader_id = None



    if request.method == "POST":

        file = request.files.get("file")

        file_type = request.form.get("file_type", "General")

       

        if file and file.filename != "":

            filename = secure_filename(file.filename)

            file.save(os.path.join(UPLOAD_FOLDER, filename))

            cur_up = db.cursor()

            cur_up.execute("""

                INSERT INTO uploads (subject_id, user_id, file_name, status, file_type)

                VALUES (%s, %s, %s, 'pending', %s)

            """, (id, uploader_id, filename, file_type))



    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM subjects WHERE id=%s", (id,))

    subject_info = cur.fetchone()



    cur.execute("""

        SELECT

            uploads.*,

            COALESCE(users.name, 'Admin') as uploader_name,

            (SELECT COUNT(*) FROM likes WHERE upload_id = uploads.id) as likes_count,

            (SELECT COUNT(*) FROM comments WHERE upload_id = uploads.id) as comments_count

        FROM uploads

        LEFT JOIN users ON uploads.user_id = users.id

        WHERE subject_id=%s AND (status='approved' OR user_id=%s OR (user_id IS NULL AND %s=0))

    """, (id, session["id"], session["id"]))

    files = cur.fetchall()

   

    for file in files:

        cur.execute("""

            SELECT comments.*, COALESCE(users.name, 'Admin') as user_name

            FROM comments

            LEFT JOIN users ON comments.user_id = users.id

            WHERE upload_id = %s ORDER BY created_at ASC

        """, (file['id'],))

        file['comments'] = cur.fetchall()



    db.close()

    return render_template("subject.html", subject=subject_info, files=files)



# ================= INTERACTIONS =================



@app.route("/add_comment/<int:upload_id>", methods=["POST"])

def add_comment(upload_id):

    if "id" not in session: return redirect("/login")

    comment_text = request.form.get("comment_text")

    user_id = session.get("id")

    user_name = session.get("name")

    if user_id == 0: user_id = None



    if comment_text:

        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT user_id, file_name FROM uploads WHERE id=%s", (upload_id,))

        upload = cur.fetchone()

       

        cur.execute("INSERT INTO comments (upload_id, user_id, comment_text) VALUES (%s, %s, %s)",

                    (upload_id, user_id, comment_text))

       

        if upload and upload['user_id'] and upload['user_id'] != user_id:

            send_notification(upload['user_id'], f"💬 علق {user_name} على ملفك: {upload['file_name']}")

       

        db.close()

    return redirect(request.referrer)



@app.route("/like/<int:upload_id>")

def like_file(upload_id):

    if "id" not in session: return redirect("/login")

    user_id = session.get("id")

    if user_id == 0: user_id = None



    db = get_db()

    cur = db.cursor()

    try:

        cur.execute("INSERT INTO likes (upload_id, user_id) VALUES (%s, %s)", (upload_id, user_id))

    except:

        cur.execute("DELETE FROM likes WHERE upload_id=%s AND (user_id=%s OR (user_id IS NULL AND %s IS NULL))",

                    (upload_id, user_id, user_id))

    db.close()

    return redirect(request.referrer)



# ================= ADMIN ACTIONS & DELETE =================



@app.route("/delete_file/<int:id>", methods=["POST"])

def delete_file(id):

    if session.get("role") != "admin":

        return jsonify({"success": False, "message": "Unauthorized"}), 403



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT file_name FROM uploads WHERE id=%s", (id,))

    upload = cur.fetchone()



    if upload:

        try:

            file_path = os.path.join(UPLOAD_FOLDER, upload['file_name'])

            if os.path.exists(file_path):

                os.remove(file_path)

           

            cur.execute("DELETE FROM likes WHERE upload_id=%s", (id,))

            cur.execute("DELETE FROM comments WHERE upload_id=%s", (id,))

            cur.execute("DELETE FROM uploads WHERE id=%s", (id,))

            db.close()

            return jsonify({"success": True})

        except Exception as e:

            return jsonify({"success": False, "message": str(e)}), 500

   

    db.close()

    return jsonify({"success": False, "message": "File not found"}), 404



@app.route("/delete_subject/<int:id>", methods=["POST"])

def delete_subject(id):

    if session.get("role") != "admin":

        return jsonify({"success": False, "message": "Unauthorized"}), 403



    db = get_db()

    cur = db.cursor(dictionary=True)

    try:

        cur.execute("SELECT file_name FROM uploads WHERE subject_id=%s", (id,))

        subject_files = cur.fetchall()

        for f in subject_files:

            file_path = os.path.join(UPLOAD_FOLDER, f['file_name'])

            if os.path.exists(file_path):

                os.remove(file_path)



        cur.execute("DELETE FROM subjects WHERE id=%s", (id,))

        db.close()

        return jsonify({"success": True})

    except Exception as e:

        return jsonify({"success": False, "message": str(e)}), 500



@app.route("/admin")

def admin():

    if session.get("role") != "admin": return redirect("/login")

    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM users")

    users_list = cur.fetchall()

    cur.execute("""

        SELECT uploads.*, COALESCE(users.name, 'Admin') as user_name, subjects.name as sub_name

        FROM uploads

        LEFT JOIN users ON uploads.user_id = users.id

        JOIN subjects ON uploads.subject_id = subjects.id

        ORDER BY uploads.id DESC

    """)

    all_uploads = cur.fetchall()

    db.close()

    return render_template("admin.html", uploads=all_uploads, users=users_list)



@app.route("/approve/<int:id>")

def approve(id):

    if session.get("role") == "admin":

        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT user_id, file_name FROM uploads WHERE id=%s", (id,))

        upload = cur.fetchone()

        cur.execute("UPDATE uploads SET status='approved' WHERE id=%s", (id,))

        if upload and upload['user_id']:

            send_notification(upload['user_id'], f"✅ تم قبول ملفك: {upload['file_name']}")

        db.close()

    return redirect("/admin")



@app.route("/reject/<int:id>")

def reject(id):

    if session.get("role") == "admin":

        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT user_id, file_name FROM uploads WHERE id=%s", (id,))

        upload = cur.fetchone()

        cur.execute("UPDATE uploads SET status='rejected' WHERE id=%s", (id,))

        if upload and upload['user_id']:

            send_notification(upload['user_id'], f"❌ للأسف، تم رفض ملفك: {upload['file_name']}")

        db.close()

    return redirect("/admin")



# ================= FILE ACCESS & LOGOUT =================

@app.route("/preview/<filename>")

def preview(filename):

    return send_from_directory(UPLOAD_FOLDER, filename)



@app.route("/download/<filename>")

def download(filename):

    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)



@app.route("/logout")

def logout():

    session.clear()

    return redirect("/login")



if __name__ == "__main__":

    app.run(debug=True)