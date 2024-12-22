from flask import Flask, request, render_template, jsonify
from backend import *
from sqlalchemy import inspect, text
from backend.queries.update_data import UpdateDataQuery

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
        disposal = DisposeSQL(db_engine)
        message = disposal.close_connection()
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

@app.route("/drop_table", methods=["POST"])
def drop_table():
    table_name = request.form.get("dropTableNameInput")
    
    if not table_name:
        return "Failed: Undefined Table Name"
    
    drop_table_query = DropTableQuery(db_engine, table_name)
    message = drop_table_query.execute()
    return message

@app.route("/insert_data", methods=["POST"])
def insert_data():
    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_values = request.form.getlist("columnValueInput")
    
    if not table_name or not table_name.strip():
        return "Failed: Undefined Table Name"
    
    if not column_names or any(not name.strip() for name in column_names):
        return "Failed: Undefined Column Names"
    
    column_values = [value.split(",") for value in column_values]
    max_length_values = max(len(values) for values in column_values)
    
    for values in column_values:
        while len(values) < max_length_values:
            values.append(None)

    data = []
    for values in zip(*column_values):
        row = {}
        for i in range(len(column_names)):
            column_name = column_names[i]
            value = values[i]
            if value is not None:
                value = value.strip()
            else:
                value = None
            row[column_name] = value
        data.append(row)

    insert_data_query = InsertDataQuery(db_engine, table_name, column_names, data)
    message = insert_data_query.execute()
    return message

@app.route("/get_db_info", methods=["GET"])
def get_db_info():
    global db_engine
    if db_engine:
        db_status = "Connected"
        status_class = "success"
    else:
        db_status = "Unconnected"
        status_class = "fail"
    if db_engine:
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
    else:
        tables = []
    return jsonify({"db_status": db_status, "status_class": status_class, "tables": tables})

@app.route("/get_table_data/<table_name>", methods=["GET"])
def get_table_data(table_name):
    global db_engine
    if db_engine:
        with db_engine.connect() as c:
            query = f"SELECT * FROM {table_name}"
            output = c.execute(text(query))
            rows = []
            columnNames = output.keys()
            for row in output.fetchall():
                row_dict = dict(zip(columnNames, row))
                rows.append(row_dict)
            column_names_query = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
            column_names_output = c.execute(text(column_names_query))
            column_names = []
            column_types = []
            for row in column_names_output.fetchall():
                column_name = row[0]
                column_type = row[1]
                column_names.append(column_name)
                column_types.append(column_type)
        return jsonify({"table_name": table_name, "column_names": column_names, "column_types": column_types, "rows": rows})
    else:
        return None

@app.route("/update_data", methods=["POST"])
def update_data():
    table_name = request.form.get("tableNameInput")
    condition_column = request.form.get("conditionColInput")
    condition_value = request.form.get("conditionValueInput")
    target_columns = request.form.getlist("targetColInput")
    target_values = request.form.getlist("targetValueInput")

    if not table_name or not table_name.strip():
        return "Failed: Undefined Table Name"
    
    if not condition_column or not condition_column.strip():
        return "Failed: Undefined Condition Column"
    
    if not condition_value or not condition_value.strip():
        return "Failed: Undefined Condition Value"
    
    if not target_columns or any(not column.strip() for column in target_columns):
        return "Failed: Undefined Target Columns"
    
    if not target_values or any(not value.strip() for value in target_values):
        return "Failed: Undefined Target Values"
    
    update_data_query = UpdateDataQuery(db_engine, table_name, condition_column, condition_value, target_columns, target_values)
    message = update_data_query.execute()
    return message

if __name__ == "__main__":
    app.run(debug=True)