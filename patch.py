import pandas as pd
import paramiko
import requests
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(filename='patch_management.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ServiceNow credentials
SNOW_INSTANCE = "https://dev198403.service-now.com"
SNOW_USERNAME = "admin"
SNOW_PASSWORD = "eCXMH%3p7=sl"
SNOW_TABLE = "/api/now/table/incident"  # Endpoint for problem management
SNOW_CHANGE_TABLE = "/api/now/table/change_request"#?sysparm_limit=1"  # Endpoint for change requests

def get_change_request():
    """Retrieve a change request ticket from ServiceNow."""
    URL = f"{SNOW_INSTANCE}/api/now/table/change_request"
    HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json"
            }
    QUERY = "?sysparm_query=requested_by.name=Harini R K"

    try:
        response = requests.get(URL + QUERY, auth=(SNOW_USERNAME, SNOW_PASSWORD), headers=HEADERS)
        if response.status_code == 200:
            change_data = response.json()
            if change_data["result"]:
                change_request = change_data["result"][0]
                change_number = change_data["result"][0].get("number")
                change_sys_id = change_data["result"][0].get("sys_id")
                logging.info(f"ServiceNow change request retrieved: {change_number}")
                print(f"ServiceNow change request retrieved: {change_number}")
                return change_sys_id
            else:
                logging.info("No new change requests found.")
                print("No new change requests found.")
                return None
        else:
            logging.error(f"Failed to retrieve change request: {response.status_code} - {response.text}")
            print(f"Failed to retrieve change request: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error while retrieving change request: {e}")
        print(f"Error while retrieving change request: {e}")
    return None

def create_ticket(description):
    """Create a ServiceNow ticket for the issue."""
    url = SNOW_INSTANCE + SNOW_TABLE
    headers = {"Content-Type": "application/json"}
    payload = {
        "short_description": "Patch Management Failure",
        "description": description,
        "priority": "3",
        "state": "1",  # New state
    }
    try:
        response = requests.post(url, auth=(SNOW_USERNAME, SNOW_PASSWORD), headers=headers, data=json.dumps(payload))
        if response.status_code == 201:
            ticket_data = response.json()
            ticket_number = ticket_data["result"]["number"]
            ticket_sys_id = ticket_data["result"]["sys_id"]
            logging.info(f"ServiceNow ticket created: {ticket_number}")
            print(f"ServiceNow ticket created: {ticket_number}")
            return ticket_sys_id
        else:
            logging.error(f"Failed to create ticket: {response.status_code} - {response.text}")
            print(f"Failed to create ticket: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error while creating ticket: {e}")
        print(f"Error while creating ticket: {e}")
    return None

def resolve_ticket(ticket_sys_id):
    """Resolve a ServiceNow ticket after the issue is fixed."""
    URL1 = f"{SNOW_INSTANCE}/api/now/table/change_request/{ticket_sys_id}"
    HEADERS = {
            "Content-Type": "application/json",
            "Accept": "application/json"
                }
    update_data = {

            "state": "3",  # 3 is the state code for "Resolved"
            "close_code": "Solved (Permanently)",
            "close_notes": "Change successfully implemented."
                    }

    try:
        response = requests.patch(URL1, auth=(SNOW_USERNAME, SNOW_PASSWORD), headers=HEADERS, data=json.dumps(update_data))
        if response.status_code == 200:
            logging.info(f"ServiceNow ticket resolved: {ticket_sys_id}")
            print(f"ServiceNow ticket resolved: {ticket_sys_id}")
        else:
            logging.error(f"Failed to resolve ticket: {response.status_code} - {response.text}")
            print(f"Failed to resolve ticket: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error while resolving ticket: {e}")
        print(f"Error while resolving ticket: {e}")

def check_maintenance_window():
    """Check if the current time is within the maintenance window."""
    current_time = datetime.now()
    if current_time.weekday() == 1 and 6 <= current_time.hour < 20:
        print("Within maintenance window")
        return True
    print("Outside maintenance window")
    return True

def patch_server(hostname, username, password):
    """Perform patching on the server."""
    try:
        # Initialize SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Connect to the remote server
        logging.info(f"Connecting to the remote server {hostname}...")
        print(f"Connecting to the remote server {hostname}...")
        client.connect(hostname, username=username, password=password)
        logging.info(f"Connection to {hostname} successful!")
        print(f"Connection to {hostname} successful!")

        # Pre-patch: Close unnecessary services
        services_to_stop = ["apache2"]  # Replace with actual service names
        for service in services_to_stop:
            logging.info(f"Stopping service {service} on {hostname}...")
            print(f"Stopping service {service} on {hostname}...")
            stdin, stdout, stderr = client.exec_command(f"sudo systemctl stop {service}")
            stdin.write(password + "\n")
            stdin.flush()
            stdout.channel.recv_exit_status()  # Wait for the command to complete
            error = stderr.read().decode()
            if error:
                logging.error(f"Error stopping service {service}: {error}")
                print(f"Error stopping service {service}: {error}")
                create_ticket(f"Failed to stop service {service} on {hostname}. Error: {error}")
                return False

        # Commands for patch management
        commands = [
            "sudo apt update",
            "sudo apt upgrade -y",
            "sudo apt autoremove -y",
            "sudo apt autoclean"
        ]
        for command in commands:
            logging.info(f"Executing: {command}")
            print(f"Executing: {command}")
            stdin, stdout, stderr = client.exec_command(command)
            # Provide the sudo password if needed
            if "sudo" in command:
                stdin.write(password + "\n")
                stdin.flush()
            output = stdout.read().decode()
            error = stderr.read().decode()
            print(output)
            logging.info(output)
            if "warning" in error.lower():
                logging.warning(f"Warning during {command}: {error}")
                print(f"Warning during {command}: {error}")
            elif error:
                logging.error(f"Error during {command}: {error}")
                print(f"Error during {command}: {error}")
                create_ticket(f"Failed to execute '{command}' on {hostname}. Error: {error}")
                return False

        # Post-patch: Reboot the server
        logging.info(f"Rebooting the server {hostname} after patching...")
        print(f"Rebooting the server {hostname} after patching...")
        stdin, stdout, stderr = client.exec_command("sudo systemctl restart apache2")
        stdin.write(password + "\n")
        stdin.flush()
        stdout.channel.recv_exit_status()  # Wait for the command to complete
        error = stderr.read().decode()
        if error:
            logging.error(f"Error during post-patch: {error}")
            print(f"Error during post-patch: {error}")
            create_ticket(f"Failed during post-patch on {hostname}. Error: {error}")
            return False

        logging.info(f"Patch management for {hostname} completed successfully!")
        print(f"Patch management for {hostname} completed successfully!")
        return True
    except Exception as e:
        logging.error(f"Error on {hostname}: {e}")
        print(f"Error on {hostname}: {e}")
        create_ticket(f"Unexpected error on {hostname}: {e}")
        return False
    finally:
        # Close the SSH connection
        client.close()
        logging.info(f"Disconnected from the remote server {hostname}.")
        print(f"Disconnected from the remote server {hostname}.")

def patch_management():
    # Retrieve change request from ServiceNow
    change_request_id = get_change_request()
    if not change_request_id:
        print("No change request available. Exiting.")
        return

    # Load server details from CSV
    df = pd.read_csv('maintenance_window.csv')
    report = []
    for index, row in df.iterrows():
        hostname = row['Hostname']
        owner = row['Owner']
        username = row['Username']
        password = row['Password']
        print(f"Processing server: {hostname}")
        if check_maintenance_window():
            if patch_server(hostname, username, password):
                logging.info(f"Patch successful for {hostname}")
                print(f"Patch successful for {hostname}")
                report.append({"Hostname": hostname, "Status": "Success"})
            else:
                logging.error(f"Patch failed for {hostname}")
                print(f"Patch failed for {hostname}")
                report.append({"Hostname": hostname, "Status": "Failed"})
        else:
            logging.info(f"Skipping {hostname} as it is outside the maintenance window")
            print(f"Skipping {hostname} as it is outside the maintenance window")

    # Save the report to an Excel file
    report_df = pd.DataFrame(report)
    report_df.to_excel('patch_management_report.xlsx', index=False)
    print("Patch management report saved to patch_management")
    if change_request_id and check_maintenance_window() :
        resolve_ticket(change_request_id)
        print(f"Change request {change_request_id} resolved.")

if __name__ == "__main__":
    patch_management()
