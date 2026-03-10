FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment directly (assuming .venv exists in project root)
COPY .venv /app/.venv

# Enable the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Copy the application code
COPY application /app/application
COPY pyproject.toml /app/

# Copy other necessary directories
COPY config /app/config
COPY dataset /app/dataset
COPY sky_executor /app/sky_executor

# Expose the backend port
EXPOSE 8000

# Run the FastAPI server with uvicorn
CMD ["uvicorn", "application.backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
