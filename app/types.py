from typing import TypedDict, Any

from telegram.ext import CallbackContext, Dispatcher


class Quote(TypedDict):
    q: str  # quote
    a: str  # author
    h: str  # HTML


CCT = CallbackContext[dict[Any, Any], dict[Any, Any], dict[Any, Any]]
DP = Dispatcher[CCT, dict[Any, Any], dict[Any, Any], dict[Any, Any]]
