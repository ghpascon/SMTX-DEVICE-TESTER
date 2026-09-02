AVAILABLE_DEVICES = {
	'XPAD': {
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
			'READ_POWER': 20,
		},
	},
	'X714': {
		'tests': {
			'connection': False,
			'reading': False,
			'tag': False,
			'serial_number': False,
			'read_ant_1': False,
			'read_ant_2': False,
			'read_ant_3': False,
			'read_ant_4': False,
			'usb_power_source': False,
			'ext_power_source': False,
		},
		'config': {
			'READER': 'X714',
			'BUZZER': True,
			'SESSION': 0,
			'START_READING': True,
			'READ_POWER': 20,
			'ACTIVE_ANT': [1, 2, 3, 4],
		},
	},
}
