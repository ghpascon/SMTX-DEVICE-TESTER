"""
poetry run python build_exe.py
"""

# Remove build directory after completion
import shutil
import os

import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all, collect_submodules
from importlib.metadata import distributions
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# === USER CONFIGURATION ===
EXE_PATH = 'TEMP'  # Base folder to store builds
ENTRY_SCRIPT = 'main.py'  # Main script
APP_NAME = 'main'  # Final executable name
EXTRA_FOLDERS = [
	'app',
	'examples',
	'docs',
]  # Extra folders to include in the build

# === Icon path (platform dependent) ===
if os.name == 'nt':
	icon_file = 'logo.ico'
else:
	icon_file = 'logo.png'  # PyInstaller on Linux usually uses PNG

try:
	icon_path = os.path.abspath(os.path.join('app', 'static', 'icons', icon_file))
except Exception as e:
	logging.info(f'[WARN] Could not find icon file: {e}')
	icon_path = None

# === Define output folder ===
output_dir = EXE_PATH
work_dir = os.path.join(output_dir, 'build')

# Create folders if they don't exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(work_dir, exist_ok=True)

# === Extra hidden imports ===
manual_hidden = [
	'uvicorn.config',
	'uvicorn.main',
	'uvicorn.loops.auto',
]

# Pacotes manuais que às vezes não são detectados automaticamente
manual_packages = [
	'smartx_rfid',
]


# === Collect submodules for serial and serial_asyncio ===
def safe_collect_submodules(pkg_name):
	try:
		subs = collect_submodules(pkg_name)
		logging.info(f'[INFO] Found {pkg_name} submodules: {subs}')
		return subs
	except Exception as e:
		logging.info(f'[WARN] Could not collect {pkg_name} submodules: {e}')
		return []


serial_tools_hidden = safe_collect_submodules('serial.tools')
serial_asyncio_hidden = safe_collect_submodules('serial_asyncio')

# Merge all hidden imports
all_manual_hidden = manual_hidden + serial_tools_hidden + serial_asyncio_hidden


# === Helper functions ===
def get_installed_packages():
	packages = set()

	for dist in distributions():
		name = dist.metadata.get('Name')

		if not name:
			continue

		# NÃO transformar automaticamente
		packages.add(name)

	return sorted(packages)


def collect_all_from_packages(packages):
	datas = []
	binaries = []
	hiddenimports = set()

	for pkg in packages:
		try:
			logging.info(f'[INFO] Collecting {pkg}')

			d, b, h = collect_all(pkg)

			datas.extend(d)
			binaries.extend(b)
			hiddenimports.update(h)

			# Garante módulos importados dinamicamente
			try:
				subs = collect_submodules(pkg)
				hiddenimports.update(subs)
			except Exception:
				pass

		except Exception as e:
			logging.info(f'[WARN] {pkg}: {e}')

	return datas, binaries, sorted(hiddenimports)


# === Read packages from pyproject.toml ===
packages = get_installed_packages()
datas, binaries, hiddenimports = collect_all_from_packages(packages)

# Tenta coletar explicitamente pacotes críticos que podem não
# corresponder exatamente ao nome da distribuição (ex.: smartx-rfid)
try:
	m_datas, m_binaries, m_hidden = collect_all_from_packages(manual_packages)
	datas.extend(m_datas)
	binaries.extend(m_binaries)
	hiddenimports = sorted(set(hiddenimports).union(set(m_hidden)))
except Exception as e:
	logging.info(f'[WARN] Could not collect manual packages: {e}')


# === Add extra folders as data (cross-platform) ===
extra_data = []
for folder in EXTRA_FOLDERS:
	os.makedirs(folder, exist_ok=True)
	if os.path.exists(folder):
		if os.name == 'nt':
			# Windows: use ; as separator
			extra_data.append(f'{folder}{os.sep};{folder}')
		else:
			# Linux: use : as separator
			extra_data.append(f'{folder}{os.sep}:{folder}')


# === Run PyInstaller ===

# === Platform-specific options ===
opts = [
	ENTRY_SCRIPT,
	f'--name={APP_NAME}',
	'--onefile',
	f'--icon={icon_path}' if icon_path else '',
	f'--distpath={output_dir}',
	f'--workpath={work_dir}',
	'--noconfirm',
]
if os.name == 'nt':
	opts.append('--noconsole')

# Hidden imports
opts += [f'--hidden-import={h}' for h in sorted(set(hiddenimports + all_manual_hidden))]

# Datas
opts += [f'--add-data={src}{os.pathsep}{dst}' for src, dst in datas]

# Binaries
opts += [f'--add-binary={src}{os.pathsep}{dst}' for src, dst in binaries]

# Extra folders
opts += [f'--add-data={d}' for d in extra_data]

PyInstaller.__main__.run(opts)


try:
	shutil.rmtree(work_dir)
	logging.info(f'[INFO] Removed build directory: {work_dir}')
except Exception as e:
	logging.info(f'[WARN] Could not remove build directory: {e}')
