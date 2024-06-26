from datetime import date as d
from datetime import datetime as dt

from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session

from misc.db import DISHES, ORDERS, USERS
from misc.roles import Admin, Cooker, Deliverier, Manager, User, Worker
from misc.utils import role_required

app = Flask('CubeFood')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

TABLES = 15


@app.route("/")
def index():
    status = session.get("status")
    session.pop("status", None)
    auth_credits = session.get("auth_credits")

    return render_template("index.html", status=status, auth_credits=auth_credits)


@app.route("/reg", methods=["POST"])
def reg():
    login = request.form["regLogin"]
    password = request.form["regPassword"]
    fio = request.form["regFio"]

    session['auth_credits'] = {'login': login, "password": password}

    reg_user = User(login, password)
    reg_result = reg_user._registration(fio)
    session["status"] = reg_result
    return redirect("/")


@app.route("/log", methods=["POST"])
def log():
    login = request.form["logLogin"]
    password = request.form["logPassword"]

    session['auth_credits'] = {'login': login, "password": password}

    log_user = User(login, password)
    log_result = log_user._login()
    if log_result[1]:
        session["user"] = log_result[1]
        return redirect(url_for("account"))
    else:
        session["status"] = log_result[0], False
        return redirect("/")


@app.route("/account")
def account():
    user = session["user"]
    match user:
        case Worker():
            worker = USERS.find_one({"login": session["user"].login})
            dishes = list(DISHES.find({}))
            date = dt.combine(d.today(), dt.min.time())
            busy = f"{((len(list(ORDERS.find({"date": date}))) / TABLES) * 100):10.2f}%"
            my_orders = list(ORDERS.find({'user_login': session["user"].login}))
            for i, order in enumerate(my_orders):
                my_orders[i]['date'] = dt.strftime(order['date'], '%d/%m/%Y')

            context = {"worker": worker, "dishes": dishes, "busy": busy, 'orders': my_orders}

        case Deliverier():
            deliverier = USERS.find_one({"login": session["user"].login})
            orders = list(ORDERS.find({'deliverier': session["user"].login}))
            for i, order in enumerate(orders):
                orders[i]['date'] = dt.strftime(order['date'], '%d/%m/%Y')

            context = {"deliverier": deliverier, 'orders': orders}

        case Cooker():
            cooker = USERS.find_one({"login": session["user"].login})
            unbound_users = list(USERS.find({"role": None}))
            deliveriers = list(USERS.find({"role": 'deliverier'}))
            dishes = list(DISHES.find({}))
            orders = list(ORDERS.find({"date": dt.combine(d.today(), dt.min.time())}))
            for i, order in enumerate(orders):
                orders[i]['date'] = dt.strftime(order['date'], '%d/%m/%Y')

            context = {"cooker": cooker, "users": unbound_users, "deliveriers": deliveriers, "dishes": dishes,
                       "orders": orders}

        case Manager():
            manager = USERS.find_one({"login": session["user"].login})
            dishes = list(DISHES.find({}))
            date = dt.combine(d.today(), dt.min.time())
            busy = f"{((len(list(ORDERS.find({"date": date}))) / TABLES) * 100):10.2f}%"
            unbound_users = list(USERS.find({"role": None}))

            context = {
                "manager": manager,
                "dishes": dishes,
                'busy': busy,
                "users": unbound_users,
            }

        case Admin():
            admin = USERS.find_one({"login": session["user"].login})
            unbound_users = list(USERS.find({"role": None}))
            cooker = USERS.find_one({"role": 'cooker'})

            context = {
                "admin": admin,
                "users": unbound_users,
                "cooker": cooker
            }

        case _:
            return "Ошибка! Неизвестная роль!"
    return render_template(f"{user.__class__.__name__.lower()}_account.html", **context)


@app.route("/make_order", methods=["POST"])
@role_required(Worker, Manager)
def make_order():
    executor: Worker | Manager = session["user"]

    data = request.get_json()

    executor._make_order(**data)
    return redirect(url_for("account"))


@app.route("/set_order_status", methods=["POST"])
@role_required(Deliverier, Cooker)
def set_order_status():
    executor: Deliverier | Cooker = session["user"]

    order_status = request.form['orderStatus'] or request.form['orderStatus']
    order_id = request.form['orderId']

    executor._set_order_status(order_id, order_status)
    return redirect(url_for("account"))


@app.route("/add_worker", methods=["POST"])
@role_required(Manager)
def add_worker():
    executor: Manager = session["user"]

    worker_login = request.form["workerLoginForAdd"]
    executor._add_worker(worker_login)
    return redirect(url_for("account"))


@app.route("/remove_worker", methods=["POST"])
@role_required(Manager)
def remove_worker():
    executor: Manager = session["user"]

    worker_login = request.form["workerLoginForRemove"]
    executor._remove_worker(worker_login)
    return redirect(url_for("account"))


@app.route("/add_deliverier", methods=["POST"])
@role_required(Cooker)
def add_deliverier():
    executor: Cooker = session["user"]

    deliverier_login = request.form["deliverierLoginForAdd"]
    executor._add_deliverier(deliverier_login)
    return redirect(url_for("account"))


@app.route("/remove_deliverier", methods=["POST"])
@role_required(Cooker)
def remove_deliverier():
    executor: Cooker = session["user"]

    deliverier_login = request.form["deliverierLoginForRem"]
    executor._remove_deliverier(deliverier_login)
    return redirect(url_for("account"))


@app.route("/give_order", methods=["POST"])
@role_required(Cooker)
def give_order():
    executor: Cooker = session["user"]
    order_id = request.form["orderId"]
    deliverier_login = request.form["deliverierLogin"]

    executor._give_order(order_id, deliverier_login)
    return redirect(url_for("account"))


@app.route("/add_dish", methods=["POST"])
@role_required(Cooker)
def add_dish():
    executor: Cooker = session["user"]

    dish_title = request.form["dishAddTitle"]
    dish_structure = request.form["dishAddStructure"]
    dish_image = request.files["dishAddImage"]
    dish_cost = int(request.form["dishAddCost"])

    executor._add_dish(dish_title, dish_structure, dish_image, dish_cost)
    return redirect(url_for("account"))


@app.route("/edit_dish", methods=["POST"])
@role_required(Cooker)
def edit_dish():
    executor: Cooker = session["user"]

    old_dish_title = request.form['dishOldTitle']
    dish_title = request.form["dishEditTitle"]
    dish_structure = request.form["dishEditStructure"]
    dish_image = request.files["dishEditImage"]
    dish_cost = int(request.form["dishEditCost"])

    executor._edit_dish(old_dish_title, dish_title, dish_structure, dish_image, dish_cost)
    return redirect(url_for("account"))


@app.route("/remove_dish", methods=["POST"])
@role_required(Cooker)
def remove_dish():
    executor: Cooker = session["user"]

    dish_title = request.form["dishRemTitle"]

    executor._remove_dish(dish_title)
    return redirect(url_for("account"))


@app.route("/add_manager", methods=["POST"])
@role_required(Admin)
def add_manager():
    """Устанавливает юзеру роль (с фронта можно выбрать только юзеров из дб с role=None)"""

    executor: Admin = session['user']

    user_login = request.form["userLoginForAdd"]

    executor._add_manager(user_login)
    return redirect(url_for("account"))


@app.route("/remove_user", methods=["POST"])
@role_required(Admin)
def remove_manager():
    executor: Admin = session['user']

    user_login = request.form["userLoginForRemove"]

    executor._remove_manager(user_login)
    return redirect(url_for("account"))


@app.route('/change_cooker', methods=["POST"])
@role_required(Admin)
def change_cooker():
    executor: Admin = session['user']

    user_login = request.form["userLoginForChange"]

    executor._change_cooker(user_login)
    return redirect(url_for('account'))


if __name__ == "__main__":
    app.run(debug=True)
