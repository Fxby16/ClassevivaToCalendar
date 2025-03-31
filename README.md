# ClassevivaToCalendar
A Python script that loads your Classeviva calendar and adds the events to your Google Calendar.

## Python requirements
- Python 3.9 or higher
- `requests`
- `zoneinfo`
- `google-auth-oauthlib`
- `google-api-python-client`
- `google-auth-httplib2`
Install the required libraries using `pip install -r requirements.txt`.

## Credentials requirements
- A Google Cloud Platform project with the Google Calendar API enabled
- A Google Cloud Platform OAuth 2.0 client ID
- A Classeviva account

## Usage
1. Clone the repository
2. Install the required libraries
3. Create a new project on the Google Cloud Platform
4. Enable the Google Calendar API
5. Create a new OAuth 2.0 client ID
6. Download the client secret JSON file and save it as `credentials.json` in the repository folder
7. Create a file named `classeviva_credentials.json` in the repository folder with the following content:
```json
{
    "pass": "YOUR_CLASSEVIVA_PASSWORD",
    "uid": "YOUR_CLASSEVIVA_UID"
}
```
7. Run the script using `python3 main.py`
8. Follow the instructions to authenticate with Google
9. Wait for the script to finish