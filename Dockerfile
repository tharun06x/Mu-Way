FROM python:3.10-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project
COPY . /app/

# Build the frontend
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Setup the backend
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Collect static files for Django
RUN python manage.py collectstatic --noinput

# Expose the default port used by Hugging Face Spaces
EXPOSE 7860

# Run the Django server using gunicorn
CMD ["gunicorn", "icrs_backend.wsgi:application", "--bind", "0.0.0.0:7860"]
