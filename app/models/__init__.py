"""
Model auto-discovery module for SMARTX Connector.

This module automatically discovers and imports all SQLAlchemy models
from the models package, providing a centralized access point.
"""

import inspect
import pkgutil
from typing import List, Type
import importlib

try:
	from sqlalchemy.orm import DeclarativeBase
except ImportError:
	from sqlalchemy.ext.declarative import declarative_base

	DeclarativeBase = declarative_base()

# Import all model modules to ensure they're registered
from smartx_rfid.models import Base, BaseMixin

EXTERNAL_MODEL_MODULES: List[str] = [
	'smartx_rfid.models',  # imports Base, BaseMixin, etc.
	'smartx_rfid.models.orders',  # imports ProductsOrders, ProductsType, ReadersType …
	'smartx_rfid.models.users',
	'smartx_rfid.models.license',
]


def _load_external_models() -> List[Type]:
	"""Import every SQLAlchemy model class found in EXTERNAL_MODEL_MODULES."""
	discovered: List[Type] = []
	current_globals = globals()

	for module_path in EXTERNAL_MODEL_MODULES:
		try:
			module = importlib.import_module(module_path)
		except ImportError as exc:
			print(f"[models] Could not import '{module_path}': {exc}")
			continue

		for attr_name in dir(module):
			attr = getattr(module, attr_name)
			if (
				inspect.isclass(attr)
				and hasattr(attr, '__tablename__')
				and hasattr(attr, '__table__')
			):
				discovered.append(attr)
				# Expose the class in this package's namespace
				current_globals[attr_name] = attr
			elif inspect.isclass(attr) or not inspect.isroutine(attr):
				# Also re-export non-model symbols (Base, BaseMixin, …)
				# only if they originate from the target module
				if getattr(attr, '__module__', None) == module_path:
					current_globals[attr_name] = attr

	return discovered


def get_all_models() -> List[Type]:
	"""
	Automatically discover and return all SQLAlchemy models with DeclarativeBase.

	Returns:
	    List[Type]: List of all discovered model classes
	"""
	models = _load_external_models()

	# Get current module
	current_module = inspect.getmodule(inspect.currentframe())
	current_package = current_module.__package__ if current_module else None

	if not current_package:
		return models

	# Iterate through all modules in the package
	for _, name, _ in pkgutil.iter_modules(__path__, current_package + '.'):
		try:
			module = __import__(name, fromlist=[''])

			# Inspect all attributes in the module
			for attr_name in dir(module):
				attr = getattr(module, attr_name)

				# Check if it's a class and has SQLAlchemy table attributes
				if (
					inspect.isclass(attr)
					and hasattr(attr, '__tablename__')
					and hasattr(attr, '__table__')
					and attr.__module__ == name
				):
					models.append(attr)

		except (ImportError, AttributeError):
			# Skip modules that can't be imported or don't have the expected structure
			continue

	return models
