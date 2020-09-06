FROM python:3.6-buster

# copy over our requirements.txt file
COPY requirements.txt /tmp/
COPY agents/ml/requirements.txt /tmp/ml_agent_requirements.txt
COPY agents/bert_agent/requirements.txt /tmp/bert_agent_requirements.txt

# Set up GCS bucket
COPY kube/gcsfuse.repo /etc/yum.repos.d/
COPY kube/gcs_credentials.json /gcs_credentials.json
RUN echo "deb http://packages.cloud.google.com/apt gcsfuse-buster main" | tee /etc/apt/sources.list.d/gcsfuse.list
RUN cat /etc/apt/sources.list.d/gcsfuse.list
RUN apt-get install curl
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install -y gcsfuse
RUN mkdir -p /gui/backend/logs

# upgrade pip and install required python packages
RUN pip install -U pip
RUN pip install -r /tmp/requirements.txt
RUN pip install -r /tmp/ml_agent_requirements.txt
RUN pip install -r /tmp/bert_agent_requirements.txt

# copy over our app code
COPY . .

EXPOSE 5000

WORKDIR "gui/backend"
CMD ["python", "main.py"]
