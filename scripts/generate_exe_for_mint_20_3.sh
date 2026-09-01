#!/usr/bin/env bash
set -euo pipefail

# generate_exe_for_mint_20_3.sh
# Creates a temporary Docker container (Linux Mint 20.3 preferred), copies
# the current repository into the container, installs Python 3.13 + Poetry,
# runs `scripts/build_exe.py` and on success copies the produced `main`
# executable into the host `build/` folder. The container (and image if
# pulled by this script) are removed at the end. All steps printed in English.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOST_BUILD_DIR="$PROJECT_ROOT/build"
CONTAINER_WORKDIR="/workspace"
BUILD_SCRIPT="scripts/build_exe.py"

IMAGES=(
	"linuxmintd/mint:20.3"
	"linuxmint/mint:20.3"
	"linuxmint/mint20.3"
	"linuxmint/mint"
	"ubuntu:20.04"
	"python:3.13-slim"
)

CONTAINER_NAME="xbridge_mint20_3_build_$(date +%s)"
SELECTED_IMAGE=""
IMAGE_PULLED=false
DOCKER_NETWORK="${DOCKER_NETWORK:-}"

# If the caller sets DOCKER_NETWORK (for example: DOCKER_NETWORK=host),
# we will pass it to `docker create` so the container can share the host
# network stack (useful when the host is already authenticated to a
# captive-portal network).
if [ -n "$DOCKER_NETWORK" ]; then
	DOCKER_NET_ARG="--network $DOCKER_NETWORK"
	echo "[INFO] Using Docker network: $DOCKER_NETWORK"
else
	DOCKER_NET_ARG=""
fi

echo "[1/8] Starting: Generate exe inside a temporary Docker container"

if ! command -v docker >/dev/null 2>&1; then
	echo "ERROR: Docker is not installed or not in PATH. Aborting."
	exit 1
fi

mkdir -p "$HOST_BUILD_DIR"

echo "[2/8] Looking for a suitable base image (prefers Linux Mint 20.3)..."
for IMG in "${IMAGES[@]}"; do
	echo "  Trying to pull image: $IMG"
	if docker pull "$IMG"; then
		SELECTED_IMAGE="$IMG"
		IMAGE_PULLED=true
		echo "  -> Selected image: $SELECTED_IMAGE"
		break
	else
		echo "  -> Could not pull $IMG, trying next candidate..."
	fi
done

if [ -z "$SELECTED_IMAGE" ]; then
	echo "ERROR: Could not pull any candidate images. Please check your network or Docker configuration."
	exit 1
fi

cleanup() {
	echo "[8/8] Cleaning up temporary Docker resources..."
	if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
		echo "  Removing container: $CONTAINER_NAME"
		docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
	fi
	if [ "$IMAGE_PULLED" = true ] && [ -n "$SELECTED_IMAGE" ]; then
		echo "  Removing image: $SELECTED_IMAGE"
		docker rmi -f "$SELECTED_IMAGE" >/dev/null 2>&1 || true
	fi
}

trap cleanup EXIT

echo "[3/8] Creating temporary container: $CONTAINER_NAME (image: $SELECTED_IMAGE)"
CONTAINER_ID=$(docker create --name "$CONTAINER_NAME" $DOCKER_NET_ARG -w "$CONTAINER_WORKDIR" -it "$SELECTED_IMAGE" bash)

echo "[4/8] Copying project files into container ($CONTAINER_WORKDIR)"
docker cp "$PROJECT_ROOT/." "$CONTAINER_ID":"$CONTAINER_WORKDIR"

echo "[5/8] Starting container"
docker start "$CONTAINER_ID" >/dev/null

# Attempt to prepare Python 3.13 + Poetry and run the build inside the container.
# If the chosen image cannot install Python 3.13, the script will fall back to
# using the official `python:3.13-slim` image.

run_build_in_container() {
	echo "[6/8] Preparing environment and running build inside container ($CONTAINER_NAME)"

	docker exec "$CONTAINER_NAME" bash -lc "set -eux;
		export DEBIAN_FRONTEND=noninteractive || true;
		echo 'Inside container: updating package lists';
		if command -v apt-get >/dev/null 2>&1; then apt-get update -y; fi;
		if command -v apt-get >/dev/null 2>&1; then \
			apt-get install -y --no-install-recommends ca-certificates curl wget git build-essential locales xz-utils libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev libncurses5-dev libgdbm-dev liblzma-dev || true; \
		fi;

		echo 'Attempting to install Python 3.11 via package manager';
		if command -v apt-get >/dev/null 2>&1 && apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils 2>/dev/null; then
			PY_BIN=python3.11;
		else
			echo 'Python 3.11 not available from apt; trying deadsnakes PPA (Ubuntu-based images)';
			if command -v add-apt-repository >/dev/null 2>&1 || apt-get install -y software-properties-common >/dev/null 2>&1; then
				add-apt-repository ppa:deadsnakes/ppa -y || true; apt-get update -y;
				if apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils 2>/dev/null; then
					PY_BIN=python3.11;
				else
					# Try fallbacks: 3.12 then 3.13
					if apt-get install -y python3.12 python3.12-venv python3.12-dev python3.12-distutils 2>/dev/null; then
						PY_BIN=python3.12;
					elif apt-get install -y python3.13 python3.13-venv python3.13-dev python3.13-distutils 2>/dev/null; then
						PY_BIN=python3.13;
					else
						echo 'PYTHON_NOT_AVAILABLE'; exit 3;
					fi;
				fi;
			else
				echo 'PYTHON_NOT_AVAILABLE'; exit 3;
			fi;
		fi;

		echo 'Using Python: '; \$PY_BIN --version || true;

		echo 'Installing pip for the chosen Python';
		curl -sS https://bootstrap.pypa.io/get-pip.py | \$PY_BIN - || true;

		echo 'Installing Poetry';
		curl -sSL https://install.python-poetry.org | \$PY_BIN - || true;
		# Prefer explicit poetry binary rather than exporting to PATH
		if [ -x /root/.local/bin/poetry ]; then \
			POETRY_BIN=/root/.local/bin/poetry; \
		elif command -v poetry >/dev/null 2>&1; then \
			POETRY_BIN=poetry; \
		else \
			POETRY_BIN=; \
		fi;

		cd $CONTAINER_WORKDIR;
		echo 'Configuring Poetry to avoid virtualenvs (system environment)';
		if [ -n "\$POETRY_BIN" ]; then \$POETRY_BIN config virtualenvs.create false --local || true; fi;

		echo 'Installing project dependencies with Poetry (may take several minutes)';
		if [ -n "\$POETRY_BIN" ]; then \
			\$POETRY_BIN install --no-interaction || true; \
			# Ensure PyInstaller is available (it may be a dev dependency)
			if ! \$PY_BIN -c "import PyInstaller" >/dev/null 2>&1; then \
				echo 'PyInstaller not found after Poetry install, installing via pip'; \
				\$PY_BIN -m pip install pyinstaller || true; \
			fi; \
		else \
			echo 'Poetry not available; trying pip install fallback (best-effort)'; \
			if [ -f pyproject.toml ]; then \
				echo 'pyproject.toml found; attempting pip install of direct dependencies is not implemented. Please run poetry manually inside the image.'; \
			fi; \
		fi;

		echo 'Running build script';
		if [ -n "\$POETRY_BIN" ]; then \
			\$POETRY_BIN run python $BUILD_SCRIPT || \$PY_BIN $BUILD_SCRIPT || exit 4; \
		else \
			\$PY_BIN $BUILD_SCRIPT || exit 4; \
		fi;

		echo 'Build finished inside container';
		exit 0
	"
}

	if run_build_in_container; then
	echo "[7/8] Build completed inside container. Copying artifact to host $HOST_BUILD_DIR"
	# Try to copy the expected artifact; build_exe.py places executable in TEMP/ by default
	if docker exec "$CONTAINER_NAME" bash -lc "test -f $CONTAINER_WORKDIR/TEMP/main" >/dev/null 2>&1; then
		echo "[7.1/8] Found artifact inside container. Verifying executable before copying..."
		echo "  Running ldd and a short runtime test inside the container (timeout 10s)"

		if docker exec "$CONTAINER_NAME" bash -lc "set -uo pipefail; \n  file $CONTAINER_WORKDIR/TEMP/main || true; \n  ldd $CONTAINER_WORKDIR/TEMP/main || true; \n  if ldd $CONTAINER_WORKDIR/TEMP/main 2>&1 | grep -q 'not found'; then echo 'MISSING_LIBS'; exit 5; fi; \n  if command -v timeout >/dev/null 2>&1; then timeout 10 $CONTAINER_WORKDIR/TEMP/main > $CONTAINER_WORKDIR/TEMP/main.run.log 2>&1 || true; RCODE=\$?; else $CONTAINER_WORKDIR/TEMP/main > $CONTAINER_WORKDIR/TEMP/main.run.log 2>&1 & PID=\$!; sleep 10; kill -0 \$PID >/dev/null 2>&1 && kill \$PID || true; wait \$PID 2>/dev/null || true; RCODE=\$?; fi; \n  echo RUNTIME_EXIT_CODE:\$RCODE; \n  tail -n 200 $CONTAINER_WORKDIR/TEMP/main.run.log || true; \n  if [ \$RCODE -ne 0 ] && [ \$RCODE -ne 124 ]; then echo 'RUNTIME_FAIL'; exit 6; fi; \n  exit 0"; then
			docker cp "$CONTAINER_NAME":"$CONTAINER_WORKDIR/TEMP/main" "$HOST_BUILD_DIR/main"
			chmod +x "$HOST_BUILD_DIR/main" || true
			echo "  Copied: $HOST_BUILD_DIR/main"
		else
			RET_VERIFY=$?
			if [ "$RET_VERIFY" -eq 5 ]; then
				echo "ERROR: Missing shared libraries detected inside container. Not copying artifact."
				docker exec "$CONTAINER_NAME" bash -lc "ldd $CONTAINER_WORKDIR/TEMP/main || true; echo '--- RUNTIME LOG ---'; cat $CONTAINER_WORKDIR/TEMP/main.run.log || true" || true
				exit 1
			elif [ "$RET_VERIFY" -eq 6 ]; then
				echo "ERROR: Executable failed at runtime (non-zero exit). Not copying artifact. See logs:"
				docker exec "$CONTAINER_NAME" bash -lc "cat $CONTAINER_WORKDIR/TEMP/main.run.log || true"
				exit 1
			else
				echo "ERROR: Verification failed (exit code: $RET_VERIFY). Not copying artifact."
				docker exec "$CONTAINER_NAME" bash -lc "ls -la $CONTAINER_WORKDIR/TEMP || true; cat $CONTAINER_WORKDIR/TEMP/main.run.log || true" || true
				exit $RET_VERIFY
			fi
		fi
	else
		echo "  WARNING: Could not find expected output $CONTAINER_WORKDIR/TEMP/main inside container. Listing TEMP/:";
		docker exec "$CONTAINER_NAME" bash -lc "ls -la $CONTAINER_WORKDIR/TEMP || true"
		echo "  Please inspect the container logs for details."
		exit 1
	fi
else
	RETVAL=$?
	if [ "$RETVAL" -eq 3 ]; then
		echo "[!] Python 3.13 was not available or incompatible in the chosen image. Falling back to Ubuntu 20.04 (glibc 2.31)."
		echo "Stopping and removing the temporary container to recreate with ubuntu:20.04"
		docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
		SELECTED_IMAGE="ubuntu:20.04"
		IMAGE_PULLED=true
		echo "Pulling fallback image: $SELECTED_IMAGE"
		docker pull "$SELECTED_IMAGE"
		echo "Creating fallback container"
		CONTAINER_ID=$(docker create --name "$CONTAINER_NAME" $DOCKER_NET_ARG -w "$CONTAINER_WORKDIR" -it "$SELECTED_IMAGE" bash)
		docker cp "$PROJECT_ROOT/." "$CONTAINER_ID":"$CONTAINER_WORKDIR"
		docker start "$CONTAINER_ID" >/dev/null

		echo "Running build inside fallback container (ubuntu:20.04)"
		docker exec "$CONTAINER_NAME" bash -lc "set -eux; export DEBIAN_FRONTEND=noninteractive; \
		apt-get update -y; \
		apt-get install -y --no-install-recommends software-properties-common curl build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev xz-utils || true; \
		add-apt-repository ppa:deadsnakes/ppa -y || true; apt-get update -y; \
		# Try to install Python 3.11 as the preferred version
		if apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils 2>/dev/null; then \
			PY_BIN=python3.11; \
		elif apt-get install -y python3.12 python3.12-venv python3.12-dev python3.12-distutils 2>/dev/null; then \
			PY_BIN=python3.12; \
		elif apt-get install -y python3.13 python3.13-venv python3.13-dev python3.13-distutils 2>/dev/null; then \
			PY_BIN=python3.13; \
		else \
			# Fall back to system python3 (may be older and incompatible)
			PY_BIN=python3; \
		fi; \
		$PY_BIN --version || true; \
		$PY_BIN -m pip install --upgrade pip || true; \
		curl -sSL https://install.python-poetry.org | $PY_BIN - || true; \
		# Prefer explicit poetry binary rather than exporting to PATH
		if [ -x /root/.local/bin/poetry ]; then \
			POETRY_BIN=/root/.local/bin/poetry; \
		elif command -v poetry >/dev/null 2>&1; then \
			POETRY_BIN=poetry; \
		else \
			POETRY_BIN=; \
		fi; \
		cd $CONTAINER_WORKDIR; \
		if [ -n "\$POETRY_BIN" ]; then \$POETRY_BIN config virtualenvs.create false --local || true; \$POETRY_BIN install --no-interaction || true; if ! \$PY_BIN -c \"import PyInstaller\" >/dev/null 2>&1; then \$PY_BIN -m pip install pyinstaller || true; fi; \$POETRY_BIN run python $BUILD_SCRIPT || \$PY_BIN $BUILD_SCRIPT; else \$PY_BIN $BUILD_SCRIPT; fi;"

		echo "Copying artifact from fallback container"
		if docker exec "$CONTAINER_NAME" bash -lc "test -f $CONTAINER_WORKDIR/TEMP/main" >/dev/null 2>&1; then
			echo "[7.1/8] Found artifact inside fallback container. Verifying executable before copying..."
			echo "  Running ldd and a short runtime test inside the fallback container (timeout 10s)"

			if docker exec "$CONTAINER_NAME" bash -lc "set -uo pipefail; \n  file $CONTAINER_WORKDIR/TEMP/main || true; \n  ldd $CONTAINER_WORKDIR/TEMP/main || true; \n  if ldd $CONTAINER_WORKDIR/TEMP/main 2>&1 | grep -q 'not found'; then echo 'MISSING_LIBS'; exit 5; fi; \n  if command -v timeout >/dev/null 2>&1; then timeout 10 $CONTAINER_WORKDIR/TEMP/main > $CONTAINER_WORKDIR/TEMP/main.run.log 2>&1 || true; RCODE=\$?; else $CONTAINER_WORKDIR/TEMP/main > $CONTAINER_WORKDIR/TEMP/main.run.log 2>&1 & PID=\$!; sleep 10; kill -0 \$PID >/dev/null 2>&1 && kill \$PID || true; wait \$PID 2>/dev/null || true; RCODE=\$?; fi; \n  echo RUNTIME_EXIT_CODE:\$RCODE; \n  tail -n 200 $CONTAINER_WORKDIR/TEMP/main.run.log || true; \n  if [ \$RCODE -ne 0 ] && [ \$RCODE -ne 124 ]; then echo 'RUNTIME_FAIL'; exit 6; fi; \n  exit 0"; then
				docker cp "$CONTAINER_NAME":"$CONTAINER_WORKDIR/TEMP/main" "$HOST_BUILD_DIR/main"
				chmod +x "$HOST_BUILD_DIR/main" || true
				echo "  Copied: $HOST_BUILD_DIR/main"
			else
				RET_VERIFY=$?
				if [ "$RET_VERIFY" -eq 5 ]; then
					echo "ERROR: Missing shared libraries detected inside fallback container. Not copying artifact."
					docker exec "$CONTAINER_NAME" bash -lc "ldd $CONTAINER_WORKDIR/TEMP/main || true; echo '--- RUNTIME LOG ---'; cat $CONTAINER_WORKDIR/TEMP/main.run.log || true" || true
					exit 1
				elif [ "$RET_VERIFY" -eq 6 ]; then
					echo "ERROR: Executable failed at runtime (non-zero exit) in fallback container. Not copying artifact. See logs:"
					docker exec "$CONTAINER_NAME" bash -lc "cat $CONTAINER_WORKDIR/TEMP/main.run.log || true"
					exit 1
				else
					echo "ERROR: Verification failed in fallback container (exit code: $RET_VERIFY). Not copying artifact."
					docker exec "$CONTAINER_NAME" bash -lc "ls -la $CONTAINER_WORKDIR/TEMP || true; cat $CONTAINER_WORKDIR/TEMP/main.run.log || true" || true
					exit $RET_VERIFY
				fi
			fi
		else
			echo "ERROR: Build did not produce $CONTAINER_WORKDIR/TEMP/main in fallback container. Listing TEMP/:";
			docker exec "$CONTAINER_NAME" bash -lc "ls -la $CONTAINER_WORKDIR/TEMP || true"
			exit 1
		fi
	else
		echo "ERROR: Build failed inside container (exit code: $RETVAL). Check the container logs for details."
		exit $RETVAL
	fi
fi

echo "All done. The built executable (if successful) is at: $HOST_BUILD_DIR/main"