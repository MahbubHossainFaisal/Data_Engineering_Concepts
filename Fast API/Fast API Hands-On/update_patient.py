from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re

class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None

    @field_validator('state')
    def validate_state(cls, value):
        valid_states = {'DHAKA', 'CHITTAGONG', 'KHULNA', 'RAJSHAHI', 'BARISHAL', 'SYLHET', 'RANGPUR', 'MYMENSINGH'}
        if value and value.upper() not in valid_states:
            raise ValueError(f"Invalid state: {value}. Must be one of {valid_states}.")
        return value.upper() if value else value

class Patient_update(BaseModel):
    patient_id: Optional[str] = None
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    date_of_birth: Optional[str] = None
    gender: Optional[str] = Field(None, pattern=r'^(male|female|other)$')
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[Address] = None

    @field_validator('date_of_birth')
    def validate_date_of_birth(cls, value):
        if value:
            try:
                dob = datetime.strptime(value, '%Y-%m-%d')
                if dob.year < 1900:
                    raise ValueError("Date of birth must be after 1900.")
            except ValueError:
                raise ValueError("Date of birth must be in YYYY-MM-DD format.")
        return value

    @field_validator('phone')
    def validate_phone(cls, value):
        phone_pattern = re.compile(r'^\+?[\d\s\-\(\)]{7,}$')
        if value and not phone_pattern.match(value):
            raise ValueError("Invalid phone number format.")
        return value