from datetime import datetime, timedelta
from flask import current_app

from ..utils import get_logger
from ..utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class DashboardService:
    """Dashboard data service for customer metrics and analytics."""

    def __init__(self, app):
        # Configuration
        self.project_id = app.cfg.project
        self.dataset_id = app.cfg.bigquery_dataset

        # Services
        self.bigquery_service = app.bigquery_service
        self.firestore_service = app.firestore_service

    def get_customer_overview(self, customer_name):
        """Get customer overview data (purchased boxes and ACV)."""
        try:
            # Get purchased boxes and calculate ACV
            query = f"""
            SELECT 
                SUM(purchased) as total_purchased
            FROM `{self.project_id}.events.company_events`
            WHERE company = @customer_name
                AND type = 'purchased'
                AND purchased IS NOT NULL
            """

            results = current_app.bigquery_service.client.query(
                query,
                job_config=self._get_query_config({"customer_name": customer_name}),
            ).result()
            purchased = 0
            for row in results:
                if row.total_purchased:
                    purchased = row.total_purchased
                    break

            acv = purchased * 2499  # Same calculation as original

            return {"purchased": purchased, "acv": acv, "customer": customer_name}

        except Exception as e:
            logger.error(
                f"Error getting customer overview for {customer_name}", error=str(e)
            )
            return {"purchased": 0, "acv": 0, "customer": customer_name}

    def get_card_data(self, card_type, customer_name):
        """Route dashboard card requests to appropriate metric methods."""
        try:
            if card_type == "boxes_purchased_cumulative_30d":
                return self._get_boxes_purchased_cumulative_30d(customer_name)
            elif card_type == "boxes_provisioned_pct_cumulative_30d":
                return self._get_boxes_provisioned_pct_cumulative_30d(customer_name)
            elif card_type == "calls_breakdown_7d":
                return self._get_calls_breakdown_7d(customer_name)
            elif card_type == "ratings_average_7d_window_30d":
                return self._get_ratings_average_7d_window_30d(customer_name)
            elif card_type == "boxes_provisioned_cumulative_30d":
                return self._get_boxes_provisioned_cumulative_30d(customer_name)
            elif card_type == "users_active_7d_window_30d":
                return self._get_users_active_7d_window_30d(customer_name)
            elif card_type == "dialin_count_7d_window_30d":
                return self._get_dialin_count_7d_window_30d(customer_name)
            elif card_type == "users_registered_cumulative_30d":
                return self._get_users_registered_cumulative_30d(customer_name)
            elif card_type == "calls_count_7d_window_30d":
                return self._get_calls_count_7d_window_30d(customer_name)
            elif card_type == "support_tickets_7d_window_30d":
                return self._get_support_tickets_7d_window_30d(customer_name)
            elif card_type == "comments_recent_7d":
                return self._get_comments_recent_7d(customer_name)
            else:
                return {"error": f"Unknown card type: {card_type}"}

        except Exception as e:
            logger.error(
                f"Error getting card data for {card_type}, customer {customer_name}",
                error=str(e),
            )
            return {"error": str(e)}

    def _get_query_config(self, params):
        """Create BigQuery job config with query parameters."""
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(k, "STRING", v) for k, v in params.items()
            ]
        return job_config

    # Dashboard metric methods
    def _get_boxes_purchased_cumulative_30d(self, customer_name):
        """Get cumulative purchased boxes over 30 days."""
        logger.info(f"Getting purchased boxes cumulative data for {customer_name}")
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COALESCE(SUM(purchased), 0)
                FROM `{self.project_id}.{self.dataset_id}.company_events`
                WHERE company = @customer_name
                    AND type = 'purchased'
                    AND purchased IS NOT NULL
                    AND DATE(timestamp) <= day
            ) as total_purchased
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Purchased"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.total_purchased])
            value = row.total_purchased  # Last value

        return {"value": value, "history": history}

    def _get_boxes_provisioned_pct_cumulative_30d(self, customer_name):
        """Get percentage of purchased boxes provisioned over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY),
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            CASE 
                WHEN (
                    SELECT COALESCE(SUM(purchased), 0)
                    FROM `{self.project_id}.{self.dataset_id}.company_events`
                    WHERE company = @customer_name
                        AND type = 'purchased'
                        AND purchased IS NOT NULL
                        AND DATE(timestamp) <= day
                ) > 0 THEN 
                ROUND((
                    SELECT COALESCE(SUM(provisioned), 0)
                    FROM `{self.project_id}.{self.dataset_id}.company_events`
                    WHERE company = @customer_name
                        AND type = 'provisioned'
                        AND provisioned IS NOT NULL
                        AND DATE(timestamp) <= day
                ) / (
                    SELECT COALESCE(SUM(purchased), 0)
                    FROM `{self.project_id}.{self.dataset_id}.company_events`
                    WHERE company = @customer_name
                        AND type = 'purchased'
                        AND purchased IS NOT NULL
                        AND DATE(timestamp) <= day
                ) * 100, 2)
                ELSE NULL
            END as pct_provisioned
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "% Provisioned"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.pct_provisioned])
            value = row.pct_provisioned  # Last value

        return {"value": value, "history": history}

    def _get_calls_breakdown_7d(self, customer_name):
        """Get call breakdown by type, users, and OS from last 7 days."""
        # Calls by type
        query_type = f"""
        SELECT call_type, COUNT(*) as calls
        FROM `{self.project_id}.events.user_events`
        WHERE company = @customer_name
            AND type = 'call'
            AND call_type IS NOT NULL
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY call_type
        ORDER BY calls DESC
        """

        results = current_app.bigquery_service.client.query(
            query_type,
            job_config=self._get_query_config({"customer_name": customer_name}),
        ).result()

        calls_by_type = [["Type", "Calls"]]
        for row in results:
            calls_by_type.append([row.call_type, row.calls])

        # Calls by number of users
        query_users = f"""
        SELECT call_num_users, COUNT(*) as calls
        FROM `{self.project_id}.events.user_events`
        WHERE company = @customer_name
            AND type = 'call'
            AND call_num_users IS NOT NULL
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY call_num_users
        ORDER BY call_num_users
        """

        results = current_app.bigquery_service.client.query(
            query_users,
            job_config=self._get_query_config({"customer_name": customer_name}),
        ).result()

        calls_by_users = [["# Users", "Calls"]]
        for row in results:
            calls_by_users.append([str(row.call_num_users), row.calls])

        # Calls by OS
        query_os = f"""
        SELECT call_os, COUNT(*) as calls
        FROM `{self.project_id}.events.user_events`
        WHERE company = @customer_name
            AND type = 'call'
            AND call_os IS NOT NULL
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY call_os
        ORDER BY calls DESC
        """

        results = current_app.bigquery_service.client.query(
            query_os,
            job_config=self._get_query_config({"customer_name": customer_name}),
        ).result()

        calls_by_os = [["OS", "Calls"]]
        for row in results:
            calls_by_os.append([row.call_os, row.calls])

        return {"cbt": calls_by_type, "cbu": calls_by_users, "cbo": calls_by_os}

    def _get_ratings_average_7d_window_30d(self, customer_name):
        """Get average ratings using 7-day sliding window over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT AVG(rating)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'rating'
                    AND rating IS NOT NULL
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as avg_rating,
            (
                SELECT COUNT(rating)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'rating'
                    AND rating IS NOT NULL
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as num_rating
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Avg. Rating"]]
        value = {"avg": "--", "num": "--"}

        for row in results:
            if row.avg_rating is not None:
                avg_rounded = round(row.avg_rating, 2)
                history.append([row.day.strftime("%b %d"), avg_rounded])
                value = {
                    "avg": avg_rounded,
                    "num": row.num_rating,
                }  # Last value
            else:
                history.append([row.day.strftime("%b %d"), None])

        return {"value": value, "history": history}

    # Column 2 Cards
    def _get_boxes_provisioned_cumulative_30d(self, customer_name):
        """Get provisioned boxes cumulative data over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COALESCE(SUM(provisioned), 0)
                FROM `{self.project_id}.{self.dataset_id}.company_events`
                WHERE company = @customer_name
                    AND type = 'provisioned'
                    AND provisioned IS NOT NULL
                    AND DATE(timestamp) <= day
            ) as total_provisioned
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Provisioned"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.total_provisioned])
            value = row.total_provisioned  # Last value

        return {"value": value, "history": history}

    def _get_users_active_7d_window_30d(self, customer_name):
        """Get 7-day active users using sliding window over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COUNT(DISTINCT user)
                FROM `{self.project_id}.{self.dataset_id}.user_events`
                WHERE company = @customer_name
                    AND type IN ('call', 'dialin')
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as sdau
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "7DAU"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.sdau])
            value = row.sdau  # Last value

        return {"value": value, "history": history}

    def _get_dialin_count_7d_window_30d(self, customer_name):
        """Get dialin session counts using 7-day sliding window over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COUNT(*)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'dialin'
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as dialins
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Dialins"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.dialins])
            value = row.dialins  # Last value (including 0)

        return {"value": value, "history": history}

    # Column 3 Cards
    def _get_users_registered_cumulative_30d(self, customer_name):
        """Get registered user totals cumulative over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COUNT(*)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'register'
                    AND DATE(timestamp) <= day
            ) as total_registered
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Cumulative Reg. Users"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.total_registered])
            value = row.total_registered  # Last value

        return {"value": value, "history": history}

    def _get_calls_count_7d_window_30d(self, customer_name):
        """Get call counts using 7-day sliding window over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COUNT(*)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'call'
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as calls
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Calls"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.calls])
            value = row.calls  # Last value (including 0)

        return {"value": value, "history": history}

    def _get_support_tickets_7d_window_30d(self, customer_name):
        """Get support ticket counts using 7-day sliding window over 30 days."""
        query = f"""
        WITH all_days AS (
            SELECT day
            FROM UNNEST(GENERATE_DATE_ARRAY(
                DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY), 
                CURRENT_DATE()
            )) AS day
        )
        SELECT 
            day,
            (
                SELECT COUNT(*)
                FROM `{self.project_id}.events.user_events`
                WHERE company = @customer_name
                    AND type = 'support_ticket'
                    AND DATE(timestamp) >= DATE_SUB(day, INTERVAL 6 DAY)
                    AND DATE(timestamp) <= day
            ) as support_tickets
        FROM all_days
        ORDER BY day
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        history = [["Date", "Support Tickets"]]
        value = "--"

        for row in results:
            history.append([row.day.strftime("%b %d"), row.support_tickets])
            value = row.support_tickets  # Last value (including 0)

        return {"value": value, "history": history}

    def _get_comments_recent_7d(self, customer_name):
        """Get recent comments from the last 7 days."""
        query = f"""
        SELECT 
            DATE(timestamp) as comment_date,
            user,
            comment,
            timestamp
        FROM `{self.project_id}.events.user_events`
        WHERE company = @customer_name
            AND type = 'comment'
            AND comment IS NOT NULL
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        ORDER BY timestamp DESC
        LIMIT 50
        """

        results = current_app.bigquery_service.client.query(
            query, job_config=self._get_query_config({"customer_name": customer_name})
        ).result()

        comments_array = []

        for row in results:
            logger.info(row)
            # Format as [comment_text, user_name, timestamp] for enhanced frontend display
            comments_array.append([row.comment, row.user, row.timestamp.isoformat()])

        return comments_array
