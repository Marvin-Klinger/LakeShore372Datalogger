import time

import pandas
from datetime import datetime
import numpy as np


def acquire_samples_debug(model372, number_of_samples, channel_number, time_at_startup, channel_settings=None):
    if channel_settings is not None:
        model372.configure_input(channel_number, channel_settings)

    #data = pandas.DataFrame(columns=["Timestamp", "Elapsed time", "R", "iR", "P"])
    rng = np.random.default_rng()

    current_timestamp = datetime.now()
    timedelta = current_timestamp - time_at_startup
    readings = {
            "resistance": rng.random()*1000 + 6000,
            "quadrature": rng.random() * 10 + 60,
            "power": rng.random() * 1E-6 + 6E-6,
    }
    data = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                            readings['quadrature'], readings['power']]],
                            columns=["Timestamp", "Elapsed time", "R", "iR", "P"])
    for _ in range(number_of_samples):
        current_timestamp = datetime.now()
        timedelta = current_timestamp - time_at_startup

        readings = {
            "resistance": rng.random()*1000 + 6000,
            "quadrature": rng.random() * 10 + 60,
            "power": rng.random() * 1E-6 + 6E-6,
        }

        series_for_concat = pandas.DataFrame([[datetime.now(), timedelta.total_seconds(), readings['resistance'],
                                               readings['quadrature'], readings['power']]],
                                             columns=["Timestamp", "Elapsed time", "R", "iR", "P"])

        data = pandas.concat([data, series_for_concat], ignore_index=True)
    return data
