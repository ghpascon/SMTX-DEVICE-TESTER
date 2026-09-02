from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core import templates

router = APIRouter(prefix='', tags=['Pages'])


@router.get('/auth', response_class=HTMLResponse)
async def auth(request: Request):
	return templates.TemplateResponse(
		'pages/auth/main.html',
		{'request': request, 'title': 'Autenticação', 'include_header': False},
		media_type='text/html; charset=utf-8',
	)
