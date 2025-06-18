from functools import wraps
from flask import jsonify, session
import re

class RequestHandler:
    def __init__(self, database_manager):
        self.database_manager = database_manager

    def require_db_connection(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            engine = self.get_db_engine()
            if not engine:
                return self.error_response("Failed: No Active DB Connection")
            return f(engine, *args, **kwargs)
        return decorated_function

    def get_db_engine(self):
        hashed_session_key = session.get("hashed_session_key")
        return self.database_manager.get_db_engine(hashed_session_key)

    @staticmethod
    def validate_required_fields(fields):
        for field_name, field_value in fields.items():
            if RequestHandler._is_empty_field(field_value):
                return False, f"Failed: Undefined {field_name.replace('_', ' ').title()}"
        return True, ""
    
    @staticmethod
    def _is_empty_field(field_value):
        if not field_value:
            return True
        if isinstance(field_value, str) and not field_value.strip():
            return True
        if isinstance(field_value, list) and any(not str(item).strip() for item in field_value):
            return True
        return False

    @staticmethod
    def success_response(message, query=None, **kwargs):
        response = {"message": message}
        if query:
            response["query"] = query
        response.update(kwargs)
        return jsonify(response)

    @staticmethod
    def error_response(message, query=None):
        return jsonify({"message": message, "query": query})

    @staticmethod
    def handle_query_response(message, query):
        return RequestHandler.success_response(message, query) if "Succeed" in message else RequestHandler.error_response(message)

    @staticmethod
    def parse_delete_conditions(columns, operators, values, logical_operators):
        conditions = []
        operator_handlers = {
            "BETWEEN": lambda col, val: f"{col} BETWEEN {' AND '.join(re.split(r'\\s+and\\s+', val, flags=re.IGNORECASE))}",
            "IN": lambda col, val: f"{col} IN ({', '.join(element.strip() for element in val.split(','))})",
            "NOT IN": lambda col, val: f"{col} NOT IN ({', '.join(element.strip() for element in val.split(','))})",
            "IS NULL": lambda col, val: f"{col} IS NULL",
            "IS NOT NULL": lambda col, val: f"{col} IS NOT NULL"
        }
        
        for i, (column, operator, value) in enumerate(zip(columns, operators, values)):
            if operator in operator_handlers:
                condition = operator_handlers[operator](column, value)
            else:
                condition = f"{column} {operator} {value}"
            
            conditions.append(condition)
            if i < len(logical_operators) and i < len(columns) - 1:
                conditions.append(logical_operators[i])
        
        return conditions

    @staticmethod
    def parse_insert_data(column_names, column_values):
        parsed_values = [value.split(",") for value in column_values]
        max_length = max(len(values) for values in parsed_values) if parsed_values else 0
        
        for values in parsed_values:
            values.extend([None] * (max_length - len(values)))

        data = []
        for row_values in zip(*parsed_values):
            row = {
                column_names[i]: row_values[i].strip() if row_values[i] is not None else None
                for i in range(len(column_names))
            }
            data.append(row)
        return data 