FROM python:3.11-slim

# Set timezone to Asia/Kolkata (IST) for Indian financial markets
ENV TZ=Asia/Kolkata
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install timezone data and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data and logs directories exist
RUN mkdir -p data logs

# Expose Streamlit dashboard port
EXPOSE 8501

# Default CMD runs background daemon
CMD ["python", "main.py", "start-daemon"]
