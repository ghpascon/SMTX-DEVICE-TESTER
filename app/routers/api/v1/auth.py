import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from smartx_rfid.utils.path import get_prefix_from_path

from app.schemas.auth import AuthSchema
from app.services import auth_manager
from app.core.user import get_user
from app.services import rfid_manager

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.post('/login')
async def login(request: Request, auth_data: AuthSchema):
	try:
		user: dict = rfid_manager.controller.get_user_by_username(auth_data.username)
		if not user:
			return JSONResponse(status_code=401, content={'error': 'Usuário não encontrado'})
		if not auth_manager.verify_password(auth_data.password, user.get('password_hash')):
			return JSONResponse(status_code=401, content={'error': 'Senha inválida'})
		# Generate and return a token or session here
		token = auth_manager.create_token(
			{
				'user_id': user.get('id'),
				'username': user.get('username'),
				'roles': user.get('role').split(','),  # Convert comma-separated roles into a list
			}
		)
		# Add token to the response headers
		response = JSONResponse(
			status_code=200, content={'message': 'Login realizado com sucesso', 'token': token}
		)
		response.set_cookie(
			key='Authorization',
			value=f'Bearer {token}',
			secure=False,
		)
		return response
	except Exception as e:
		logging.error(f'Error during login: {e}')
		return JSONResponse(status_code=500, content={'error': f'Falha ao realizar login: {e}'})


@router.get('/me')
async def get_current_user(request: Request):
	user = get_user(request)
	if not user:
		return JSONResponse(status_code=401, content={'error': 'Não autorizado'})
	return JSONResponse(
		content={
			'user_id': user.get('user_id'),
			'username': user.get('username'),
			'roles': user.get('roles'),
		}
	)


@router.post('/logout')
async def logout():
	response = JSONResponse(status_code=200, content={'message': 'Logout realizado com sucesso'})
	response.delete_cookie(key='Authorization')
	return response
