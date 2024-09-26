"""
This project executes a series of TSA techniques as well as ML models

NOTE: The data collection and preprocessing has been already performed.
"""

import os

from preprocessing import preprocessing
from tsDataPreparation import data_prepare
from bayesian_prediction import bayesian_dglm
from bayesian_prediction_orbit_DLT import bayesian_orbit
from bayesian_prediction_orbit_ETS import bayesian_orbit_ets


from commons import SARIMAX, SIMULATION, SIMULATION_FUTURE_POINTS,  RELATED_WORK, ML_MODELS, COMBINE_RESULTS, PREPROCESSING, DGLM, ORBIT


def main():

    # Preprocess the data and generate the clean tables for analysis with biweekly, monthly and complete data
    if PREPROCESSING:
        #preprocessing()
        data_prepare()
    if DGLM:
        bayesian_dglm(seasonality=True)
    if ORBIT:
        bayesian_orbit()
        #bayesian_orbit_ets()


if __name__ == '__main__':
    main()