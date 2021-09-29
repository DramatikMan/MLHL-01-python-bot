pip install poetry
pip install poetry-exec-plugin
poetry config virtualenvs.in-project true

mkdir -p .venv

if [[ ${build_env} != 'production' ]]; then
    poetry install --no-root
else
    poetry install --without dev --no-root
fi