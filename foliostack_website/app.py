from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os
import uuid

app = Flask(__name__)
app.secret_key = "your_secret_key"

# db = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="0000",
#     database="foliostack"
# )
# cursor = db.cursor(dictionary=True)

UPLOAD_FOLDER = 'static/img/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    role = request.form.get("role")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect(url_for("index") + "#section-5")

    hashed_password = generate_password_hash(password)

    try:
        cursor.execute(
            "INSERT INTO users (role, username, email, password) VALUES (%s, %s, %s, %s)",
            (role, username, email, hashed_password)
        )
        db.commit()
        if role == "recruiter":
            # Get the new user's ID and store it in the session
            # to link it to the verification form.
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            session['new_recruiter_id'] = cursor.fetchone()['id']
            return redirect(url_for("verify_recruiter"))
        else:
            flash("Registration successful! Please log in.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Error: {e}", "danger")

    return redirect(url_for("index") + "#section-3")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # ---------- ADMIN LOGIN ----------
        if username == "admin" and password == "admin123":
            session["role"] = "admin"
            session["username"] = "admin"
            flash("Welcome Admin!", "success")
            return redirect(url_for("admin_panel"))

        # ---------- NORMAL USER LOGIN ----------
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            flash("Login successful!", "success")

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"].lower()

            if user["role"].lower() == "admin":
                return redirect(url_for("admin_panel"))
            elif user["role"].lower() == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            elif user["role"].lower() == "builder":
                return redirect(url_for("builder_dashboard"))
            else:
                flash("Unknown role for user.", "danger")
                return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("index") + "#section-3")

    return render_template("home.html")



# ---------------- DASHBOARD ----------------
@app.route("/dashboard/recruiter")
def recruiter_dashboard():
    if "user_id" not in session or session.get("role") != "recruiter":
        flash("Access denied!", "danger")
        return redirect(url_for("index") + "#section-3")

    # Check if the recruiter is approved
    cursor.execute("SELECT status FROM recruiter_verifications WHERE user_id = %s", (session['user_id'],))
    verification = cursor.fetchone()

    is_verified = verification and verification['status'] == 'verified'

    portfolios = []
    if is_verified:
        # Fetch all portfolios if the recruiter is verified
        cursor.execute("SELECT name, position, portfolio_url FROM user_data WHERE portfolio_url IS NOT NULL")
        portfolios = cursor.fetchall()


    return render_template("dashboard/recruiter.html", username=session["username"], is_verified=is_verified, portfolios=portfolios, is_dashboard=True)

@app.route("/dashboard/builder")
def builder_dashboard():
    if "user_id" not in session or session.get("role") != "builder":
        flash("Access denied!", "danger")
        return redirect(url_for("index") + "#section-3")

    # Fetch portfolio data for the logged-in user
    cursor.execute("SELECT * FROM user_data WHERE user_id = %s", (session['user_id'],))
    portfolio_data = cursor.fetchone()

    return render_template("dashboard/builder.html", username=session["username"], user=portfolio_data, is_dashboard=True)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# ---------------- CONTACT ----------------
@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    cursor.execute(
        "INSERT INTO contact (name, email, message) VALUES (%s, %s, %s)",
        (name, email, message)
    )
    db.commit()

    flash("Message sent successfully!", "success")
    return redirect(url_for("index") + "#section-4")

# ---------------- HOME ----------------
@app.route("/")
def index():
    return render_template("home.html")

# ---------------- VIEW PORTFOLIO ----------------
@app.route('/portfolio/<portfolio_slug>')
def view_portfolio(portfolio_slug):
    # Construct the full URL path to match what's in the database
    portfolio_url = f"/portfolio/{portfolio_slug}"
    cursor.execute("SELECT * FROM user_data WHERE portfolio_url = %s", (portfolio_url,))
    user = cursor.fetchone()
    if not user:
        flash("Portfolio not found", "danger")
        return redirect(url_for('index'))

    # Only allow verified recruiters or admins to view portfolios
    if session.get('role') == 'recruiter':
        cursor.execute("SELECT status FROM recruiter_verifications WHERE user_id = %s", (session.get('user_id'),))
        verification = cursor.fetchone()
        if not verification or verification['status'] != 'verified':
            flash("You must be a verified recruiter to view portfolios.", "danger")
            return redirect(url_for('recruiter_dashboard'))

    skills = user['skills'].split(',') if user['skills'] else []
    qualification_titles = user['qualification_titles'].split(',') if user['qualification_titles'] else []
    qualification_desc = user['qualification_desc'].split(',') if user['qualification_desc'] else []
    experience_titles = user['experience_titles'].split(',') if user['experience_titles'] else []
    experience_desc = user['experience_desc'].split(',') if user['experience_desc'] else []
    gallery_images = user['gallery_images'].split(',') if user['gallery_images'] else []
    certifications = user['certifications'].split(',') if user['certifications'] else []
    
    # Determine which template to render based on user's choice
    template_name = user.get('template', 'template1') # Default to template1 if not set
    if template_name == 'template2':
        template_file = 'portfolio-templates/created_portfolio2.html'
    else:
        template_file = 'portfolio-templates/created_portfolio1.html'

    return render_template(
        template_file,
        name=user['name'],
        email=user['email'],
        position=user['position'],
        about=user.get('about', ''),
        linkedin=user.get('linkedin', ''),
        github=user.get('github', ''),
        profile_image=user.get('profile_image', ''),
        skills=skills,
        qualification_titles=qualification_titles,
        qualification_desc=qualification_desc,
        experience_titles=experience_titles,
        experience_desc=experience_desc,
        gallery_images=gallery_images,
        certifications=certifications,
        user=user,
        zip=zip,
    )
@app.route('/preview/<template>', endpoint='preview_portfolio')
def preview_portfolio(template):
    # Simply render the template HTML file (static design)
    return render_template(f'portfolio-templates/{template}.html')



@app.route('/fill_form/<template>', methods=['GET', 'POST'])
def fill_form(template):
    if request.method == 'POST':
        # ---------------- POST: save form data ----------------
        name = request.form.get('name')
        email = request.form.get('email')
        position = request.form.get('position')
        linkedin = request.form.get('linkedin')
        about = request.form.get('about')
        github = request.form.get('github')

        # Skills
        skills = request.form.getlist('skills[]')
        skills_str = ','.join(skills)

        # Qualifications
        qualifications_titles = request.form.getlist('qualification_titles[]')
        qualifications_desc = request.form.getlist('qualification_desc[]')
        qualifications_titles_str = ','.join(qualifications_titles)
        qualifications_desc_str = ','.join(qualifications_desc)

        # Work Experiences
        experience_titles = request.form.getlist('experience_titles[]')
        experience_desc = request.form.getlist('experience_desc[]')
        experience_titles_str = ','.join(experience_titles)
        experience_desc_str = ','.join(experience_desc)

        # Profile image
        profile_image_file = request.files.get('profile_image')
        profile_image_filename = None
        if profile_image_file and allowed_file(profile_image_file.filename):
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_images'), exist_ok=True)
            profile_image_filename = f"{uuid.uuid4().hex}_{secure_filename(profile_image_file.filename)}"
            profile_image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_images', profile_image_filename))

        # Gallery
        gallery_images = []
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)
        for file in request.files.getlist('gallery_images[]'):
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery', filename))
                gallery_images.append(filename)
        gallery_str = ','.join(gallery_images)

        # Certifications
        certifications = []
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'certifications'), exist_ok=True)
        for file in request.files.getlist('certifications[]'):
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'certifications', filename))
                certifications.append(filename)
        certifications_str = ','.join(certifications)

        flash("Portfolio saved successfully!", "success")

        # Generate portfolio URL and update DB
        portfolio_slug = name.replace(' ', '_').lower()
        portfolio_url = f"/portfolio/{portfolio_slug}"
        cursor.execute("SELECT * FROM user_data WHERE user_id = %s", (session['user_id'],))

        user = cursor.fetchone()

        if user:
             cursor.execute("""
                 UPDATE user_data SET 
                     name=%s, email=%s, position=%s, about=%s, linkedin=%s, github=%s,
                     skills=%s, qualification_titles=%s, qualification_desc=%s,
                     experience_titles=%s, experience_desc=%s, template=%s, profile_image=%s,
                     gallery_images=%s, certifications=%s, portfolio_url=%s
                 WHERE user_id=%s
             """, (
                 name, email, position, about, linkedin, github,
                 skills_str, qualifications_titles_str, qualifications_desc_str,
                 experience_titles_str, experience_desc_str, template, profile_image_filename,
                 gallery_str, certifications_str, portfolio_url, session['user_id']
             ))
        else:
             cursor.execute("""
                 INSERT INTO user_data 
                 (user_id, name, email, position, about, linkedin, github, skills, qualification_titles, qualification_desc, experience_titles, experience_desc, template, profile_image, gallery_images, certifications, portfolio_url)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             """, (
                 session['user_id'], name, email, position, about, linkedin, github, skills_str,
                 qualifications_titles_str, qualifications_desc_str, experience_titles_str,
                 experience_desc_str, template, profile_image_filename, gallery_str, certifications_str, portfolio_url
             ))

        db.commit()

        # Redirect to the newly created portfolio page
        return redirect(portfolio_url)

    # ---------------- GET: show empty form ----------------
    user_data = None
    if 'user_id' in session:
        cursor.execute("SELECT * FROM user_data WHERE user_id = %s", (session['user_id'],))
        user_data = cursor.fetchone()
        if user_data:
            # Convert comma-separated strings back to lists for the template
            user_data['skills'] = user_data['skills'].split(',') if user_data.get('skills') else []
            
            qt = user_data['qualification_titles'].split(',') if user_data.get('qualification_titles') else []
            qd = user_data['qualification_desc'].split(',') if user_data.get('qualification_desc') else []
            user_data['qualifications'] = zip(qt, qd)

            et = user_data['experience_titles'].split(',') if user_data.get('experience_titles') else []
            ed = user_data['experience_desc'].split(',') if user_data.get('experience_desc') else []
            user_data['experiences'] = zip(et, ed)

            user_data['certifications'] = user_data['certifications'].split(',') if user_data.get('certifications') else []
            user_data['gallery_images'] = user_data['gallery_images'].split(',') if user_data.get('gallery_images') else []

    return render_template('fill_form.html', template=template, user_data=user_data, is_dashboard=True)



@app.route("/generate_portfolio", methods=["POST"])
def generate_portfolio():
    if "user_id" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Get user info
    cursor.execute("SELECT name FROM user_data WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("builder_dashboard"))

    name = user['name']
    portfolio_url = f"/portfolio/{name.replace(' ', '_').lower()}"

    # Save portfolio URL to DB
    cursor.execute("UPDATE user_data SET portfolio_url=%s WHERE user_id=%s", (portfolio_url, user_id))
    db.commit()

    return jsonify({
        "success": True,
        "portfolio_url": portfolio_url
    })

# @app.route("/admin/login", methods=["GET", "POST"])
# def admin_login():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = request.form["password"]

#         if username == "admin" and password == "admin123":
#             session["admin_logged_in"] = True
#             return redirect(url_for("admin_panel"))
#         else:
#             flash("Invalid credentials", "danger")
#     return render_template("dashboard/admin_login.html")  # optional separate login

# ---------- ADMIN PANEL ----------

@app.route('/dashboard/admin_panel')
def admin_panel():
    # Optional: restrict to admin login
    if 'role' not in session or session['role'] != 'admin':
        flash("Access denied! Admins only.", "danger")
        return redirect(url_for('login'))

    # --- Fetch Registered Users ---
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()

    # --- Fetch Recruiter Verifications ---
    cursor.execute("SELECT * FROM recruiter_verifications ORDER BY created_at DESC")
    recruiter_verifications = cursor.fetchall()

    # --- Fetch Feedbacks ---
    cursor.execute("SELECT id, name, email, message, created_at FROM contact")
    contact = cursor.fetchall()

    return render_template(
        'dashboard/admin_panel.html',
        users=users,
        recruiter_verifications=recruiter_verifications,
        contact=contact,
        # templates=templates
        is_dashboard=True)

# Delete a user (from users table)
@app.route("/delete/<int:user_id>", methods=["POST"])
def delete(user_id):
    if session.get("role") != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for("index"))

    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        flash("User deleted successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Error deleting user: {e}", "danger")

    return redirect(url_for("admin_panel"))

@app.route("/approve_recruiter/<int:recruiter_id>", methods=["POST"])
def approve_recruiter(recruiter_id):
    if session.get("role") != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for("index"))

    try:
        # Update the status in the recruiter_verifications table
        cursor.execute("UPDATE recruiter_verifications SET status = 'verified' WHERE id = %s", (recruiter_id,))
        db.commit()
        flash("Recruiter approved successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Error approving recruiter: {e}", "danger")

    return redirect(url_for("admin_panel"))


# Delete a recruiter (from recruiters table)
@app.route("/delete_recruiter/<int:recruiter_id>", methods=["POST"])
def delete_recruiter(recruiter_id):
    if session.get("role") != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for("index"))

    try:
        cursor.execute("DELETE FROM recruiter_verifications WHERE id = %s", (recruiter_id,))
        db.commit()
        flash("Recruiter deleted successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Error deleting recruiter: {e}", "danger")

    return redirect(url_for("admin_panel"))

# Delete feedback (from contact table)
@app.route("/delete_feedback/<int:feedback_id>", methods=["POST"])
def delete_feedback(feedback_id):
    if session.get("role") != "admin":
        flash("Access denied!", "danger")
        return redirect(url_for("index"))
    try:
        cursor.execute("DELETE FROM contact WHERE id = %s", (feedback_id,))
        db.commit()
        flash("Feedback deleted successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Error deleting feedback: {e}", "danger")

    return redirect(url_for("admin_panel"))

@app.route("/verify_recruiter", methods=["GET", "POST"])
def verify_recruiter():
    # Ensure we have a user ID from the registration step
    if 'new_recruiter_id' not in session:
        flash("Please register as a recruiter first.", "warning")
        return redirect(url_for('index') + "#section-5")

    user_id = session['new_recruiter_id']
    if request.method == "POST":
        name = request.form["name"]
        company_name = request.form["company_name"]
        company_website = request.form["company_website"]
        company_email = request.form["company_email"]
        phone = request.form.get("phone")
        designation = request.form["designation"]
        linkedin = request.form.get("linkedin")
        message = request.form.get("message")

        cursor.execute("""
            INSERT INTO recruiter_verifications
            (user_id, name, company_name, company_website, company_email, phone, designation, linkedin, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, name, company_name, company_website, company_email, phone, designation, linkedin, message))
        db.commit()

        # Clear the temporary session variable
        session.pop('new_recruiter_id', None)

        flash("Your verification request has been submitted!", "success")
        return redirect(url_for("recruiter_dashboard"))

    return render_template("verify_recruiter.html", is_dashboard=True)


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
