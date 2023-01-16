from multiprocessing import Process, Queue
from LS_Datalogger2_v2 import acquire_samples
from lakeshore import Model372
from lakeshore import Model372SensorExcitationMode, Model372MeasurementInputCurrentRange, Model372AutoRangeMode, \
    Model372InputSensorUnits, Model372MeasurementInputResistance, Model372InputSetupSettings
import time
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from TemperatureCalibration import cal_ser6, cal_ser8, cal_mk1


def visualize_single_channel(queue, time_at_beginning_of_experiment, measurements_per_scan=70, delimiter=',',
                             filename='resistance_single_channel', save_raw_data=True):
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

    plt.ion()
    fig, axs = plt.subplots(2, 1)

    """Read from the queue; this spawns as a separate Process"""
    while True:
        if queue.qsize() == 0:
            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(0.05)
            continue
        sample_data = queue.get()  # Read from the queue
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


def read_single_channel(queue, _time_at_beginning_of_experiment, channel=1, configure_input=False,
                        ip_address="192.168.0.12", measurements_per_scan=70):
    """"""
    instrument_372 = Model372(baud_rate=None, ip_address=ip_address)

    if configure_input:
        settings_thermometer = Model372InputSetupSettings(Model372SensorExcitationMode.CURRENT,
                                                          Model372MeasurementInputCurrentRange.RANGE_1_NANO_AMP,
                                                          Model372AutoRangeMode.CURRENT, False,
                                                          Model372InputSensorUnits.OHMS,
                                                          Model372MeasurementInputResistance.RANGE_63_POINT_2_KIL_OHMS)

        instrument_372.configure_input(channel, settings_thermometer)

    instrument_372.set_scanner_status(input_channel=channel, status=False)
    time.sleep(4)

    while True:
        sample_data = acquire_samples(instrument_372, measurements_per_scan, channel, _time_at_beginning_of_experiment)
        queue.put(sample_data)


def start_data_visualizer(queue, time_at_beginning_of_experiment, measurements_per_scan=70, delimeter=',',
                          filename='resistance_single_channel', save_raw_data=True):
    """Start the reader processes and return all in a list to the caller"""
    all_reader_procs = list()
    ### reader_p() reads from qq as a separate process...
    reader_p = Process(target=visualize_single_channel, args=(queue, time_at_beginning_of_experiment,
                                                              measurements_per_scan, delimeter, filename,
                                                              save_raw_data))
    reader_p.daemon = True
    reader_p.start()  # Launch reader_p() as another proc
    return reader_p


if __name__ == "__main__":
    time_at_beginning_of_experiment = datetime.now()
    measurements_per_scan = 70
    _filename = "ADR"
    save_raw_data = True
    ls_data_queue = Queue()  # writer() writes to ls_data_queue from _this_ process

    visualizer_process = start_data_visualizer(ls_data_queue, time_at_beginning_of_experiment, filename=_filename)
    read_single_channel(ls_data_queue, time_at_beginning_of_experiment, channel=1)
    visualizer_process.join()
    print("main end")
