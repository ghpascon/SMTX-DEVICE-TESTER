from fastapi import Request
from app.services import auth_manager


def get_user(request: Request) -> dict:
	token = request.cookies.get('Authorization') or request.headers.get('Authorization')
	valid = False
	user = None
	if token:
		if token.startswith('Bearer '):
			token = token[7:]  # Remove 'Bearer ' prefix
		valid, user = auth_manager.decode_token(token)
	return user if valid else None


def validate_role(request: Request, required_role: str | list) -> bool:
	user = get_user(request)
	if not user:
		return False
	roles = user.get('roles', [])
	if isinstance(required_role, str):
		return required_role in roles
	return any(role in roles for role in required_role)
