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


def get_resistance_channel(channel_number, number_of_samples=10, time_at_startup=datetime.now()):
    with Model372(baud_rate=None, ip_address="192.168.0.12") as model372:
        resistance = np.empty(1)
        quadrature = np.empty(1)
        power = np.empty(1)
        time = np.empty(1)
        elapsed = np.empty(1)

        for _ in range(number_of_samples):
            readings = model372.get_all_input_readings(channel_number)
            timedelta = datetime.now() - time_at_startup
            resistance = resistance.append(readings['resistance'])
            quadrature = quadrature.append(readings['quadrature'])
            power = power.append(readings['power'])
            time = time.append(datetime.now())
            elapsed = elapsed.append(timedelta.total_seconds())

    return time, timedelta, resistance, quadrature, power


def acquire_samples(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

    for _ in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = model372.get_all_input_readings(channel_number)
        series_for_concat = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                                               readings['quadrature'], readings['power']]],
                                             columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

        data = pandas.concat([data, series_for_concat], ignore_index=True)
    return data


def cal_generic_ruthenium_oxide_2k(x):
    x = 11.2 - np.log(x - 1400)
    return np.exp(
        -70.2510845934072 + 431.958495397983 * x - 1243.35486928959 * x ** 2 + 2079.851674501 * x ** 3 - 2221.82752732689 * x ** 4 + 1569.15315029492 * x ** 5 - 725.225041039035 * x ** 6 + 201.344808133961 * x ** 7 + -21.1752645798767 * x ** 8 - 5.69301101480164 * x ** 9 + 2.35844703642311 * x ** 10 - 0.259954447641701 * x ** 11 - 0.0187741721390738 * x ** 12 + 0.00669498065063297 * x ** 13 - 4.39871175653045E-4 * x ** 14)


def model372_thermometer_and_sample(thermometer_channel, sample_channel, filename='', save_raw_data=False,
                                    configure_inputs=False, delimeter=',', ip_address="192.168.0.12",
                                    measurements_per_scan=100):
    time_at_beginning_of_experiment = datetime.now()

    # configure logging for regular data output (preprocessed, small files)
    lgr = logging.getLogger('resistance1')
    lgr.setLevel(logging.DEBUG)
    fh = logging.FileHandler('./' + str(time_at_beginning_of_experiment) + 'ADR_Data_' + filename + '.csv')
    fh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(message)s')
    fh.setFormatter(frmt)
    lgr.addHandler(fh)
    lgr.info("Measurement of sample resistivity and thermometer resistivity with Lake Shore 372 AC Bridge")
    lgr.info(
        "Only one channel can be measured at a time. Two thermometer readings are combined to find the approx. " +
        "Readings at the time of sample measurement.")
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
        "Power_thermometer_error" + delimeter +
        "Resistance_sample" + delimeter +
        "Resistance_sample_error" + delimeter +
        "Quadrature_sample" + delimeter +
        "Quadrature_sample_error" + delimeter +
        "Power_sample" + delimeter +
        "Power_sample_error"
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
        "Watt" + delimeter +
        "Ohm" + delimeter +
        "Ohm" + delimeter +
        "iOhm" + delimeter +
        "iOhm" + delimeter +
        "Watt" + delimeter +
        "Watt"
    )

    # lists for plots, this data will not be saved to disk
    time_plot = []
    time_error_plot = []
    temperature_plot = []
    temperature_error_plot = []
    resistance_plot = []
    resistance_error_plot = []

    plt.ion()
    fig, axs = plt.subplots(2, 1)
    # User interface:
    # axs[0]: T(t) + ΔT(t)
    # axs[1]: R(T) + ΔR(T)

    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

    if configure_inputs:
        settings_thermometer = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                          Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                          Model372AutoRangeMode.CURRENT, False,
                                                          Model372InputSensorUnits.OHMS,
                                                          Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

        settings_sample = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                     Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                     Model372AutoRangeMode.CURRENT, False,
                                                     Model372InputSensorUnits.OHMS,
                                                     Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

        instrument_372.configure_input(thermometer_channel, settings_thermometer)
        instrument_372.configure_input(sample_channel, settings_sample)

    instrument_372.set_scanner_status(input_channel=thermometer_channel, status=False)
    time.sleep(4)
    last_thermometer_results = acquire_samples(instrument_372, measurements_per_scan, thermometer_channel, time_at_beginning_of_experiment)

    while True:
        # measure the sample
        instrument_372.set_scanner_status(input_channel=sample_channel, status=False)
        time.sleep(4)
        sample_data = acquire_samples(instrument_372, measurements_per_scan, sample_channel, time_at_beginning_of_experiment)

        # measure the thermometer
        instrument_372.set_scanner_status(input_channel=thermometer_channel, status=False)
        time.sleep(4)
        thermometer_results = acquire_samples(instrument_372, measurements_per_scan, thermometer_channel, time_at_beginning_of_experiment)

        two_last_thermometer_data = pandas.concat([last_thermometer_results, thermometer_results])

        # process the thermometer
        resistance_thermometer = two_last_thermometer_data["R"].mean()
        quadrature_thermometer = two_last_thermometer_data["iR"].mean()
        power_thermometer = two_last_thermometer_data["P"].mean()
        time_thermometer = two_last_thermometer_data["Elapsed time"].mean()
        resistance_thermometer_err = two_last_thermometer_data["R"].std()
        quadrature_thermometer_err = two_last_thermometer_data["iR"].std()
        power_thermometer_err = two_last_thermometer_data["P"].std()
        time_thermometer_err = two_last_thermometer_data["Elapsed time"].std()

        # calculate the temperature and error during the resistivity measurement
        temperature = cal_generic_ruthenium_oxide_2k(resistance_thermometer)
        temperature_error = cal_generic_ruthenium_oxide_2k(resistance_thermometer - resistance_thermometer_err / 2)
        temperature_error = temperature - cal_generic_ruthenium_oxide_2k(
            resistance_thermometer + resistance_thermometer_err / 2)
        temperature_plot.append(temperature)
        temperature_error_plot.append(temperature_error)
        # TODO: test the temperature error calculation

        # process the sample data
        resistance_sample = sample_data["R"].mean()
        quadrature_sample = sample_data["iR"].mean()
        power_sample = sample_data["P"].mean()
        time_sample = sample_data["Elapsed time"].mean()
        resistance_sample_err = sample_data["R"].std()
        quadrature_sample_err = sample_data["iR"].std()
        power_sample_err = sample_data["P"].std()
        time_sample_err = sample_data["Elapsed time"].std()
        time_plot.append(time_sample)
        time_error_plot.append(time_thermometer_err)  # this might be too large, about 2s
        resistance_plot.append(resistance_sample)
        resistance_error_plot.append(resistance_sample_err)
        # TODO: consider the time shift between time_thermometer and time_sample -> additional error factor

        # save the current results for the next run
        last_thermometer_results = thermometer_results

        # log aggregated Data
        lgr.info(
            str(datetime.now()) + delimeter +
            str(time_sample) + delimeter +
            str(time_sample_err) + delimeter +
            str(temperature) + delimeter +
            str(temperature_error) + delimeter +
            str(resistance_thermometer) + delimeter +
            str(resistance_thermometer_err) + delimeter +
            str(quadrature_thermometer) + delimeter +
            str(quadrature_thermometer_err) + delimeter +
            str(power_thermometer) + delimeter +
            str(power_thermometer_err) + delimeter +
            str(resistance_sample) + delimeter +
            str(resistance_sample_err) + delimeter +
            str(quadrature_sample) + delimeter +
            str(quadrature_sample_err) + delimeter +
            str(power_sample) + delimeter +
            str(power_sample_err))

        if save_raw_data:
            # no longer necessary, as data is now saved incrementally (with mode='a')
            # data_thermometer = pandas.concat([data_thermometer, results])
            # data_sample = pandas.concat([data_sample, results])
            #
            # save the raw data from the instrument - this gets large fast!
            thermometer_results.to_csv(
                './' + str(time_at_beginning_of_experiment) + 'ADR_RAW_Data_thermometer' + filename + '.csv', mode='a')
            sample_data('./' + str(time_at_beginning_of_experiment) + 'ADR_RAW_Data_sample' + filename + '.csv',
                        mode='a')

        # reset the display for the next draw call
        axs[0].clear()
        axs[1].clear()

        # draw the T(t) plot
        axs[0].errorbar(time_plot, temperature_plot, yerr=temperature_error_plot, label='Thermometer', fmt='o')
        if resistance_thermometer > 2400:
            axs[0].set_title('T[K]= ' + str(temperature) + ' ± ' + str(temperature_error), fontsize=10)
        else:
            axs[0].set_title('T > 4K')

        axs[0].set_ylabel('Temperature [K]')
        axs[0].yscale('log')
        axs[0].set_xlabel('Elapsed time [s]')

        # draw the R(t) plot
        axs[1].errorbar(temperature_plot, resistance_plot, yerr=resistance_error_plot, label='Sample', fmt='o')
        axs[1].set_ylabel('Sample Resistance [Ohms]')
        axs[1].set_xlabel('Temperature [K]')
        axs[1].set_title('R_sample[Ohm]= ' + str(int(resistance_sample)) + ' ± ' + str(int(resistance_sample_err)), fontsize=10)

        # draw the new information for the user
        fig.canvas.draw()
        fig.canvas.flush_events()


model372_thermometer_and_sample(1, 1, "test")
