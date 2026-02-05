from abc import ABC, abstractmethod
from app.pipeline.context import PipelineContext
from app.ir.validation import ValidationResult


class PipelineStage(ABC):
    name: str

    @abstractmethod
    def run(self, context: PipelineContext) -> ValidationResult:
        """
        Must:
        - read from context
        - write to context
        - NEVER call other stages
        """
        pass
