import os
import pandas as pd
import numpy as np
from orbit.models import DLT, ETS, LGT, KTR
from orbit.diagnostics.metrics import smape
from orbit.diagnostics.plot import plot_predicted_data
from orbit.forecaster import Forecaster
from commons import DATA_PATH
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.stats.stattools import durbin_watson
from statsmodels.graphics.tsaplots import plot_acf
import matplotlib.pyplot as plt
from modules import MAPE, RMSE, MAE, MSE, check_encoding, detect_existing_output


def hypertune_dlt_model(training_df, y_train, x_train, y_test, testing_df, seasonality):
    # Define the hyperparameter grid
    trend_options = ['linear', 'loglinear', 'flat', 'logistic']
    estimators = ['stan-map', 'stan-mcmc']
    penalties = [None, 0.01, 0.1, 1.0]  # Regularization penalties

    best_mae = float('inf')
    best_model = None
    best_config = None

    # Iterate over each combination of trend, estimator, and penalty
    for trend in trend_options:
        for estimator in estimators:
            for penalty in penalties:
                # Define the model with the current set of hyperparameters
                print(f"Training with trend={trend}, estimator={estimator}, penalty={penalty}")
                
                model = DLT(
                    seasonality=seasonality,
                    response_col='SQALE_INDEX',
                    date_col='COMMIT_DATE',
                    estimator=estimator,
                    global_trend_option=trend,
                    seed=8888,
                    regressor_col=x_train.columns.tolist(),
                    n_bootstrap_draws=1000,
                    regressor_sign=[penalty] * len(x_train.columns) if penalty is not None else None
                )
                
                # Fit the model
                model.fit(df=training_df)
                
                # Predict and calculate MAE
                predicted_df = model.predict(df=testing_df)
                predicted = predicted_df['prediction'].values
                
                mae = mean_absolute_error(y_test, predicted)
                
                print(f"MAE for trend={trend}, estimator={estimator}, penalty={penalty}: {mae:.2f}")
                
                # Check if the current model is better
                if mae < best_mae:
                    best_mae = mae
                    best_model = model
                    best_config = {
                        'trend': trend,
                        'estimator': estimator,
                        'penalty': penalty
                    }

    print(f"Best configuration: {best_config} with MAE: {best_mae:.2f}")
    
    # Return the best model and configuration
    return best_model, best_config


# Main method to trigger the prediction process
def trigger_prediction(df_path, project_name, periodicity=None, seasonality=None):
    df = pd.read_csv(df_path)

    # Convert dates
    df['COMMIT_DATE'] = pd.to_datetime(df['COMMIT_DATE'])
    df['SQALE_INDEX'] = pd.to_numeric(df['SQALE_INDEX'], errors='coerce')
    df = df.dropna()

    # Splitting data into training (80%) and testing (20%)
    split_point = round(len(df) * 0.8)
    training_df = df.iloc[:split_point, :]
    testing_df = df.iloc[split_point:, :]

    # Dependent and independent variables
    y_train = training_df['SQALE_INDEX'].values
    x_train = training_df.drop(columns=['COMMIT_DATE', 'SQALE_INDEX'])
    y_test = testing_df['SQALE_INDEX'].values
    x_test = testing_df.drop(columns=['COMMIT_DATE', 'SQALE_INDEX'])

    # Hypertune the DLT model
    best_model, best_config = hypertune_dlt_model(
        training_df=training_df, 
        y_train=y_train, 
        x_train=x_train, 
        y_test=y_test, 
        testing_df=testing_df, 
        seasonality=seasonality
    )

    # Use the best model for final predictions
    predicted_df = best_model.predict(df=testing_df)
    
    actual = y_test
    predicted = predicted_df['prediction'].values
    
    # Calculate error metrics
    mae = round(MAE(predicted, actual), 2)
    mape_value = round(MAPE(predicted, actual), 2)
    mse = round(MSE(predicted, actual), 2)
    rmse = round(RMSE(predicted, actual), 2)

    # Log the metrics
    print(f"Final MAE: {mae:.2f}")
    print(f"Final MAPE: {mape_value:.2f}%")
    print(f"Final RMSE: {rmse:.2f}")
    print(f"Final MSE: {mse:.2f}")

    # Store the results in a dictionary
    result_data = {
        'Project': project_name,
        'Model': 'DLT',
        'Trend': best_config['trend'],
        'Estimator': best_config['estimator'],
        'Penalty': best_config['penalty'],
        'MAE': mae,
        'MAPE': mape_value,
        'RMSE': rmse,
        'MSE': mse
    }

    # Output path to save the results
    base_path = os.path.join(DATA_PATH, 'ORBIT_ML', 'DLT_Result', periodicity)
    os.makedirs(base_path, exist_ok=True)
    csv_output_path = os.path.join(base_path, "assessment.csv")

    # Save result_df as a CSV file
    results_df = pd.DataFrame([result_data])
    if not os.path.isfile(csv_output_path):
        results_df.to_csv(csv_output_path, mode='w', index=False, header=True)
    else:
        results_df.to_csv(csv_output_path, mode='a', index=False, header=False)

    print(f"Results for {project_name} saved in {base_path}")
    return result_data


# Example function call
def bayesian_orbit():
    biweekly_data_path = os.path.join(DATA_PATH, "biweekly_data_1")
    monthly_data_path = os.path.join(DATA_PATH, "monthly_data_1")
    complete_data_path = os.path.join(DATA_PATH, "complete_data_1")

    biweekly_files = os.listdir(biweekly_data_path) 
    monthly_files = os.listdir(monthly_data_path)
    complete_files = os.listdir(complete_data_path)

    for i in range(len(biweekly_files)):
        if biweekly_files[i] == '.DS_Store':
            continue
        project = biweekly_files[i][:-4]

        # Process biweekly data
        print(f"> Processing {project} for biweekly data")
        method_biweekly = trigger_prediction(
            df_path=os.path.join(biweekly_data_path, biweekly_files[i]),
            project_name=project,
            periodicity="biweekly",
            seasonality=26
        )

        # Process monthly data
        print(f"> Processing {project} for monthly data")
        method_monthly = trigger_prediction(
            df_path=os.path.join(monthly_data_path, monthly_files[i]),
            project_name=project,
            periodicity="monthly",
            seasonality=12
        )

        # Process complete data
        print(f"> Processing {project} for complete data")
        method_complete = trigger_prediction(
            df_path=os.path.join(complete_data_path, complete_files[i]),
            project_name=project,
            periodicity="complete",
            seasonality=None
        )