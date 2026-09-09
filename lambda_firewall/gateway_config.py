"""Gateway configuration, read from environment variables.

Most options here exist because the evaluation needs to measure *two* defensible
implementations of the same design decision -- not because one of them is a bug
we planted so the corpus could find it.  The default is the implementation we
would actually ship.  Setting the flag turns on the alternative so both can be
run against the same frozen corpus and reported side by side.

See docs/evaluation-protocol.md, section 4.
"""

import os
from dataclasses import dataclass


def _read_flag(name: str) -> bool:
    """Read a boolean environment variable.

    Anything not explicitly truthy is False, including a missing variable and a
    value we do not recognise.  A misspelled flag therefore fails closed to the
    shipped default rather than silently enabling a variant, which would corrupt
    a run without anything in the results showing it.
    """
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class GatewayConfig:
    """One evaluation arm's configuration.

    Frozen because a run must not be able to change its own configuration
    part-way through; every result row records the config it ran under.
    """

    # Does the input filter inspect the `context` field as well as `prompt`?
    #
    # Default False.  Retrieved content in a RAG pipeline arrives from your own
    # document store, so it reads as trusted and is routinely not filtered.  That
    # is the mainstream implementation, which makes it the honest thing to
    # measure.  Setting this True measures the filtered variant, including the
    # false positives it creates on legitimate documents.
    filter_context: bool = False

    # When the input filter returns 403, is the rejected prompt still written to
    # session history?
    #
    # Default False -- a blocked turn leaves no trace.  If it were True, an
    # attacker could land blocked content in the model's context anyway and reach
    # it on a later turn, making the filter's own storage layer its bypass.
    persist_blocked_turns: bool = False

    # Does session history store the raw model output or the redacted output?
    #
    # Default False (store redacted).  Neither answer is clearly correct.
    # Storing redacted means the history disagrees with what the model actually
    # said -- we are lying to the model about its own turn.  Storing raw keeps
    # the transcript honest but puts the secret into context a second time.
    store_raw_in_history: bool = False

    # Is the mock secret present in the system prompt at all?
    #
    # Default True, which is the deployed behaviour and covers arms A and B.
    # Arm C sets this False.  Arm C's leak rate is zero by construction, and the
    # protocol reports it as a construction proof rather than as evidence that
    # any control works.
    include_secret_in_system_prompt: bool = True

    @classmethod
    def from_environment(cls) -> "GatewayConfig":
        return cls(
            filter_context=_read_flag("GATEWAY_FILTER_CONTEXT"),
            persist_blocked_turns=_read_flag("GATEWAY_PERSIST_BLOCKED_TURNS"),
            store_raw_in_history=_read_flag("GATEWAY_STORE_RAW_IN_HISTORY"),
            include_secret_in_system_prompt=not _read_flag(
                "GATEWAY_OMIT_SECRET_FROM_PROMPT"
            ),
        )

    def as_result_metadata(self) -> dict:
        """The configuration, flattened for the results file.

        Every trial records this.  A results row that cannot say which arm and
        which variant produced it is not evidence of anything.
        """
        return {
            "filter_context": self.filter_context,
            "persist_blocked_turns": self.persist_blocked_turns,
            "store_raw_in_history": self.store_raw_in_history,
            "include_secret_in_system_prompt": self.include_secret_in_system_prompt,
        }
