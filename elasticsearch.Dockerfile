FROM elasticsearch:8.10.4

USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
USER elasticsearch 