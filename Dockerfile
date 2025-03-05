# Dockerfile
FROM python:3.11-slim

# 필수 도구 설치
RUN apt-get update && apt-get install -y curl

# wait-for-it 스크립트 다운로드
RUN curl -sSLO https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh && \
    chmod +x wait-for-it.sh && \
    mv wait-for-it.sh /usr/local/bin/wait-for-it

# 작업 디렉터리 설정
WORKDIR /app

# 로컬 파일을 컨테이너의 /app 디렉터리로 복사
COPY . .

# 필요한 Python 패키지 설치
RUN pip install -r requirements.txt

# ENTRYPOINT로 실행 설정
ENTRYPOINT ["sh", "-c", "wait-for-it rabbitmq:5672 --timeout=15 && nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > /app/nohup.out 2>&1"]
