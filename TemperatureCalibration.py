import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tkinter.filedialog import askopenfilename, askdirectory
import os


def cal_ser8(x):
    x = 11.2 - np.log(x - 1400)
    return np.exp(
        -70.2510845934072 + 431.958495397983 * x - 1243.35486928959 * x ** 2 + 2079.851674501 * x ** 3 - 2221.82752732689 * x ** 4 + 1569.15315029492 * x ** 5 - 725.225041039035 * x ** 6 + 201.344808133961 * x ** 7 + -21.1752645798767 * x ** 8 - 5.69301101480164 * x ** 9 + 2.35844703642311 * x ** 10 - 0.259954447641701 * x ** 11 - 0.0187741721390738 * x ** 12 + 0.00669498065063297 * x ** 13 - 4.39871175653045E-4 * x ** 14)


def cal_ser6(x):
    x = 11.2 - np.log(x - 1400)
    return np.exp(
        -418.66269190557 + 2030.22369066585 * x - 4302.49551086799 * x ** 2 + 5133.14952507189 * x ** 3 - 3719.23040793288 * x ** 4 + 1605.56403609629 * x ** 5 - 332.397935938044 * x ** 6 - 23.0801113001037 * x ** 7 + 26.8652824936315 * x ** 8 - 1.88491652328337 * x ** 9 - 2.21422793002565 * x ** 10 + 0.813246835982012 * x ** 11 - 0.129335143412473 * x ** 12 + 0.0100828066451444 * x ** 13 - 3.06270610070887E-4 * x ** 14)


def cal_mk1(x):
    return 4.17542532415951 * (np.log(((x - 974.133666737063)/706.468770240909)))**(-1/0.345)


def show_plot(save_calibrated_file=False, filename=""):
    if filename == "":
        filename = askopenfilename(initialdir=r'/home/marvin/Nextcloud/Uni/Masterarbeit_Marvin/35_Messdaten_ADR')

    if filename == "":
        print("No File!")
        return

    raw_data = pd.read_csv(filename, delimiter='\t', skiprows=2,
                           names=['time', 'temperature', 'resistance', 'resistance_range', 'excitation_range'])

    data_with_increased_resistance = raw_data.loc[raw_data['resistance'] > 2900]
    calibrated_data = data_with_increased_resistance[['time', 'resistance']].copy()

    calibrated_data['temperature'] = calibrated_data['resistance'].apply(cal_mk1())
    calibrated_data.plot(x='time', y='temperature', kind='scatter')

    print("Minimal Temperature reached: " + str(calibrated_data['temperature'].min()))
    print("Maximum resistance reached: " + str(raw_data['resistance'].max()))

    if save_calibrated_file:
        calibrated_data.to_csv(filename[:-4] + '.cal')

    plt.show()


def calibrate_all_files_in_dir(ser_number=0, directory=""):
    if directory == "":
        directory = askdirectory(initialdir=r'/home/marvin/Nextcloud/Uni/Masterarbeit_Marvin/35_Messdaten_ADR')

    if directory == "":
        print("No directory supplied, exiting...")
        return

    list_of_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file[-3:] == "dat" and not file[0:3] == "log":
                list_of_files.append(os.path.join(root, file))

    print("Found " + str(len(list_of_files)) + " .dat files")

    for filename in list_of_files:
        raw_data = pd.read_csv(filename, delimiter='\t', skiprows=2,
                               names=['time', 'temperature', 'resistance', 'resistance_range', 'excitation_range'])

        data_with_increased_resistance = raw_data.loc[raw_data['resistance'] > 2900]
        calibrated_data = data_with_increased_resistance[['time', 'resistance']].copy()

        if ser_number == 8 or filename[-5:] == "8.dat":
            calibrated_data['temperature'] = calibrated_data['resistance'].apply(cal_ser8)

        if ser_number == 6 or filename[-5:] == "6.dat":
            calibrated_data['temperature'] = calibrated_data['resistance'].apply(cal_ser6)

        print(calibrated_data)

        calibrated_data.to_csv(filename[:-3] + 'cal')

# calibrate_all_files_in_dir(6)


#calibrate_all_files_in_dir(6)
show_plot()