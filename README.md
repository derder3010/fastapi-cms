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

## Requirements

- Python 3.8+
- FastAPI
- Tortoise ORM
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

## Running the Application

1. Start the application:
   ```
   uvicorn app.main:app --reload
   ```

2. Access the application:
   - Home Page: [http://localhost:8000/](http://localhost:8000/)
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Admin Interface: [http://localhost:8000/admin/](http://localhost:8000/admin/)

## Default Admin User

A default admin user is created automatically when you first run the application:
- Username: `admin`
- Password: `admin`

Be sure to change these credentials in a production environment.

## Project Structure

- `app/`: Main application package
  - `main.py`: FastAPI application entry point
  - `models.py`: Database models using Tortoise ORM
  - `config.py`: Application configuration
- `templates/`: Jinja2 templates
  - `admin/`: Admin dashboard templates
  - `index.html`: Homepage template
- `static/`: Static files directory (if needed)
- `upload/`: Media uploads directory
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

## Security Considerations

For production use, please ensure you:
1. Change the default admin credentials
2. Generate new secure keys for JWT authentication and other security features
3. Configure CORS appropriately
4. Use a production-ready database like PostgreSQL
5. Set up HTTPS
6. Add rate limiting for authentication endpoints

## License

MIT 