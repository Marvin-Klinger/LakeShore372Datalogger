import pandas
from lakeshore import Model372
from datetime import datetime
import numpy as np
import time
import MultiPyVu as mpv


def get_resistance_channel(channel_number, number_of_samples=10, time_at_startup=datetime.now()):
    with Model372(baud_rate=None, ip_address="192.168.0.12") as model372:
        resistance = np.empty(1)
        quadrature = np.empty(1)
        power = np.empty(1)
        sample_time = np.empty(1)
        elapsed = np.empty(1)

        for _ in range(number_of_samples):
            readings = model372.get_all_input_readings(channel_number)
            timedelta = datetime.now() - time_at_startup
            resistance = resistance.append(readings['resistance'])
            quadrature = quadrature.append(readings['quadrature'])
            power = power.append(readings['power'])
            sample_time = sample_time.append(datetime.now())
            elapsed = elapsed.append(timedelta.total_seconds())

    return time, timedelta, resistance, quadrature, power


def acquire_samples(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    # data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

    current_timestamp = datetime.now()
    timedelta = current_timestamp - time_at_startup

    readings = model372.get_all_input_readings(channel_number)
    data = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                            readings['quadrature'], readings['power']]],
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

    for _ in range(number_of_samples - 1):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = model372.get_all_input_readings(channel_number)
        series_for_concat = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                                               readings['quadrature'], readings['power']]],
                                             columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

        data = pandas.concat([data, series_for_concat], ignore_index=True)
    return data


def acquire_samples_ppms(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None,
                         _mpv_client=mpv.Client()):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    # Create empty DataFrame with the required columns
    # data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

    # Pre-allocate the DataFrame with the correct number of rows
    data = pandas.DataFrame(index=range(number_of_samples),
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

    # Collect data for each sample
    for i in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = model372.get_all_input_readings(channel_number)

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
            np.nan,
            readings['power'],
            field,
            temp
        ]
        time.sleep(0.1)

    return data
