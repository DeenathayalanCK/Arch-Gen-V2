from app.pipeline.context import PipelineContext
from app.pipeline.decomposition_stage import DecompositionStage

ctx = PipelineContext(
    requirements_text="Users place orders. Orders are stored in a database. The system runs in the cloud."
)

stage = DecompositionStage()
result = stage.run(ctx)

print("VALID:", result.is_valid)
print("ERRORS:", result.errors)
print("DECOMPOSED:", ctx.decomposed)
