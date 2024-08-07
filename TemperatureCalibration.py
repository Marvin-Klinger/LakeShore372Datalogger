import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tkinter.filedialog import askopenfilename, askdirectory
import os
from UliEngineering.Physics.RTD import pt1000_temperature


def cal_ht1(x):
    if x < 4600:
        return 400
    t = 1.14239E10 * (np.log(-(4427.66529-x)/0.50214) ** (-1/0.1))
    if t < 1.7 or t > 300:
        return 400
    return t


def cal_ht2(x):
    if x < 4600:
        return 400
    t = 1.00019E10 * (np.log(-(4393.21183 - x) / 0.56481) ** (-1 / 0.1))
    if t < 1.7 or t > 300:
        return 400
    return t


def cal_ht3(x):
    if x < 4600:
        return 400
    t = 1.02639E10 * (np.log(-(4402.71193 - x) / 0.54942) ** (-1 / 0.1))
    if t < 1.7 or t > 300:
        return 400
    return t


def cal_III(x):
    x = 11.2 - np.log(x - 1400)
    T = np.exp( 3.02890855e-04 * x** 14 - 5.75616996e-03 * x**13 + 4.57449826e-02 * x**12 - 1.92476825e-01 * x**11 + 4.29386069e-01 * x**10 - 3.24290943e-01 * x**9 - 7.20758129e-01 * x**8 + 2.13213145e+00 * x**7 - 2.17631225e+00 * x**6 + 7.39243297e-01 * x**5 + 2.53107792e-01 * x**4 - 2.14102245e-01 * x**3 + 2.71741053e-01 * x**2 + 4.06882605e-01 * x -2.88096256e+00 )
    if (T > 2) or (T < 0.01):
        return 400
    return T
def cal_generic_pt1000(x):
    return (cal_pt1000_Ch1_Baffle5(x) + cal_pt1000_Ch2_Baffle4(x)) / 2

def cal_pt1000_Ch1_Baffle5(x):
    if x < 105:
        return 5.74834 + 0.43974 * x**0.88354 + 4.11545 * np.log(x - 10.34234) + 3.42096 * np.tanh(x / (-8.85332*(10**14)) + 3.37344*(10**15))
    return cal_pt1000(x)

def cal_pt1000_Ch2_Baffle4(x):
    if x < 89.58:
        return 7.85391 + 0.451 * x**0.87903 + 4.0281 * np.log(x -7.79381) - 2.19714 * np.tanh(x / (-2.36548*(10*15)) -7.27357*(10**19)) 
    return cal_pt1000(x)

def cal_pt1000(r):
    t = pt1000_temperature(r) + 273.15
    if t < 0:
        t = 9999
    return t

def cal_cam_cool(x):
    if x < 1400:
        return 9999
    x = 11.2 - np.log(x - 1400)
    return np.exp(-2.96106634147848 + -5.18089054649127 * x + 25.9564389751936 * x ** 2 - 67.919802323554 * x ** 3 +
                  117.974122540099 * x ** 4 - 142.685187179576 * x ** 5 + 123.779073338133 * x ** 6 -
                  78.2257644232516 * x ** 7 + 36.217633977666 * x ** 8 + -12.2416617747187 * x ** 9 +
                  2.97848537774922 * x ** 10 - 0.506678458162558 * x ** 11 + 0.0570440155878966 * x ** 12 +
                  -0.00380768004287375 * x ** 13 + 1.13699100097316E-4 * x ** 14)


def cal_mx_01(x):
    return 0.1254 * (np.log(-(-5892.98581-x)/7844.98581)) ** (-1/0.56628)


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


def cal_mk1a(x):
    return 1.4360138613965 * (np.log((x / 1448.30330553877))) ** (-1 / 0.345)


def cal_mk2(x):
    return 5.79932922661894 * (np.log(((x - 1204.52243625155) / 451.516270863735))) ** (-1 / 0.345)


def cal_mk2a(x):
    return 1.19449771640497 * (np.log((x / 1350.65650744707))) ** (-1 / 0.345)


def cal_mk3(x):
    if x > 2900:
        # more precise at lower temperature
        return 0.315915896272482 * (np.log(((x + 1874.50552748311) / 2907.47986525929))) ** (-1 / 0.345)
    else:
        return 0.47964313772239 * (np.log(((x +1025.38141190532) / 2225.92222846437))) ** (-1 / 0.345)


def cal_mk4(x):
    if x > 2850:
        # more precise at lower temperature
        return 0.398384267309045 * (np.log(((x + 1710.66844432221) / 2724.93512315828))) ** (-1 / 0.345)
    else:
        return 0.583704981084618 * (np.log(((x + 927.546890248635) / 2114.96434715406))) ** (-1 / 0.345)


def cal_mk7(x):
    if x > 620:
        return 0.019666659791949 * (np.log(((x + 1079.95162254202) / 1316.99960317984))) ** (-1 / 0.345)
    if x > 500:
        return 0.048300975064506 * (np.log(((x + 595.78347167658) / 858.932321950173))) ** (-1 / 0.345)
    else:
        return 0.0725238847028473 * (np.log(((x + 428.519497335669) / 702.665844315736))) ** (-1 / 0.345)


def cal_mk8(x):
    if x > 52000:
        return 11.4750634118558 * (np.log(((x + 2166.84587906996) / 1796.57472456776))) ** (-1 / 0.345)
    if x > 9000:
        return 16.6186885986779 * (np.log(((x - 2614.8579149542) / 1029.46467803875))) ** (-1 / 0.345)
    else:
        return 16.592768580112 * (np.log(((x - 2602.58081008141) / 1031.84217910761))) ** (-1 / 0.345)


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

    calibrated_data['temperature'] = calibrated_data['resistance'].apply(cal_mk3)
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
if __name__ == "__main__":
    show_plot()

#calibrate_all_files_in_dir(6)
#show_plot()

