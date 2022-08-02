import os
import psycopg2.extras


def get_pgfutter_path():
    uname = os.uname()
    if uname.machine == "aarch64":
        return "/root/pgfutter_arm"
    else:
        return "/root/pgfutter_x64"
    return None


def get_column_operators(
    target_columns, no_override_columns, source, table, output_map, DB_IMPORT_SCHEMA
):
    column_assignments = []
    column_comparisons = []
    column_aggregators = []
    for column in target_columns:
        if (not column["column_name"] in no_override_columns) and column[
            "column_name"
        ] in source:
            column_assignments.append(
                f"{column['column_name']} = {DB_IMPORT_SCHEMA}.{table}.{column['column_name']}"
            )
            column_comparisons.append(
                # there are two ways to be equal. Either be of the same value and type or /both/ be undefined
                f"""
                (
                    public.{output_map[table]}.{column['column_name']} = {DB_IMPORT_SCHEMA}.{table}.{column['column_name']}
                OR
                    ( public.{output_map[table]}.{column['column_name']} IS NULL AND {DB_IMPORT_SCHEMA}.{table}.{column['column_name']} IS NULL )
                )
                """
            )
            column_aggregators.append(
                f"""
                case when not (
                    public.{output_map[table]}.{column['column_name']} = {DB_IMPORT_SCHEMA}.{table}.{column['column_name']}
                    or
                    (public.{output_map[table]}.{column['column_name']} is null and {DB_IMPORT_SCHEMA}.{table}.{column['column_name']} is null)
                ) then '{column['column_name']}' else null end
            """
            )
    return column_assignments, column_comparisons, column_aggregators


def check_if_update_is_a_non_op(
    pg,
    column_comparisons,
    output_map,
    table,
    linkage_clauses,
    public_key_sql,
    DB_IMPORT_SCHEMA,
):
    sql = "select (" + " and ".join(column_comparisons) + ") as skip_update\n"
    sql += f"from public.{output_map[table]}\n"
    sql += (
        f"left join {DB_IMPORT_SCHEMA}.{table} on ("
        + " and ".join(linkage_clauses)
        + ")\n"
    )
    sql += f"where {public_key_sql}\n"

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    skip_update_query = cursor.fetchone()
    if skip_update_query["skip_update"]:
        return True
    else:
        return False


def get_changed_columns(
    pg,
    column_aggregators,
    output_map,
    table,
    linkage_clauses,
    public_key_sql,
    DB_IMPORT_SCHEMA,
):
    sql = "select "
    sql += (
        "array_remove(array["
        + ",".join(column_aggregators)
        + "], null)"
        + "as changed_columns "
    )
    sql += f"from public.{output_map[table]} "
    sql += (
        f"left join {DB_IMPORT_SCHEMA}.{table} on ("
        + " and ".join(linkage_clauses)
        + ")\n"
    )
    sql += f"where {public_key_sql}\n"
    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    changed_columns = cursor.fetchone()
    return changed_columns


def get_key_clauses(table_keys, output_map, table, source, DB_IMPORT_SCHEMA):
    # form some snippets we'll reuse
    public_key_clauses = []
    import_key_clauses = []
    for key in table_keys[output_map[table]]:
        public_key_clauses.append(f"public.{output_map[table]}.{key} = {source[key]}")
        import_key_clauses.append(f"{DB_IMPORT_SCHEMA}.{table}.{key} = {source[key]}")
    public_key_sql = " and ".join(public_key_clauses)
    import_key_sql = " and ".join(import_key_clauses)
    return public_key_sql, import_key_sql


def fetch_target_record(pg, output_map, table, public_key_sql):
    # build and execute a query to find our target record; we're looking for it to exist
    sql = f"""
    select * 
    from public.{output_map[table]}
    where 
    {public_key_sql}
    """
    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    target = cursor.fetchone()
    return target


def form_update_statement(
    output_map, table, column_assignments, DB_IMPORT_SCHEMA, public_key_sql, linkage_sql
):
    sql = "update public." + output_map[table] + " set "
    # this next line adds the column assignments generated above into this query.
    sql += ", ".join(column_assignments) + " "
    sql += f"""
    from {DB_IMPORT_SCHEMA}.{table}
    where 
    {public_key_sql}
    {linkage_sql}
    """
    return sql


def form_insert_statement(
    output_map, table, input_column_names, import_key_sql, DB_IMPORT_SCHEMA
):
    sql = f"insert into public.{output_map[table]} "
    sql += "(" + ", ".join(input_column_names) + ") "
    sql += "(select "
    sql += ", ".join(input_column_names)
    sql += f" from {DB_IMPORT_SCHEMA}.{table}"
    sql += f" where {import_key_sql})"
    return sql


def try_statement(pg, output_map, table, public_key_sql, sql):
    try:
        cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql)
        pg.commit()
    except Exception as error:
        print(
            f"There is likely an issue with existing data. Try looking for results in {output_map[table]} with the following WHERE clause:\n'{public_key_sql}'"
        )
        print(f"Error executing:\n\n{sql}\n")
        print("\a")  # 🛎


def get_input_column_names(pg, DB_IMPORT_SCHEMA, table, target_columns):
    sql = f"""
    SELECT
        column_name,
        data_type,
        character_maximum_length AS max_length,
        character_octet_length AS octet_length
    FROM
        information_schema.columns
    WHERE true
        AND table_schema = '{DB_IMPORT_SCHEMA}'
        AND table_name = '{table}'
    """

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    input_table_column_types = cursor.fetchall()

    input_column_names = []
    for column in input_table_column_types:
        if column in target_columns:
            input_column_names.append(column["column_name"])
    return input_column_names
