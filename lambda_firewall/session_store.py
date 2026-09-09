"""Server-side conversation state for the gateway.

Why this exists
---------------
The gateway was stateless: one system message, one user message, no history.
Multi-turn attacks cannot be measured against a stateless service.  If the test
harness replayed the conversation from the client on every request, the thing
under measurement would be the harness's own loop, not a control the gateway
owns.  Putting conversation state on the server side of the trust boundary is
what makes a multi-turn result mean anything.

What is deliberately missing
----------------------------
Only an in-memory backend exists.  A deployed gateway needs durable storage --
Lambda execution contexts are recycled, so an in-memory dict does not survive in
production.  That backend is not written here on purpose: the evaluation never
exercises it, and untested code must not be presented as a control.  The
evaluation therefore measures conversation-assembly logic, not persistence, and
the protocol says so.
"""

from abc import ABC, abstractmethod

# How many prior messages are replayed to the model.
#
# This is a security-relevant number, not just a cost control.  Everything inside
# the window is content the model still acts on; everything that falls out of it
# is content an attacker can no longer reach.  A larger window is a longer-lived
# opportunity to plant something on an early turn and use it later.
MAX_HISTORY_MESSAGES = 12


class SessionStore(ABC):
    """Conversation history, keyed by session id.

    A stored message is a plain dict shaped like the model API's own messages,
    `{"role": "user" | "assistant", "content": str}`, so nothing has to be
    converted on the way to the model call.
    """

    @abstractmethod
    def load(self, session_id: str) -> list:
        """Return this session's messages, oldest first.  Unknown id returns []."""

    @abstractmethod
    def append(self, session_id: str, role: str, content: str) -> None:
        """Add one message to the end of this session's history."""

    @abstractmethod
    def clear(self, session_id: str) -> None:
        """Forget a session entirely."""


class InMemorySessionStore(SessionStore):
    """Process-local conversation state.

    Correct for the evaluation harness and for unit tests.  Not correct for a
    deployed Lambda, where each execution context has its own memory and a user's
    second turn may land on a different one.
    """

    def __init__(self, max_messages: int = MAX_HISTORY_MESSAGES):
        self._sessions: dict = {}
        self._max_messages = max_messages

    def load(self, session_id: str) -> list:
        # Return a copy.  A caller that mutated the list it got back would be
        # editing stored history as a side effect, which is the kind of bug that
        # would silently corrupt a multi-turn result.
        return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, role: str, content: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": role, "content": content})
        # Drop from the front once the window is full, so the newest turns are
        # the ones retained.
        if len(history) > self._max_messages:
            del history[: len(history) - self._max_messages]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
