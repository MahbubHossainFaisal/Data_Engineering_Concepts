from fastapi import FastAPI, Path, Query, HTTPException
from typing import Dict, List
from create_patient import Patient_info
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
async def create_patient(patient_info: Patient_info):
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