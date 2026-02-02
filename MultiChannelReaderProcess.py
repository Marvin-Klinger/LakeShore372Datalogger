from multiprocessing import Process, Queue, Value
from LS_Datalogger2_v2 import acquire_samples_ppms
from emulator import acquire_samples_debug_ppms
from lakeshore import Model372, Model372InputSetupSettings
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
import TemperatureCalibration
import MultiPyVu as mpv
from collections import deque
import numpy as np
import time
import os
import pandas
from pymeasure.instruments.srs import SR830
from zhinst.toolkit import Session
from zhinst.core import ziDiscovery
import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog
import webbrowser

LakeShoreCommunicationMethod = {
  "tbd": 0,
  "usb": 1,
  "ip": 2
}
LakeShoreIPAddress = "192.168.0.12"
ActiveLakeShoreCommunicationMethod = LakeShoreCommunicationMethod["usb"]

def on_close(thread_stop_indicator):
    thread_stop_indicator.value = True

def auto_cal(_filepath, ip_address, _time_at_beginning_of_experiment, _mpv_client, channels):
    number_of_samples = 100
    cal_channels = [9,10,11,12]
    cal_values = [2000, 20000, 49.9, 49.9*3]

    cal_currents = [Model372.MeasurementInputCurrentRange.RANGE_316_PICO_AMPS,
                  Model372.MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                  Model372.MeasurementInputCurrentRange.RANGE_3_POINT_16_NANO_AMPS,
                  Model372.MeasurementInputCurrentRange.RANGE_10_NANO_AMPS]

    cal_ranges = [Model372.MeasurementInputResistance.RANGE_2_KIL_OHMS,
                  Model372.MeasurementInputResistance.RANGE_6_POINT_32_KIL_OHMS,
                  Model372.MeasurementInputResistance.RANGE_20_KIL_OHMS,
                  Model372.MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS,
                  Model372.MeasurementInputResistance.RANGE_200_KIL_OHMS,
                  Model372.MeasurementInputResistance.RANGE_632_KIL_OHMS]

    for channel in channels:
        for range in cal_ranges:
            for current in cal_currents:
                channel_settings = Model372InputSetupSettings(Model372.SensorExcitationMode.CURRENT,
                                                              current,
                                                              Model372.AutoRangeMode.OFF, False,
                                                              Model372.InputSensorUnits.OHMS, range)
                ip_address = LakeShoreIPAddress
                if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["usb"]:
                    instrument_372 = Model372(57600)
                if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["ip"]:
                    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

                instrument_372.configure_input(channel, channel_settings)
                instrument_372.set_scanner_status(input_channel=channel, status=False)
                time.sleep(5)
                sample_data = acquire_samples_ppms(instrument_372, number_of_samples, channel,
                                                   _time_at_beginning_of_experiment, _mpv_client=_mpv_client)
                sample_data.to_csv(_filepath, sep=',', encoding='utf-8', index=False, header=True)

def setup_new_logger(channel_number, _time, measurements_per_scan, filepath='./', delimiter=','):
    name = f"logger {channel_number}"
    lgr = logging.getLogger(name)
    lgr.setLevel(logging.DEBUG)
    fh = logging.FileHandler(
        f"{filepath}/Channel {channel_number}.csv")
    fh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(message)s')
    fh.setFormatter(frmt)
    lgr.addHandler(fh)
    lgr.info("Measurement of thermometer resistivity with Lake Shore 372 AC Bridge")
    lgr.info("Data is aggregated with " + str(measurements_per_scan) + " samples for every line of this log.")
    lgr.info("This file does not contain raw data!")
    lgr.info("Data field names and types:")
    lgr.info(
        "Timestamp" + delimiter +
        "Elapsed_time" + delimiter +
        "Elapsed_time_error" + delimiter +
        "Thermometer_temperature" + delimiter +
        "Thermometer_temperature_error" + delimiter +
        "Resistance_thermometer" + delimiter +
        "Resistance_thermometer_error" + delimiter +
        "Quadrature_thermometer" + delimiter +
        "Quadrature_thermometer_error" + delimiter +
        "Power_thermometer" + delimiter +
        "Power_thermometer_error" + delimiter +
        "Field_PPMS" + delimiter +
        "Field_PPMS_error" + delimiter +
        "Temperature_PPMS" + delimiter +
        "Temperature_PPMS_error"
    )
    lgr.info(
        "[YYYY-MM-DD hh:mm:ss.###]" + delimiter +
        "second" + delimiter +
        "second" + delimiter +
        "Kelvin" + delimiter +
        "Kelvin" + delimiter +
        "Ohm" + delimiter +
        "Ohm" + delimiter +
        "iOhm" + delimiter +
        "iOhm" + delimiter +
        "Watt" + delimiter +
        "Watt" + delimiter +
        "Oe" + delimiter +
        "Oe" + delimiter +
        "Kelvin" + delimiter +
        "Kelvin"
    )
    return lgr


def visualize_n_channels(channels, queue, _time_at_beginning_of_experiment, measurements_per_scan, filepath,
                         temperature_calibrations, delimiter=',', thread_stop_indicator=Value('b', False)):

    colors = ["#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff", "#d53e3eff"]

    #colors = ["#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff"]
    max_recent_points = 100  # Maximum points in recent deque
    buffer_threshold = 200  # When to downsample buffer points

    # Initialize data storage for each channel using two-part storage strategy
    channel_data = {ch: {
        'historical': {  # Twice downsampled, fixed
            'time': [],
            'resistance': [],
            'temperature': []
        },
        'recent': {  # Most recent points, full resolution
            'time': deque(maxlen=max_recent_points),
            'resistance': deque(maxlen=max_recent_points),
            'temperature': deque(maxlen=max_recent_points)
        },
        'buffer': {  # Once downsampled points
            'time': [],
            'resistance': [],
            'temperature': []
        }
    } for ch in channels}

    # Setup loggers
    loggers = [[] for _ in range(17)]
    for channel in channels:
        _lgr = setup_new_logger(channel, _time_at_beginning_of_experiment, measurements_per_scan, filepath)
        _lgr.disabled = False
        _lgr.propagate = False
        loggers[channel] = _lgr

    # Plot setup - create figure before turning on interactive mode
    fig, axs = plt.subplots(2, 1, constrained_layout=True, sharex=True, figsize=(10, 8))

    # Configure axes
    axs[0].set_ylabel('Resistance [Ohm]')
    axs[1].set_ylabel('Calibrated temperature [K]')
    axs[1].set_yscale('log')
    axs[0].set_yscale('log')
    axs[1].set_xlabel('Time [s]')
    axs[0].set_title(os.path.basename(os.getcwd()))
    axs[0].grid(False)
    axs[1].grid(False)

    # Initialize line objects for each channel (separate lines for each data type)
    channel_lines = {ch: {
        'resistance': {
            'historical': axs[0].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2)[0],
            'buffer': axs[0].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2)[0],
            'recent': axs[0].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2,
                                  label=f"Ch {ch}")[0]
        },
        'temperature': {
            'historical': axs[1].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2)[0],
            'buffer': axs[1].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2)[0],
            'recent': axs[1].plot([], [], color=colors[ch - 1], linestyle='', marker='.', markersize=2)[0]
        }
    } for ch in channels}

    axs[0].legend(loc='upper left')

    def downsample_buffer(buffer_data):
        """Downsample buffer data by averaging adjacent pairs of points"""
        if len(buffer_data['time']) < 2:
            return buffer_data

        # Convert to numpy arrays for efficient processing
        times = np.array(buffer_data['time'])
        resistances = np.array(buffer_data['resistance'])
        temperatures = np.array(buffer_data['temperature'])

        # Calculate number of complete pairs
        n_pairs = len(times) // 2

        # Downsample by averaging pairs
        downsampled = {
            'time': np.mean(times[:2 * n_pairs].reshape(-1, 2), axis=1).tolist(),
            'resistance': np.mean(resistances[:2 * n_pairs].reshape(-1, 2), axis=1).tolist(),
            'temperature': np.mean(temperatures[:2 * n_pairs].reshape(-1, 2), axis=1).tolist()
        }

        # Handle any remaining odd point
        if len(times) % 2:
            downsampled['time'].append(times[-1])
            downsampled['resistance'].append(resistances[-1])
            downsampled['temperature'].append(temperatures[-1])

        return downsampled

    def update_plot_data(ch):
        """Update plot data for a specific channel"""
        data = channel_data[ch]

        # Update historical data
        channel_lines[ch]['resistance']['historical'].set_data(
            data['historical']['time'],
            data['historical']['resistance']
        )
        channel_lines[ch]['temperature']['historical'].set_data(
            data['historical']['time'],
            data['historical']['temperature']
        )

        # Update buffer data
        channel_lines[ch]['resistance']['buffer'].set_data(
            data['buffer']['time'],
            data['buffer']['resistance']
        )
        channel_lines[ch]['temperature']['buffer'].set_data(
            data['buffer']['time'],
            data['buffer']['temperature']
        )

        # Update recent data
        channel_lines[ch]['resistance']['recent'].set_data(
            list(data['recent']['time']),
            list(data['recent']['resistance'])
        )
        channel_lines[ch]['temperature']['recent'].set_data(
            list(data['recent']['time']),
            list(data['recent']['temperature'])
        )

    # Initial draw
    fig.canvas.draw()
    plt.show(block=False)

    # Connect close event
    fig.canvas.mpl_connect('close_event', lambda event: on_close(thread_stop_indicator))

    last_update = time.time()
    update_interval = 0.4
    was_zoomed = False

    while True:
        if thread_stop_indicator.value:
            break

        data_processed = False
        while not queue.empty():
            channel_index, sample_data = queue.get()

            # Calculate means
            resistance = sample_data["R"].mean()
            time_value = sample_data["Elapsed time"].mean()
            temperature = temperature_calibrations[channel_index - 1](resistance)

            data = channel_data[channel_index]

            # If recent deque is full, move oldest point to buffer
            if len(data['recent']['time']) == max_recent_points:
                data['buffer']['time'].append(data['recent']['time'][0])
                data['buffer']['resistance'].append(data['recent']['resistance'][0])
                data['buffer']['temperature'].append(data['recent']['temperature'][0])

            # Add new point to recent
            data['recent']['time'].append(time_value)
            data['recent']['resistance'].append(resistance)
            data['recent']['temperature'].append(temperature)

            # Check if buffer needs downsampling
            if len(data['buffer']['time']) >= buffer_threshold:
                # First, move current buffer to historical (after downsampling)
                downsampled = downsample_buffer(data['buffer'])
                data['historical']['time'].extend(downsampled['time'])
                data['historical']['resistance'].extend(downsampled['resistance'])
                data['historical']['temperature'].extend(downsampled['temperature'])

                # Clear buffer
                data['buffer']['time'].clear()
                data['buffer']['resistance'].clear()
                data['buffer']['temperature'].clear()

            # Log data
            log_data(loggers[channel_index], sample_data, temperature_calibrations[channel_index - 1], delimiter)
            data_processed = True

        # Update plots if needed
        current_time = time.time()
        if data_processed and current_time - last_update >= update_interval:
            for ch in channels:
                update_plot_data(ch)

                # Handle auto-scaling
            if fig.canvas.toolbar.mode == '':
                if was_zoomed:
                    axs[0].autoscale()
                    axs[1].autoscale()
                    was_zoomed = False
                for ax in axs:
                    ax.relim()
                    ax.autoscale_view()
            else:
                was_zoomed = True

            fig.canvas.draw_idle()
            fig.canvas.flush_events()
            last_update = current_time

        plt.pause(0.4)

def log_data(logger, sample_data, temperature_calibration, delimiter):
    """Helper function to handle logging of data"""
    resistance = sample_data["R"].mean()
    quadrature = sample_data["iR"].mean()
    power = sample_data["P"].mean()
    time_val = sample_data["Elapsed time"].mean()
    temperature_ppms = sample_data["PPMS_T"].mean()
    field_ppms = sample_data["PPMS_B"].mean()

    resistance_err = sample_data["R"].std()
    quadrature_err = sample_data["iR"].std()
    power_err = sample_data["P"].std()
    time_err = sample_data["Elapsed time"].std()
    temperature_ppms_err = sample_data["PPMS_T"].std()
    field_ppms_err = sample_data["PPMS_B"].std()

    temperature = temperature_calibration(resistance)
    temperature_upper = temperature_calibration(resistance - resistance_err)
    temperature_lower = temperature_calibration(resistance + resistance_err)
    temperature_error = np.absolute((temperature_upper - temperature_lower) / 2)

    logline = (f"{datetime.now()}{delimiter}"
               f"{time_val}{delimiter}{time_err}{delimiter}"
               f"{temperature}{delimiter}{temperature_error}{delimiter}"
               f"{resistance}{delimiter}{resistance_err}{delimiter}"
               f"{quadrature}{delimiter}{quadrature_err}{delimiter}"
               f"{power}{delimiter}{power_err}{delimiter}"
               f"{field_ppms}{delimiter}{field_ppms_err}{delimiter}"
               f"{temperature_ppms}{delimiter}{temperature_ppms_err}")

    logger.info(logline)


def read_lakeshore_channel_a(queue, _time_at_beginning_of_experiment, measurements_per_scan, thread_stop_indicator=Value('b', False), debug=False):
    mpv_client = mpv.Client()

    if measurements_per_scan > 100:
        measurements_per_scan = 100

    try:
        mpv_client.open()
    except:
        print("LS Channel A : Could not connect to PPMS")

    while debug:
        time.sleep(0.1)
        data = acquire_samples_debug_ppms(False, measurements_per_scan, 'A',
                                          _time_at_beginning_of_experiment, _mpv_client=mpv_client)
        queue.put((13, data))
        if thread_stop_indicator.value:
            mpv_client.close_client()
            mpv_client.close_server()
            break

    ip_address = LakeShoreIPAddress
    if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["usb"]:
        instrument_372 = Model372(57600)
    if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["ip"]:
        instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

    while True:
        if thread_stop_indicator.value:
            mpv_client.close_client()
            mpv_client.close_server()
            break

        sample_data = acquire_samples_ppms(instrument_372, measurements_per_scan, 'A',
                                           _time_at_beginning_of_experiment, _mpv_client=mpv_client)
        queue.put((13, sample_data))


def read_sr830(queue, _time_at_beginning_of_experiment, measurements_per_scan, thread_stop_indicator=Value('b', False), debug=False):

    current_setting_resistor = 2382
    wire_resistance_roundtrip = 30
    preamp_gain = 10000

    mpv_client = mpv.Client()
    try:
        mpv_client.open()
    except:
        print("SR830 : Could not connect to PPMS")

    while debug:
        time.sleep(0.1)
        data = acquire_samples_debug_ppms(False, measurements_per_scan, 'A',
                                          _time_at_beginning_of_experiment, _mpv_client=mpv_client)
        queue.put((14, data))
        time.sleep(0.1)

        if thread_stop_indicator.value:
            mpv_client.close_client()
            mpv_client.close_server()
            break

    lia = SR830("GPIB0::9::INSTR")

    # Set the lock-in amplifier parameters
    # lia.frequency = 1000  # Set the lock-in frequency to 1 kHz
    # lia.sensitivity = 1e-6  # Set the sensitivity to 1 µV
    # lia.time_constant = 1e-3  # Set the time constant to 1 ms

    while True:
        if thread_stop_indicator.value:
            lia.disconnect()
            mpv_client.close_client()
            mpv_client.close_server()
            break

        data = pandas.DataFrame(index=range(measurements_per_scan),
                                columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

        for i in range(measurements_per_scan):
            current_timestamp = datetime.now()
            timedelta = current_timestamp - _time_at_beginning_of_experiment

            x = lia.x / preamp_gain
            y = lia.y / preamp_gain
            v = lia.sine_voltage
            current = v / (current_setting_resistor + wire_resistance_roundtrip)
            resistance = x / current
            quadrature = y / current
            power = current * current * x

            try:
                field, field_status = mpv_client.get_field()
            except:
                field = field_status = np.nan

            try:
                temp, temp_status = mpv_client.get_temperature()
            except:
                temp = temp_status = np.nan

            # Insert data into the pre-allocated DataFrame
            data.iloc[i] = [
                current_timestamp,
                timedelta.total_seconds(),
                resistance,
                quadrature,
                power,
                field,
                temp
            ]
            time.sleep(0.1)

        queue.put((14, data))


def read_zurich(queue, _time_at_beginning_of_experiment, measurements_per_scan, thread_stop_indicator=Value('b', False), debug=False):
    device_id = 'dev30987'
    server_host = '192.168.156.14'#'127.0.0.1'#

    current_setting_resistor = 9000
    wire_resistance_roundtrip = 108
    preamp_gain = 1

    devices = list_local_zi_devices()
    if not devices:
        print("No Zurich Instruments devices found.")
        return
    else:
        dev_id, serverhost = select_device_dialog(devices)
        if dev_id is None:
            print("No device selected.")
        else:
            print(f"Selected device: {dev_id}")
            device_id = dev_id
            server_host = serverhost

    value = ask_for_resistor(
        title="MFLI setup",
        prompt="Enter the value of your current limiting resistor in Ohms",
        min_value=1,
        max_value=100000000000,
    )

    if value is None:
        print("User cancelled.")
    else:
        print(f"User entered: {value} Ohms")

    mpv_client = mpv.Client()
    try:
        mpv_client.open()
    except:
        print("Zurich : Could not connect to PPMS (non fatal, main thread is connected)")

    while debug:
        time.sleep(0.1)
        data = acquire_samples_debug_ppms(False, measurements_per_scan, 'A',
                                          _time_at_beginning_of_experiment, _mpv_client=mpv_client)
        queue.put((15, data))
        time.sleep(0.1)

        if thread_stop_indicator.value:
            mpv_client.close_client()
            mpv_client.close_server()
            break

    # Connect to the device
    session = Session(server_host)
    device = session.devices[device_id]

    print("Zurich : Session and Device created, launching browser...")
    webbrowser.open(f'http://{server_host}')

    while True:
        if thread_stop_indicator.value:
            session.disconnect_device(device_id)

            mpv_client.close_client()
            mpv_client.close_server()
            break

        device.demods[0].sample.subscribe()
        time.sleep(measurements_per_scan / 4)
        current_timestamp = datetime.now()
        timedelta = current_timestamp - _time_at_beginning_of_experiment
        time.sleep(measurements_per_scan / 4)
        device.demods[0].sample.unsubscribe()

        data = session.poll()
        try:
            demod_sample = data[device.demods[0].sample]
        except:
            print("Error getting data from MFLI, retrying...")
            continue

        try:
            field, field_status = mpv_client.get_field()
        except:
            field = field_status = np.nan

        try:
            temp, temp_status = mpv_client.get_temperature()
        except:
            temp = temp_status = np.nan

        output_voltage = device.sigouts[0].amplitudes[1]()
        output_voltage = output_voltage / np.sqrt(2)
        current = output_voltage / (current_setting_resistor + wire_resistance_roundtrip)

        data = pandas.DataFrame(index=range(len(demod_sample['x'])),
                                columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B", "PPMS_T"])

        data["Timestamp"] = current_timestamp
        data["Elapsed time"] = timedelta.total_seconds()
        data["R"] = demod_sample['x'] / (current * preamp_gain)
        data["iR"] = demod_sample['y'] / (current * preamp_gain)
        data["P"] = demod_sample['x'] * current / preamp_gain

        data["PPMS_B"] = field
        data["PPMS_T"] = temp

        queue.put((15, data))
        time.sleep(0.1)


def read_multi_channel(channels, queue, _time_at_beginning_of_experiment, measurements_per_scan, configure_input=False,
                        ip_address="192.168.0.12", thread_stop_indicator=Value('b', False),
                        debug=False):
    """"""
    mpv_client = mpv.Client()

    try:
        mpv_client.open()
    except:
        print("Could not connect to PPMS")

    if not debug:
        ip_address = LakeShoreIPAddress
        if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["usb"]:
            instrument_372 = Model372(57600)
        if ActiveLakeShoreCommunicationMethod == LakeShoreCommunicationMethod["ip"]:
            instrument_372 = Model372(baud_rate=None, ip_address=ip_address)
        if configure_input:
            settings_thermometer = Model372InputSetupSettings(Model372.SensorExcitationMode.CURRENT,
                                                              Model372.MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                              Model372.AutoRangeMode.ROX102B, False,
                                                              Model372.InputSensorUnits.OHMS,
                                                              Model372.MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)
            for channel in channels:
                instrument_372.configure_input(channel, settings_thermometer)

        if len(channels) == 1:
            channel = channels[0]
            instrument_372.set_scanner_status(input_channel=channel, status=False)
            input_parameters = instrument_372.get_filter(channel)
            #wait for the filter to settle

            time.sleep(4)
            while True:
                sample_data = acquire_samples_ppms(instrument_372, measurements_per_scan, channel,
                                              _time_at_beginning_of_experiment, _mpv_client=mpv_client)
                queue.put((channel, sample_data))
                if thread_stop_indicator.value:
                    mpv_client.close_client()
                    mpv_client.close_server()
                    break
        else:
            while True:
                for channel in channels:
                    instrument_372.set_scanner_status(input_channel=channel, status=False)
                    time.sleep(4)
                    time.sleep(10)
                    sample_data = acquire_samples_ppms(instrument_372, measurements_per_scan, channel,
                                                  _time_at_beginning_of_experiment, _mpv_client=mpv_client)
                    queue.put((channel, sample_data))
                if thread_stop_indicator.value:
                    mpv_client.close_client()
                    mpv_client.close_server()
                    break
    else:
        while True:
            time.sleep(0.1)
            for channel in channels:
                sample_data = acquire_samples_debug_ppms(False, measurements_per_scan, channel, _time_at_beginning_of_experiment, _mpv_client = mpv_client)
                #print(queue.qsize())
                queue.put((channel, sample_data))

            if thread_stop_indicator.value:
                mpv_client.close_client()
                mpv_client.close_server()
                break

def start_data_visualizer(channels, queue, _time_at_beginning_of_experiment, measurements_per_scan, filepath, temperature_calibrations, delimiter=',',
                          save_raw_data=True,
                          thread_stop_indicator=Value('b', False)):
    visualizer = Process(target=visualize_n_channels, args=(channels, queue, _time_at_beginning_of_experiment,
                                                                measurements_per_scan, filepath, temperature_calibrations, delimiter, thread_stop_indicator))
    visualizer.daemon = True
    visualizer.start()  # Launch reader_p() as another proc
    return visualizer

def nullFunction(x):
    return np.nan

def main(path):
    """Use these options to configure the measurement"""
    _filepath = path
    _save_raw_data = True
    with open(f"{_filepath}/settings.json") as settingsFile:
        settingsJSON = json.load(settingsFile)
        print(settingsJSON)
    _channels = settingsJSON["Channels"]
    _debug=settingsJSON["debug"]
    _measurements_per_scan = settingsJSON["samplerate"]

    _temperature_calibrations = []
    for calString in settingsJSON["calibration"]:
        if calString == "None":
            _temperature_calibrations.append(nullFunction)
        else:
            _temperature_calibrations.append(getattr(TemperatureCalibration, calString))

    time_at_beginning_of_experiment = datetime.now()
    # used to transport data from the reader process to the visualizer
    ls_data_queue = Queue()
    # used to terminate the reader if visualizer is closed
    shared_stop_indicator = Value('b', False)

    _lakeshore_scanner_channels = []
    for channel in _channels:
        _lakeshore_scanner_channels.append(channel)

    if 13 in _channels:
        _lakeshore_scanner_channels.remove(13)
        ls_chan_a_process = Process(target=read_lakeshore_channel_a, args=(ls_data_queue,
                                                                           time_at_beginning_of_experiment,
                                                                           _measurements_per_scan,
                                                                           shared_stop_indicator, _debug))
        ls_chan_a_process.daemon = True
        ls_chan_a_process.start()

    if 14 in _channels:
        _lakeshore_scanner_channels.remove(14)
        sr830_process = Process(target=read_sr830, args=(ls_data_queue, time_at_beginning_of_experiment,
                                                         _measurements_per_scan, shared_stop_indicator, _debug))
        sr830_process.daemon = True
        sr830_process.start()

    if 15 in _channels:
        _lakeshore_scanner_channels.remove(15)
        mfli_process = Process(target=read_zurich, args=(ls_data_queue, time_at_beginning_of_experiment,
                                                         _measurements_per_scan, shared_stop_indicator, _debug))
        mfli_process.daemon = True
        mfli_process.start()

    visualizer_process = start_data_visualizer(_channels, ls_data_queue, time_at_beginning_of_experiment,
                                               _measurements_per_scan, _filepath, _temperature_calibrations,
                                               save_raw_data=_save_raw_data,
                                               thread_stop_indicator=shared_stop_indicator)

    if len(_lakeshore_scanner_channels) > 0:
        read_multi_channel(_lakeshore_scanner_channels, ls_data_queue, time_at_beginning_of_experiment,
                           _measurements_per_scan, debug=_debug, thread_stop_indicator=shared_stop_indicator)
    else:
        while not shared_stop_indicator:
            time.sleep(0.5)

    visualizer_process.join()
    ls_chan_a_process.join()
    sr830_process.join()


def list_local_zi_devices():
    """Return a dict of all locally discovered Zurich Instruments devices."""
    discovery = ziDiscovery()
    dev_ids = discovery.findAll()

    devices = {}
    for dev_id in dev_ids:
        props = discovery.get(dev_id)
        devices[dev_id] = props
    return devices


def select_device_dialog(devices):
    """
    Show a popup window to select one device.

    `devices` is a dict: {dev_id: props_dict}
    Returns (dev_id, server_host) or (None, None).
    """
    selected = {"dev_id": None, "server_host": None}

    root = tk.Tk()
    root.title("Select Zurich Instruments Device")
    root.resizable(False, False)

    tk.Label(root, text="Select a device:").pack(padx=10, pady=(10, 5))

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=5, fill="both", expand=True)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(frame, height=8, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)

    scrollbar.config(command=listbox.yview)

    # Map listbox index -> (dev_id, server_host)
    index_to_dev = []
    for dev_id, props in devices.items():
        server_addr = props.get("serveraddress", "unknown")
        display_text = f"{dev_id}  [{server_addr}]"
        listbox.insert(tk.END, display_text)
        index_to_dev.append((dev_id, server_addr))

    def on_ok(event=None):
        sel = listbox.curselection()
        if sel:
            idx = sel[0]
            dev_id, server_host = index_to_dev[idx]
            selected["dev_id"] = dev_id
            selected["server_host"] = server_host
        root.destroy()

    def on_cancel():
        selected["dev_id"] = None
        selected["server_host"] = None
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(padx=10, pady=(5, 10))

    ok_btn = ttk.Button(btn_frame, text="OK", command=on_ok)
    ok_btn.pack(side="left", padx=5)

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=on_cancel)
    cancel_btn.pack(side="left", padx=5)

    listbox.bind("<Double-Button-1>", on_ok)
    root.bind("<Return>", on_ok)
    root.protocol("WM_DELETE_WINDOW", on_cancel)

    root.mainloop()
    return selected["dev_id"], selected["server_host"]


def ask_for_resistor(title="Input required",
                   prompt="Please enter a number:",
                   min_value=None,
                   max_value=None):
    """
    Show a dialog asking the user for an integer.

    Returns the integer value, or None if the user cancels.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    number = simpledialog.askinteger(
        title,
        prompt,
        parent=root,
        minvalue=min_value,
        maxvalue=max_value,
    )

    root.destroy()
    return number