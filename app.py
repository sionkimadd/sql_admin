import hashlib
import os
import secrets
import re
import time
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify, send_file, session
import numpy as np
import chardet
from backend import *
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import io
import datetime

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

db_connections = {}

def generate_session_key():
    current_time = str(time.time_ns())
    random_1 = secrets.token_hex(8)
    random_2 = secrets.token_hex(8)
    random_3 = secrets.token_hex(8)
    raw_session_key = f"{current_time}_{random_1}_{random_2}_{random_3}"
    return hash_session_key(raw_session_key)

def hash_session_key(raw_session_key):
    hashed_session_key = hashlib.sha512(raw_session_key.encode()).hexdigest()
    return hashed_session_key

def get_db_engine():
    hashed_session_key = session.get("hashed_session_key")
    if not hashed_session_key or hashed_session_key not in db_connections:
        return None
    return db_connections[hashed_session_key]["engine"]
    
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect_db", methods=["POST"])
def connect_db():
    connection_mode = request.form.get("connection_mode")
    db_url = None
    if connection_mode == "url":
        db_url = request.form.get("dbURLInput", "").strip()
        if not db_url:
            return jsonify({"message": "Failed: Required DB URL", "query": None})
    if connection_mode == "custom":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        host     = request.form.get("host", "").strip()
        port     = request.form.get("port", "").strip()
        database = request.form.get("database", "").strip()
        if not all([username, password, host, port, database]):
            return jsonify({
                "message": "Failed: Required custom connection details",
                "query": None
            })
        db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    
    if "hashed_session_key" not in session:
        session["hashed_session_key"] = generate_session_key()

    hashed_session_key = session["hashed_session_key"]

    try:
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+pymysql://")

        engine = create_engine(db_url, echo=False)

        with engine.connect() as c:
            c.execute(text("SELECT 1"))

        db_connections[hashed_session_key] = {
            "engine": engine
        }

        return jsonify({"message": "Succeed: Connected DB", "query": "CONNECT TO DATABASE"})
    except Exception as e:
        return jsonify({"message": f"Failed: {str(e)}", "query": None})

@app.route("/dispose_db", methods=["POST"])
def dispose_db():
    hashed_session_key = session.get("hashed_session_key")
    if not hashed_session_key or hashed_session_key not in db_connections:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

    if hashed_session_key in db_connections:
        db_connections[hashed_session_key]["engine"].dispose()
        del db_connections[hashed_session_key]
        session.pop("hashed_session_key", None)
        return jsonify({"message": "Succeed: Disposed DB", "query": "DISPOSE DATABASE CONNECTION"})
    else:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

@app.route("/create_table", methods=["POST"])
def create_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_types = request.form.getlist("columnTypeInput")
    
    if not table_name or not column_names or not column_types:
        return jsonify({"message": "Failed: Undefined Table Name or Columns", "query": None})

    columns = []
    foreign_keys = []
    for i in range(len(column_names)):
        constraints = request.form.getlist(f"columnConstraintsInput[{i}]")
        constraint_strs = []
        if "NOT NULL" in constraints:
            constraint_strs.append("NOT NULL")
        if "NULL" in constraints:
            constraint_strs.append("NULL")
        if "DEFAULT" in constraints:
            default = request.form.get(f"defaultValueInput[{i}]")
            constraint_strs.append(f"DEFAULT {default}")
        if "UNIQUE" in constraints:
            constraint_strs.append("UNIQUE")
        if "PRIMARY KEY" in constraints:
            constraint_strs.append("PRIMARY KEY")
        if "AUTO_INCREMENT" in constraints:
            constraint_strs.append("AUTO_INCREMENT")
        if "FOREIGN KEY" in constraints:
            foreign_table = request.form.get(f"foreignTableInput[{i}]")
            foreign_column = request.form.get(f"foreignColumnInput[{i}]")
            if foreign_table and foreign_column:
                inspector = inspect(engine)
                if foreign_table not in inspector.get_table_names():
                    return jsonify({"message": f"Failed: Referenced Table {foreign_table} Unexist", "query": None})
                
                columns_info = inspector.get_columns(foreign_table)
                indexes = inspector.get_indexes(foreign_table)
                primary_keys = inspector.get_pk_constraint(foreign_table)["constrained_columns"]
                unique_keys = [index["column_names"] for index in indexes if index.get("unique", False)]

                is_primary_key = foreign_column in primary_keys
                is_indexed = any(index["column_names"] == [foreign_column] for index in indexes)
                is_unique_key = [foreign_column] in unique_keys

                is_valid_foreign_key = False
                for col in columns_info:
                    if col["name"] == foreign_column:
                        if is_primary_key or is_indexed or is_unique_key:
                            is_valid_foreign_key = True
                            break

                if not is_valid_foreign_key:
                    return jsonify({
                        "message": f"Failed: Referenced Column {foreign_column} in Table {foreign_table} without index, unique key, or primary key",
                        "query": None
                    })

                foreign_keys.append(f"FOREIGN KEY ({column_names[i]}) REFERENCES {foreign_table}({foreign_column})")
            else:
                return jsonify({"message": f"Failed: Undefined Referenced Table or Column for foreign key in column {column_names[i]}", "query": None})
        if "CHECK" in constraints:
            check = request.form.get(f"checkValueInput[{i}]")
            constraint_strs.append(f"CHECK ({check})")
        if "ON UPDATE" in constraints:
            on_update = request.form.get(f"onUpdateValueInput[{i}]")
            constraint_strs.append(f"ON UPDATE {on_update}")
        if "COMMENT" in constraints:
            comment = request.form.get(f"commentValueInput[{i}]")
            constraint_strs.append(f"COMMENT {comment}")
        if "COLLATION" in constraints:
            collation = request.form.get(f"collationValueInput[{i}]")
            constraint_strs.append(f"COLLATE {collation}")
        if "CHARACTER SET" in constraints:
            character_set = request.form.get(f"characterSetValueInput[{i}]")
            constraint_strs.append(f"CHARACTER SET {character_set}")
        
        columns.append((column_names[i], column_types[i], constraint_strs))

    create_table_query = CreateTableQuery(engine, table_name, columns, foreign_keys)
    message, query = create_table_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/drop_table", methods=["POST"])
def drop_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("dropTableNameInput")
    
    if not table_name:
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    drop_table_query = DropTableQuery(engine, table_name)
    message, query = drop_table_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/insert_data", methods=["POST"])
def insert_data():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_values = request.form.getlist("columnValueInput")
    
    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if not column_names or any(not name.strip() for name in column_names):
        return jsonify({"message": "Failed: Undefined Column Names", "query": None})
    
    if not column_values or any(not value.strip() for value in column_values):
        return jsonify({"message": "Failed: Undefined Column Values", "query": None})
    
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

    insert_data_query = InsertDataQuery(engine, table_name, column_names, data)
    message, query = insert_data_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/get_db_info", methods=["GET"])
def get_db_info():
    engine = get_db_engine()
    if not engine:
        return jsonify({"db_status": "Unconnected", "status_class": "fail", "tables": []})

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return jsonify({"db_status": "Connected", "status_class": "success", "tables": tables})

@app.route("/get_table_data/<table_name>", methods=["GET"])
def get_table_data(table_name):
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    if engine:
        with engine.connect() as c:
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
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("tableNameInput")
    condition_column = request.form.get("conditionColInput")
    condition_value = request.form.get("conditionValueInput")
    target_columns = request.form.getlist("targetColInput")
    target_values = request.form.getlist("targetValueInput")

    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if not condition_column or not condition_column.strip():
        return jsonify({"message": "Failed: Undefined Condition Column", "query": None})
    
    if not condition_value or not condition_value.strip():
        return jsonify({"message": "Failed: Undefined Condition Value", "query": None})
    
    if not target_columns or any(not column.strip() for column in target_columns):
        return jsonify({"message": "Failed: Undefined Target Columns", "query": None})
    
    if not target_values or any(not value.strip() for value in target_values):
        return jsonify({"message": "Failed: Undefined Target Values", "query": None})
    
    update_data_query = UpdateDataQuery(engine, table_name, condition_column, condition_value, target_columns, target_values)
    message, query = update_data_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/delete_data", methods=["POST"])
def delete_data():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("tableNameInput")
    columns = request.form.getlist("columnInput")
    operators = request.form.getlist("operatorInput")
    values = request.form.getlist("valueInput")
    logical_operators = request.form.getlist("logicalOperatorInput")

    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if not columns or any(not column.strip() for column in columns):
        return jsonify({"message": "Failed: Undefined Columns", "query": None})
    
    if not operators or any(not operator.strip() for operator in operators):
        return jsonify({"message": "Failed: Undefined Operators", "query": None})
    
    if not values or any(not value.strip() for value in values):
        return jsonify({"message": "Failed: Undefined Values", "query": None})
    
    conditions = []
    for i, (column, operator, value) in enumerate(zip(columns, operators, values)):
        if operator == "BETWEEN":
            value1, value2 = re.split(r"\sand\s", value, flags=re.IGNORECASE)
            condition = f"{column} BETWEEN {value1} AND {value2}"
        elif operator in ["IN", "NOT IN"]:
            values_list = ", ".join([f"{element .strip()}" for element  in value.split(",")])
            condition = f"{column} {operator} ({values_list})"
        elif operator == "IS NULL":
            condition = f"{column} IS NULL"
        elif operator == "IS NOT NULL":
            condition = f"{column} IS NOT NULL"
        else:
            condition = f"{column} {operator} {value}"
        conditions.append(condition)
        conditions.append(logical_operators[i])
    conditions.pop()
    delete_data_query = DeleteDataQuery(engine, table_name, conditions)
    message, query = delete_data_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/modify_table", methods=["POST"])
def modify_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("tableNameInput")
    command = request.form.get("commandInput")
    column_name = request.form.get("columnNameInput")
    column_type = request.form.get("columnTypeInput")
    column_new_name = request.form.get("columnNewNameInput")

    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if not command or not command.strip():
        return jsonify({"message": "Failed: Undefined Command", "query": None})
    
    if not column_name or not column_name.strip():
        return jsonify({"message": "Failed: Undefined Column Name", "query": None})
    
    modify_table_query = ModifyTableQuery(engine, table_name, command, column_name, column_type, column_new_name)
    message, query = modify_table_query.execute()
    return jsonify({"message": message, "query": query})

@app.route("/join_table", methods=["POST"])
def join_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

    table_name = request.form.get("tableNameInput")
    join_types = request.form.getlist("joinTypes")
    join_tables = request.form.getlist("joinTables")
    join_conditions = request.form.getlist("joinConditions")
    select_columns = request.form.getlist("selectColumns")
    where_conditions = request.form.getlist("whereConditions")
    
    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if not join_types or any(not join_type.strip() for join_type in join_types):
        return jsonify({"message": "Failed: Undefined Join Types", "query": None})
    
    if not join_tables or any(not join_table.strip() for join_table in join_tables):
        return jsonify({"message": "Failed: Undefined Join Tables", "query": None})

    if not join_conditions or any(not join_condition.strip() for join_condition in join_conditions):
        return jsonify({"message": "Failed: Undefined Join Conditions", "query": None})

    if not select_columns or any(not select_column.strip() for select_column in select_columns):
        return jsonify({"message": "Failed: Undefined Select Columns", "query": None})

    join_query = JoinTableQuery(engine, table_name, join_types, join_tables, join_conditions, select_columns, where_conditions)
    message, query, rows, column_names = join_query.execute()
    
    return jsonify({
        "message": message,
        "query": query,
        "rows": [dict(row._mapping) for row in rows],
        "column_names": column_names
    })

@app.route("/sorting_table", methods=["POST"])
def sorting_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

    table_name = request.form.get("tableNameInput")
    order_columns = request.form.getlist("orderColumnNameInput")
    order_sortings = request.form.getlist("sortingInput")
    select_columns = request.form.getlist("selectColumnNameInput")

    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})

    if not order_columns or any(not column.strip() for column in order_columns):
        return jsonify({"message": "Failed: Undefined Order Columns", "query": None})

    if not order_sortings or any(not sorting.strip() for sorting in order_sortings):
        return jsonify({"message": "Failed: Undefined Order Sortings", "query": None})

    if not select_columns or any(not column.strip() for column in select_columns):
        return jsonify({"message": "Failed: Undefined Select Columns", "query": None})

    sorting_query = SortingTableQuery(engine, table_name, order_columns, order_sortings, select_columns)
    message, query, rows, column_names = sorting_query.execute()

    return jsonify({
        "message": message,
        "query": query,
        "rows": [dict(row._mapping) for row in rows],
        "column_names": column_names
    })

@app.route("/export_table", methods=["POST"])
def export_table():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})

    table_name = request.form.get("exportTableNameInput")
    
    if not table_name or not table_name.strip():
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    
    if engine:
        with engine.connect() as c:
            query = f"SELECT * FROM {table_name}"
            output = c.execute(text(query))
            df = pd.DataFrame(output.fetchall(), columns=output.keys())
            
            excel_data = io.BytesIO()
            with pd.ExcelWriter(excel_data, engine = "xlsxwriter") as w:
                df.to_excel(w, index=False, sheet_name=table_name)
            excel_data.seek(0)
            
            return send_file(
                excel_data,
                download_name=f"{table_name}.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        return jsonify({"message": "Failed: Deactivated DB", "query": None})

@app.route("/import_excel", methods=["POST"])
def import_excel():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    table_name = request.form.get("importTableNameInput")
    file = request.files.get("importExcelFile")

    if not table_name:
        return jsonify({"message": "Failed: Undefined Table Name", "query": None})
    if not file:
        return jsonify({"message": "Failed: Undefined Excel File", "query": None})

    try:
        filename = file.filename.lower()

        try:

            if filename.endswith(".csv"):
                encoding_sample = file.read(7000)
                file.seek(0)

                detected_encoding = chardet.detect(encoding_sample).get("encoding", "utf-8")

                encodings = list(dict.fromkeys([detected_encoding, "utf-8", "utf-8-sig", "latin1", "iso-8859-1", "windows-1252"]))

                for encoding in encodings:
                    try:
                        df = pd.read_csv(file, encoding=encoding, engine="python")
                        break
                    except Exception:
                        file.seek(0)
                else:
                    raise ValueError("Undecoded CSV file")

            elif filename.endswith(".xlsx"):
                file.seek(0)
                df = pd.read_excel(file, engine="openpyxl")

            elif filename.endswith(".xls"):
                file.seek(0)
                df = pd.read_excel(file, engine="xlrd")

            else:
                raise ValueError("Unsupported file format")

        except Exception as e:
            return jsonify({"message": f"Failed: {str(e)}", "query": None})

        df.columns = df.columns.str.strip().str.lower()

        normalized_column_names = []

        for column in df.columns:
            normalized_column_name = re.sub(r"\W+", "_", column.strip())
            normalized_column_names.append(normalized_column_name)
            
        df.columns = normalized_column_names

        normalized_df = df.copy()

        normalized_df = normalized_df.replace({ "N/A": None, np.nan: None })

        data = normalized_df.to_dict(orient="records")

        for row in data:
            for key, value in row.items():
                if isinstance(value, str):
                    row[key] = f"'{value.replace(chr(39), chr(39)*2)}'"
                elif isinstance(value, (datetime.date, datetime.datetime)):
                    row[key] = f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
                elif value is None:
                    row[key] = None

        def is_integer(val):
            if isinstance(val, int):
                return True
            if isinstance(val, float):
                return False
            if isinstance(val, str) and val.isdigit():
                return True
            try:
                return float(val).is_integer()
            except (ValueError, TypeError):
                return False

        def is_float(val):
            if isinstance(val, float):
                return True
            if isinstance(val, int):
                return False
            if isinstance(val, str):
                val = val.strip()
                if val.count(".") == 1 and val.replace(".", "").isdigit():
                    return True
            try:
                float(val)
                return True
            except (ValueError, TypeError):
                return False

        column_types = []
        df_data = df.iloc[1:].reset_index(drop=True)

        for column in df.columns:
            dtype = df_data[column].dtype
            col_data = df[column].dropna()
            col_str = col_data.astype(str)

            if np.issubdtype(dtype, np.integer):
                column_types.append("INT")
            elif np.issubdtype(dtype, np.floating):
                column_types.append("FLOAT")
            elif np.issubdtype(dtype, np.bool_):
                column_types.append("TINYINT(1)")
            elif np.issubdtype(dtype, np.datetime64):
                if col_str.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
                    column_types.append("DATE")
                elif col_str.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}").all():
                    column_types.append("DATETIME")
                else:
                    column_types.append("VARCHAR(255)")
            elif col_data.apply(is_float).all():
                column_types.append("FLOAT")
            elif col_data.apply(is_integer).all():
                column_types.append("INT")
            elif col_str.str.fullmatch(r"(?i)TRUE|FALSE").all():
                column_types.append("TINYINT(1)")
            elif col_str.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
                column_types.append("DATE")
            elif col_str.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}").all():
                column_types.append("DATETIME")
            else:
                max_length = col_str.str.len().max()
                if max_length is not None and max_length <= 255:
                    column_types.append("VARCHAR(255)")
                else:
                    column_types.append("TEXT")

        create_table_query = CreateTableQuery(
            engine, 
            table_name, 
            list(zip(df.columns, column_types, [None] * len(df.columns))),  
            []
        )
        message, query = create_table_query.execute()

        if "Failed" in message:
            return jsonify({"message": message, "query": query})

        insert_data_query = InsertDataQuery(engine, table_name, df.columns.tolist(), data)
        message, query = insert_data_query.execute()

        return jsonify({"message": message, "query": query})
    
    except Exception as e:
        return jsonify({"message": f"Failed: {str(e)}", "query": None})
    
def gather_related_tables(inspector, start_table):
    visited = set()
    edges = []
    seen_edges = set()

    def dfs(table):
        if table in visited:
            return
        visited.add(table)

        for fk in inspector.get_foreign_keys(table):
            parent_table = fk.get("referred_table")
            if parent_table:
                edge_key = (
                    table,
                    parent_table,
                    tuple(fk.get("constrained_columns", [])),
                    tuple(fk.get("referred_columns", []))
                )
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append((table, parent_table, fk))
                if parent_table not in visited:
                    dfs(parent_table)
        
        all_tables = inspector.get_table_names()
        for other_table in all_tables:
            if other_table == table:
                continue
            for fk in inspector.get_foreign_keys(other_table):
                if fk.get("referred_table") == table:
                    edge_key = (
                        other_table,
                        table,
                        tuple(fk.get("constrained_columns", [])),
                        tuple(fk.get("referred_columns", []))
                    )
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append((other_table, table, fk))
                    if other_table not in visited:
                        dfs(other_table)

    dfs(start_table)
    return visited, edges

def generate_table_uml(inspector, table_name):
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    primary_keys = set(pk_constraint.get("constrained_columns", []))
    foreign_keys = inspector.get_foreign_keys(table_name)
    unique_indexes = {
        col
        for idx in inspector.get_indexes(table_name)
        if idx.get("unique")
        for col in idx.get("column_names", [])
    }

    content_lines = [table_name]
    for col in columns:
        line = col["name"]

        if col["name"] in primary_keys:
            line += " (PK)"

        for fk in foreign_keys:
            if col["name"] in fk.get("constrained_columns", []):
                line += f" (FK->{fk.get('referred_table', '?')})"

        if col["name"] in unique_indexes:
            line += " (UQ)"

        if not col.get("nullable", True):
            line += " (NN)"

        default_value = col.get("default")
        if default_value is not None:
            line += f" (DF:{default_value})"

        line += f" : {str(col['type'])}"
        content_lines.append(line)

    max_line_length = max(len(line) for line in content_lines)
    box_width = max_line_length + 4
    border = "+" + "-" * (box_width - 2) + "+"

    uml_lines = [border]
    uml_lines.append(f"|{table_name.center(box_width - 2)}|")
    uml_lines.append(border)
    for line in content_lines[1:]:
        uml_lines.append(f"| {line.ljust(box_width - 3)}|")
    uml_lines.append(border)
    return uml_lines

@app.route("/generate_uml", methods=["POST"])
def generate_uml():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "uml": None})

    start_table = request.form.get("umlTableNameInput")
    if not start_table:
        return jsonify({"message": "Failed: Undefined Table Name", "uml": None})

    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    if start_table not in all_tables:
        return jsonify({"message": f"Failed: Table {start_table} Unexist", "uml": None})

    visited_tables, edges = gather_related_tables(inspector, start_table)

    full_uml_lines = []
    for tbl in sorted(visited_tables):
        table_uml = generate_table_uml(inspector, tbl)
        full_uml_lines.extend(table_uml)
        full_uml_lines.append("")

    relationship_lines = []
    for (child_tbl, parent_tbl, fk) in edges:
        constrained_cols = ", ".join(fk.get("constrained_columns", []))
        referred_cols = ", ".join(fk.get("referred_columns", []))
        relationship_lines.append(f"({child_tbl}) [{constrained_cols}] -> ({parent_tbl}) [{referred_cols}]")

    if relationship_lines:
        full_uml_lines.append("=== Relationships ===")
        full_uml_lines.extend(relationship_lines)

    uml_text = "\n".join(full_uml_lines)
    return jsonify({"message": "Succeed: ERD Generated", "uml": uml_text})

@app.route("/execute_custom_query", methods=["POST"])
def execute_custom_query():
    engine = get_db_engine()
    if not engine:
        return jsonify({"message": "Failed: No Active DB Connection", "query": None})
    
    data = request.get_json()
    sql_query = data.get('query', '').strip()
    
    if not sql_query:
        return jsonify({"message": "Failed: Empty Query", "query": None})
    
    try:
        with engine.connect() as c:
            is_select = sql_query.strip().upper().startswith("SELECT")
            
            if is_select:
                result = c.execute(text(sql_query))
                rows = result.fetchall()
                column_names = result.keys()
                serializable_rows = [dict(row._mapping) for row in rows]
                return jsonify({
                    "message": "Succeed: Query executed successfully",
                    "query": sql_query,
                    "rows": serializable_rows,
                    "column_names": list(column_names)
                })
            else:
                with c.begin():
                    result = c.execute(text(sql_query))
                    return jsonify({
                        "message": "Succeed: Query executed successfully",
                        "query": sql_query
                    })
    except Exception as e:
        return jsonify({"message": f"Failed: {str(e)}", "query": None})
    
# if __name__ == "__main__":
#     app.run(debug=True)
if __name__ == "__main__":
    app.run()