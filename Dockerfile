FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Stop Python from creating .pyc files or __pycache__ directories.
# Disable the default buffering behavior of Python's I/O streams; this is
# equivalent to running a Python script with the -u command-line flag.

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for PostgreSQL client
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

EXPOSE 8000

# Define the command to run your application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
