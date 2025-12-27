from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DB CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- CREATE TABLES ----------------
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


# ---------------- HOME / DASHBOARD ----------------
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "Username already exists"
        finally:
            conn.close()

        return redirect('/login')

    return render_template('register.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            return redirect('/')
        else:
            return "Invalid username or password"

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- ADD TRANSACTION ----------------
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        amount = request.form['amount']
        type_ = request.form['type']
        category = request.form['category']
        date = request.form['date']
        description = request.form.get('description', '')

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO transactions 
            (user_id, amount, type, category, date, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session['user_id'], amount, type_, category, date, description))
        conn.commit()
        conn.close()

        return redirect('/transactions')

    return render_template('add_transaction.html')


# ---------------- VIEW TRANSACTIONS ----------------
@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM transactions WHERE user_id = ?",
        (session['user_id'],)
    )
    rows = cursor.fetchall()

    return render_template("transactions.html", transactions=rows)



# ---------------- MONTHLY INPUT PAGE ----------------
@app.route('/monthly')
@login_required
def monthly():
    return render_template('monthly.html')


# ---------------- MONTHLY REPORT ----------------
@app.route('/report', methods=['POST'])
@login_required
def report_post():
    month = request.form['month']  # format: YYYY-MM
    return redirect(f'/report/{month}')


@app.route('/report/<month>')
@login_required
def monthly_report(month):
    conn = get_db_connection()
    data = conn.execute("""
        SELECT type, category, SUM(amount) AS total
        FROM transactions
        WHERE user_id = ?
        AND strftime('%Y-%m', date) = ?
        GROUP BY type, category
    """, (session['user_id'], month)).fetchall()
    conn.close()

    return render_template('report.html', data=data, month=month)


# ---------------- RUN APP ----------------
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
