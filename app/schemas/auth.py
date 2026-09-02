from pydantic import BaseModel, Field


class AuthSchema(BaseModel):
	username: str = Field(..., description='Username for authentication')
	password: str = Field(..., description='Password for authentication')


class AddUserSchema(AuthSchema):
	role: str = Field(..., description='Role of the user (e.g. admin, user)')
	email: str = Field(..., description='Email address of the user')
