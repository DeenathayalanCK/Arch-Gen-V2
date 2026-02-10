# arch_gen/renderer/visual_spec_example.py

def get_sample_visual_spec():
    return {
        "canvas": {
            "width": 1400,
            "height": 900
        },
        "nodes": [
            {
                "id": "actor_customer",
                "x": 100,
                "y": 80,
                "width": 160,
                "height": 60,
                "label": "Customer"
            },
            {
                "id": "web_app",
                "x": 400,
                "y": 80,
                "width": 220,
                "height": 70,
                "label": "Web Application"
            },
            {
                "id": "order_service",
                "x": 400,
                "y": 220,
                "width": 260,
                "height": 80,
                "label": "Order Management Service"
            }
        ],
        "edges": [
            {
                "from": "actor_customer",
                "to": "web_app",
                "label": "uses"
            },
            {
                "from": "web_app",
                "to": "order_service",
                "label": "calls"
            }
        ]
    }
