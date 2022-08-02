
import os

def get_pgfutter_path():
    uname = os.uname()
    if uname.machine == "aarch64":
        return "/root/pgfutter_arm"
    else:
        return "/root/pgfutter_x64"
    return None


def get_column_operators(
    target_columns, no_override_columns, source, table, output_map
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
    pg, column_comparisons, output_map, table, linkage_clauses, public_key_sql
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
    pg, column_aggregators, output_map, table, linkage_clauses, public_key_sql
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
