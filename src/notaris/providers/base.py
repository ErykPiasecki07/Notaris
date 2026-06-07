"""Provider interface for clinical note extraction."""

from abc import ABC, abstractmethod

from notaris.domain import ClinicalNote, ExtractionResult, ExtractionSchema


class BaseExtractionProvider(ABC):
    """Interface implemented by extraction providers."""

    @abstractmethod
    def extract(
        self,
        note: ClinicalNote,
        schema: ExtractionSchema,
    ) -> ExtractionResult:
        """Extract schema values from one clinical note."""
