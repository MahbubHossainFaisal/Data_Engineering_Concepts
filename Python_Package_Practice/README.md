# Data Toolkit

## Data Loading Module

### Supported File Formats
- CSV
- JSON
- Excel

### Usage

```python
from data_toolkit.data_loader import load_csv, load_json, load_excel

# Load CSV
data_csv = load_csv('path/to/file.csv')

# Load JSON
data_json = load_json('path/to/file.json')

# Load Excel
data_excel = load_excel('path/to/file.xlsx', sheet_name='Sheet1')


## Data Validation Module

### Supported Validation Checks
- Missing values
- Data type mismatches
- Duplicates
- Custom validation rules (e.g., value ranges, regex patterns)

### Usage

```python
from data_toolkit.data_validator import generate_detailed_report, check_value_range, check_pattern

# Load your data
data = load_csv('path/to/file.csv')

# Define expected data types
expected_types = {'name': 'object', 'age': 'float64', 'email': 'object'}
