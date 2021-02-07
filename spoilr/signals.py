import importlib
from .signals_register import *

import hunt.callbacks
import nuntius.callbacks

def emit(msg, *args, **kwargs):
    if not msg in subscriptions:
        logger.info("Message with no subscribers: " + str(msg))
        return

    # Resolve strings into functions
    for i, s in enumerate(subscriptions[msg]):
        if isinstance(s, str):
            modulename, fname = s.rsplit('.', 1)
            func = getattr(importlib.import_module(modulename), fname)
            subscriptions[msg][i] = func
    print('Signal: %s' % (msg))
    for s in subscriptions[msg]:
        try:
            s(*args, **kwargs)
        except Exception as e:
            logger.error("Subscriber " + str(s) + " could not handle message " + str(msg) + ": " + str(args) + str(kwargs), exc_info=1)
