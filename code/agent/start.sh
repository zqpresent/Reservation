if [ -f .env ]; then
  set -a
  . ./.env
  set +a
elif [ -f .env.example ]; then
  set -a
  . ./.env.example
  set +a
fi

uvicorn main:app --reload --host 0.0.0.0 --port "${AGENT_PORT:-8100}"
