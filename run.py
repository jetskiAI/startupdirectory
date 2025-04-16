"""
Purpose: Main entry point for the application
Features:
- Creates and runs the Flask application
- Sets debug mode to True for development
- Handles command line arguments
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
