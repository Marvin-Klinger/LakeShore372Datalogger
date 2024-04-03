from multiprocessing import Process, Queue, Value

import numpy as np

from LS_Datalogger2_v2 import acquire_samples
from lakeshore import Model372
from lakeshore import Model372SensorExcitationMode, Model372MeasurementInputCurrentRange, Model372AutoRangeMode, \
    Model372InputSensorUnits, Model372MeasurementInputResistance, Model372InputSetupSettings
import time
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from TemperatureCalibration import cal_mk4, cal_mk4 as cal_mk8


def on_close(thread_stop_indicator):
    thread_stop_indicator.value = True


def visualize_two_thermometers(queue_a, queue_b, time_at_beginning_of_experiment, measurements_per_scan=70,
                               delimiter=',',
                               filename='resistance_single_channel', save_raw_data=True,
                               thread_stop_indicator=Value('b', False)):
    lgr1 = logging.getLogger('dual_thermometers')
    lgr1.setLevel(logging.DEBUG)
    fh = logging.FileHandler('./' + str(time_at_beginning_of_experiment) + 'ADR_Data_Therm1_' + filename + '.csv')
    fh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(message)s')
    fh.setFormatter(frmt)
    lgr1.addHandler(fh)
    lgr1.info("Measurement of dual thermometer resistivity (1) MK4 with Lake Shore 372 AC Bridge")
    lgr1.info("Data is aggregated with " + str(measurements_per_scan) + " samples for every line of this log.")
    lgr1.info("This file does not contain raw data!")
    lgr1.info("Data field names and types:")
    lgr1.info(
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
    lgr1.info(
        "[YYYY-MM-DD hh:mm:ss,###]" + delimiter +
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

    lgr2 = logging.getLogger('dual_thermometers_2')
    lgr2.setLevel(logging.DEBUG)
    fh = logging.FileHandler('./' + str(time_at_beginning_of_experiment) + 'ADR_Data_Therm2_' + filename + '.csv')
    fh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(message)s')
    fh.setFormatter(frmt)
    lgr2.addHandler(fh)
    lgr2.info("Measurement of dual thermometer resistivity (2) MK4 with Lake Shore 372 AC Bridge")
    lgr2.info("Data is aggregated with " + str(measurements_per_scan) + " samples for every line of this log.")
    lgr2.info("This file does not contain raw data!")
    lgr2.info("Data field names and types:")
    lgr2.info(
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
    lgr2.info(
        "[YYYY-MM-DD hh:mm:ss,###]" + delimiter +
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

    time_plot = []
    time_error_plot = []
    temperature_plot = []
    temperature_error_plot = []
    resistance_plot = []
    resistance_error_plot = []

    time_plot2 = []
    time_error_plot2 = []
    temperature_plot2 = []
    temperature_error_plot2 = []
    resistance_plot2 = []
    resistance_error_plot2 = []

    plt.ion()
    fig, axs = plt.subplots(2, 1)
    fig.canvas.mpl_connect('close_event', lambda event: on_close(thread_stop_indicator))

    while True:
        if queue_a.qsize() == 0 or queue_b.qsize() == 0:
            # wait for both queues to have data
            # until then, redraw the plots
            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(0.05)
            continue

        # only reached, if both queues are longer than 0
        sample_data = queue_a.get()  # Read from the queue
        resistance_thermometer = sample_data["R"].mean()
        quadrature_thermometer = sample_data["iR"].mean()
        power_thermometer = sample_data["P"].mean()
        time_thermometer = sample_data["Elapsed time"].mean()
        resistance_thermometer_err = sample_data["R"].std()
        quadrature_thermometer_err = sample_data["iR"].std()
        power_thermometer_err = sample_data["P"].std()
        time_thermometer_err = sample_data["Elapsed time"].std()

        # calculate the temperature during the resistivity measurement
        temperature = cal_mk8(resistance_thermometer)
        temperature_plot.append(temperature)

        # calculate temperature error
        temperature_upper = cal_mk8(resistance_thermometer - resistance_thermometer_err)
        temperature_lower = cal_mk8(resistance_thermometer + resistance_thermometer_err)
        temperature_error = np.absolute(temperature_upper - temperature_lower) / 2
        temperature_error_plot.append(temperature_error)

        time_plot.append(time_thermometer)
        time_error_plot.append(time_thermometer_err)  # this might be too large, about 2s
        resistance_plot.append(resistance_thermometer)
        resistance_error_plot.append(resistance_thermometer_err)

        lgr1.info(
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

        if save_raw_data:
            sample_data.to_csv(
                './' + str(time_at_beginning_of_experiment) + 'RAW_resistance_data_A_' + filename + '.csv',
                mode='a', index=False, header=False)

        sample_data_b = queue_b.get()  # Read from the queue
        resistance_thermometer2 = sample_data_b["R"].mean()
        quadrature_thermometer2 = sample_data_b["iR"].mean()
        power_thermometer2 = sample_data_b["P"].mean()
        time_thermometer2 = sample_data_b["Elapsed time"].mean()
        resistance_thermometer_err2 = sample_data_b["R"].std()
        quadrature_thermometer_err2 = sample_data_b["iR"].std()
        power_thermometer_err2 = sample_data_b["P"].std()
        time_thermometer_err2 = sample_data_b["Elapsed time"].std()

        # calculate the temperature during the resistivity measurement
        temperature2 = cal_mk4(resistance_thermometer2)
        temperature_plot2.append(temperature2)

        # calculate temperature error
        temperature_upper2 = cal_mk4(resistance_thermometer2 - resistance_thermometer_err2)
        temperature_lower2 = cal_mk4(resistance_thermometer2 + resistance_thermometer_err2)
        temperature_error2 = np.absolute(temperature_upper2 - temperature_lower2) / 2
        temperature_error_plot2.append(temperature_error2)

        time_plot2.append(time_thermometer2)
        time_error_plot2.append(time_thermometer_err2)  # this might be too large, about 2s
        resistance_plot2.append(resistance_thermometer2)
        resistance_error_plot2.append(resistance_thermometer_err2)

        lgr2.info(
            str(datetime.now()) + delimiter +
            str(time_thermometer2) + delimiter +
            str(time_thermometer_err2) + delimiter +
            str(temperature2) + delimiter +
            str(temperature_error2) + delimiter +
            str(resistance_thermometer2) + delimiter +
            str(resistance_thermometer_err2) + delimiter +
            str(quadrature_thermometer2) + delimiter +
            str(quadrature_thermometer_err2) + delimiter +
            str(power_thermometer2) + delimiter +
            str(power_thermometer_err2))

        if save_raw_data:
            sample_data_b.to_csv(
                './' + str(time_at_beginning_of_experiment) + 'RAW_resistance_data_B_' + filename + '.csv', mode='a',
                index=False, header=False)

        if queue_a.qsize() < 2 and queue_b.qsize() < 2:
            axs[0].clear()
            axs[1].clear()
            # draw the R(t) plot
            axs[0].errorbar(time_plot, resistance_plot, yerr=resistance_error_plot, label='Chan1', fmt='o')
            axs[0].errorbar(time_plot2, resistance_plot2, yerr=resistance_error_plot2, label='Chan2', fmt='o')
            axs[0].set_title('R_1 = ' + str(resistance_thermometer) + '±' + str(
                round(resistance_thermometer_err, 1)) + ' Ω  T_cal_1 = ' + str(round(1000 * temperature, 1)) + ' ± ' + str(
                round(1000 * temperature_error, 1)) + ' mK' + '    R_2 = ' + str(
                round(resistance_thermometer2, 1)) + '±' + str(
                round(resistance_thermometer_err2, 1)) + ' Ω  T_cal_2 = ' + str(round(1000 * temperature2, 1)) + ' ± ' + str(
                round(1000 * temperature_error2, 1)) + ' mK')
            axs[0].set_ylabel('Resistance [Ohm]')
            # axs[0].set_xlabel('Elapsed time [s]')
            # draw the T(t) plot (for new thermometers this will be wildly inaccurate)
            axs[1].errorbar(time_plot, temperature_plot, yerr=temperature_error_plot, label='Chan1', fmt='o')
            axs[1].errorbar(time_plot2, temperature_plot2, yerr=temperature_error_plot2, label='Chan2', fmt='o')
            axs[1].set_ylabel('Calibrated temperature [K]')
            axs[1].set_yscale('log')
            # axs[1].set_ylim(0.02, 3)
            axs[1].set_xlabel('Time [s]')
            # draw the new information for the user
            fig.canvas.draw()
            fig.canvas.flush_events()


def read_dual_channel(queue_a, queue_b, _time_at_beginning_of_experiment, channel_a=1, channel_b=2,
                      configure_input=False, ip_address="192.168.0.12", measurements_per_scan=70,
                      thread_stop_indicator=Value('b', False)):
    """"""
    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

    if configure_input:
        settings_thermometer = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                          Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                          Model372AutoRangeMode.CURRENT, False,
                                                          Model372InputSensorUnits.OHMS,
                                                          Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

        instrument_372.configure_input(channel_a, settings_thermometer)
        instrument_372.configure_input(channel_b, settings_thermometer)

    instrument_372.set_scanner_status(input_channel=channel_a, status=False)
    time.sleep(4)

    while True:
        if thread_stop_indicator.value:
            break
        sample_data_a = acquire_samples(instrument_372, measurements_per_scan, channel_a,
                                        _time_at_beginning_of_experiment)
        queue_a.put(sample_data_a)
        instrument_372.set_scanner_status(input_channel=channel_b, status=False)
        time.sleep(4)
        sample_data_b = acquire_samples(instrument_372, measurements_per_scan, channel_b,
                                        _time_at_beginning_of_experiment)
        queue_b.put(sample_data_b)
        instrument_372.set_scanner_status(input_channel=channel_a, status=False)
        time.sleep(4)


def start_data_visualizer(queue_a, queue_b, time_at_beginning_of_experiment, measurements_per_scan=70, delimeter=',',
                          filename='resistance_dual_channel', save_raw_data=True,
                          thread_stop_indicator=Value('b', False)):
    """Start the reader processes and return all in a list to the caller"""
    visualizer = Process(target=visualize_two_thermometers, args=(queue_a, queue_b, time_at_beginning_of_experiment,
                                                                  measurements_per_scan, delimeter, filename,
                                                                  save_raw_data, thread_stop_indicator))
    visualizer.daemon = True
    visualizer.start()
    return visualizer


if __name__ == "__main__":
    _measurements_per_scan = 100
    _filename = "Calibration_mx_01_camcool_1_uncal_r2"
    _save_raw_data = True

    shared_stop_indicator = Value('b', False)
    time_at_beginning_of_experiment = datetime.now()
    ls_data_queue_a = Queue()  # writer() writes to ls_data_queue from _this_ process
    ls_data_queue_b = Queue()  # writer() writes to ls_data_queue from _this_ process
    visualizer_process = start_data_visualizer(ls_data_queue_a, ls_data_queue_b, time_at_beginning_of_experiment,
                                               filename=_filename, save_raw_data=_save_raw_data,
                                               measurements_per_scan=_measurements_per_scan,
                                               thread_stop_indicator=shared_stop_indicator)
    read_dual_channel(ls_data_queue_a, ls_data_queue_b, time_at_beginning_of_experiment, channel_a=1, channel_b=2,
                      thread_stop_indicator=shared_stop_indicator, measurements_per_scan=_measurements_per_scan)
    visualizer_process.join()
    print("main end")
