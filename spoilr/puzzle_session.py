"""
# Example usage: receive a number, return the total sum of all numbers
# received so far.

class SummationModel(PuzzleSessionModelBase):
    total = IntegerField(default=0)

@puzzle_session(SummationModel)
def summation_ajax_view(request, state):
    # You can check integrity of the request with exceptions.
    # The wrapper will log the error and respond to the client with an opaque,
    # uninformative error message.
    value = int(request.POST['value'])
    if not (1 <= value <= 10):
        raise Exception("value is invalid")

    # Update the state. Don't save it; the wrapper takes care of that.
    state.total += value

    # Return a JSON-able dictionary.
    return {"total" : state.total}

# Renders the page containing JavaScript code to interface with the above
# AJAX endpoint. This page uses puzzle_session.js to do so.
def summation_view(request):
    return render(request, "summation.html")
"""

import json
import logging
import random
import string
import traceback

from django.db.models import Model, IntegerField, CharField, TextField
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from spoilr.decorators import require_puzzle_access

logger = logging.getLogger(__name__)

SESSION_ID_LEN = 32

class PuzzleSessionModelBase(Model):
    session_id = CharField(max_length=SESSION_ID_LEN, unique=True, null=False)
    seq = IntegerField(null=False)
    previous_request = CharField(null=False, max_length=1024)
    previous_response = TextField()

    class Meta:
        abstract = True

# TODO should use an atomic database transaction

def puzzle_session(PuzzleSessionModel):
    assert issubclass(PuzzleSessionModel, PuzzleSessionModelBase)

    def decorator(fn):
        @csrf_exempt
        @require_puzzle_access
        def view_fn(request):
            try:
                if request.method != 'POST':
                    raise Exception("Method is not POST")

                seq = int(request.POST['seq'])
                if seq < 0:
                    raise Exception("seq should be nonnegative")

                request_serialized = repr(sorted([(k, request.POST[k]) for k in request.POST
                            if k not in ('seq', 'session_id')]))

                if seq == 0:
                    # First message of the session
                    # Create a new session object with a new session_id
                    session_id = "".join(random.choice(string.ascii_lowercase + string.digits)
                            for _ in xrange(SESSION_ID_LEN))

                    session = PuzzleSessionModel.objects.create(
                        session_id=session_id,
                        seq=0,
                        previous_request="",
                        previous_response="")
                else:
                    # Continuation of existing session
                    session_id = request.POST['session_id']
                    session = PuzzleSessionModel.objects.get(session_id=session_id)
                    if session is None:
                        raise Exception("No session found for session id '%s'" % session_id)
                    if seq not in (session.seq, session.seq - 1):
                        raise Exception("Invalid seq %d for session id '%s'" % (seq, session_id))

                    if seq == session.seq - 1:
                        # This request is a retry of a request that was already processed.
                        # Check that the request is actually the same, then return
                        # the same response.
                        if session.previous_request != request_serialized:
                            raise Exception("request does not match previous request of same seq")
                        return HttpResponse(session.previous_response, content_type="application/json")

                resp = fn(request, session)

                # If this is the first request of the session, we return the newly-generated
                # session_id so the client can continue the session.
                if seq == 0:
                    resp["session_id"] = session_id
                resp["query_success"] = "true"

                response_serialized = json.dumps(resp)

                session.seq += 1
                session.previous_request = request_serialized
                session.previous_response = response_serialized
                session.save()

                return HttpResponse(response_serialized, content_type="application/json")

            except Exception as e:
                logger.exception("Unhandled exception in puzzle_session for '%s'" % fn.__name__)

                return HttpResponse(json.dumps({"query_success": "false"}), content_type="application/json")

        return view_fn
    return decorator
