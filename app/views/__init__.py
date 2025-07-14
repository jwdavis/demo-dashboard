from flask import Blueprint, current_app, jsonify, render_template, request

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def home():
    """Home page with service status warnings."""
    # Check service availability
    warnings = []

    # Check BigQuery service
    if (
        not hasattr(current_app, "bigquery_service")
        or current_app.bigquery_service is None
    ):
        warnings.append(
            {
                "service": "BigQuery",
                "message": (
                    "BigQuery service is unavailable. Data tracking and analytics features will not work."
                ),
                "type": "danger",
            }
        )

    # Check Firestore service
    if (
        not hasattr(current_app, "firestore_service")
        or current_app.firestore_service is None
    ):
        warnings.append(
            {
                "service": "Firestore",
                "message": (
                    "Firestore service is unavailable. User data and application features will not work."
                ),
                "type": "danger",
            }
        )

    # Fetch upcoming projects from Firestore
    upcoming_projects = []
    upcoming_renewals = []
    recent_trends = []
    if (
        hasattr(current_app, "firestore_service")
        and current_app.firestore_service is not None
    ):
        try:
            # Get projects collection and order by date (ascending for nearest dates first)
            projects_ref = current_app.firestore_service.client.collection("projects")
            projects_query = projects_ref.order_by("date").limit(3)

            for doc in projects_query.stream():
                project_data = doc.to_dict()
                project_data["id"] = doc.id

                # Format the date for display
                if "date" in project_data and project_data["date"]:
                    # Convert Firestore timestamp to datetime if needed
                    date_obj = project_data["date"]
                    if hasattr(date_obj, "date"):
                        # It's a datetime object
                        project_data["formatted_date"] = date_obj.strftime("%m/%d")
                    elif hasattr(date_obj, "strftime"):
                        # It's a datetime-like object
                        project_data["formatted_date"] = date_obj.strftime("%m/%d")
                    else:
                        # It might be a string or other format
                        project_data["formatted_date"] = str(date_obj)
                elif "due" in project_data and project_data["due"]:
                    # Handle legacy 'due' field
                    date_obj = project_data["due"]
                    if hasattr(date_obj, "strftime"):
                        project_data["formatted_date"] = date_obj.strftime("%m/%d")
                    else:
                        project_data["formatted_date"] = str(date_obj)
                else:
                    project_data["formatted_date"] = "No date"

                upcoming_projects.append(project_data)

            # Get renewals collection and order by due date (ascending for nearest dates first)
            renewals_ref = current_app.firestore_service.client.collection("renewals")
            renewals_query = renewals_ref.order_by("due").limit(3)

            for doc in renewals_query.stream():
                renewal_data = doc.to_dict()
                renewal_data["id"] = doc.id

                # Format the date for display
                if "due" in renewal_data and renewal_data["due"]:
                    # Convert Firestore timestamp to datetime if needed
                    date_obj = renewal_data["due"]
                    if hasattr(date_obj, "date"):
                        # It's a datetime object
                        renewal_data["formatted_date"] = date_obj.strftime("%m/%d")
                    elif hasattr(date_obj, "strftime"):
                        # It's a datetime-like object
                        renewal_data["formatted_date"] = date_obj.strftime("%m/%d")
                    else:
                        # It might be a string or other format
                        renewal_data["formatted_date"] = str(date_obj)
                else:
                    renewal_data["formatted_date"] = "No date"

                # Format the amount for display (assuming it's a number)
                if "amount" in renewal_data and renewal_data["amount"]:
                    amount = renewal_data["amount"]
                    if isinstance(amount, (int, float)):
                        renewal_data["formatted_amount"] = f"${amount:,.0f}"
                    else:
                        renewal_data["formatted_amount"] = str(amount)
                else:
                    renewal_data["formatted_amount"] = "TBD"

                upcoming_renewals.append(renewal_data)

            # Get trending collection and order by date (descending for most recent/future dates first)
            trending_ref = current_app.firestore_service.client.collection("trending")
            trending_query = trending_ref.order_by(
                "date", direction="DESCENDING"
            ).limit(3)

            for doc in trending_query.stream():
                trend_data = doc.to_dict()
                trend_data["id"] = doc.id

                # Format the date for display
                if "date" in trend_data and trend_data["date"]:
                    # Convert Firestore timestamp to datetime if needed
                    date_obj = trend_data["date"]
                    if hasattr(date_obj, "date"):
                        # It's a datetime object
                        trend_data["formatted_date"] = date_obj.strftime("%m/%d")
                    elif hasattr(date_obj, "strftime"):
                        # It's a datetime-like object
                        trend_data["formatted_date"] = date_obj.strftime("%m/%d")
                    else:
                        # It might be a string or other format
                        trend_data["formatted_date"] = str(date_obj)
                else:
                    trend_data["formatted_date"] = "No date"

                # Format the value as a percentage change (assuming it's a number)
                if "value" in trend_data and trend_data["value"]:
                    value = trend_data["value"]
                    if isinstance(value, (int, float)):
                        # Show as percentage with one decimal place
                        trend_data["change"] = f"{value:.1f}%"
                    else:
                        trend_data["change"] = str(value)
                else:
                    trend_data["change"] = "0%"

                recent_trends.append(trend_data)

        except Exception as e:
            # If there's an error fetching data, just log it and continue
            current_app.logger.warning(
                f"Could not fetch projects/renewals/trends: {str(e)}"
            )

    return render_template(
        "home.html",
        warnings=warnings,
        projects=upcoming_projects,
        renewals=upcoming_renewals,
        trends=recent_trends,
    )


@views_bp.route("/setup")
def setup():
    """Setup page for configuring BigQuery and other services."""
    # Check BigQuery service status
    bigquery_available = (
        hasattr(current_app, "bigquery_service")
        and current_app.bigquery_service is not None
    )

    # Check Firestore service status
    firestore_available = (
        hasattr(current_app, "firestore_service")
        and current_app.firestore_service is not None
    )

    return render_template(
        "setup.html",
        bigquery_available=bigquery_available,
        firestore_available=firestore_available,
    )


@views_bp.route("/customer/<customer_name>")
def customer_dashboard(customer_name):
    """Customer dashboard page with synchronous overview data."""
    # Check if dashboard service is available
    if (
        not hasattr(current_app, "dashboard_service")
        or current_app.dashboard_service is None
    ):
        return (
            render_template(
                "error.html",
                error="Dashboard service is unavailable. Please check your configuration.",
            ),
            500,
        )

    # Get card parameter for async requests
    card = request.args.get("card")

    # If card parameter is present, return JSON data for that card (async endpoint)
    if card:
        try:
            card_data = current_app.dashboard_service.get_card_data(card, customer_name)
            return jsonify(card_data)
        except Exception as e:
            current_app.logger.error(f"Error getting card data for {card}: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Otherwise, render the main dashboard page with overview data (sync)
    try:
        overview_data = current_app.dashboard_service.get_customer_overview(
            customer_name
        )
        return render_template("customer.html", **overview_data)
    except Exception as e:
        current_app.logger.error(
            f"Error loading customer dashboard for {customer_name}: {str(e)}"
        )
        return (
            render_template(
                "error.html",
                error=f"Error loading customer dashboard: {str(e)}",
            ),
            500,
        )
