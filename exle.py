import pandas as pd

# Define the maintenance window data
data = {
    "Hostname": ["192.168.0.61","192.168.0.241"],
    "Username":["ansible","ansible"],
    "Password":["Netapp1!","Netapp1!"],
    "Owner": ["root","root"],
    "Maintenance Window": ["Every 2nd Tuesday 6 to 20 hours","Every 2nd Tuesday 6 to 20 hours"]
}

# Create a DataFrame
df = pd.DataFrame(data)

# Save the DataFrame to an Excel file
df.to_excel("maintenance_window.xlsx", index=False)

print("Maintenance window details have been saved to maintenance_window.xlsx")
