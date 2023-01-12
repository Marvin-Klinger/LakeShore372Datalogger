from lakeshore import Model372
from lakeshore import Model372SensorExcitationMode, Model372MeasurementInputCurrentRange, Model372AutoRangeMode, \
    Model372InputSensorUnits, Model372MeasurementInputResistance, Model372InputSetupSettings
import pandas
from datetime import datetime
import logging
import numpy


def log_resistance_two_channels():
    # Number of samples before switching channel
    samples_per_scan = 10

    # The channel for the thermometer resistor (1 and 2 are swapped for the PPMS puck)
    thermometer_channel = 2

    # Resistor for device under test (dut)
    dut_channel = 1

    instrument_372 = Model372(57600)
    time_at_startup = datetime.now()

    # Create Model372InputSetupSettings object with current excitation mode, 31.6 uA excitation current, autoranging on
    # (tracking current), current source not shunted, preferred units of Ohms, and a resistance range of 20.0 kOhms
    sensor_settings_thermometer_channel = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                                     Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                                     Model372AutoRangeMode.CURRENT, False,
                                                                     Model372InputSensorUnits.OHMS,
                                                                     Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

    # Create Model372InputSetupSettings object with current excitation mode, 31.6 uA excitation current, autoranging on
    # (tracking current), current source not shunted, preferred units of Ohms, and a resistance range of 20.0 kOhms
    sensor_settings_channel_dut = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                             Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                             Model372AutoRangeMode.CURRENT, False,
                                                             Model372InputSensorUnits.OHMS,
                                                             Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

    # Configure the channels according to user settings
    instrument_372.configure_input(thermometer_channel, sensor_settings_thermometer_channel)
    instrument_372.configure_input(dut_channel, sensor_settings_channel_dut)

    # Pandas sections
    # Initialize the pandas dataframes for holding DUT and Thermometer Info
    data_thermometer = pandas.DataFrame({"Timestamp", "Elapsed time", "R", "iR", "P"})
    data_dut = pandas.DataFrame({"Timestamp", "Elapsed time", "R", "iR", "P"})

    while True:
        results_thermometer = acquire_samples(instrument_372, samples_per_scan, thermometer_channel, time_at_startup,
                                              sensor_settings_thermometer_channel)
        results_dut = acquire_samples(instrument_372, samples_per_scan, dut_channel, time_at_startup,
                                      sensor_settings_channel_dut)

        data_thermometer.append(results_thermometer)
        data_dut.append(results_dut)


def acquire_samples(model372, number_of_samples, channel_number, time_at_startup, channel_settings=False):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    results = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

    for _ in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = model372.get_all_input_readings(channel_number)
        results = results.append(pandas.Series([datetime.now(), timedelta.total_seconds(), readings['resistance'], readings['quadrature'], readings['power']], index=results.columns), ignore_index=True)
    return results


def test_instrument():
    instrument_372 = Model372(baud_rate=None, ip_address="192.168.0.12")
    time_at_startup = datetime.now()

    sensor_settings_thermometer_channel = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                                     Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                                     Model372AutoRangeMode.CURRENT, False,
                                                                     Model372InputSensorUnits.OHMS,
                                                                     Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

    results = acquire_samples(instrument_372, 20, 1, time_at_startup, None)

    print(results)


def run_datalogger_single_channel(channel_number):
    lgr = logging.getLogger('outgassing')
    lgr.setLevel(logging.DEBUG)


def get_resistance_channel(channel_number, number_of_samples=10, time_at_startup=datetime.now()):
    with Model372(baud_rate=None, ip_address="192.168.0.12") as model372:
        resistance = []
        quadrature = []
        power = []
        time = []
        elapsed = []

        for _ in range(number_of_samples):
            readings = model372.get_all_input_readings(channel_number)
            timedelta = datetime.now() - time_at_startup
            resistance.append(readings['resistance'])
            quadrature.append(readings['quadrature'])
            power.append(readings['power'])
            time.append(datetime.now())
            elapsed.append(timedelta.total_seconds())

    return time, timedelta, resistance, quadrature, power