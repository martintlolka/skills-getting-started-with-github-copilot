# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Unregister from activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/signup?email=student@mergington.edu` | Unregister from an activity                                          |

Signup returns `409` if the student is already registered. Both signup and
unregister return `404` for an unknown activity; unregister also returns `404`
if the student is not registered. Both require the `email` query parameter
and return `422` when it is missing.

Concurrent participant changes are synchronized within each application process.
The activity list refreshes after successful signup and unregister requests.
Only the latest refresh updates the page, so delayed responses cannot restore
removed participants or stale availability counts. Keyboard focus stays near
the removed participant, falling back to the activity heading when needed.

## Testing

From the repository root, install the dependencies and run the backend tests:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

The suite lives in `tests/` and uses pytest with FastAPI's `TestClient`, so no
running server is needed. The dependencies include `httpx2`, the HTTP client
used by Starlette's `TestClient`. Each test receives a fresh copy of the in-memory
activity data to prevent changes from leaking between tests.

Follow Arrange-Act-Assert (AAA) when adding tests: arrange inputs and expected
results, act by making HTTP requests, then assert responses and resulting state.
Keep these phases separated by blank lines.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
Separate server processes do not share activity data.
