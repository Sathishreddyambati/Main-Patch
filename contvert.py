import pandas as pd

# Load the Excel file
df = pd.read_excel('maintenance_window.xlsx', engine='openpyxl')

# Save the DataFrame to a CSV file
df.to_csv('maintenance_window.csv', index=False)

print("Excel file has been converted to CSV successfully!")

