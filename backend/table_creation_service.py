from .queries.create_table import CreateTableQuery
from .foreign_key_validator import ForeignKeyValidator

class TableCreationService:
    CONSTRAINT_MAPPINGS = {
        "NOT NULL": "NOT NULL",
        "NULL": "NULL", 
        "UNIQUE": "UNIQUE",
        "PRIMARY KEY": "PRIMARY KEY",
        "AUTO_INCREMENT": "AUTO_INCREMENT"
    }
    
    VALUE_CONSTRAINTS = [
        ("DEFAULT", "defaultValueInput", "DEFAULT {}"),
        ("CHECK", "checkValueInput", "CHECK ({})"),
        ("ON UPDATE", "onUpdateValueInput", "ON UPDATE {}"),
        ("COMMENT", "commentValueInput", "COMMENT {}"),
        ("COLLATION", "collationValueInput", "COLLATE {}"),
        ("CHARACTER SET", "characterSetValueInput", "CHARACTER SET {}")
    ]
    
    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.fk_validator = ForeignKeyValidator(db_engine)

    def create_table_with_constraints(self, table_name, column_names, column_types, form_data):
        if not table_name or not column_names or not column_types:
            return "Failed: Undefined Table Name or Columns", None

        columns = []
        foreign_keys = []
        
        for i, column_name in enumerate(column_names):
            constraints = form_data.getlist(f"columnConstraintsInput[{i}]")
            
            constraint_strs = self._process_basic_constraints(constraints)
            constraint_strs.extend(self._process_value_constraints(constraints, i, form_data))
            
            fk_result = self._process_foreign_key(constraints, i, column_name, form_data)
            if isinstance(fk_result, tuple):
                return fk_result
            elif fk_result:
                foreign_keys.append(fk_result)
            
            columns.append((column_name, column_types[i], constraint_strs))

        create_table_query = CreateTableQuery(self.db_engine, table_name, columns, foreign_keys)
        return create_table_query.execute()

    def _process_basic_constraints(self, constraints):
        return [
            sql_text for constraint, sql_text in self.CONSTRAINT_MAPPINGS.items()
            if constraint in constraints
        ]

    def _process_value_constraints(self, constraints, index, form_data):
        constraint_strs = []
        
        for constraint, input_name, format_str in self.VALUE_CONSTRAINTS:
            if constraint in constraints:
                value = form_data.get(f"{input_name}[{index}]")
                if value:
                    constraint_strs.append(format_str.format(value))
        
        return constraint_strs

    def _process_foreign_key(self, constraints, index, column_name, form_data):
        if "FOREIGN KEY" not in constraints:
            return None
            
        foreign_table = form_data.get(f"foreignTableInput[{index}]")
        foreign_column = form_data.get(f"foreignColumnInput[{index}]")
        
        if not foreign_table or not foreign_column:
            return f"Failed: Undefined Referenced Table or Column for foreign key in column {column_name}", None
            
        is_valid, error_message = self.fk_validator.validate_foreign_key(foreign_table, foreign_column)
        if not is_valid:
            return f"Failed: {error_message}", None
            
        return f"FOREIGN KEY ({column_name}) REFERENCES {foreign_table}({foreign_column})" 