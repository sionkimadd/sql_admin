import os
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify, send_file, session
from backend import *

load_dotenv()

os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("GCP_PROJECT_ID")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GCP_CREDENTIALS_PATH")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

database_manager = DatabaseManager()
gemini_chat = GeminiChat()
request_handler = RequestHandler(database_manager)
    
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect_db", methods=["POST"])
def connect_db():
    connection_mode = request.form.get("connection_mode")
    
    kwargs = {}
    if connection_mode == "url":
        kwargs["db_url"] = request.form.get("dbURLInput", "").strip()
    elif connection_mode == "custom":
        kwargs.update({
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", "").strip(),
            "host": request.form.get("host", "").strip(),
            "port": request.form.get("port", "").strip(),
            "database": request.form.get("database", "").strip(),
        })

    session_key, message = database_manager.connect_database(connection_mode, **kwargs)
    
    if session_key:
        session["hashed_session_key"] = session_key
        return request_handler.success_response(message, "CONNECT TO DATABASE")
    else:
        return request_handler.error_response(message)

@app.route("/dispose_db", methods=["POST"])
def dispose_db():
    hashed_session_key = session.get("hashed_session_key")
    message = database_manager.dispose_database(hashed_session_key)

    if "Succeed" in message:
        session.pop("hashed_session_key", None)
        return request_handler.success_response(message, "DISPOSE DATABASE CONNECTION")
    else:
        return request_handler.error_response(message)

@app.route("/create_table", methods=["POST"])
@request_handler.require_db_connection
def create_table(engine):
    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_types = request.form.getlist("columnTypeInput")
    
    table_creation_service = TableCreationService(engine)
    message, query = table_creation_service.create_table_with_constraints(
        table_name, column_names, column_types, request.form
    )
    
    return request_handler.handle_query_response(message, query)

@app.route("/drop_table", methods=["POST"])
@request_handler.require_db_connection
def drop_table(engine):
    table_name = request.form.get("dropTableNameInput")
    
    is_valid, error_msg = request_handler.validate_required_fields({"table_name": table_name})
    if not is_valid:
        return request_handler.error_response(error_msg)
    
    drop_table_query = DropTableQuery(engine, table_name)
    message, query = drop_table_query.execute()
    return request_handler.handle_query_response(message, query)

@app.route("/insert_data", methods=["POST"])
@request_handler.require_db_connection
def insert_data(engine):
    table_name = request.form.get("tableNameInput")
    column_names = request.form.getlist("columnNameInput")
    column_values = request.form.getlist("columnValueInput")
    
    is_valid, error_msg = request_handler.validate_required_fields({
        "table_name": table_name,
        "column_names": column_names,
        "column_values": column_values
    })
    if not is_valid:
        return request_handler.error_response(error_msg)
    
    data = request_handler.parse_insert_data(column_names, column_values)
    insert_data_query = InsertDataQuery(engine, table_name, column_names, data)
    message, query = insert_data_query.execute()
    return request_handler.handle_query_response(message, query)

@app.route("/get_db_info", methods=["GET"])
def get_db_info():
    engine = request_handler.get_db_engine()
    table_info_service = TableInfoService(engine)
    return jsonify(table_info_service.get_db_info())

@app.route("/get_table_data/<table_name>", methods=["GET"])
def get_table_data(table_name):
    engine = request_handler.get_db_engine()
    table_info_service = TableInfoService(engine)
    result = table_info_service.get_table_data(table_name)
    
    if result:
        return jsonify(result)
    else:
        return request_handler.error_response("Failed: No Active DB Connection")

@app.route("/update_data", methods=["POST"])
@request_handler.require_db_connection
def update_data(engine):
    fields = {
        "table_name": request.form.get("tableNameInput"),
        "condition_column": request.form.get("conditionColInput"),
        "condition_value": request.form.get("conditionValueInput"),
        "target_columns": request.form.getlist("targetColInput"),
        "target_values": request.form.getlist("targetValueInput")
    }

    is_valid, error_msg = request_handler.validate_required_fields(fields)
    if not is_valid:
        return request_handler.error_response(error_msg)
    
    update_data_query = UpdateDataQuery(
        engine, fields["table_name"], fields["condition_column"], 
        fields["condition_value"], fields["target_columns"], fields["target_values"]
    )
    message, query = update_data_query.execute()
    return request_handler.handle_query_response(message, query)

@app.route("/delete_data", methods=["POST"])
@request_handler.require_db_connection
def delete_data(engine):
    fields = {
        "table_name": request.form.get("tableNameInput"),
        "columns": request.form.getlist("columnInput"),
        "operators": request.form.getlist("operatorInput"),
        "values": request.form.getlist("valueInput")
    }

    is_valid, error_msg = request_handler.validate_required_fields(fields)
    if not is_valid:
        return request_handler.error_response(error_msg)
    
    logical_operators = request.form.getlist("logicalOperatorInput")
    conditions = request_handler.parse_delete_conditions(
        fields["columns"], fields["operators"], fields["values"], logical_operators
    )
    
    delete_data_query = DeleteDataQuery(engine, fields["table_name"], conditions)
    message, query = delete_data_query.execute()
    return request_handler.handle_query_response(message, query)

@app.route("/modify_table", methods=["POST"])
@request_handler.require_db_connection
def modify_table(engine):
    fields = {
        "table_name": request.form.get("tableNameInput"),
        "command": request.form.get("commandInput"),
        "column_name": request.form.get("columnNameInput")
    }

    is_valid, error_msg = request_handler.validate_required_fields(fields)
    if not is_valid:
        return request_handler.error_response(error_msg)
    
    column_type = request.form.get("columnTypeInput")
    column_new_name = request.form.get("columnNewNameInput")

    modify_table_query = ModifyTableQuery(
        engine, fields["table_name"], fields["command"], 
        fields["column_name"], column_type, column_new_name
    )
    message, query = modify_table_query.execute()
    return request_handler.handle_query_response(message, query)

@app.route("/join_table", methods=["POST"])
@request_handler.require_db_connection
def join_table(engine):
    fields = {
        "table_name": request.form.get("tableNameInput"),
        "join_types": request.form.getlist("joinTypes"),
        "join_tables": request.form.getlist("joinTables"),
        "join_conditions": request.form.getlist("joinConditions"),
        "select_columns": request.form.getlist("selectColumns")
    }
    
    is_valid, error_msg = request_handler.validate_required_fields(fields)
    if not is_valid:
        return request_handler.error_response(error_msg)

    where_conditions = request.form.getlist("whereConditions")
    join_query = JoinTableQuery(
        engine, fields["table_name"], fields["join_types"], 
        fields["join_tables"], fields["join_conditions"], 
        fields["select_columns"], where_conditions
    )
    message, query, rows, column_names = join_query.execute()
    
    return request_handler.success_response(
        message, query,
        rows=[dict(row._mapping) for row in rows],
        column_names=column_names
    )

@app.route("/sorting_table", methods=["POST"])
@request_handler.require_db_connection
def sorting_table(engine):
    fields = {
        "table_name": request.form.get("tableNameInput"),
        "order_columns": request.form.getlist("orderColumnNameInput"),
        "order_sortings": request.form.getlist("sortingInput"),
        "select_columns": request.form.getlist("selectColumnNameInput")
    }

    is_valid, error_msg = request_handler.validate_required_fields(fields)
    if not is_valid:
        return request_handler.error_response(error_msg)

    sorting_query = SortingTableQuery(
        engine, fields["table_name"], fields["order_columns"], 
        fields["order_sortings"], fields["select_columns"]
    )
    message, query, rows, column_names = sorting_query.execute()

    return request_handler.success_response(
        message, query,
        rows=[dict(row._mapping) for row in rows],
        column_names=column_names
    )

@app.route("/export_table", methods=["POST"])
@request_handler.require_db_connection
def export_table(engine):
    table_name = request.form.get("exportTableNameInput")
    file_service = FileService(engine)
    
    excel_data, message = file_service.export_table_to_excel(table_name)
    
    if excel_data:
            return send_file(
                excel_data,
                download_name=f"{table_name}.xlsx",
                as_attachment=True,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        return request_handler.error_response(message)

@app.route("/import_excel", methods=["POST"])
@request_handler.require_db_connection
def import_excel(engine):
    table_name = request.form.get("importTableNameInput")
    file = request.files.get("importExcelFile")
    file_service = FileService(engine)

    message, query = file_service.import_excel_to_table(table_name, file)
    return request_handler.handle_query_response(message, query)

@app.route("/generate_uml", methods=["POST"])
@request_handler.require_db_connection
def generate_uml(engine):
    start_table = request.form.get("umlTableNameInput")
    uml_service = UMLService(engine)
    
    message, uml_text = uml_service.generate_uml(start_table)
    return jsonify({"message": message, "uml": uml_text})

@app.route("/execute_custom_query", methods=["POST"])
@request_handler.require_db_connection
def execute_custom_query(engine):
    data = request.get_json()
    sql_query = data.get('query', '').strip()
    query_executor = QueryExecutor(engine)
    
    message, query, rows, column_names = query_executor.execute_custom_query(sql_query)
    
    if rows is not None and column_names is not None:
        return request_handler.success_response(message, query, rows=rows, column_names=column_names)
    else:
        return request_handler.success_response(message, query)
    
@app.route('/chat_with_vertex', methods=['POST'])
def chat_with_vertex():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        response = gemini_chat.get_response(user_message)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'response': f'Failed: {str(e)}'}), 500

# if __name__ == "__main__":
#     app.run(debug=True)
if __name__ == "__main__":
    app.run()