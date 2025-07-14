from flask import Blueprint, request, current_app, jsonify, render_template

from ..utils import ApiResponse, ValidationError, get_logger

logger = get_logger(__name__)

# API blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/setup/bigquery", methods=["POST"])
def setup_bigquery():
    """Setup BigQuery dataset and tables."""
    result = current_app.bigquery_service.setup()

    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500


@api_bp.route("/setup/firestore", methods=["POST"])
def setup_firestore():
    """Setup Firestore database."""
    result = current_app.firestore_service.setup()

    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500


@api_bp.route("/setup/demo_data", methods=["POST"])
def setup_demo_data():
    """Create demo data for the application."""
    if (
        not hasattr(current_app, "demo_data_service")
        or current_app.demo_data_service is None
    ):
        return (
            jsonify(
                {"success": False, "message": "Demo data service is not available"}
            ),
            500,
        )

    # Get user_limit from request data
    data = request.get_json() or {}
    user_limit = data.get("user_limit")

    result = current_app.demo_data_service.create_demo_data(user_limit=user_limit)

    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500


@api_bp.route("/setup/demo_data_status")
def demo_data_status():
    """Get demo data status."""
    # Check if demo data service is available
    if (
        not hasattr(current_app, "demo_data_service")
        or current_app.demo_data_service is None
    ):
        return (
            jsonify(
                {"success": False, "message": "Demo data service is not available"}
            ),
            500,
        )

    try:
        result = current_app.demo_data_service.get_status()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting demo data status: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Error getting demo data status: {str(e)}",
                }
            ),
            500,
        )


@api_bp.route("/events/add", methods=["POST"])
def add_event():
    """Add a new event to the appropriate BigQuery table."""
    # Check if BigQuery service is available
    if (
        not hasattr(current_app, "bigquery_service")
        or current_app.bigquery_service is None
    ):
        return (
            jsonify({"success": False, "message": "BigQuery service is not available"}),
            500,
        )

    # Get event data from request
    event_data = request.get_json()
    if not event_data:
        return (
            jsonify({"success": False, "message": "No event data provided"}),
            400,
        )

    # Validate required fields
    if "type" not in event_data:
        return (
            jsonify({"success": False, "message": "Event type is required"}),
            400,
        )

    event_type = event_data["type"]

    # Additional validation for company events
    if event_type in ["purchased", "provisioned"]:
        if "company" not in event_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Company is required for company events",
                    }
                ),
                400,
            )
        if event_type == "purchased" and "purchased" not in event_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Purchased field is required for purchased events",
                    }
                ),
                400,
            )
        if event_type == "provisioned" and "provisioned" not in event_data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": (
                            "Provisioned field is required for provisioned events"
                        ),
                    }
                ),
                400,
            )

    try:
        # Route to appropriate table based on event type
        if event_type in ["purchased", "provisioned"]:
            table_name = "company_events"
        else:
            table_name = "user_events"

        # Write event to BigQuery
        result = current_app.bigquery_service.write_rows_to_table(
            table_name, [event_data]
        )

        if result["success"]:
            # For company events, also update the company document in Firestore
            if event_type in ["purchased", "provisioned"]:
                # Check if Firestore service is available
                if (
                    not hasattr(current_app, "firestore_service")
                    or current_app.firestore_service is None
                ):
                    logger.warning(
                        "Firestore service not available for company document update"
                    )
                else:
                    try:
                        # Get the company document
                        company_name = event_data["company"]
                        company_entity = current_app.firestore_service.get_company(
                            company_name
                        )

                        if company_entity:
                            # Update company fields based on event type
                            if event_type == "purchased":
                                purchased = company_entity.boxes_bought
                                if not purchased:
                                    purchased = 0
                                company_entity.boxes_bought = (
                                    purchased + event_data["purchased"]
                                )

                            if event_type == "provisioned":
                                provisioned = company_entity.boxes_prov
                                if not provisioned:
                                    provisioned = 0
                                company_entity.boxes_prov = (
                                    provisioned + event_data["provisioned"]
                                )

                            # Save the updated company document
                            current_app.firestore_service.update_company(company_entity)
                            logger.info(
                                f"Updated company {company_name} for {event_type} event"
                            )
                        else:
                            logger.warning(
                                f"Company {company_name} not found for event update"
                            )
                    except Exception as firestore_error:
                        # Log the error but don't fail the entire request since BigQuery write succeeded
                        logger.error(
                            f"Failed to update company document: {str(firestore_error)}"
                        )

            return jsonify(
                {
                    "success": True,
                    "message": f"Event successfully added to {table_name}",
                    "table": table_name,
                    "event_type": event_type,
                    "rows_inserted": result.get("rows_inserted", 1),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": (
                            f"Failed to write event to {table_name}: {result.get('message', 'Unknown error')}"
                        ),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Error adding event: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Error adding event: {str(e)}"}),
            500,
        )


@api_bp.route("/customer/<customer_name>/card/<card_type>")
def customer_card_data(customer_name, card_type):
    """API endpoint for getting specific card data."""
    # Check if dashboard service is available
    if (
        not hasattr(current_app, "dashboard_service")
        or current_app.dashboard_service is None
    ):
        return jsonify({"error": "Dashboard service is unavailable"}), 500

    try:
        card_data = current_app.dashboard_service.get_card_data(
            card_type, customer_name
        )
        return jsonify(card_data)
    except Exception as e:
        logger.error(f"Error getting card data for {card_type}: {str(e)}")
        return jsonify({"error": str(e)}), 500
