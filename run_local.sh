#!/usr/bin/env bash

COMPOSE_INFRA="docker compose -f docker-compose.infra.yml"

infra_up() {
    echo "Starting infrastructure (postgres, redis, rabbitmq, minio)..."
    $COMPOSE_INFRA up -d
    echo "Infrastructure up. Run './run_local.sh run' to start the app in debug mode."
}

infra_down() {
    echo "Stopping infrastructure..."
    $COMPOSE_INFRA down
    echo "Done."
}

infra_logs() {
    $COMPOSE_INFRA logs -f "$@"
}

install() {
    echo "creating venv and installing dependencies..."
    uv venv --python 3.12
    source .venv/bin/activate
    uv pip install -r pyproject.toml
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
  infra)
    infra_up
    ;;
  infra_down)
    infra_down
    ;;
  infra_logs)
    shift
    infra_logs "$@"
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
    echo "Usage: $0 {install|run|run_test|infra|infra_down|infra_logs|clean}"
    echo "  infra       - start infra only (docker-compose.infra.yml), for local debug"
    echo "  infra_down  - stop infra"
    echo "  infra_logs  - follow infra logs"
    exit 1
    ;;
esac