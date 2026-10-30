FROM python:3.13
WORKDIR /app

# Install the application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code in the directory source
COPY app.py /app
EXPOSE 5000

# Run app.py when the container launches
CMD ["python3", "app.py"]