from typing import Any

from telegram.ext import CallbackContext, Dispatcher


CCT = CallbackContext[dict[Any, Any], dict[Any, Any], dict[Any, Any]]
DP = Dispatcher[CCT, dict[Any, Any], dict[Any, Any], dict[Any, Any]]
