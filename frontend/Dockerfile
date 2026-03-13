FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY frontend/requirements.txt /app/frontend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/frontend/requirements.txt

COPY frontend/streamlit_app.py /app/streamlit_app.py

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]

