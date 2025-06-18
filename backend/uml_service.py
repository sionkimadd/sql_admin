from sqlalchemy import inspect

class UMLService:
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def generate_uml(self, start_table):
        if not self.db_engine:
            return "Failed: No Active DB Connection", None

        if not start_table:
            return "Failed: Undefined Table Name", None

        inspector = inspect(self.db_engine)
        all_tables = inspector.get_table_names()
        if start_table not in all_tables:
            return f"Failed: Table {start_table} Unexist", None

        visited_tables, edges = self._gather_related_tables(inspector, start_table)

        full_uml_lines = []
        for tbl in sorted(visited_tables):
            table_uml = self._generate_table_uml(inspector, tbl)
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
        return "Succeed: ERD Generated", uml_text

    def _gather_related_tables(self, inspector, start_table):
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

    def _generate_table_uml(self, inspector, table_name):
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