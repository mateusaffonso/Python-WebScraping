FROM ubuntu:latest

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    sudo

RUN sudo apt install libevent-2.1-7

# Install Playwright dependencies
RUN npx playwright install-deps

# Set the working directory
WORKDIR /app

# Copy the project files
COPY . .

# Install Python dependencies
RUN pip3 install poetry

RUN poetry install --no-dev

# Command to run the Python script
CMD ["python3", "proj_scraper/run.py", "trabalha-brasil", "extract-data"]