"""
Docstring for app.services.rfid.controller
This module will be used for custom logic.
"""

from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
from smartx_rfid.dispatcher import EventDispatcher
from app.core import DISPATCHER_PATH, EXAMPLES_DISPATCHER_PATH
from .integration import Integration
import asyncio
from app.core import settings
import logging
from app.services.license import license_manager
from smartx_rfid.schemas.tag import WriteTagValidator
from .default_configs import AVAILABLE_DEVICES
from smartx_rfid.models.users import Users
from smartx_rfid.smtx_db import SmtxDb
from datetime import datetime
from copy import deepcopy


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList, integration: Integration):
		self.tags = tags
		self.devices = devices
		self.integration = integration
		self.dispatcher = EventDispatcher(
			dispatches_path=DISPATCHER_PATH,
			example_path=EXAMPLES_DISPATCHER_PATH,
		)
		self.write_list: dict = {}

		# TESTS
		self.current_device = None
		self.current_config = None
		self.tests = {}

		self.smtx_db = SmtxDb(settings.DATABASE_URL)  # Store the db_manager for user retrieval

	# [ EVENTS ]
	def on_event(self, name: str, event_type: str, event_data):
		logging.info(f'[ EVENT ] {name} - {event_type}: {event_data}')

		if event_type in self.tests:
			self.tests[event_type] = True

		if event_type == 'receive':
			if event_data.startswith('#POWER'):
				source = event_data.split(':')[1].strip()
				if source == 'USB' and 'usb_power_source' in self.tests:
					self.tests['usb_power_source'] = True
				elif source == 'EXT' and 'ext_power_source' in self.tests:
					self.tests['ext_power_source'] = True

	# [ Reading Events ]
	def on_start(self, name: str):
		logging.info(f'[ START ] {name}')
		if settings.CLEAR_ON_START:
			self.tags.remove_tags_by_device(device=name)

	def on_stop(self, name: str):
		logging.info(f'[ STOP ] {name}')

	# [ Tag Events ]
	def on_new_tag(self, name: str, tag: dict):
		logging.info(f'[ TAG ] {name} - {tag}')
		if not license_manager.validate_license():
			return
		self.tests['tag'] = True
		self.read_ant_test_event(tag.get('ant', 0))

	def on_existing_tag(self, name: str, tag: dict):
		asyncio.create_task(self.check_target(tag))
		self.read_ant_test_event(tag.get('ant', 0))

	def read_ant_test_event(self, ant):
		field = f'read_ant_{ant}'
		if field in self.tests:
			self.tests[field] = True

	# [ WRITE LIST ]
	def create_write_list_prefix(self, epcs: list, prefix: str):
		self.clear_write_list()
		for epc in epcs:
			target = f'{prefix}{epc[len(prefix):]}'
			current_tag = self.tags.get_by_identifier(epc)
			if current_tag:
				self.add_to_write_list(current_tag, target)
			else:
				logging.error(f'Epc: {epc} not in tags, skipping...')
		return self.write_list

	def add_to_write_list(self, tag: dict, target: str):
		self.write_list[tag.get('tid')] = {
			'target': target.lower(),
			'original_epc': tag.get('epc'),
		}
		tag['target'] = target
		logging.info(f"Added tag {tag.get('tid')} to write list with target {tag.get('target')}")
		self.on_event(name='write_list', event_type='add_to_write_list', event_data=tag)

	def remove_from_write_list(self, tag: dict):
		tid = tag.get('tid')
		if tid in self.write_list:
			logging.info(f'Removed tag {tid} from write list')
			self.on_event(
				name='write_list',
				event_type='remove_from_write_list',
				event_data={**tag, 'original_epc': self.write_list[tid]['original_epc']},
			)
			del self.write_list[tid]
			if not self.write_list:
				logging.info('Write list is now empty')
				self.on_event(name='write_list', event_type='write_list_empty', event_data={})
				return True
		return False

	def clear_write_list(self):
		self.write_list.clear()
		logging.info('Cleared write list')
		self.on_event(name='write_list', event_type='write_list_cleared', event_data={})

	async def check_target(self, tag: dict):
		target = tag.get('target')
		if not target:
			return
		if tag.get('epc') == tag.get('target'):
			logging.info(f"Tag {tag.get('tid')} already has target EPC, removing from write list")
			tag['target'] = None
			self.remove_from_write_list(tag)
			return
		await self.devices.write_epc(
			device_name=tag.get('device'),
			write_tag=WriteTagValidator(
				target_identifier='tid',
				target_value=tag.get('tid'),
				new_epc=tag.get('target'),
				password='00000000',
			),
		)

	# [ TEST ]
	def reset_tests(self):
		self.current_device = None
		self.tests = {}
		logging.info('Reset tests to default values')

	async def set_test_device(self, device_name: str, config: dict = None):
		if device_name not in AVAILABLE_DEVICES:
			logging.error(f'Device {device_name} is not available for testing')
			return False
		self.current_device = device_name
		current_device = self.devices.get_devices()
		for device in current_device:
			await self.devices.delete_device_config(device)

		default_config: dict = deepcopy(AVAILABLE_DEVICES.get(device_name, {}))
		if config is not None:
			await self.devices.create_device_config(device_name, config)
			self.current_config = config
		else:
			config = default_config.get('config', {})
			await self.devices.create_device_config(device_name, config)
			self.current_config = config
		self.tests = default_config.get('tests', {})

		return True

	def validate_tests(self):
		if not self.current_device:
			return False
		for test, passed in self.tests.items():
			if not passed:
				return False
		return True

	# USER
	def get_user_by_username(self, username: str):
		try:
			with self.smtx_db.db_manager.get_session() as session:
				result = session.query(Users).filter_by(username=username).first()
				return result.to_dict() if result else None
		except Exception as e:
			logging.error(f'Error fetching user with username {username}: {e}')
			return None

	def get_reader_type_hostname(self, reader_type: str, serial_number: str = None):
		if reader_type not in AVAILABLE_DEVICES:
			logging.error(f'Reader type {reader_type} is not available')
			return None

		reader_model = AVAILABLE_DEVICES[reader_type]['config'].get('READER')
		if reader_model == 'X714':
			return serial_number
		else:
			reader = self.devices.get_device(reader_type)
			if not reader:
				logging.error(f'Reader type {reader_type} not found in devices')
				return None
			hostname = reader.hostname or reader.ip or reader.ip_address or reader.serial_number
			if not hostname:
				logging.error(f'No hostname found for reader type {reader_type}')
				return None
			return hostname

	def mark_tested(self, user_info: dict):
		if not self.current_device:
			msg = 'Sem dispositivo definido para teste. Não é possível marcar como testado.'
			logging.error(msg)
			return False, msg
		if not self.validate_tests():
			msg = f'Nem todos os testes foram aprovados para o dispositivo {self.current_device}. Não é possível marcar como testado.'
			logging.error(msg)
			return False, msg
		try:
			serial_number = self.devices.get_device_info(self.current_device)[0].get(
				'serial_number'
			)
			if not serial_number or serial_number.lower() == 'unknown':
				msg = f'Serial number não encontrado para o dispositivo {self.current_device}. Não é possível marcar como testado.'
				logging.error(msg)
				return False, msg
			reader = self.smtx_db.get_reader_by_serial(serial_number)
			if not reader:
				reader_type = (
					AVAILABLE_DEVICES.get(self.current_device, {}).get('config', {}).get('READER')
				)
				reader_types = self.smtx_db.get_reader_types()
				hostname = self.get_reader_type_hostname(reader_type, serial_number)
				for r in reader_types:
					if r.get('name') == reader_type:
						success, msg = self.smtx_db.add_reader(r.get('id'), serial_number, hostname)
						if not success:
							logging.error(
								f'Erro ao adicionar o leitor {self.current_device} com serial {serial_number}: {msg}'
							)
							return False, msg

						# reload reader
						reader = self.smtx_db.get_reader_by_serial(serial_number)
						break
				else:
					msg = f'Tipo de leitor {reader_type} não encontrado no banco de dados. Não é possível marcar como testado.'
					logging.error(msg)
					return False, msg

			test_info = {
				'timestamp': datetime.now().astimezone().isoformat(),
				'tested_by': user_info,
				'tests': self.tests,
				'reader_type': self.current_device,
				'reader_config': self.current_config,
				'reader_info': {
					k: v
					for k, v in reader.items()
					if k not in ['created_at', 'updated_at', 'can_generate_license', 'test_info']
				},
			}
			return self.smtx_db.set_test_info_for_reader(reader.get('id'), test_info)
		except Exception as e:
			msg = f'Erro ao marcar o dispositivo {self.current_device} como testado: {e}'
			logging.error(msg)
			return False, msg
