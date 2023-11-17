from flask import Flask, render_template, redirect, url_for, request, session, send_file
from flask_session import Session

from typing import Literal

from roles import User
from roles import Worker
from roles import Admin
from roles import Cooker
from roles import Abc

from utils import _role_required

from db_conn import USERS, OFFICES, FILES

from io import BytesIO

from icecream import ic

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/")
def index():
    auth_error = session.get("auth_error")
    session.pop("auth_error", None)

    return render_template("index.html", error_msg=auth_error)


@app.route("/reg", methods=["POST"])
def reg():
    login = request.form["regLogin"]
    password = request.form["regPassword"]
    fio = request.form["regFio"]

    reg_user = User(login, password, fio)
    reg_result = reg_user._registration("worker")
    if reg_result[1]:
        session["user"] = reg_result[1]
        return redirect(url_for("worker_account"))
    else:
        session["auth_error"] = reg_result[0]
        return redirect("/")


@app.route("/log", methods=["POST"])
def log():
    login = request.form["logLogin"]
    password = request.form["logPassword"]
    log_user = User(login, password, "")
    log_result = log_user._login()
    if log_result[1]:
        session["user"] = log_result[1]
        return redirect(url_for("account"))
    else:
        session["auth_error"] = log_result[0]
        return redirect("/")


@app.route("/account")
def account():
    user = session["user"]
    match type(user).__qualname__:
        case Worker.__qualname__:
            worker = USERS.find_one({"login": session["user"].login})
            if not worker:
                return redirect("/")
            office = OFFICES.find_one({"workers_logins": {"$in": [worker["login"]]}})

            context = {"worker": worker, "office": office}
        case Admin.__qualname__:
            admin = USERS.find_one({"login": session["user"].login})
            office = OFFICES.find_one({"admin_login": session["user"].login})
            meals = session["user"]._get_meals_order()

            context = {"admin": admin, "office": office, "meals": meals}
        case Cooker.__qualname__:
            cooker = USERS.find_one({"login": session["user"].login})

            context = {"cooker": cooker}
        case _:
            return "Ошибка! Неизвестная роль!"
    return render_template(f"{user.__class__.__name__.lower()}_account.html", **context)


@app.route("/exit")
@_role_required(User)
def exit():
    session.pop("user", None)
    return redirect("/")


@app.route("/send_meals", methods=["POST"])
@_role_required(Worker)
def send_meals():
    executor: Worker = session["user"]

    meals: dict[
        Literal["breakfast", "dinner"], bool
    ] = NotImplemented  # надо будет получать с фронта данные о двух галочках

    executor._send_meals(meals)
    return redirect(url_for("account"))


@app.route("/add_worker", methods=["POST"])
@_role_required(Admin)
def add_worker():
    executor: Admin = session["user"]

    worker_login = request.form["workerLoginForAdd"]
    executor._add_worker(worker_login)
    return redirect(url_for("account"))


@app.route("/remove_worker", methods=["POST"])
@_role_required(Admin)
def remove_worker():
    executor: Admin = session["user"]

    worker_login = request.form["workerLoginForRem"]
    executor._remove_worker(worker_login)
    return redirect(url_for("account"))


@app.route("/add_dish", methods=["POST"])
@_role_required(Abc)
def add_dish():
    executor: Abc = session["user"]

    dish_title = request.form["dishTitle"]
    dish_description = request.form["dishDescription"]
    dish_structure = request.form["dishStructure"]
    dish_image = request.files["dishImage"]
    dish_cost = request.form["dishCost"]

    executor._add_dish(dish_title, dish_description, dish_structure, dish_image, dish_cost)
    return redirect(url_for("account"))



@app.route("/send_meals_order", methods=["POST"])
@_role_required(Admin)
def send_meals_order():
    executor: Admin = session["user"]

    # executor._send_meals_order()
    return redirect(url_for("account"))


@app.route("/add_office", methods=["POST"])
@_role_required(Cooker)
def add_office():
    executor: Cooker = session["user"]

    login = request.form["officeLoginForAdd"]
    password = request.form["officePasswordForAdd"]
    fio = request.form["officeFioForAdd"]
    name = request.form["companyNameForAdd"]
    address = request.form["officeAddressForAdd"]

    executor._add_office(login, password, fio, name, address)
    return redirect(url_for("account"))


@app.route("/remove_office", methods=["POST"])
@_role_required(Cooker)
def remove_office():
    executor: Cooker = session["user"]

    admin_login = request.form["adminLoginForRem"]

    executor._remove_office(admin_login)
    return redirect(url_for("account"))


@app.route("/image/<filename>")
def image(filename):
    f = FILES.find_one({"filename": filename})
    if not f:
        return "Картинка отсутствует на сервере!"
    return send_file(BytesIO(f.read()), mimetype="image/jpg")


if __name__ == "__main__":
    app.run(debug=True)
