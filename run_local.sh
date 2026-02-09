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

    source .env
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

run_test() {
  echo "running the app..."
  source .venv/bin/activate

  source .env
  
  TEST=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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
  run_test)
    run_test
    ;;
  clean)
    clean
    ;;
  *)
    echo "Usage: $0 {install|run|clean|run_test}"
    exit 1
    ;;
esac