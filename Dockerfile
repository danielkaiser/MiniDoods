FROM python:3.10-bullseye

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    libgl1-mesa-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install python libs
ADD requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

RUN useradd -m -s /bin/bash -d /opt/doods doods
RUN mkdir -p /opt/doods/models && chown -R doods:doods /opt/doods
COPY config.yaml /opt/doods/config.yaml

USER doods

WORKDIR /opt/doods

ADD . .

ENTRYPOINT ["python3", "main.py"]
CMD ["api"]
