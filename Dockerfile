FROM python:3.12-slim

WORKDIR /src

COPY src/requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

# code
COPY src /src
ENV PYTHONPATH=/src

EXPOSE 8000

#CMD ["uvicorn", "main:src", "--host", "0.0.0.0", "--port", "8000", "--reload"]
CMD ["python", "main.py"]