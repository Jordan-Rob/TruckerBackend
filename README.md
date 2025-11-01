# SpotterAI Backend API

Django REST Framework API for truck route planning and ELD (Electronic Logging Device) log generation.

## Features

- Route calculation between multiple locations using OpenRouteService
- Hours of Service (HOS) compliance for property-carrying drivers (70hrs/8days)
- ELD log generation with daily segments
- Automatic stop planning (fueling, breaks, rest periods)
- Comprehensive API documentation with Swagger UI

## Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- OpenRouteService API key (get one free at [openrouteservice.org](https://openrouteservice.org/dev/#/signup))

## Setup

### 1. Create and activate virtual environment

Make sure the virtual environment is located in the project-folder folder:

```bash
cd project-folder
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create environment file

Create a `.env` file in the `backend` directory:

```bash
# Required: OpenRouteService API key
ORS_API_KEY=your_api_key_here

# Optional: Django configuration
DJANGO_SECRET_KEY=your-secret-key-here  # Optional: defaults to insecure dev key
DJANGO_DEBUG=True  # Set to False in production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1  # Comma-separated list

```

**Important:** Replace `your_api_key_here` with your actual OpenRouteService API key.

### 4. Run database migrations

```bash
python manage.py migrate
```

### 5. Create superuser (optional)

To access Django admin panel:

```bash
python manage.py createsuperuser
```

## Running the Development Server

```bash
python manage.py runserver
```

The API will be available at:
- API Base: `http://127.0.0.1:8000/api/`
- API Documentation (Swagger UI): `http://127.0.0.1:8000/api/docs/`
- Django Admin: `http://127.0.0.1:8000/admin/`

## API Endpoints

### Health Check
- `GET /api/health/` - Check API health status

### Trip Planning
- `POST /api/plan_trip/` - Plan a trip route
  - Query parameter: `?save=1` to persist trip in database

### ELD Logs
- `GET /api/eld_logs/?trip_id=<id>` - Generate ELD logs from saved trip
- `GET /api/eld_logs/?duration_s=<seconds>&current_cycle_hours_used=<hours>` - Generate ELD logs from duration

For detailed API documentation, visit `/api/docs/` when the server is running.

## Testing

### Run all tests

```bash
pytest
```

### Run tests with coverage

```bash
pytest --cov=planner --cov-report=html
```

### Run specific test file

```bash
pytest planner/tests/test_plan_trip_endpoint.py
```

### Run specific test

```bash
pytest planner/tests/test_plan_trip_endpoint.py::test_plan_trip_success
```

### Run tests in verbose mode

```bash
pytest -v
```

## Code Quality Checks

### Code Formatting with Black

```bash
# Check formatting
black --check .

# Format code
black .
```

### Linting with Flake8

```bash
flake8 .
```

### Type Checking with mypy

```bash
mypy planner/
```

### Run all code checks

```bash
black --check . && flake8 . && mypy planner/
```

## Project Structure

```
backend/
├── config/              # Django project settings
│   ├── settings.py     # Main settings file
│   └── urls.py         # Root URL configuration
├── planner/            # Main application
│   ├── models.py       # Database models
│   ├── views.py        # API views
│   ├── serializers.py  # DRF serializers
│   ├── urls.py         # App URL patterns
│   ├── services/       # Business logic
│   │   ├── route_service.py  # Route calculation service
│   │   └── eld_service.py    # ELD log generation service
│   └── tests/          # Test suite
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
├── pytest.ini         # Pytest configuration
└── .env               # Environment variables (create this)
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ORS_API_KEY` | OpenRouteService API key | Yes | - |
| `DJANGO_SECRET_KEY` | Django secret key | No | Insecure dev key |
| `DJANGO_DEBUG` | Enable debug mode | No | `False` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts (comma-separated) | No | `*` |

## HOS Rules (Hours of Service)

This API implements property-carrying driver rules:
- **70 hours maximum** within any rolling 8-day period
- **Up to 11 hours driving** per day
- **14-hour duty window** per day
- **34-hour reset** required after reaching 70-hour limit

## Assumptions

- Property-carrying driver, 70hrs/8days cycle
- No adverse driving conditions
- Fueling at least once every 1,000 miles
- 1 hour for pickup and drop-off operations

## Troubleshooting


Make sure you've activated the virtual environment and installed dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### ORS_API_KEY not configured error

Ensure your `.env` file exists in the `backend` directory and contains:
```
ORS_API_KEY=your_actual_api_key
```

### Database errors

Run migrations:
```bash
python manage.py migrate
```

### Port already in use

Use a different port:
```bash
python manage.py runserver 8001
```

## Production Deployment

1. Set `DJANGO_DEBUG=False` in production
2. Set a strong `DJANGO_SECRET_KEY`
3. Configure `DJANGO_ALLOWED_HOSTS` with your domain
4. Configure `CORS_ALLOWED_ORIGINS` for your frontend domain
5. Use a production database (PostgreSQL recommended)
6. Set up static file serving
7. Use a production WSGI server (e.g., Gunicorn)


