from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional 
import re

class Address(BaseModel):
    street: str = Field(...,min_length=2,max_length=100)
    city: str = Field(...,min_length=2, max_length=50)
    state: str = Field(...,min_length=2, max_length=10)
    zip: str = Field(...,min_length=5,max_length=10)

    @field_validator('state')
    def validate_upper_state(cls, value):
        valid_states = {'DHAKA', 'CHITTAGONG', 'KHULNA', 'RAJSHAHI', 'BARISHAL', 'SYLHET', 'RANGPUR', 'MYMENSINGH'}
        if value.upper() not in valid_states: 
            raise ValueError(f"Invalid state: {value}. Must be one of {valid_states}.")
        return value.upper()

class Patient_info(BaseModel):
    patient_id : str = Field(..., min_length=4, max_length=20)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    date_of_birth: str
    gender: str = Field(..., pattern=r'^(male|female|other)$')
    phone: str
    email: EmailStr
    address: Address

    @field_validator('date_of_birth')
    def validate_dob_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        
        # Additional business logic
        if datetime.strptime(v, '%Y-%m-%d').year < 1900:
            raise ValueError('Patient must be born after 1900')
        return v
    
    @field_validator('phone')
    def validate_phone(cls, v):
        phone_pattern = re.compile(r'^\+?[\d\s\-\(\)]{7,}$')
        if not phone_pattern.match(v):
            raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('gender')
    def validate_gender(cls, v):
        return v.lower()
    

