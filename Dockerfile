FROM python:latest

WORKDIR /code

# Upgrade pip
RUN pip install --upgrade pip

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# command to run on container start
ENTRYPOINT [ "python", "app.py" ]
