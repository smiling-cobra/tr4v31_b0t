# Use an official Python runtime as the base image
FROM python:3

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory into the container at /app
COPY . /app

# Set the default command to run when the container starts
CMD [ "python", "your_script.py" ]
