
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

def no_override_columns():
    return {
        'atd_txdot_crashes': {
            'crash_id', # key column
            "longitude_primary",
            "latitude_primary",
            "city_id",
            "crash_speed_limit",
            "road_type_id",
            "traffic_cntl_id",
            "crash_sev_id",
            "atd_fatality_count",
            "apd_confirmed_death_count",
            "tot_injry_cnt",
            "atd_txdot_crashes.sus_serious_injry_cnt",
            "address_confirmed_primary",
            "address_confirmed_secondary",
            "private_dr_fl",
            "road_constr_zone_fl",
            "micromobility_device_flag",
        },
    }