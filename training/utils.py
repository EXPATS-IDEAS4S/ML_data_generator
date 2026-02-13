"""
Collection of functions that do basic operations on the data, such initializing logger, 
check if time is valid, parse timestamps etc
date: 2024-06-20
author: Claudia Acquistapace
"""




def is_valid_time(timestamp, month, day, hour):
    """
    Checks if the given timestamp falls within the specified month, day, and hour ranges of the config 
    """
    return (
        MONTH_START <= month <= MONTH_END and
        HOUR_START <= hour < HOUR_END and
        DAY_START <= day <= DAY_END 

    )

def parse_timestamp(timestamp):
    """
    Extracts hour, month, day, year, and minute from a timestamp.
    """
    # extract hour from timestamp
    hour = str(timestamp).split('T')[1][0:2]
    month = str(timestamp).split('T')[0].split('-')[1]
    day = str(timestamp).split('T')[0].split('-')[2]
    yyyy = str(timestamp).split('T')[0].split('-')[0]
    minute = str(timestamp).split('T')[1][3:5]

    return hour, month, day, yyyy, minute