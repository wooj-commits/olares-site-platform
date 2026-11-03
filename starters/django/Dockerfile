FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000 DJANGO_SETTINGS_MODULE=hello.settings
EXPOSE 8000
USER nobody
CMD ["sh", "-c", "gunicorn hello.wsgi:application -b 0.0.0.0:${PORT:-8000}"]
