"""MineOS terminal agent: a router, one Python tool, and a graph memory.

Ported from clarkeAgent ("Onyx") and reshaped for a desktop OS:

* the model is served by llama.cpp (``llama-server``) over the OpenAI-compatible
  API, or by any hosted endpoint *if the user supplies a key*;
* a cheap router answers the obvious requests ("open firefox", "volume 40")
  without calling the language model at all;
* everything else goes to the model, which has exactly **one** tool -- it
  writes Python, and that Python reaches the computer only through the
  safeguarded ``mine`` API (see :mod:`mineos_agent.os_api`).

Standard library only, so it runs on a stock Debian 13 ``python3``.
"""

__version__ = "0.1.0"
