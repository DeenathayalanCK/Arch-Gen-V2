from app.pipeline.controller import PipelineController

requirements = """
Users place orders.
Orders are stored in a database.
The system runs in the cloud.
"""

controller = PipelineController()
context = controller.run(requirements)

print("\n--- DECOMPOSED ---")
print(context.decomposed)

print("\n--- BUSINESS IR ---")
print(context.business_ir)

print("\n--- SERVICE IR ---")
print(context.service_ir)

print("\n--- DATA IR ---")
print(context.data_ir)

print("\n--- INFRA IR ---")
print(context.infra_ir)

print("\n--- ERRORS ---")
print(context.errors)
