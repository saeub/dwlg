FROM python:3.10

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update && apt-get install -y google-chrome-stable

# Install ChromeDriver
RUN wget -O /tmp/chromedriver.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)/linux64/chromedriver-linux64.zip
RUN unzip -j /tmp/chromedriver.zip chromedriver-linux64/chromedriver -d /usr/local/bin/

# Install Python dependencies
RUN pip install --upgrade pip
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Copy code
COPY scrape.py extract.py scrape_and_extract.sh /app/
COPY splits/ /app/splits/
WORKDIR /app

# Run
CMD ./scrape_and_extract.sh
