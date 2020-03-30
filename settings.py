
from dotenv import load_dotenv
from pathlib import Path  
import os
from orkg import ORKG

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Setup the ORKG API, optionally with user credentials 
def init_orkg():
    creds = ()
    if os.getenv('ORKG_API_CREDS_EMAIL') != '' and os.getenv('ORKG_API_CREDS_PASSWORD') != '':
        creds = (os.getenv('ORKG_API_CREDS_EMAIL'), os.getenv('ORKG_API_CREDS_PASSWORD'))
        
    return ORKG(host=os.getenv('ORKG_API'), creds=creds)
