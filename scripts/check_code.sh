clear

poetry run mypy \
    ${PWD}/app \
    --ignore-missing-imports \
    --show-error-codes \
    --strict

poetry run flake8 \
    ${PWD}/app \
    --count \
    --statistics \
    --show-source