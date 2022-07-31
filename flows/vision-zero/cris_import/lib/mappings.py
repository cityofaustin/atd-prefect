
def get_table_map():
    return {
        'crash': 'atd_txdot_crashes',
        'unit': 'atd_txdot_units',
        'person': 'atd_txdot_person',
        'primaryperson': 'atd_txdot_primaryperson',
        'charges': 'atd_txdot_charges',
        }

def get_key_columns():
    return {
        'atd_txdot_crashes': ['crash_id'],
        'atd_txdot_units': ['crash_id', 'unit_nbr'],
        'atd_txdot_person': ['crash_id', 'prsn_nbr'],
        'atd_txdot_primaryperson': ['crash_id', 'prsn_nbr'],
        'atd_txdot_charges': ['crash_id', 'prsn_nbr', 'unit_nbr'],
    }