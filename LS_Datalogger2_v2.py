import pandas
import requests
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
            readings['quadrature'],
            readings['power'],
            field,
            temp
        ]

    return data

def acquire_data_synktek(number_of_samples, time_at_startup, _mpv_client=mpv.Client()):


    # Pre-allocate the DataFrame with the correct number of rows
    data_a = pandas.DataFrame(index=range(number_of_samples),
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])
    data_b = pandas.DataFrame(index=range(number_of_samples),
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])
    data_c = pandas.DataFrame(index=range(number_of_samples),
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

    # Collect data for each sample
    for i in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        try:
            field, field_status = _mpv_client.get_field()
        except:
            field = field_status = np.nan

        try:
            temp, temp_status = _mpv_client.get_temperature()
        except:
            temp = temp_status = np.nan

        X = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[0]/').json()
        Y = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/Y[0]/').json()
        I = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[10]/').json()


        R = X/I
        # Insert data into the pre-allocated DataFrame
        data_a.iloc[i] = [
            current_timestamp,
            timedelta.total_seconds(),
            R,
            Y,
            I*I*X,
            field,
            temp
        ]

        X = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[2]/').json()
        Y = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/Y[2]/').json()
        I = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[11]/').json()


        R = X / I
        # Insert data into the pre-allocated DataFrame
        data_b.iloc[i] = [
            current_timestamp,
            timedelta.total_seconds(),
            R,
            Y,
            I * I * X,
            field,
            temp
        ]

        X = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[4]/').json()
        Y = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/Y[4]/').json()
        I = requests.get(
            'http://172.22.11.2:8002/MCL/api?type=data&id=L1&action=get&path=/output_cluster/DataReadings/X[12]/').json()

        R = X / I
        # Insert data into the pre-allocated DataFrame
        data_c.iloc[i] = [
            current_timestamp,
            timedelta.total_seconds(),
            R,
            Y,
            I * I * X,
            field,
            temp
        ]

    return data_a, data_b#, data_c
