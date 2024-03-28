from flask import Flask, g, request, abort, redirect, render_template, url_for, make_response
import jwt

from functools import wraps
import secrets
import hashlib
import sqlite3


app = Flask(__name__)
DATABASE = "/tmp/shop.db"
SECRET = secrets.token_bytes(16)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def username():
    username = getattr(g, 'username', None)
    return username


def one(cursor):
    it = cursor.fetchone()
    if it:
        it = it[0]

    return it


@app.teardown_appcontext
def close_connection(_exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.before_request
def before_request():
    if request.method == "GET" and (error := request.args.get("_error", None)):
        g._error = error
    if request.method == "GET" and (info := request.args.get("_info", None)):
        g._info = info

    token = request.cookies.get("Access-Token", None)
    if token is None:
        return

    try:
        data = jwt.decode(token, SECRET)
    except (jwt.DecodeError, jwt.InvalidSignatureError):
        return

    for key, value in data.items():
        setattr(g, key, value)


def authorized(**constraints):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kvargs):
            if username() is None:
                abort(redirect(url_for("login")))

            for key, value in constraints.items():
                if g.get(key, None) != value:
                    abort(redirect(url_for("login")))

            return func(*args, **kvargs)

        return wrapper
    return decorator


@app.route("/")
def index():
    return redirect(url_for("shop"))


@app.route("/logout", methods=["GET", "POST"])
def logout():
    resp = redirect(url_for("login"))
    resp.delete_cookie('Access-Token')
    return resp


@app.route("/login", methods=["GET", "POST"])
def login():
    match request.method:
        case "GET":
            return render_template("login.html")
        case "POST":
            username = request.form.get("username", None)
            password = request.form.get("password", None)

            if username is None or password is None:
                return redirect(url_for("login", _error="Nutzername und Passwort benötigt!"))

            password_hash = hashlib.sha256(password.encode(errors="ignore")).hexdigest()

            db = get_db()
            c = db.execute(f"SELECT id FROM users WHERE username = ? AND password = ?", (username, password_hash))
            if one(c) is None:
                return redirect(url_for("login", _error="Nutzername oder Passwort sind falsch!"))

            data = { "username": username }
            token = jwt.encode(data, SECRET, "HS256")

            resp = make_response(redirect(url_for("shop", _info="Login erfolgreich!")))
            resp.set_cookie("Access-Token", token.decode("utf-8"))

            return resp

    abort(500)


@app.route("/register", methods=["GET", "POST"])
def register():
    match request.method:
        case "GET":
            return render_template("register.html")
        case "POST":
            username = request.form.get("username", None)
            password = request.form.get("password", None)
            password_confirm = request.form.get("password_confirm", None)

            if username is None or password is None:
                return redirect(url_for("register", _error="Nutzername und Passwort benötigt!"))

            if password_confirm != password:
                return redirect(url_for("register", _error="Passwörter stimmen nicht überein!"))

            password_hash = hashlib.sha256(password.encode(errors="ignore")).hexdigest()

            db = get_db()
            try:
                db.execute(f"INSERT INTO users (username, password, account_balance) VALUES (?, ?, 100.00)", (username, password_hash))
            except sqlite3.IntegrityError:
                return redirect(url_for("register", _error="Nutzername existiert bereits!"))
            db.commit()

            return redirect(url_for("login", _info="Nutzer erfolgreich angelegt. Sie können sich nun einloggen"))

    abort(500)


@app.route("/user")
@authorized()
def user():
    db = get_db()
    rows = db.execute("SELECT title, description, theme, price FROM items LEFT JOIN users ON owner_id = users.id WHERE username = ? ORDER BY price", (username(),)).fetchall()
    bought_items = []
    for item in rows:
        bought_items.append({
            key: item[i] for i, key in enumerate(("title", "description", "theme", "price"))
        })

    rows = db.execute("SELECT title, description, theme, price FROM items LEFT JOIN users ON created_by = users.id WHERE username = ? ORDER BY price", (username(),)).fetchall()
    created_items = []
    for item in rows:
        created_items.append({
            key: item[i] for i, key in enumerate(("title", "description", "theme", "price"))
        })

    return render_template("user.html", bought_items=bought_items, created_items=created_items)


@app.route("/admin")
@authorized(username="admin")
def admin():
    db = get_db()
    rows = db.execute("SELECT id, username, account_balance FROM users WHERE username != 'admin'").fetchall()
    users = []
    for user in rows:
        users.append({
            key: user[i] for i, key in enumerate(("id", "username", "account_balance"))
        })

    return render_template("admin.html", users=users)

@app.route("/admin/delete_user", methods=["POST"])
@authorized(username="admin")
def delete_user():
    id = request.form.get("user_id", None, type=int)
    if id is None:
        abort(403)

    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (id,))
    db.commit()

    return redirect(url_for("admin"))


@app.route("/admin/add_balance", methods=["POST"])
@authorized(username="admin")
def add_balance():

    id = request.form.get("user_id", None, type=int)
    balance = request.form.get("add_balance", None, type=float)

    if balance is None or id is None:
        abort(403)

    db = get_db()
    db.execute("UPDATE users SET account_balance = account_balance + ? WHERE id = ?", (balance, id))
    db.commit()

    return redirect(url_for("admin"))


@app.route("/shop", methods=["GET", "POST"])
def shop():
    match request.method:
        case "GET":
            db = get_db()
            rows = db.execute("SELECT items.id, title, description, theme, price, username FROM items LEFT JOIN users ON owner_id = users.id ORDER BY price").fetchall()
            items = []
            for item in rows:
                items.append({
                    key: item[i] for i, key in enumerate(("id", "title", "description", "theme", "price", "owner"))
                })

            return render_template("shop.html", items=items)
        case "POST":
            title = request.form.get("title", None)
            description = request.form.get("description", None)
            price = request.form.get("price", None, type=float)
            theme = request.form.get("theme", None)

            if title is None or description is None or price is None:
                abort(403)

            db = get_db()
            c = db.cursor()

            c.execute("SELECT id FROM users WHERE username = ?", (username(),))
            created_by = one(c)
            try:
                c.execute("INSERT INTO items (title, description, theme, price, created_by) VALUES (?, ?, ?, ?, ?)", (title, description, theme, price, created_by))
            except sqlite3.IntegrityError:
                abort(403)

            db.commit()
            return redirect(url_for("shop", _info=f"{title} wurde angelegt!"))

    abort(500)


@app.route("/buy", methods=["POST"])
@authorized()
def buy():
    id = request.form.get("id", None, type=int)
    if id is None:
        abort(403)

    db = get_db()
    c = db.cursor()

    c.execute(f"SELECT price FROM items WHERE id = {id} AND owner_id IS NULL")
    if (price := one(c)) is None:
        abort(404)

    c.execute(f"SELECT id FROM users WHERE username = '{username()}'")
    userid = one(c)

    q = f"UPDATE users SET account_balance = account_balance - {price} WHERE id = {userid} AND account_balance >= {price}"
    modified = c.execute(q).rowcount
    if not modified:
        return redirect(url_for("shop", _error="Deine Ersparnisse reichen leider nicht aus."))

    c.execute(f"UPDATE items SET owner_id = {userid} WHERE id = {id}")
    db.commit()

    return redirect(url_for("shop", _info="Erfolgreich gekauft!"))


def main():
    app.run("127.0.0.1", 8080, debug=True)

if __name__ == '__main__':
    main()
