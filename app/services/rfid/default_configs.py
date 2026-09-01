import logging
from copy import deepcopy

AVAILABLE_DEVICES = ['XPAD']

DEFAULT_XPAD_CONFIG = {
	'tests': {
		'connection': False,
		'reading': False,
		'tag': False,
		'serial_number': False,
	},
	'config': {
		'READER': 'X714',
		'BUZZER': True,
		'SESSION': 0,
		'START_READING': True,
		'READ_POWER': 25,
	},
}


def get_default_config(device_name: str):
	if device_name == 'XPAD':
		return deepcopy(DEFAULT_XPAD_CONFIG)
	else:
		logging.error(f'Device {device_name} is not available for testing')
		return None
