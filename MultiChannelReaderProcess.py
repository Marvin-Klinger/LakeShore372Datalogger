from multiprocessing import Process, Queue, Value
from LS_Datalogger2_v2 import acquire_samples_ppms
from emulator import acquire_samples_debug_ppms
from lakeshore import Model372, Model372InputSetupSettings
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import TemperatureCalibration
import MultiPyVu as mpv
from collections import deque
import numpy as np
import time
import os
from multiprocessing import Value

def on_close(thread_stop_indicator):
    thread_stop_indicator.value = True

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

    colors = ["#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff"]

    colors = ["#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff"]
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

    axs[0].legend(loc='lower right')

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
            plt.savefig(f"{filepath}/overview.png")
            plt.savefig(f"{filepath}/overview.jpg")
            plt.savefig(f"{filepath}/overview.pdf")
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

        time.sleep(0.05)

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
        instrument_372 = Model372(baud_rate=None, ip_address=ip_address)
        if configure_input:
            settings_thermometer = Model372InputSetupSettings(Model372.SensorExcitationMode.CURRENT,
                                                              Model372.MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                              Model372.AutoRangeMode.CURRENT, False,
                                                              Model372.InputSensorUnits.OHMS,
                                                              Model372.MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)
            for channel in channels:
                instrument_372.configure_input(channel, settings_thermometer)

        if len(channels) == 1:
            channel = channels[0]
            instrument_372.set_scanner_status(input_channel=channel, status=False)
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
    _lakeshore_channels = settingsJSON["Channels"]
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
    visualizer_process = start_data_visualizer(_lakeshore_channels, ls_data_queue, time_at_beginning_of_experiment, _measurements_per_scan, _filepath, _temperature_calibrations,
                                               save_raw_data=_save_raw_data,
                                               thread_stop_indicator=shared_stop_indicator)
    read_multi_channel(_lakeshore_channels, ls_data_queue, time_at_beginning_of_experiment, _measurements_per_scan, debug=_debug,
                        thread_stop_indicator=shared_stop_indicator)
    visualizer_process.join()

