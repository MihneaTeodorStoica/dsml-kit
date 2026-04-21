#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

ensure_image

docker run --rm "$image_name" sh -lc '
  echo "Python: $(python --version 2>&1)"
  echo "uv: $(uv --version)"
  echo "jupyterlab: $(python -c "import jupyterlab; print(jupyterlab.__version__)")"
  echo "notebook: $(python -c "import notebook; print(notebook.__version__)")"
  echo "h11: $(python -c "import h11; print(h11.__version__)")"
  echo "urllib3: $(python -c "import urllib3; print(urllib3.__version__)")"
  echo "playwright: $(python -m playwright --version)"
  echo "chromium dirs: $(find /ms-playwright -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l)"
  echo "nitro-ai-judge: $(python -m pip show jupyterlab-nitro-ai-judge >/dev/null 2>&1 && echo installed || echo missing)"
  echo "sudo package: $(dpkg-query -W -f="\${Version}" sudo 2>/dev/null || echo not-installed)"
'

if docker scout version >/dev/null 2>&1; then
  docker scout quickview "$image_name"
elif command -v trivy >/dev/null 2>&1; then
  trivy image "$image_name"
else
  echo "No scanner available. Install Docker Scout or Trivy to scan the image."
fi
