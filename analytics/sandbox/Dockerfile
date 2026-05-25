FROM python:3.10-slim

# Install only necessary data analysis libraries
RUN pip install --no-cache-dir pandas numpy matplotlib seaborn

# Add a non-root user to run the code
RUN useradd -m sandboxuser
USER sandboxuser

# Set working directory where data and code will be mounted
WORKDIR /workspace
