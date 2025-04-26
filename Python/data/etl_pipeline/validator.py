def validate_data(data: list) -> list:
    print("Validating data...")
    return [{"validated_data": item['cleaned_data']} for item in data]