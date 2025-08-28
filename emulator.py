import time

import pandas
from datetime import datetime
import numpy as np
import random
import MultiPyVu as mpv

def acquire_samples_debug(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    #data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])
    rng = np.random.default_rng()

    current_timestamp = datetime.now()
    timedelta = current_timestamp - time_at_startup
    readings = {
            "resistance": rng.random()*1000 + 6000,
            "quadrature": rng.random() * 10 + 60,
            "power": rng.random() * 1E-6 + 6E-6,
    }
    data = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                            readings['quadrature'], readings['power']]],
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P"])
    for _ in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup
        readings = {
            "resistance": _ * rng.random() * 1000 + 6000,
            "quadrature": _ * rng.random() * 10 + 60,
            "power": _ * rng.random() * 1E-6 + 6E-6,
        }
        series_for_concat = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                                               readings['quadrature'], readings['power']]],
                                             columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

        data = pandas.concat([data, series_for_concat], ignore_index=True)
    return data


def acquire_samples_debug_ppms(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None,
                               _mpv_client=mpv.Client()):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    # Create random number generator
    rng = np.random.default_rng()

    # Pre-allocate the DataFrame with the correct number of rows
    data = pandas.DataFrame(index=range(number_of_samples + 1),  # +1 because original code had an extra initial row
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

    # Collect data for each sample
    for i in range(number_of_samples + 1):  # +1 to match original behavior
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        # Generate debug readings with same random distribution as original
        readings = {
            "resistance": i * rng.random() * 1000 + 6000,
            "quadrature": i * rng.random() * 10 + 60,
            "power": i * rng.random() * 1E-6 + 6E-6,
        }

        try:
            field, field_status = _mpv_client.get_field()
        except:
            field = field_status = np.nan

        try:
            temp, temp_status = _mpv_client.get_temperature()
        except:
            temp = temp_status = np.nan

        # Insert data into the pre-allocated DataFrame
        data.iloc[i] = [
            current_timestamp,
            timedelta.total_seconds(),
            readings['resistance'],
            readings['quadrature'],
            readings['power'],
            field,
            temp
        ]

    return data