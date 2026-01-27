FROM --platform=linux/amd64 python:2.7.18-slim-stretch

# Use archive.debian.org for old Stretch packages
RUN sed -i 's|deb.debian.org|archive.debian.org|g' /etc/apt/sources.list \
    && sed -i '/stretch-updates/d' /etc/apt/sources.list \
    && sed -i '/security.debian.org/d' /etc/apt/sources.list \
    && apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y tar espeak libespeak1 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y tar && rm -rf /var/lib/apt/lists/*

COPY ./pynaoqi.tar.gz /software/pynaoqi.tar.gz
WORKDIR /software

RUN tar -xzf pynaoqi.tar.gz && rm pynaoqi.tar.gz

ENV PYTHONPATH=/software/pynaoqi-python2.7-2.8.7.4-linux64-20210819_141148/lib/python2.7/site-packages:${PYTHONPATH}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "app.py"]
