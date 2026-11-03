"""
extensions/multi_document.py — STUB: Multi-document intelligence (v3+)

Future capability:
  Synthesise knowledge across multiple documents simultaneously, enabling
  cross-document entity resolution, contradiction detection, and topic clustering.

  See interfaces/synthesis.py for the contract.
"""
from interfaces.synthesis import SynthesisBackend


class MultiDocumentSynthesisBackend(SynthesisBackend):
    """Placeholder — not implemented in v2."""

    def synthesise(self, chunks, api_key=None, model=None, **kwargs):
        raise NotImplementedError("MultiDocumentSynthesisBackend is not yet implemented.")

    def reduce(self, partial_results, api_key=None, model=None):
        raise NotImplementedError("MultiDocumentSynthesisBackend is not yet implemented.")
