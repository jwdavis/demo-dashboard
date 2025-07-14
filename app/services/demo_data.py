import random
import time
from collections import defaultdict
from datetime import datetime, timedelta

from flask import current_app, jsonify, request
from google.api_core import exceptions
from google.cloud import firestore, firestore_admin_v1
from google.cloud.firestore_admin_v1.types import Database
from google.cloud.firestore_admin_v1.types.firestore_admin import CreateDatabaseRequest

from ..utils import get_logger
from ..utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class DemoDataService:
    """Generate demo data for dashboard (users, companies, events, renewals)."""

    def __init__(self, app):
        # Core configuration
        self.project_id = app.cfg.project
        self.good_comments = app.cfg.good_comments
        self.bad_comments = app.cfg.bad_comments
        self.operating_systems = app.cfg.operating_systems
        self.call_types = app.cfg.call_types
        self.drivers = app.cfg.drivers
        self.project_list = app.cfg.project_list
        self.metric_list = app.cfg.metric_list

        # Demo data generation limits
        self.demo_min_projects_per_company = app.cfg.demo_min_projects_per_company
        self.demo_max_projects_per_company = app.cfg.demo_max_projects_per_company
        self.demo_project_start_delay_days = app.cfg.demo_project_start_delay_days
        self.demo_trending_metrics_count = app.cfg.demo_trending_metrics_count
        self.demo_trending_data_interval_days = app.cfg.demo_trending_data_interval_days
        self.demo_trending_data_period_days = app.cfg.demo_trending_data_period_days
        self.demo_min_renewal_days = app.cfg.demo_min_renewal_days
        self.demo_max_renewal_days = app.cfg.demo_max_renewal_days
        self.demo_max_reg_delay_minutes = app.cfg.demo_max_reg_delay_minutes

        # Services
        self.bigquery_service = app.bigquery_service
        self.firestore_service = app.firestore_service

    def create_demo_data(self, user_limit):
        """Create complete demo dataset (users, companies, events, renewals)."""
        logger.info("Starting demo data creation", user_limit=user_limit)
        try:
            # Create core collections
            users = self._create_user_collection(user_limit)
            companies = self._create_company_collection(users)
            projects = self._create_projects_collection(companies)
            trending = self._create_trending_collection(companies)

            # Generate and write company events to BigQuery
            company_events = self._generate_company_events(companies)
            self._clear_bigquery_tables()
            self._write_company_events_to_bigquery(company_events)

            # Generate company updates and create renewals
            company_updates = self._generate_company_updates(company_events)
            renewals = self._create_renewals_collection(company_updates)
            self._update_company_docs_with_purchases_and_provisions(company_updates)

            # Generate and write user events to BigQuery
            user_events = self._generate_user_events(users)
            self._write_user_events_to_bigquery(user_events)

            return {
                "success": True,
                "message": "Demo data created successfully",
                "stats": {
                    "users": len(users),
                    "companies": len(companies),
                    "projects": len(projects),
                    "trending_entries": len(trending),
                    "renewals": len(renewals),
                    "company_events": len(company_events),
                    "user_events": len(user_events),
                },
            }

        except Exception as e:
            logger.error("Demo data creation failed", error=str(e))
            return {
                "success": False,
                "message": f"Demo data creation failed: {str(e)}",
                "error": str(e),
            }

    def _create_user_collection(self, user_limit):
        """Create users collection with demo user data."""
        logger.info("Deleting existing user documents")
        try:
            deleted_count = current_app.firestore_service.delete_all_documents("users")
            logger.info(f"Deleted {deleted_count} existing user documents")
        except Exception as e:
            logger.error("Failed to delete existing user documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to delete existing user documents: {str(e)}"
            )

        users = self._get_users(user_limit)

        if not users:
            logger.warning("No users data available")
            raise ExternalServiceError(
                "No user records found in BigQuery database. Cannot generate demo data without source user data."
            )

        users = self._create_user_docs(users)

        try:
            current_app.firestore_service.batch_write("users", users)
        except Exception as e:
            logger.error("Failed to write user documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to create user documents: {str(e)}"
            )

        logger.info("User documents created successfully")
        return users

    def _create_company_collection(self, users):
        """Create companies collection with demo company data."""
        logger.info("Deleting existing company documents")
        try:
            deleted_count = current_app.firestore_service.delete_all_documents(
                "companies"
            )
            logger.info(f"Deleted {deleted_count} existing company documents")
        except Exception as e:
            logger.error("Failed to delete existing company documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to delete existing company documents: {str(e)}"
            )

        companies = self._create_company_docs(users)

        try:
            current_app.firestore_service.batch_write("companies", companies)
        except Exception as e:
            logger.error("Failed to write company documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to create company documents: {str(e)}"
            )

        logger.info("Company documents created successfully")
        return companies

    def _create_projects_collection(self, companies):
        """Create projects collection with demo project data."""
        logger.info("Deleting existing project documents")
        try:
            deleted_count = current_app.firestore_service.delete_all_documents(
                "projects"
            )
            logger.info(f"Deleted {deleted_count} existing project documents")
        except Exception as e:
            logger.error("Failed to delete existing project documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to delete existing project documents: {str(e)}"
            )

        projects = self._create_project_docs(companies)

        try:
            current_app.firestore_service.batch_write("projects", projects)
        except Exception as e:
            logger.error("Failed to write project documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to create project documents: {str(e)}"
            )

        logger.info("Projects collection created successfully")
        return projects

    def _create_trending_collection(self, companies):
        """Create trending metrics collection with demo data."""
        logger.info("Deleting existing trending documents")
        try:
            deleted_count = current_app.firestore_service.delete_all_documents(
                "trending"
            )
            logger.info(f"Deleted {deleted_count} existing trending documents")
        except Exception as e:
            logger.error("Failed to delete existing trending documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to delete existing trending documents: {str(e)}"
            )

        trending_data = self._create_trending_data_docs(companies)

        try:
            current_app.firestore_service.batch_write("trending", trending_data)
        except Exception as e:
            logger.error("Failed to write trending documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to create trending documents: {str(e)}"
            )

        logger.info("Trending collection created successfully")
        return trending_data

    def _create_renewals_collection(self, company_updates):
        """Create renewals collection with renewal dates and details."""
        logger.info("Deleting existing renewal documents")
        try:
            deleted_count = current_app.firestore_service.delete_all_documents(
                "renewals"
            )
            logger.info(f"Deleted {deleted_count} existing renewal documents")
        except Exception as e:
            logger.error("Failed to delete existing renewal documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to delete existing renewal documents: {str(e)}"
            )

        renewals = self._create_renewal_docs(company_updates)

        try:
            current_app.firestore_service.batch_write("renewals", renewals)
        except Exception as e:
            logger.error("Failed to write renewal documents", error=str(e))
            raise ExternalServiceError(
                f"Firestore service failed to create renewal documents: {str(e)}"
            )

        logger.info("Renewals collection created successfully")
        return renewals

    def _get_users(self, user_limit):
        """Fetch user data from BigQuery with optional limit."""
        try:
            limit_clause = f"LIMIT {user_limit}" if user_limit else ""
            query = f"""
            SELECT email, company, offset FROM `success-hq.datastore.user`
            ORDER BY email {limit_clause}
            """

            return current_app.bigquery_service.execute_query(query)
        except Exception as e:
            logger.error("Failed to fetch users data", error=str(e))
            raise ExternalServiceError(
                f"BigQuery service failed to fetch user data: {str(e)}"
            )

    def _create_user_docs(self, users):
        """Process users data to create Firestore documents."""
        user_docs = []

        for user in users:
            reg_date = datetime.now() + timedelta(
                days=-user["offset"],
                minutes=-random.randint(0, self.demo_max_reg_delay_minutes),
            )
            user["reg_date"] = reg_date
            del user["offset"]  # Remove offset as it's not needed in the document
            user_docs.append(user)

        logger.info("Processed users", count=len(user_docs))
        return user_docs

    def _create_company_docs(self, users):
        """Create company documents from user data."""
        companies_users = defaultdict(list)
        for user in users:
            companies_users[user["company"]].append(user)

        company_docs = [
            {
                "name": company_name,
                "earliest_reg": min(user["reg_date"] for user in company_users),
                "boxes_bought": 0,
                "boxes_prov": 0,
            }
            for company_name, company_users in companies_users.items()
        ]

        logger.info("Created companies", count=len(company_docs))
        return company_docs

    def _create_project_docs(self, companies):
        """Generate project documents for each company."""
        projects = []

        for company in companies:
            num_projects = random.randint(
                self.demo_min_projects_per_company, self.demo_max_projects_per_company
            )

            # Calculate the period start and end dates
            period_start = company["earliest_reg"] + timedelta(
                days=90
            )  # 90 days after earliest reg
            period_end = datetime.now() + timedelta(
                days=30
            )  # 30 days after current date

            # Only create projects if the period makes sense (start before end)
            if period_start >= period_end:
                # Skip this company if the time period is invalid
                continue

            period_length_days = (period_end - period_start).days

            # Distribute projects roughly equally across the period
            if num_projects > 0:
                # Calculate interval between projects
                interval_days = period_length_days / num_projects

                # Generate project dates with some randomness around the equal distribution
                project_dates = []
                for i in range(num_projects):
                    # Base position for this project (evenly spaced)
                    base_days = i * interval_days

                    # Add some randomness (+/- 25% of interval) to avoid exact spacing
                    randomness_range = max(1, int(interval_days * 0.25))
                    random_offset = random.randint(-randomness_range, randomness_range)

                    # Calculate final date
                    final_days = max(
                        0, min(period_length_days - 1, base_days + random_offset)
                    )
                    project_date = period_start + timedelta(days=final_days)
                    project_dates.append(project_date)

                # Ensure at least one project is after current date
                current_date = datetime.now()
                future_projects = [d for d in project_dates if d > current_date]

                if not future_projects:
                    # Replace the latest project with one that's definitely in the future
                    # Ensure it's between tomorrow and the period end
                    future_start = current_date + timedelta(days=1)
                    if future_start < period_end:
                        future_range_days = (period_end - future_start).days
                        if future_range_days > 0:
                            random_future_days = random.randint(
                                0, future_range_days - 1
                            )
                            project_dates[-1] = future_start + timedelta(
                                days=random_future_days
                            )

                # Create project documents
                for project_date in project_dates:
                    project_name = random.choice(self.project_list)
                    project = {
                        "name": project_name,
                        "company": company["name"],
                        "date": project_date,
                    }
                    projects.append(project)

        logger.info("Created projects", count=len(projects))
        return projects

    def _create_trending_data_docs(self, companies):
        trending_data = []

        for company in companies:
            for metric in self.metric_list[
                : self.demo_trending_metrics_count
            ]:  # Use first N metrics
                for days_offset in range(
                    0,
                    self.demo_trending_data_period_days,
                    self.demo_trending_data_interval_days,
                ):  # Interval data points
                    date = datetime.now() - timedelta(days=days_offset)
                    value = random.uniform(10.0, 100.0)

                    trending = {
                        "metric": metric,
                        "company": company["name"],
                        "value": round(value, 2),
                        "date": date,
                    }
                    trending_data.append(trending)

        logger.info("Created trending data", count=len(trending_data))
        return trending_data

    def _generate_company_events(self, companies):
        """Generate purchase/provision events for companies."""
        logger.info("Generating company events")
        all_events = []

        for company in companies:
            company_name = company["name"]
            reg_date = company["earliest_reg"]

            # Generate events for this company (similar to build_company_events in beam code)
            company_events = self._build_company_events(company_name, reg_date)
            all_events.extend(company_events)

        logger.info(f"Generated {len(all_events)} total company events")
        return all_events

    def _build_company_events(self, company_name, reg_date):
        """Build events for a single company based on the beam logic.

        Args:
            company_name: Name of the company
            reg_date: Registration date of the company

        Returns:
            List of event dictionaries for this company
        """
        event_list = []

        # Initial purchase event
        initial_purchase = random.randint(1, 15)
        pur_event = {
            "timestamp": reg_date.isoformat(),
            "type": "purchased",
            "company": company_name,
            "purchased": initial_purchase,
            "provisioned": None,
            "serial_number": None,
            "box_name": None,
        }
        event_list.append(pur_event)

        # Initial provisioning events
        prov_date = reg_date + timedelta(days=random.randint(2, 14))
        initial_prov = random.randint(1, initial_purchase)

        for device in range(initial_prov):
            prov_event = {
                "timestamp": prov_date.isoformat(),
                "type": "provisioned",
                "company": company_name,
                "purchased": None,
                "provisioned": 1,
                "serial_number": f"A{random.randint(100000, 2000000)}",
                "box_name": f"{company_name}.room.{device+1:02d}",
            }
            event_list.append(prov_event)

        # Calculate time-based parameters
        seconds = (datetime.now() - reg_date).total_seconds()
        days_since_reg = int(seconds / 86400)
        months_since_reg = int(days_since_reg / 30) + 1

        # Additional purchases and provisioning
        boxes = initial_prov
        last_purchase_date = reg_date
        purchases = int(random.randint(1, 2) * months_since_reg)

        for purchase in range(1, purchases):
            purchased = random.randint(5, 15)
            purchase_fraction = purchase / purchases
            last_purchase_date = (
                reg_date + (datetime.now() - reg_date) * purchase_fraction
            )

            # Purchase event
            pur_event = {
                "timestamp": last_purchase_date.isoformat(),
                "type": "purchased",
                "company": company_name,
                "purchased": purchased,
                "provisioned": None,
                "serial_number": None,
                "box_name": None,
            }
            event_list.append(pur_event)

            # Provisioning events for this purchase
            prov_date = last_purchase_date + timedelta(days=random.randint(2, 14))
            last_prov = random.randint(purchased // 2, purchased)

            for device in range(1, last_prov + 1):
                boxes += 1
                prov_event = {
                    "timestamp": prov_date.isoformat(),
                    "type": "provisioned",
                    "company": company_name,
                    "purchased": None,
                    "provisioned": 1,
                    "serial_number": f"A{random.randint(100000, 2000000)}",
                    "box_name": f"{company_name}.room.{boxes:02d}",
                }
                event_list.append(prov_event)

        return event_list

    def _clear_bigquery_tables(self):
        logger.info("Clearing existing BigQuery table data")
        tables_to_clear = ["company_events", "user_events"]

        for table_name in tables_to_clear:
            try:
                result = self.bigquery_service.delete_all_rows(table_name)
                if result["success"]:
                    logger.info(f"Successfully cleared table {table_name}")
                else:
                    logger.warning(
                        f"Failed to clear table {table_name}: {result['message']}"
                    )
            except Exception as e:
                logger.warning(f"Could not clear table {table_name}: {str(e)}")

        # Add a brief delay after clearing tables to ensure BigQuery is ready
        # This helps prevent "Table not found" errors when writing immediately after truncation
        logger.info("Waiting for BigQuery table state to stabilize after truncation...")
        time.sleep(2)

    def _write_company_events_to_bigquery(self, company_events):
        logger.info(f"Writing {len(company_events)} company events to BigQuery")

        try:
            result = self.bigquery_service.write_rows_to_table(
                "company_events", company_events
            )
            if result["success"]:
                logger.info(
                    f"Successfully wrote {result['rows_inserted']} company events to BigQuery"
                )
            else:
                raise ExternalServiceError(
                    f"Failed to write company events: {result['message']}"
                )

        except Exception as e:
            logger.error("Failed to write company events to BigQuery", error=str(e))
            raise ExternalServiceError(
                f"BigQuery service failed to write company events: {str(e)}"
            )

    def _generate_company_updates(self, company_events):
        logger.info("Generating company updates from company events")

        # Dictionary to collect purchases per company
        purchases = {}
        provisions = {}

        # Process all company events to extract purchased and provisioned amounts
        for event in company_events:
            company = event["company"]

            if event["type"] == "purchased":
                if company not in purchases:
                    purchases[company] = 0
                purchases[company] += event["purchased"]

            elif event["type"] == "provisioned":
                if company not in provisions:
                    provisions[company] = 0
                provisions[company] += event["provisioned"]

        # Build company_updates in the format expected by beam pipeline
        # Structure: (company_name, {'purchased': [total_purchased], 'provisioned': [total_provisioned]})
        company_updates = []

        # Get all companies that have either purchases or provisions
        all_companies = set(purchases.keys()) | set(provisions.keys())

        for company in all_companies:
            purchased_total = purchases.get(company, 0)
            provisioned_total = provisions.get(company, 0)

            company_update = (
                company,
                {"purchased": [purchased_total], "provisioned": [provisioned_total]},
            )
            company_updates.append(company_update)

        logger.info(f"Generated {len(company_updates)} company updates")
        return company_updates

    def _create_renewal_docs(self, company_updates):
        """
        Create renewal documents based on company updates using the beam logic.

        Replicates the build_renewal_entities function from beam code:
        - Calculates amount as purchased total * 2499
        - Generates random health score with specific distribution
        - Creates renewal with due date, amount, health, and company
        """
        renewals = []

        for company_update in company_updates:
            company_name = company_update[0]
            update_data = company_update[1]

            # Calculate amount based on purchased total (beam logic)
            purchased_total = update_data["purchased"][0]
            amount = purchased_total * 2499

            # Generate health score using same distribution as beam code
            health_index = random.randint(0, 5)
            if health_index < 1:
                health = random.randint(10, 30)
            elif health_index < 3:
                health = random.randint(30, 60)
            else:
                health = random.randint(60, 100)

            # Create renewal document
            renewal = {
                "company": company_name,
                "amount": amount,
                "health": health,
                "due": datetime.now() + timedelta(days=random.randint(30, 120)),
            }
            renewals.append(renewal)

        logger.info(f"Created {len(renewals)} renewal documents")
        return renewals

    def _generate_user_events(self, users):
        """
        Generate user events based on the beam logic.
        Creates three types of events: registration, tickets, and calls.

        Args:
            users: List of user documents with email, company, and reg_date

        Returns:
            List of all user event dictionaries combined
        """
        logger.info("Generating user events")

        # Generate each type of event
        reg_events = self._generate_registration_events(users)
        ticket_events = self._generate_ticket_events(users)
        call_events = self._generate_call_events(users)

        # Combine all events (equivalent to beam.Flatten())
        all_events = reg_events + ticket_events + call_events

        logger.info(f"Generated {len(all_events)} total user events")
        logger.info(f"  Registration events: {len(reg_events)}")
        logger.info(f"  Ticket events: {len(ticket_events)}")
        logger.info(f"  Call events: {len(call_events)}")

        return all_events

    def _generate_registration_events(self, users):
        """Generate registration events for users (beam: build_reg_event)."""
        reg_events = []

        for user in users:
            event = {
                "timestamp": user["reg_date"].isoformat(),
                "type": "register",
                "user": user["email"],
                "company": user["company"],
                # Set all other fields to None for consistency with beam logic
                "call_duration": None,
                "call_type": None,
                "call_num_users": None,
                "rating": None,
                "comment": None,
                "session_id": None,
                "dialin_duration": None,
                "ticket_number": None,
                "ticket_driver": None,
                "call_os": None,
            }
            reg_events.append(event)

        return reg_events

    def _generate_ticket_events(self, users):
        """Generate support ticket events for users (beam: build_ticket_events)."""
        ticket_events = []

        for user in users:
            seconds = (datetime.now() - user["reg_date"]).total_seconds()
            days_since_reg = int(seconds / 86400)
            troubley = random.randint(0, 3)
            tickets = int(days_since_reg / (4 - troubley) / 2)

            for ticket in range(tickets):
                event_date = user["reg_date"] + timedelta(
                    seconds=int(seconds / tickets / 1.1) * ticket
                )

                event = {
                    "timestamp": event_date.isoformat(),
                    "type": "support_ticket",
                    "user": user["email"],
                    "company": user["company"],
                    "ticket_number": f"{user['email']}-{ticket}",
                    "ticket_driver": random.choice(self.drivers),
                    # Set all other fields to None
                    "call_duration": None,
                    "call_type": None,
                    "call_num_users": None,
                    "rating": None,
                    "comment": None,
                    "session_id": None,
                    "dialin_duration": None,
                    "call_os": None,
                }
                ticket_events.append(event)

        return ticket_events

    def _generate_call_events(self, users):
        """Generate call-related events for users (beam: build_call_events)."""
        call_events = []

        for user in users:
            os = random.choice(self.operating_systems)
            seconds = (datetime.now() - user["reg_date"]).total_seconds()
            days_since_reg = int(seconds / 86400)
            freq = random.randint(1, 10)

            calls = int(days_since_reg / (11 - freq) * 10)

            happy = random.randint(0, 2)
            ratey = random.randint(0, 2)
            commenty = random.randint(0, 2)
            chatty = random.randint(0, 4)
            seed = datetime(1980, 1, 1, 1, 0)

            call_num = 0

            for call in range(calls):
                call_num += 1

                # Determine if caller was happy
                call_happy_score = random.randint(0, 99)
                call_happy = call_happy_score >= (happy * 25)

                # Determine rating
                call_rating_score = random.randint(0, 99)
                if call_rating_score <= (ratey * 40):
                    if call_happy:
                        call_rating = random.randint(4, 5)
                    else:
                        call_rating = random.randint(1, 3)
                else:
                    call_rating = None

                # Determine comment
                call_comment_score = random.randint(0, 99)
                if call_comment_score <= (commenty * 33 * ratey / 3):
                    if call_rating and call_rating >= 3:
                        call_comment = random.choice(self.good_comments)
                    else:
                        call_comment = random.choice(self.bad_comments)
                else:
                    call_comment = None

                # Determine call length
                call_length = chatty * random.randint(5, 20)

                # Determine if dialin session
                call_dialin_score = random.randint(0, 99)
                if call_dialin_score < 40:
                    dialin_length = call_length
                else:
                    dialin_length = None

                # Determine call type
                call_type_score = random.randint(0, 99)
                if call_type_score < 35:
                    call_type = self.call_types[0]
                elif call_type_score < 70:
                    call_type = self.call_types[1]
                elif call_type_score < 90:
                    call_type = self.call_types[2]
                else:
                    call_type = self.call_types[3]

                # Determine number of callers
                call_size_score = random.randint(0, 99)
                if call_size_score < 35:
                    call_users = 2
                elif call_size_score < 70:
                    call_users = 3
                elif call_size_score < 95:
                    call_users = 4
                else:
                    call_users = call_size_score - 90 + 5

                # Calculate event date
                shift = int(seconds / calls + random.randint(-1000, 1000)) * call_num
                event_date = user["reg_date"] + timedelta(seconds=shift)
                if event_date > datetime.now():
                    event_date = datetime.now()

                session_id = (
                    str((datetime.now() - seed).total_seconds()) + "." + str(call)
                )

                # Create call event
                call_event = {
                    "timestamp": event_date.isoformat(),
                    "type": "call",
                    "user": user["email"],
                    "company": user["company"],
                    "call_duration": call_length,
                    "call_type": call_type,
                    "call_num_users": call_users,
                    "call_os": os,
                    "session_id": session_id,
                    "rating": None,
                    "comment": None,
                    "dialin_duration": None,
                    "ticket_number": None,
                    "ticket_driver": None,
                }
                call_events.append(call_event)

                # Create load event (1 minute before call)
                load_event = {
                    "timestamp": (event_date - timedelta(minutes=1)).isoformat(),
                    "type": "load",
                    "user": user["email"],
                    "company": user["company"],
                    "call_duration": None,
                    "call_type": None,
                    "call_num_users": None,
                    "rating": None,
                    "comment": None,
                    "session_id": None,
                    "dialin_duration": None,
                    "ticket_number": None,
                    "ticket_driver": None,
                    "call_os": None,
                }
                call_events.append(load_event)

                # Create rating event if rating exists
                if call_rating:
                    rating_event = {
                        "timestamp": event_date.isoformat(),
                        "type": "rating",
                        "user": user["email"],
                        "company": user["company"],
                        "rating": call_rating,
                        "session_id": session_id,
                        "call_duration": None,
                        "call_type": None,
                        "call_num_users": None,
                        "comment": None,
                        "dialin_duration": None,
                        "ticket_number": None,
                        "ticket_driver": None,
                        "call_os": None,
                    }
                    call_events.append(rating_event)

                # Create comment event if comment exists
                if call_comment:
                    comment_event = {
                        "timestamp": event_date.isoformat(),
                        "type": "comment",
                        "user": user["email"],
                        "company": user["company"],
                        "comment": call_comment,
                        "session_id": session_id,
                        "call_duration": None,
                        "call_type": None,
                        "call_num_users": None,
                        "rating": None,
                        "dialin_duration": None,
                        "ticket_number": None,
                        "ticket_driver": None,
                        "call_os": None,
                    }
                    call_events.append(comment_event)

                # Create dialin event if dialin exists
                if dialin_length:
                    dialin_event = {
                        "timestamp": event_date.isoformat(),
                        "type": "dialin",
                        "user": user["email"],
                        "company": user["company"],
                        "call_duration": dialin_length,
                        "call_type": None,
                        "call_num_users": None,
                        "rating": None,
                        "comment": None,
                        "session_id": None,
                        "dialin_duration": None,
                        "ticket_number": None,
                        "ticket_driver": None,
                        "call_os": None,
                    }
                    call_events.append(dialin_event)

        return call_events

    def _write_user_events_to_bigquery(self, user_events):
        """Write user events to BigQuery user_events table."""
        logger.info(f"Writing {len(user_events)} user events to BigQuery")

        try:
            result = self.bigquery_service.write_rows_to_table(
                "user_events", user_events
            )
            if result["success"]:
                logger.info(
                    f"Successfully wrote {result['rows_inserted']} user events to BigQuery"
                )
            else:
                raise ExternalServiceError(
                    f"Failed to write user events: {result['message']}"
                )

        except Exception as e:
            logger.error("Failed to write user events to BigQuery", error=str(e))
            raise ExternalServiceError(
                f"BigQuery service failed to write user events: {str(e)}"
            )

    def _update_company_docs_with_purchases_and_provisions(self, company_updates):
        """Update company documents with purchase/provision totals."""
        logger.info("Updating company documents with purchased and provisioned values")
        updated_count = 0

        for company_update in company_updates:
            company_name = company_update[0]
            update_data = company_update[1]
            purchased_total = update_data.get("purchased", [0])[0]
            provisioned_total = update_data.get("provisioned", [0])[0]

            # Prepare the update data
            update_fields = {
                "boxes_bought": purchased_total,
                "boxes_prov": provisioned_total,
            }

            try:
                # Update the company document in Firestore by searching for the company name
                current_app.firestore_service.update_document_by_field(
                    collection_name="companies",
                    field_name="name",
                    field_value=company_name,
                    update_fields=update_fields,
                )
                updated_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to update company document for {company_name}",
                    error=str(e),
                )

        logger.info(
            f"Updated {updated_count} company documents with purchase/provision data"
        )
