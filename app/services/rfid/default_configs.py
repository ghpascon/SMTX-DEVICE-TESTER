AVAILABLE_DEVICES = {
	'XPAD': {
		'tests': {
			'connection': {'state': False, 'mandatory': True},
			'reading': {'state': False, 'mandatory': True},
			'tag': {'state': False, 'mandatory': True},
			'serial_number': {'state': False, 'mandatory': True},
		},
		'config': {
			'xpad': {
				'READER': 'X714',
				'BUZZER': True,
				'SESSION': 0,
				'START_READING': True,
				'READ_POWER': 20,
			}
		},
	},
	'X714': {
		'tests': {
			'connection': {'state': False, 'mandatory': True},
			'reading': {'state': False, 'mandatory': True},
			'tag': {'state': False, 'mandatory': True},
			'serial_number': {'state': False, 'mandatory': True},
			'read_ant_1': {'state': False, 'mandatory': True},
			'read_ant_2': {'state': False, 'mandatory': False},
			'read_ant_3': {'state': False, 'mandatory': False},
			'read_ant_4': {'state': False, 'mandatory': False},
			'usb_power_source': {'state': False, 'mandatory': False},
			'ext_power_source': {'state': False, 'mandatory': True},
		},
		'config': {
			'serial': {
				'READER': 'X714',
				'BUZZER': True,
				'SESSION': 0,
				'START_READING': True,
				'READ_POWER': 20,
				'ACTIVE_ANT': [1, 2, 3, 4],
			},
			'tcp': {
				'READER': 'X714',
				'CONNECTION_TYPE': 'TCP',
				'IP': '192.168.1.101',
				'BUZZER': True,
				'SESSION': 0,
				'START_READING': True,
				'READ_POWER': 20,
				'ACTIVE_ANT': [1, 2, 3, 4],
			},
		},
	},
	'R700': {
		'tests': {
			'connection': {'state': False, 'mandatory': True},
			'reading': {'state': False, 'mandatory': True},
			'tag': {'state': False, 'mandatory': True},
			'serial_number': {'state': False, 'mandatory': True},
			'read_ant_1': {'state': False, 'mandatory': True},
			'read_ant_2': {'state': False, 'mandatory': True},
			'read_ant_3': {'state': False, 'mandatory': True},
			'read_ant_4': {'state': False, 'mandatory': True},
		},
		'config': {
			'r700': {
				'READER': 'R700_IOT',
				'IP': '192.168.1.101',
				'USERNAME': 'root',
				'PASSWORD': 'impinj',
				'START_READING': True,
				'SESSION': 0,
				'ACTIVE_ANT': [1, 2, 3, 4],
				'READ_POWER': 20,
				'READ_RSSI': -80,
				'SEARCH_MODE': 'single-target',
				'RF_MODE': 4,
				'GPI_START': False,
				'FIRMWARE_VERSION': '8.4.1',
			},
		},
	},
}
