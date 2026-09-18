from app.services import rfid_manager
import logging
import asyncio
from app.core import settings
from datetime import datetime, timedelta


async def connect_on_startup():
	"""Connect to RFID devices on application startup."""
	logging.info('Connecting to RFID devices on startup...')

	# Attempt initial connect once, then monitor the connection tasks. If all
	# tasks finish (e.g., due to errors), attempt reconnect with a small backoff.
	try:
		await rfid_manager.devices.connect_devices()
	except Exception as e:
		logging.error(f'Error during initial devices.connect_devices(): {e}')

	backoff_seconds = 1
	while True:
		# get current connect tasks
		tasks = getattr(rfid_manager.devices, '_connect_tasks', []) or []
		# If there are no tasks or all are done, attempt to reconnect after backoff
		if not tasks or all(t.done() for t in tasks):
			await asyncio.sleep(backoff_seconds)
			try:
				await rfid_manager.devices.connect_devices()
			except Exception as e:
				logging.error(f'Error reconnecting devices: {e}')
				# increase backoff up to a limit to avoid tight restart loops
				backoff_seconds = min(backoff_seconds * 2, 60)
				continue
			# reset backoff on successful start
			backoff_seconds = 1
		else:
			# tasks are running; check again later
			await asyncio.sleep(1)


async def clear_old_tags():
	while True:
		if settings.CLEAR_OLD_TAGS_INTERVAL is None or settings.CLEAR_OLD_TAGS_INTERVAL <= 0:
			await asyncio.sleep(600)
			continue
		await asyncio.sleep(
			1 if settings.CLEAR_OLD_TAGS_INTERVAL < 10 else settings.CLEAR_OLD_TAGS_INTERVAL / 2
		)
		if len(rfid_manager.tags) == 0:
			continue

		timestamp = datetime.now() - timedelta(seconds=settings.CLEAR_OLD_TAGS_INTERVAL)
		removed_tags = rfid_manager.tags.remove_tags_before_timestamp(timestamp)
		if removed_tags:
			logging.info(f'Removed {len(removed_tags)} old tags: {removed_tags}')
			for tag in removed_tags:
				rfid_manager.on_event(
					name=tag.get('device', 'unknown'),
					event_type='tag_removed',
					event_data=tag,
				)
