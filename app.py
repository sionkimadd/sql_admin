from flask import Flask, request, render_template
from backend import *

app = Flask(__name__)

db_engine = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect", methods=["POST"])
def connect_sql():
    db_url = request.form.get("dbURLInput")
    global db_engine
    if not db_url:
        return "Failed: Required DB URL"

    connection = ConnectSQL(db_url)
    message = connection.select_one()

    if message == "Succeed":
        db_engine = connection.get_engine()
        return "Succeed: Connected DB"
    else:
        return message

@app.route("/dispose", methods=["POST"])
def dispose_sql():
    global db_engine
    if db_engine:
        connection = DisposeSQL(db_engine)
        message = connection.close_connection()
        db_engine = None
        return message
    return "Failed: Deactivated DB"

if __name__ == "__main__":
    app.run(debug=True)