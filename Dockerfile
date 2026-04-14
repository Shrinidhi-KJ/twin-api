# Use an official lightweight Python image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first for better Docker layer caching
# (if code changes but requirements don't, Docker reuses the install layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project into the container
COPY . .

# Expose port 8000 so it can be reached from outside the container
EXPOSE 8000

# Default spec file to load; can be overridden at runtime
ENV SPEC_FILE=petstore.json

# When the container starts, run the mock server
CMD ["sh", "-c", "python run_mock.py $SPEC_FILE"]