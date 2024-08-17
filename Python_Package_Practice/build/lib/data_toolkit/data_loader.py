import pandas as pd

def load_csv(file_path):
    try:
        data = pd.read_csv(file_path)
        return data
    except Exception as e:
        print(f"Error loading csv file:{e}")
        return None


def load_json(file_path):
    try:
        data = pd.read_json(file_path)
        return data
    except Exception as e:
        print(f"Error loading JSON file:{e}")
        return None
    

def load_excel(file_path,sheet_name=0):
    try:
        data = pd.read_excel(file_path,sheet_name=sheet_name)
        return data
    except Exception as e:
        print(f"Error loading excel file:{e}")
        return None