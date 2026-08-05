FROM python:3.11-slim
WORKDIR /app

# Install system deps for many Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PORT=5500
ENV FLASK_ENV=production

EXPOSE $PORT

CMD ["gunicorn", "mp:app", "-b", "0.0.0.0:$PORT"]
