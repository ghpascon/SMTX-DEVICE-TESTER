from .rfid._main import RfidManager
from app.core import DEVICES_PATH, EXAMPLE_PATH
from smartx_rfid.auth import AuthManager

rfid_manager = RfidManager(devices_path=DEVICES_PATH, example_path=f'{EXAMPLE_PATH}/devices')

auth_manager = AuthManager(expiration_minutes=120)
