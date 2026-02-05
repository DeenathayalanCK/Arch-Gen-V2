REFERENCE_ARCHITECTURES = {
    "order_management": {
        "service_keywords": ["order"],
        "responsibilities": [
            {
                "name": "Validate Order",
                "description": "Validate incoming order requests",
                "type": "logic",
            },
            {
                "name": "Create Order",
                "description": "Create and persist orders",
                "type": "persistence",
            },
            {
                "name": "Update Order Status",
                "description": "Manage order lifecycle state",
                "type": "logic",
            },
            {
                "name": "Retrieve Order Details",
                "description": "Fetch order data for queries",
                "type": "api",
            },
        ],
        "datastores": [
            {
                "name": "orders",
                "store_type": "sql",
            }
        ],
    }
}
