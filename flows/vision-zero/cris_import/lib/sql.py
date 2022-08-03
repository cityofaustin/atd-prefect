import os
import psycopg2.extras


# This library is /not/ designed for reuse in other projects. It is designed to increase the
# readability of the `cris_import.py` prefect flow by pulling logical groups of code out
# and replacing them with a descriptively named function. The code was reviewed with an
# eye for getting 100% of the code which forms SQL directly into this file, as code which writes
# code is universally hard to read and grok. If one considers that each of these functions is called
# in only one place in `cris_import.py`, one may appreciate these functions exist only to improve
# readability and maintainability -- not reusability.


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


def try_statement(pg, output_map, table, public_key_sql, sql, dry_run):
    if dry_run:
        print("Dry run; skipping")
        return
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


def get_target_columns(pg, output_map, table):
    sql = f"""
    SELECT
        column_name,
        data_type,
        character_maximum_length AS max_length,
        character_octet_length AS octet_length
    FROM
        information_schema.columns
    WHERE true
        AND table_schema = 'public'
        AND table_name = '{output_map[table]}'
    """

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    target_columns = cursor.fetchall()
    return target_columns


def load_input_data_for_keying(pg, DB_IMPORT_SCHEMA, table):
    sql = f"select * from {DB_IMPORT_SCHEMA}.{table}"

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    imported_records = cursor.fetchall()
    return imported_records


def get_linkage_constructions(key_columns, output_map, table, DB_IMPORT_SCHEMA):
    linkage_clauses = []
    for column in key_columns:
        linkage_clauses.append(
            f"public.{output_map[table]}.{column} = {DB_IMPORT_SCHEMA}.{table}.{column}"
        )
    linkage_sql = " AND " + " AND ".join(linkage_clauses)
    return linkage_clauses, linkage_sql


def get_imported_tables(pg, DB_IMPORT_SCHEMA):
    sql = f"SELECT * FROM information_schema.tables WHERE table_schema = '{DB_IMPORT_SCHEMA}';"
    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    imported_tables = cursor.fetchall()
    return imported_tables


def enforce_complete_keying(
    pg, key_columns, output_table, DB_IMPORT_SCHEMA, input_table
):
    # drop any records without appropriate keying
    # keys = mappings.get_key_columns()[output_table]
    keys = key_columns[output_table]
    sql = f"delete from {DB_IMPORT_SCHEMA}.{input_table['table_name']}"
    clauses = []
    for key in keys:
        clauses.append(f"{key} ~ '^\s*$'")
    sql += " where (" + " or ".join(clauses) + ")"

    cursor = pg.cursor()
    cursor.execute(sql)
    pg.commit()


def get_output_column_types(pg, output_table):
    # This is a subtle SQL injection attack vector.
    # Beware the f-string. But I trust CRIS.
    sql = f"""
    SELECT
        column_name,
        data_type,
        character_maximum_length AS max_length,
        character_octet_length AS octet_length
    FROM
        information_schema.columns
    WHERE true
        AND table_schema = 'public'
        AND table_name = '{output_table}'
    """

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    output_column_types = cursor.fetchall()
    return output_column_types


def get_input_column_type(pg, DB_IMPORT_SCHEMA, input_table, column):
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
        AND table_name = '{input_table["table_name"]}'
        AND column_name = '{column["column_name"]}'
    """

    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    input_column_type = cursor.fetchall()
    return input_column_type


def form_alter_statement_to_apply_column_typing(DB_IMPORT_SCHEMA, input_table, column):
    # the `USING` hackery is due to the reality of the CSV null vs "" confusion
    return f"""
            ALTER TABLE {DB_IMPORT_SCHEMA}.{input_table["table_name"]}
            ALTER COLUMN {column["column_name"]} SET DATA TYPE {column["data_type"]}
            USING case when {column["column_name"]} = \'\' then null else {column["column_name"]}::{column["data_type"]} end
            """
