import pandas
from lakeshore import Model372
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
import MultiPyVu as mpv
#from TemperatureCalibration import cal_mk8 as cal_mk4


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


def acquire_samples_ppms(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None, _mpv_client = mpv.Client()):

    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    # data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

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

    data = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                            readings['quadrature'], readings['power'], field, temp]],
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B","PPMS_T"])

    for _ in range(number_of_samples - 1):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = model372.get_all_input_readings(channel_number)
        field, field_status = _mpv_client.get_field()
        temp, temp_status = _mpv_client.get_temperature()

        series_for_concat = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                                               readings['quadrature'], readings['power'], field, temp]],
                                             columns=["Timestamp", "Elapsed time", "R", "iR", "P", "PPMS_B","PPMS_T"])

        data = pandas.concat([data, series_for_concat], ignore_index=True)
    return data

#def model372_thermometer_and_sample(thermometer_channel, sample_channel, filename='', save_raw_data=False,
#                                    configure_inputs=False, delimiter=',', ip_address="192.168.0.12",
#                                    measurements_per_scan=200):
#    time_at_beginning_of_experiment = datetime.now()
#
#    # configure logging for regular data output (preprocessed, small files)
#    lgr = logging.getLogger('resistance1')
#    lgr.setLevel(logging.DEBUG)
#    fh = logging.FileHandler('./' + str(time_at_beginning_of_experiment) + 'ADR_Data_' + filename + '.csv')
#    fh.setLevel(logging.DEBUG)
#    frmt = logging.Formatter('%(message)s')
#    fh.setFormatter(frmt)
#    lgr.addHandler(fh)
#    lgr.info("Measurement of sample resistivity and thermometer resistivity with Lake Shore 372 AC Bridge")
#    lgr.info(
#        "Only one channel can be measured at a time. Two thermometer readings are combined to find the approx. " +
#        "Readings at the time of sample measurement.")
#    lgr.info("Data field names and types:")
#    lgr.info(
#        "Timestamp" + delimiter +
#        "Elapsed_time" + delimiter +
#        "Elapsed_time_error" + delimiter +
#        "Thermometer_temperature" + delimiter +
#        "Thermometer_temperature_error" + delimiter +
#        "Resistance_thermometer" + delimiter +
#        "Resistance_thermometer_error" + delimiter +
#        "Quadrature_thermometer" + delimiter +
#        "Quadrature_thermometer_error" + delimiter +
#        "Power_thermometer" + delimiter +
#        "Power_thermometer_error" + delimiter +
#        "Resistance_sample" + delimiter +
#        "Resistance_sample_error" + delimiter +
#        "Quadrature_sample" + delimiter +
#        "Quadrature_sample_error" + delimiter +
#        "Power_sample" + delimiter +
#        "Power_sample_error"
#    )
#    lgr.info(
#        "[YYYY-MM-DD hh:mm:ss,###]" + delimiter +
#        "second" + delimiter +
#        "second" + delimiter +
#        "Kelvin" + delimiter +
#        "Kelvin" + delimiter +
#        "Ohm" + delimiter +
#        "Ohm" + delimiter +
#        "iOhm" + delimiter +
#        "iOhm" + delimiter +
#        "Watt" + delimiter +
#        "Watt" + delimiter +
#        "Ohm" + delimiter +
#        "Ohm" + delimiter +
#        "iOhm" + delimiter +
#        "iOhm" + delimiter +
#        "Watt" + delimiter +
#        "Watt"
#    )
#
#    # lists for plots, this data will not be saved to disk
#    time_plot = []
#    time_error_plot = []
#    temperature_plot = []
#    temperature_error_plot = []
#    resistance_plot = []
#    resistance_error_plot = []
#
#    plt.ion()
#    fig, axs = plt.subplots(2, 1, sharex=True)
#    # User interface:
#    # axs[0]: T(t) + ΔT(t)
#    # axs[1]: R(T) + ΔR(T)
#
#    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)
#
#    if configure_inputs:
#        settings_thermometer = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
#                                                          Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
#                                                          Model372AutoRangeMode.CURRENT, False,
#                                                          Model372InputSensorUnits.OHMS,
#                                                          Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)
#
#        settings_sample = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
#                                                     Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
#                                                     Model372AutoRangeMode.CURRENT, False,
#                                                     Model372InputSensorUnits.OHMS,
#                                                     Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)
#
#        instrument_372.configure_input(thermometer_channel, settings_thermometer)
#        instrument_372.configure_input(sample_channel, settings_sample)
#
#    instrument_372.set_scanner_status(input_channel=thermometer_channel, status=False)
#    time.sleep(4)
#    last_thermometer_results = acquire_samples(instrument_372, measurements_per_scan, thermometer_channel,
#                                               time_at_beginning_of_experiment)
#
#    while True:
#        # measure the sample
#        instrument_372.set_scanner_status(input_channel=sample_channel, status=False)
#        time.sleep(4)
#        sample_data = acquire_samples(instrument_372, measurements_per_scan, sample_channel,
#                                      time_at_beginning_of_experiment)
#
#        # measure the thermometer
#        instrument_372.set_scanner_status(input_channel=thermometer_channel, status=False)
#        time.sleep(4)
#        thermometer_results = acquire_samples(instrument_372, measurements_per_scan, thermometer_channel,
#                                              time_at_beginning_of_experiment)
#
#        two_last_thermometer_data = pandas.concat([last_thermometer_results, thermometer_results])
#
#        # process the thermometer
#        resistance_thermometer = two_last_thermometer_data["R"].mean()
#        quadrature_thermometer = two_last_thermometer_data["iR"].mean()
#        power_thermometer = two_last_thermometer_data["P"].mean()
#        time_thermometer = two_last_thermometer_data["Elapsed time"].mean()
#        resistance_thermometer_err = two_last_thermometer_data["R"].std()
#        quadrature_thermometer_err = two_last_thermometer_data["iR"].std()
#        power_thermometer_err = two_last_thermometer_data["P"].std()
#        time_thermometer_err = two_last_thermometer_data["Elapsed time"].std()
#
#        # calculate the temperature during the resistivity measurement
#        temperature = cal_mk4(resistance_thermometer)
#        temperature_plot.append(temperature)
#
#        # calculate temperature error
#        temperature_upper = cal_mk4(resistance_thermometer - resistance_thermometer_err)
#        temperature_lower = cal_mk4(resistance_thermometer + resistance_thermometer_err)
#        temperature_error = temperature_lower/2 + temperature_upper/2 - temperature
#        temperature_error_plot.append(temperature_error)
#
#        # process the sample data
#        resistance_sample = sample_data["R"].mean()
#        quadrature_sample = sample_data["iR"].mean()
#        power_sample = sample_data["P"].mean()
#        time_sample = sample_data["Elapsed time"].mean()
#        resistance_sample_err = sample_data["R"].std()
#        quadrature_sample_err = sample_data["iR"].std()
#        power_sample_err = sample_data["P"].std()
#        time_sample_err = sample_data["Elapsed time"].std()
#        time_plot.append(time_sample)
#        time_error_plot.append(time_thermometer_err)  # this might be too large, about 2s
#        resistance_plot.append(resistance_sample)
#        resistance_error_plot.append(resistance_sample_err)
#        # TODO: consider the time shift between time_thermometer and time_sample -> additional error factor
#
#        # save the current results for the next run
#        last_thermometer_results = thermometer_results
#
#        # log aggregated Data
#        lgr.info(
#            str(datetime.now()) + delimiter +
#            str(time_sample) + delimiter +
#            str(time_sample_err) + delimiter +
#            str(temperature) + delimiter +
#            str(temperature_error) + delimiter +
#            str(resistance_thermometer) + delimiter +
#            str(resistance_thermometer_err) + delimiter +
#            str(quadrature_thermometer) + delimiter +
#            str(quadrature_thermometer_err) + delimiter +
#            str(power_thermometer) + delimiter +
#            str(power_thermometer_err) + delimiter +
#            str(resistance_sample) + delimiter +
#            str(resistance_sample_err) + delimiter +
#            str(quadrature_sample) + delimiter +
#            str(quadrature_sample_err) + delimiter +
#            str(power_sample) + delimiter +
#            str(power_sample_err))
#
#        if save_raw_data:
#            # no longer necessary, as data is now saved incrementally (with mode='a')
#            # data_thermometer = pandas.concat([data_thermometer, results])
#            # data_sample = pandas.concat([data_sample, results])
#            #
#            # save the raw data from the instrument - this gets large fast!
#            thermometer_results.to_csv(
#                './' + str(time_at_beginning_of_experiment) + 'ADR_RAW_Data_thermometer' + filename + '.csv', mode='a',
#                index=False, header=False)
#            sample_data.to_csv('./' + str(time_at_beginning_of_experiment) + 'ADR_RAW_Data_sample' + filename + '.csv',
#                               mode='a', index=False, header=False)
#
#        # reset the display for the next draw call
#        axs[0].clear()
#        axs[1].clear()
#
#        # draw the T(t) plot
#        axs[0].errorbar(time_plot, temperature_plot, yerr=temperature_error_plot, label='Thermometer', fmt='o')
#        if resistance_thermometer > 2400:
#            axs[0].set_title('T[K]= ' + str(temperature) + ' ± ' + str(temperature_error), fontsize=10)
#        else:
#            axs[0].set_title('T > 4K')
#
#        axs[0].set_ylabel('Temperature [K]')
#        axs[0].set_yscale('log')
#
#        axs[0].set_xlabel('Elapsed time [s]')
#
#        # draw the R(t) plot
#        axs[1].errorbar(temperature_plot, resistance_plot, yerr=resistance_error_plot, label='Sample', fmt='o')
#        axs[1].set_ylabel('Sample Resistance [Ohms]')
#        axs[1].set_xlabel('Temperature [K]')
#        axs[1].set_title('R_sample[Ohm]= ' + str(resistance_sample) + ' ± ' + str(resistance_sample_err),
#                         fontsize=10)
#
#        # draw the new information for the user
#        fig.canvas.draw()
#        fig.canvas.flush_events()
#
#
#if __name__ == "__main__":
#    model372_thermometer_and_sample(2, 1, "TwostageRun9_test1_SER8MK8_warm", True)
