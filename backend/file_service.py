import pandas as pd
import numpy as np
import chardet
import re
import datetime
import io
from sqlalchemy import text
from .queries.create_table import CreateTableQuery
from .queries.insert_data import InsertDataQuery

class FileService:
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def export_table_to_excel(self, table_name):
        if not self.db_engine:
            return None, "Failed: No Active DB Connection"
        
        if not table_name or not table_name.strip():
            return None, "Failed: Undefined Table Name"
        
        try:
            with self.db_engine.connect() as c:
                query = f"SELECT * FROM {table_name}"
                output = c.execute(text(query))
                df = pd.DataFrame(output.fetchall(), columns=output.keys())
                
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine="xlsxwriter") as w:
                    df.to_excel(w, index=False, sheet_name=table_name)
                excel_data.seek(0)
                
                return excel_data, "Succeed: Table exported to Excel"
        except Exception as e:
            return None, f"Failed: {str(e)}"

    def import_excel_to_table(self, table_name, file):
        if not self.db_engine:
            return "Failed: No Active DB Connection", None
        
        if not table_name:
            return "Failed: Undefined Table Name", None
        if not file:
            return "Failed: Undefined Excel File", None

        try:
            df = self._read_file(file)
            df = self._normalize_dataframe(df)
            data = self._prepare_data_for_insert(df)
            column_types = self._infer_column_types(df)

            message, query = self._create_and_populate_table(table_name, df, column_types, data)
            return message, query
            
        except Exception as e:
            return f"Failed: {str(e)}", None

    def _read_file(self, file):
        filename = file.filename.lower()
        
        if filename.endswith(".csv"):
            return self._read_csv_with_encoding_detection(file)
        elif filename.endswith(".xlsx"):
            file.seek(0)
            return pd.read_excel(file, engine="openpyxl")
        elif filename.endswith(".xls"):
            file.seek(0)
            return pd.read_excel(file, engine="xlrd")
        else:
            raise ValueError("Unsupported file format")

    def _read_csv_with_encoding_detection(self, file):
        encoding_sample = file.read(7000)
        file.seek(0)
        
        detected_encoding = chardet.detect(encoding_sample).get("encoding", "utf-8")
        encodings = list(dict.fromkeys([
            detected_encoding, "utf-8", "utf-8-sig", "latin1", "iso-8859-1", "windows-1252"
        ]))

        for encoding in encodings:
            try:
                file.seek(0)
                return pd.read_csv(file, encoding=encoding, engine="python")
            except Exception:
                continue
        
        raise ValueError("Undecoded CSV file")

    def _normalize_dataframe(self, df):
        df.columns = df.columns.str.strip().str.lower()
        normalized_columns = [re.sub(r"\W+", "_", col.strip()) for col in df.columns]
        df.columns = normalized_columns
        return df.replace({"N/A": None, np.nan: None})

    def _prepare_data_for_insert(self, df):
        data = df.to_dict(orient="records")
        
        for row in data:
            for key, value in row.items():
                if isinstance(value, str):
                    row[key] = f"'{value.replace(chr(39), chr(39)*2)}'"
                elif isinstance(value, (datetime.date, datetime.datetime)):
                    row[key] = f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
                elif value is None:
                    row[key] = None
        
        return data

    def _create_and_populate_table(self, table_name, df, column_types, data):
        create_table_query = CreateTableQuery(
            self.db_engine, 
            table_name, 
            list(zip(df.columns, column_types, [None] * len(df.columns))),  
            []
        )
        message, query = create_table_query.execute()

        if "Failed" in message:
            return message, query

        insert_data_query = InsertDataQuery(self.db_engine, table_name, df.columns.tolist(), data)
        return insert_data_query.execute()

    def _infer_column_types(self, df):
        column_types = []
        df_data = df.iloc[1:].reset_index(drop=True) if len(df) > 1 else df
        
        type_patterns = {
            'DATE': r"\d{4}-\d{2}-\d{2}",
            'DATETIME': r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            'BOOLEAN': r"(?i)TRUE|FALSE"
        }

        for column in df.columns:
            col_type = self._determine_column_type(df_data[column], type_patterns)
            column_types.append(col_type)

        return column_types

    def _determine_column_type(self, col_data, type_patterns):
        dtype = col_data.dtype
        col_data_clean = col_data.dropna()
        
        if len(col_data_clean) == 0:
            return "VARCHAR(255)"
            
        col_str = col_data_clean.astype(str)

        if np.issubdtype(dtype, np.integer):
            return "INT"
        elif np.issubdtype(dtype, np.floating):
            return "FLOAT"
        elif np.issubdtype(dtype, np.bool_):
            return "TINYINT(1)"
        elif np.issubdtype(dtype, np.datetime64):
            if col_str.str.fullmatch(type_patterns['DATE']).all():
                return "DATE"
            elif col_str.str.fullmatch(type_patterns['DATETIME']).all():
                return "DATETIME"
            return "VARCHAR(255)"
        
        if col_data_clean.apply(self._is_numeric_type).all():
            if col_data_clean.apply(self._is_integer).all():
                return "INT"
            return "FLOAT"
        
        for pattern_name, pattern in type_patterns.items():
            if col_str.str.fullmatch(pattern).all():
                if pattern_name == 'BOOLEAN':
                    return "TINYINT(1)"
                return pattern_name
        
        max_length = col_str.str.len().max()
        return "VARCHAR(255)" if max_length is not None and max_length <= 255 else "TEXT"

    def _is_numeric_type(self, val):
        return self._is_integer(val) or self._is_float(val)

    def _is_integer(self, val):
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

    def _is_float(self, val):
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