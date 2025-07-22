FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  git \
  unzip \
  jq \
  ffmpeg \ 
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install --upgrade pip && \
  pip3 install -r requirements.txt

RUN playwright install
RUN playwright install-deps

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -Rf ./aws ./awscliv2.zip

RUN aws --version

COPY . .

RUN ln -s /app/.aws /root/.aws
RUN chmod +x /app/aws-setup.sh

ARG VERSION
RUN echo ${VERSION}
RUN sed -i 's/##VERSION##/'${VERSION}'/' ./st_components/st_sidebar.py

RUN cd $(pip3 show open-interpreter | grep Location | cut -d ' ' -f 2) && \
    patch -p1 < /app/patches/llm.diff

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
