import pandas
from lakeshore import Model372
from lakeshore import Model372SensorExcitationMode, Model372MeasurementInputCurrentRange, Model372AutoRangeMode, \
    Model372InputSensorUnits, Model372MeasurementInputResistance, Model372InputSetupSettings
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from TemperatureCalibration import cal_ser6, cal_ser8
from LS_Datalogger2_v2 import acquire_samples
from TemperatureCalibration import cal_ser6, cal_ser8, cal_mk1


def record_resistance_single_channel(channel=1, configure_input=False, ip_address="192.168.0.12",
                                     measurements_per_scan=70, delimeter=',', filename='resistance_single_channel',
                                     save_raw_data=True):
    time_at_beginning_of_experiment = datetime.now()
    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

    lgr = logging.getLogger('resistance1')
    lgr.setLevel(logging.DEBUG)
    fh = logging.FileHandler('./' + str(time_at_beginning_of_experiment) + 'ADR_Data_' + filename + '.csv')
    fh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(message)s')
    fh.setFormatter(frmt)
    lgr.addHandler(fh)
    lgr.info("Measurement of thermometer resistivity with Lake Shore 372 AC Bridge")
    lgr.info("Data is aggregated with " + str(measurements_per_scan) + " samples for every line of this log.")
    lgr.info("This file does not contain raw data!")
    lgr.info("Data field names and types:")
    lgr.info(
        "Timestamp" + delimeter +
        "Elapsed_time" + delimeter +
        "Elapsed_time_error" + delimeter +
        "Thermometer_temperature" + delimeter +
        "Thermometer_temperature_error" + delimeter +
        "Resistance_thermometer" + delimeter +
        "Resistance_thermometer_error" + delimeter +
        "Quadrature_thermometer" + delimeter +
        "Quadrature_thermometer_error" + delimeter +
        "Power_thermometer" + delimeter +
        "Power_thermometer_error"
    )
    lgr.info(
        "[YYYY-MM-DD hh:mm:ss,###]" + delimeter +
        "second" + delimeter +
        "second" + delimeter +
        "Kelvin" + delimeter +
        "Kelvin" + delimeter +
        "Ohm" + delimeter +
        "Ohm" + delimeter +
        "iOhm" + delimeter +
        "iOhm" + delimeter +
        "Watt" + delimeter +
        "Watt"
    )

    time_plot = []
    time_error_plot = []
    temperature_plot = []
    temperature_error_plot = []
    resistance_plot = []
    resistance_error_plot = []

    if configure_input:
        settings_thermometer = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                          Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                          Model372AutoRangeMode.CURRENT, False,
                                                          Model372InputSensorUnits.OHMS,
                                                          Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

        instrument_372.configure_input(channel, settings_thermometer)

    plt.ion()
    fig, axs = plt.subplots(2, 1)

    instrument_372.set_scanner_status(input_channel=channel, status=False)
    time.sleep(4)
    while True:
        sample_data = acquire_samples(instrument_372, measurements_per_scan, channel, time_at_beginning_of_experiment)

        resistance_thermometer = sample_data["R"].mean()
        quadrature_thermometer = sample_data["iR"].mean()
        power_thermometer = sample_data["P"].mean()
        time_thermometer = sample_data["Elapsed time"].mean()
        resistance_thermometer_err = sample_data["R"].std()
        quadrature_thermometer_err = sample_data["iR"].std()
        power_thermometer_err = sample_data["P"].std()
        time_thermometer_err = sample_data["Elapsed time"].std()

        # calculate the temperature during the resistivity measurement
        temperature = cal_mk1(resistance_thermometer)
        temperature_plot.append(temperature)

        # calculate temperature error
        temperature_upper = cal_mk1(resistance_thermometer - resistance_thermometer_err)
        temperature_lower = cal_mk1(resistance_thermometer + resistance_thermometer_err)
        temperature_error = temperature_lower / 2 + temperature_upper / 2 - temperature
        temperature_error_plot.append(temperature_error)

        time_plot.append(time_thermometer)
        time_error_plot.append(time_thermometer_err)  # this might be too large, about 2s
        resistance_plot.append(resistance_thermometer)
        resistance_error_plot.append(resistance_thermometer_err)

        lgr.info(
            str(datetime.now()) + delimeter +
            str(time_thermometer) + delimeter +
            str(time_thermometer_err) + delimeter +
            str(temperature) + delimeter +
            str(temperature_error) + delimeter +
            str(resistance_thermometer) + delimeter +
            str(resistance_thermometer_err) + delimeter +
            str(quadrature_thermometer) + delimeter +
            str(quadrature_thermometer_err) + delimeter +
            str(power_thermometer) + delimeter +
            str(power_thermometer_err))

        if save_raw_data:
            # no longer necessary, as data is now saved incrementally (with mode='a')
            # data_thermometer = pandas.concat([data_thermometer, results])
            # data_sample = pandas.concat([data_sample, results])
            #
            # save the raw data from the instrument - this gets large fast!
            sample_data('./' + str(time_at_beginning_of_experiment) + 'RAW_resistance_data' + filename + '.csv',
                        mode='a', index=False, header=False)

        axs[0].clear()
        axs[1].clear()

        # draw the R(t) plot
        axs[0].errorbar(time_plot, resistance_plot, yerr=resistance_error_plot, label='sample', fmt='o')
        axs[0].set_title('R = ' + str(int(resistance_thermometer)) + '±' + str(
            int(resistance_thermometer_err)) + ' Ω  T_cal = ' + str(int(1000 * temperature)) + ' ± ' + str(
            int(1000 * temperature_error)) + ' mK')

        axs[0].set_ylabel('Resistance [Ohm]')
        # axs[0].set_xlabel('Elapsed time [s]')

        # draw the T(t) plot (for new thermometers this will be wildly inaccurate)
        axs[1].errorbar(time_plot, temperature_plot, yerr=temperature_error_plot, label='calibrated', fmt='o')
        axs[1].set_ylabel('Calibrated temperature [K]')
        axs[1].set_yscale('log')
        axs[1].set_ylim(0.01, 300)
        axs[1].set_xlabel('Time [s]')

        # draw the new information for the user
        fig.canvas.draw()
        fig.canvas.flush_events()


record_resistance_single_channel()
