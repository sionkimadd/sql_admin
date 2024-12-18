from flask import Flask, request, render_template
from backend import *

app = Flask(__name__)

db_engine = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect_db", methods=["POST"])
def connect_db():
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

@app.route("/dispose_db", methods=["POST"])
def dispose_db():
    global db_engine
    if db_engine:
        connection = DisposeSQL(db_engine)
        message = connection.close_connection()
        db_engine = None
        return message
    return "Failed: Deactivated DB"

@app.route("/create_table", methods=["POST"])
def create_table():
    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_types = request.form.getlist("columnTypeInput")
    
    if not table_name or not column_names or not column_types:
        return "Failed: Undefined Table Name or Columns"

    columns = list(zip(column_names, column_types))
    create_table_query = CreateTableQuery(db_engine, table_name, columns)
    message = create_table_query.execute()
    return message

if __name__ == "__main__":
    app.run(debug=True)