from multiprocessing import Process, Queue, Value
import numpy as np
from LS_Datalogger2_v2 import acquire_samples
from emulator import acquire_samples_debug
from lakeshore import Model372, Model372InputSetupSettings
import time
import logging
from os import makedirs
import os
import sys
import json
from datetime import datetime
import matplotlib.pyplot as plt
import TemperatureCalibration

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
        "Power_thermometer_error"
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
        "Watt"
    )
    return lgr


def visualize_n_channels(channels, queue, _time_at_beginning_of_experiment, measurements_per_scan, filepath, temperature_calibrations, delimiter=',', thread_stop_indicator=Value('b', False)):
    colors = ["#2e2e2eff", "#d53e3eff", "#b61fd6ff", "#3674b5ff"]
    loggers = [[] for _ in range(17)]
    for channel in channels:
        _lgr = setup_new_logger(channel, _time_at_beginning_of_experiment, measurements_per_scan, filepath)
        loggers[channel] = _lgr

#TODO: this creates many potentially empty lists that will never be filled
    plt.ion()
    fig, axs = plt.subplots(2, 1, constrained_layout=True, sharex=True)
    fig.canvas.mpl_connect('close_event', lambda event: on_close(thread_stop_indicator))

    axs[0].set_ylabel('Resistance [Ohm]')
    axs[0].set_title("Waiting for Data")
    axs[1].set_ylabel('Calibrated temperature [K]')
    axs[1].set_yscale('log')
    #axs[1].set_ylim(0.01, 10)
    axs[1].set_xlabel('Time [s]')

    axs[0].set_title(os.path.basename(os.getcwd()))
   
    scatter=[]
    for i in channels:
        scatter.append(axs[0].scatter([], [], color=colors[i-1], linestyle='', marker='o', label=f"Ch {i}"))
    axs[0].legend()
    for i in scatter:
        i.remove()

    while True:
        if thread_stop_indicator.value:
            break

        # redraw the plot to keep the UI going if there is no new data
        if queue.qsize() == 0:
            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(0.05)
            continue

        # new data has arrived, start working with it
        data_package = queue.get()  # Read from the queue
        channel_index = data_package[0]
        sample_data = data_package[1]

        # get mean values and standard dev of all quantities
        resistance_thermometer = sample_data["R"].mean()
        quadrature_thermometer = sample_data["iR"].mean()
        power_thermometer = sample_data["P"].mean()
        time_thermometer = sample_data["Elapsed time"].mean()
        resistance_thermometer_err = sample_data["R"].std()
        quadrature_thermometer_err = sample_data["iR"].std()
        power_thermometer_err = sample_data["P"].std()
        time_thermometer_err = sample_data["Elapsed time"].std()

        # calculate the temperature during the resistivity measurement
       
        temperature = temperature_calibrations[channel_index - 1](resistance_thermometer)
        temperature_upper = temperature_calibrations[channel_index - 1](resistance_thermometer - resistance_thermometer_err)
        temperature_lower = temperature_calibrations[channel_index - 1](resistance_thermometer + resistance_thermometer_err)
        
        # temperature_error = temperature_lower / 2 + temperature_upper / 2 - temperature
        temperature_error = np.absolute((temperature_upper - temperature_lower) / 2)

        loggers[channel_index].info(
            str(datetime.now()) + delimiter +
            str(time_thermometer) + delimiter +
            str(time_thermometer_err) + delimiter +
            str(temperature) + delimiter +
            str(temperature_error) + delimiter +
            str(resistance_thermometer) + delimiter +
            str(resistance_thermometer_err) + delimiter +
            str(quadrature_thermometer) + delimiter +
            str(quadrature_thermometer_err) + delimiter +
            str(power_thermometer) + delimiter +
            str(power_thermometer_err))
        
        axs[0].scatter(time_thermometer, resistance_thermometer, color=colors[channel_index-1], linestyle='', marker='.')
        axs[1].scatter(time_thermometer, temperature, color=colors[channel_index-1], linestyle='', marker='.')

        if queue.qsize() > 5:
            """
            Last resort. More than 5 recent measurements were not processed due to long redraw time.
            Clear interface
            """
            axs[0].clear()
            axs[1].clear()
        """
        Only refresh the plot if no more than one measurement remains to be processed. This stops the queue from
        getting to long. 
        """
        #TODO: for all time series
        if fig.canvas.toolbar.mode == '':
            if queue.qsize() < 2:
                fig.canvas.draw()
                fig.canvas.flush_events()


def read_multi_channel(channels, queue, _time_at_beginning_of_experiment, measurements_per_scan, configure_input=False,
                        ip_address="192.168.0.12", thread_stop_indicator=Value('b', False),
                        debug=False):
    """"""
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

        while True:
            for channel in channels:
                instrument_372.set_scanner_status(input_channel=channel, status=False)
                time.sleep(4)
                sample_data = acquire_samples(instrument_372, measurements_per_scan, channel,
                                              _time_at_beginning_of_experiment)
                queue.put((channel, sample_data))
            if thread_stop_indicator.value:
                break
    else:
        while True:
            time.sleep(2)
            for channel in channels:
                sample_data = acquire_samples_debug(False, measurements_per_scan, channel, _time_at_beginning_of_experiment)
                print(queue.qsize())
                queue.put((channel, sample_data))
            if thread_stop_indicator.value:
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

