# FastAPI CMS

A content management system (CMS) built with FastAPI, providing a modern admin interface for managing content with a clean and responsive UI.

## Features

- User authentication with JWT
- Role-based access control
- Content management for articles, categories, and comments
- Modern responsive admin dashboard built with Bootstrap 5
- RESTful API for CRUD operations
- SQLite database for simplicity (can be replaced with other databases)
- Jinja2 templates for server-side rendering
- Modular architecture with organized routers
- Environment-based configuration using .env files

## Requirements

- Python 3.8+
- FastAPI
- SQLModel (SQLAlchemy + Pydantic)
- Bootstrap 5 (served via CDN)
- Other dependencies listed in requirements.txt

## Installation

1. Clone this repository:

   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

3. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Configure your environment:
   ```
   # Copy the example .env file
   cp .env.example .env
   # Edit the .env file with your own settings
   ```

## Running the Application

1. Start the application:

   ```
   fastapi dev app/main.py
   ```

   Or for production:

   ```
   fastapi run
   ```

2. Access the application:
   - Home Page: [http://localhost:8000/](http://localhost:8000/)
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Admin Interface: [http://localhost:8000/admin/login](http://localhost:8000/admin/login)

## Default Admin User

A default admin user is created automatically when you first run the application:

- Username: `admin`
- Password: `admin`

Be sure to change these credentials in a production environment by modifying the .env file.

## Configuration

The application uses a `.env` file to configure various settings. The following settings can be configured:

```
# App settings
APP_NAME="FastAPI CMS"
APP_DESCRIPTION="A Content Management System built with FastAPI"
DEBUG=true
ENV=development

# Security settings
JWT_SECRET_KEY="your-secret-key"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS settings
CORS_ALLOW_ORIGINS_STR='["http://localhost:8000", "http://127.0.0.1:8000"]'

# Database settings
DATABASE_URL="sqlite:///db.sqlite3"

# Admin user
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="admin"
```

For production deployments, you should change at least:

- Set `DEBUG` to `false`
- Set `ENV` to `production`
- Generate a secure `JWT_SECRET_KEY`
- Change the admin credentials

## Project Structure

- `app/`: Main application package
  - `main.py`: FastAPI application entry point
  - `models.py`: Database models using SQLModel
  - `config.py`: Application configuration
  - `database.py`: Database connection and session management
  - `api/`: API router modules
  - `auth/`: Authentication related modules
  - `routers/`: Admin interface routers
- `templates/`: Jinja2 templates
  - `admin/`: Admin dashboard templates
  - `index.html`: Homepage template
- `static/`: Static files directory (CSS, JS, etc.)
- `media/`: Media uploads directory
- `.env`: Environment configuration
- `requirements.txt`: Python dependencies

## Admin Dashboard Features

The admin dashboard provides a comprehensive interface for managing all aspects of your CMS:

- **Dashboard**: Overview of site statistics and recent content
- **Users Management**: Create, edit, and delete users with role assignment
- **Categories Management**: Organize your content with categories
- **Articles Management**: Create and manage articles with rich text content
- **Comments Management**: Moderate user comments

## API Endpoints

### Authentication

- `POST /token`: Get JWT token

### Users

- `POST /api/users/`: Create a new user
- `GET /api/users/me`: Get current user info

### Categories

- `POST /api/categories/`: Create a new category
- `GET /api/categories/`: List all categories
- `GET /api/categories/{category_id}`: Get a specific category

### Articles

- `POST /api/articles/`: Create a new article
- `GET /api/articles/`: List all articles
- `GET /api/articles/{article_id}`: Get a specific article

### Comments

- `POST /api/comments/`: Create a new comment
- `GET /api/comments/`: List all comments
- `GET /api/comments/{comment_id}`: Get a specific comment

## Development

To clear the database and start fresh:

```
rm -f db.sqlite3*
```

The application will create a new database with the default admin user on startup.

## Database

This application uses SQLModel (SQLAlchemy + Pydantic) for database models.

### Database Models

The application uses SQLModel to define models with the following structure:

- User: Represents system users with authentication data
- Category: Content categories for organizing articles
- Article: The main content type with title, content, author relationship
- Comment: User comments on articles

Models are defined in `app/models.py`.

### Database Migrations

By default, the application creates all database tables on startup using SQLModel. If you need more sophisticated migrations, you can set up Alembic:

1. Install Alembic:

   ```bash
   pip install alembic
   ```

2. Initialize Alembic:

   ```bash
   alembic init migrations
   ```

3. Configure Alembic to use your database by editing `alembic.ini` and `migrations/env.py`

4. Create a migration:

   ```bash
   alembic revision --autogenerate -m "initial"
   ```

5. Run migrations:
   ```bash
   alembic upgrade head
   ```

The Docker setup includes support for running migrations via the entrypoint script.

## Docker Deployment

To run the application using Docker:

```bash
# Build the Docker image
docker build -t fastapi-cms .

# Run with default settings
docker run -p 8000:8000 fastapi-cms

# Or run with custom environment variables
docker run -p 8000:8000 \
  -e JWT_SECRET_KEY="your-secure-key" \
  -e ADMIN_PASSWORD="secure-password" \
  -e DEBUG=false \
  -e ENV=production \
  fastapi-cms
```

For persistent data, you can mount volumes:

```bash
docker run -p 8000:8000 \
  -v ./data:/app/data \
  -v ./static:/app/static \
  -v ./media:/app/media \
  fastapi-cms
```

The Docker entrypoint script (`docker-entrypoint.sh`) automatically:

1. Creates necessary directories
2. Can run database migrations before starting the app
3. Starts the FastAPI application

## License

MIT
