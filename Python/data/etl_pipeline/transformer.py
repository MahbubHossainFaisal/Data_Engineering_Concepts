def transform_data(data: list) -> list:
    """Transform raw data into a structured format."""
    print("Transforming data...")
    return [{"cleaned_data": item["raw_data"].upper()} for item in data]