from flask import Flask

from .config import AppConfig
from .services import (
    BigQueryService,
    FirestoreService,
    DemoDataService,
    DashboardService,
)
from .utils import get_logger, setup_logging
from .views import views_bp
from .api import api_bp

logger = get_logger(__name__)


def _initialize_services(app: Flask):
    """Initialize all application services."""
    try:
        app.bigquery_service = BigQueryService(app.cfg)
        logger.info("BigQuery service initialized")
    except Exception as e:
        app.bigquery_service = None
        logger.error(f"Failed to initialize BigQueryService: {e}")

    try:
        app.firestore_service = FirestoreService(app.cfg)
        logger.info("Firestore service initialized")
    except Exception as e:
        app.firestore_service = None
        logger.error(f"Failed to initialize FirestoreService: {e}")

    try:
        app.demo_data_service = DemoDataService(app)
        print(app.demo_data_service)
        logger.info("Demo data service initialized")
    except Exception as e:
        app.demo_data_service = None
        logger.error(f"Failed to initialize DemoDataService: {e}")

    try:
        app.dashboard_service = DashboardService(app)
        logger.info("Dashboard service initialized")
    except Exception as e:
        app.dashboard_service = None
        logger.error(f"Failed to initialize DashboardService: {e}")


def _register_blueprints(app: Flask):
    """Register Flask blueprints."""
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    logger.info("Registered views and API blueprints")


def create_app(config_name: str = None):
    app = Flask(__name__)
    app.cfg = AppConfig()

    setup_logging(app.cfg.log_level)
    logger.info("Creating Flask application")

    _initialize_services(app)
    _register_blueprints(app)
    return app
