import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder

def fill_missing_values(data,strategy='mean',columns=None):
    if columns is None:
        columns = data.columns

    for column in columns:
        if strategy == 'mean':
            data[column].fillna(data[column].mean(),inplace=True)
        elif strategy == 'median':
            data[column].fillna(data[column].median(),inplace=True)
        elif strategy == 'mode':
            data[column].fillna(data[column].mode()[0],inplace=True)

        elif strategy == 'drop':
            data.dropna(subset=[column],inplace=True)

    return data


def normalize_data(data,columns=None):
    if columns is None:
        columns = data.columns

    scaler = MinMaxScaler()

    data[columns] = scaler.fit_transform(data[columns])

    return data


def standardize_data(data,columns=None):
    if columns is None:
        columns = data.columns

    scaler = StandardScaler()

    data[columns] = scaler.fit_transform(data[columns])

    return data

def encode_categorical(data, columns=None):
    if columns is None:
        columns = data.select_dtypes(include=['object']).columns
    encoder = LabelEncoder()
    for column in columns:
        data[column] = encoder.fit_transform(data[column])
    return data