#!/usr/bin/env bash


install() {
    echo "creating venv and installing dependencies..."
    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -r requirements.txt
    echo "venv created."
}

run_app() {
    echo "running the app..."
    source .venv/bin/activate
    export DATABASE_URL=postgresql://imagepod:Kkc7HGNjxEbkBUN0OK2SrA@localhost:5432/imagepod
    export REDIS_PASSWORD="tD0Fe7OiuEZDszXx_GrFLA"
    export REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6379/0"
    export SECRET_KEY="0ZuYk9O1slaw35jItXv-VG4zUMyxAR-quB5EkZdluDI"
    export ENVIRONMENT=development
    export DEBUG=true
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

clean() {
  echo "Removing venv..."
  rm -rf ".venv"
  echo "Done."
}

case "$1" in
  install)
    install
    ;;
  run)
    run_app
    ;;
  clean)
    clean
    ;;
  *)
    echo "Usage: $0 {install|run|clean}"
    exit 1
    ;;
esac