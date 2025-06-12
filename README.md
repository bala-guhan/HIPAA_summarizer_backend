# PDF Processing Backend

This is the backend service for the PDF processing application. It handles PDF uploads, content extraction, PHI verification, and document summarization.

## Features

- PDF content extraction
- PHI (Protected Health Information) detection and verification
- Document summarization using AI
- User authentication and authorization
- Secure file handling

## Prerequisites

- Python 3.11 or higher
- Docker (for containerized deployment)
- API keys for:
  - Google AI (for document summarization)
  - Groq (for AI processing)

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your API keys and configuration:
   ```bash
   cp .env.example .env
   ```
5. Download spaCy model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Running Locally

Start the development server:

```bash
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`

## Docker Deployment

1. Build the Docker image:

   ```bash
   docker build -t pdf-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env pdf-backend
   ```

## API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

- `GOOGLE_API_KEY`: Your Google AI API key
- `GROQ_API_KEY`: Your Groq API key
- `SECRET_KEY`: Secret key for JWT token generation
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins

## Directory Structure

```
backend/
├── data/               # Directory for storing processed files
├── main.py            # FastAPI application entry point
├── auth.py            # Authentication and authorization
├── extract.py         # PDF content extraction
├── deidentify.py      # PHI detection and handling
├── llm_chain.py       # AI processing and summarization
├── prompt_templates.py # AI prompt templates
├── requirements.txt   # Python dependencies
├── Dockerfile         # Container configuration
└── .env              # Environment variables (not in repo)
```

## Security Considerations

1. All API keys and sensitive data should be stored in `.env`
2. The `.env` file should never be committed to version control
3. CORS is configured to only allow specific origins
4. JWT tokens are used for authentication
5. File uploads are validated and processed securely

## Error Handling

The application includes comprehensive error handling for:

- Invalid file uploads
- Authentication failures
- API key issues
- Processing errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
