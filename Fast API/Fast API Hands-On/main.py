from fastapi import FastAPI, Path, Query, HTTPException
from typing import Dict, List
from create_patient import Patient_info
from update_patient import Patient_update
import json
app = FastAPI()

# Json file path
json_file_path = 'patients_info.json'

# load patient data
with open('patients_info.json','r') as f:
    patients_data = json.load(f)
    #print(patients_data)

@app.get('/')
def read_root():
    return patients_data['patients']

@app.get('/patient/{patient_id}')
def get_patient_info(patient_id : str = Path(...,min_length=3,max_length=7)):
    for patient in patients_data['patients']:
        if patient['patient_id'] == patient_id:
            #print(patient)
            return patient
    raise HTTPException(status_code=404, detail="Patient not found")


@app.get('/search_patient')
def search_patient(
    gender: str = Query(..., min_length=4, max_length=6),  
    blood_group: str = Query(..., max_length=2)):         
    print(patients_data['patients'][0])
    filtered_patients = [
        patient for patient in patients_data['patients'] 
        if patient['gender'] == gender and patient['blood_type'] == blood_group
    ]
    
    if not filtered_patients: 
        raise HTTPException(status_code=404, detail="Patient not found")
        
    return filtered_patients

@app.post('/create_patient')
def create_patient(patient_info: Patient_info):
    try:
        with open(json_file_path, 'r+') as f:
            patients_data = json.load(f)
    except FileNotFoundError:
        patients_data = {'patients': []}

    for patient in patients_data['patients']:
        if patient['patient_id'] == patient_info.patient_id:
            raise HTTPException(status_code=400, detail="Patient ID already exists")

    new_patient = patient_info.model_dump()
    patients_data['patients'].append(new_patient)

    with open(json_file_path, 'w') as f:
        json.dump(patients_data, f, indent=4)

    return {"message": "Patient created successfully", "patient_id": patient_info.patient_id}

@app.put('/update_patient/{patient_id}')
def update_patient(patient_id: str, patient_info: Patient_info):
    try:
        with open(json_file_path, 'r+') as f:
            patients_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Patient data file not found")
    for i, patient in enumerate(patients_data['patients']):
        if patient['patient_id'] == patient_id:
            patients_data['patients'][i] = patient_info.model_dump()
            with open(json_file_path, 'w') as f:
                json.dump(patients_data, f, indent=4)
            return {"message": "Patient updated successfully", "patient_id": patient_id}
        


def recursive_update(original: dict, updates: dict):
    """
    Recursively update a dictionary with another dictionary.
    """
    for key, value in updates.items():
        if isinstance(value, dict) and key in original and isinstance(original[key], dict):
            # If the value is a nested dictionary, recursively update it
            recursive_update(original[key], value)
        else:
            # Otherwise, update the value directly
            original[key] = value

@app.patch('/update_patient/{patient_id}')
def update_patient_partial(patient_id: str, patient_info: Patient_update):
    try:
        with open(json_file_path, 'r+') as f:
            patients_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Patient data file not found")
    
    for i, patient in enumerate(patients_data['patients']):
        if patient['patient_id'] == patient_id:
            # Get the updates from the request
            updates = patient_info.model_dump(exclude_unset=True)
            
            # Recursively update the patient data
            recursive_update(patients_data['patients'][i], updates)
            
            # Save the updated data back to the file
            with open(json_file_path, 'w') as f:
                json.dump(patients_data, f, indent=4)
            
            return {"message": "Patient updated successfully", "patient_id": patient_id}
    
    raise HTTPException(status_code=404, detail="Patient not found")


@app.delete('/delete_patient/{patient_id}')
def delete_patient(patient_id: str):
    try:
        with open(json_file_path, 'r+') as f:
            patients_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Patient data file not found")
    
    for i, patient in enumerate(patients_data['patients']):
        if patient['patient_id'] == patient_id:
            del patients_data['patients'][i]
            with open(json_file_path, 'w') as f:
                json.dump(patients_data, f, indent=4)
            return {"message": "Patient deleted successfully", "patient_id": patient_id}
    
    raise HTTPException(status_code=404, detail="Patient not found")