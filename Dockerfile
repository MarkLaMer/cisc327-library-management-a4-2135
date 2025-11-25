# Use Python 3.11 slim image for smaller container size
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Run the Flask application
CMD ["python", "app.py"]
