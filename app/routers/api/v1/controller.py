from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
from smartx_rfid.utils.path import get_prefix_from_path
from app.schemas.write_list import WriteListPrefixModel
from app.services import rfid_manager
from app.services.rfid.default_configs import AVAILABLE_DEVICES
from app.core.user import get_user
import json
from app.core import settings

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
	'/controller_info',
	summary='Get RFID info',
)
async def controller_info():
	controller = rfid_manager.controller

	# Monta dict nome: tipo para atributos e métodos públicos
	info = {}
	for name in dir(controller):
		if name.startswith('_'):
			continue
		attr = getattr(controller, name)
		if callable(attr):
			info[name] = f'function ({type(attr).__name__})'
		else:
			info[name] = type(attr).__name__
	return info


# [WRITE LIST]
@router.get(
	'/get_write_list',
	summary='Get write list from RFID controller',
)
async def get_write_list():
	return rfid_manager.controller.write_list


@router.post(
	'/create_write_list_prefix',
	summary='Write a list of tags to the RFID controller',
)
async def create_write_list_prefix(write_list: WriteListPrefixModel):
	write_list = rfid_manager.controller.create_write_list_prefix(
		write_list.epcs, write_list.prefix
	)
	if not write_list:
		return JSONResponse(
			status_code=400, content={'message': 'Tags not found in current tag list'}
		)
	return write_list


@router.post(
	'/add_to_write_list/{tid}/{target}',
	summary='Add a tag to the write list in the RFID controller',
)
async def add_to_write_list(tid: str, target: str):
	tag = rfid_manager.controller.tags.get_by_identifier(tid.lower(), identifier_type='tid')
	if not tag:
		return JSONResponse(status_code=404, content={'message': f'Tag {tid} not found'})
	rfid_manager.controller.add_to_write_list(tag, target)
	return {'message': f'Tag {tid} added to write list with target {target} successfully'}


@router.post(
	'/clear_write_list',
	summary='Clear the write list in the RFID controller',
)
async def clear_write_list():
	rfid_manager.controller.clear_write_list()
	return {'message': 'Write list cleared successfully'}


@router.delete(
	'/delete_tid_from_write_list/{tid}',
	summary='Delete a tag from the write list in the RFID controller',
)
async def delete_tid_from_write_list(tid: str):
	tag = rfid_manager.controller.tags.get_by_identifier(tid.lower(), identifier_type='tid')
	if not tag:
		return JSONResponse(status_code=404, content={'message': f'Tag {tid} not found'})
	success = rfid_manager.controller.remove_from_write_list(tag)
	if success:
		return {'message': f'Tag {tid} removed from write list successfully'}
	else:
		return JSONResponse(
			status_code=400, content={'message': f'Failed to remove tag {tid} from write list'}
		)


# [ TESTS ]
@router.get(
	'/get_available_devices',
	summary='Get available devices for testing',
)
def get_available_devices():
	return list(AVAILABLE_DEVICES.keys()) or []


@router.get(
	'/get_available_device_configs/{device_name}',
	summary='Get available device configs for testing',
)
def get_available_device_configs(device_name: str):
	if device_name not in AVAILABLE_DEVICES:
		return JSONResponse(
			status_code=400,
			content={'message': f'Device {device_name} is not available for testing'},
		)
	return AVAILABLE_DEVICES[device_name].get('config', {})


@router.get(
	'/get_current_tests',
	summary='Get current device for testing',
)
def get_current_tests():
	return {
		'current_device': rfid_manager.controller.current_device,
		'tests': rfid_manager.controller.tests,
	}


@router.post(
	'/set_test_device/{device_name}',
	summary='Set the device for testing',
)
async def set_test_device(device_name: str, device_config: dict | str = Form(None)):
	if isinstance(device_config, str):
		try:
			device_config = json.loads(device_config)
		except Exception as e:
			return JSONResponse(
				status_code=400,
				content={'message': f'Invalid device config format: {e}'},
			)
	if device_name not in AVAILABLE_DEVICES:
		return JSONResponse(
			status_code=400,
			content={'message': f'Device {device_name} is not available for testing'},
		)

	success = await rfid_manager.controller.set_test_device(device_name, device_config)
	if success:
		return {'message': f'Device {device_name} set for testing successfully'}
	else:
		return JSONResponse(
			status_code=500, content={'message': f'Failed to set device {device_name} for testing'}
		)


@router.delete(
	'/reset_tests',
	summary='Reset the tests to default values',
)
async def reset_tests():
	rfid_manager.controller.reset_tests()
	return {'message': 'Tests reset to default values successfully'}


@router.get(
	'/validate_tests',
	summary='Validate the current tests in the RFID controller',
)
async def validate_tests():
	return rfid_manager.controller.validate_tests()


@router.post(
	'/mark_tested',
	summary='Mark a test as passed for a specific serial number',
)
async def mark_tested(request: Request):
	user_info = get_user(request)
	if not user_info:
		return JSONResponse(
			status_code=401,
			content={'message': 'Unauthorized: User information not found'},
		)
	# MARK TESTED
	success, data = rfid_manager.controller.mark_tested(user_info)
	if not success:
		return JSONResponse(
			status_code=400,
			content={'message': data},
		)
	# PRINT LABEL
	serial = str(data)
	success, data = rfid_manager.devices.print(
		settings.PRINTER_NAME, settings.ZPL.format(serial=serial)
	)
	if not success:
		return JSONResponse(
			status_code=500,
			content={'message': f'Falha ao imprimir etiqueta {serial}: {data}'},
		)
	return {'message': 'Etiqueta impressa e leitor marcado como testado com sucesso'}
