import pandas as pd

def check_missing_values(data):
    missing = data.isnull().sum()
    return missing[missing>0]

def check_data_types(data,expected_types):
    mismatched_types = {}
    for column, expected_type in expected_types.items():
        if column in data.columns:
            if not data[column].dtype == expected_type:
                mismatched_types[column] = data[column].dtype
    return mismatched_types


def check_duplicates(data):
    duplicates = data[data.duplicated()]
    return duplicates

def generate_report(data,expected_types):
    reports = {}

    reports['missing_values'] = check_missing_values(data)
    reports['mismatched_types'] = check_data_types(data,expected_types)
    reports['duplicates'] = check_duplicates(data)

    return reports


