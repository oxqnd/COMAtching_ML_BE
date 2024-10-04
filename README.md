# 프로젝트 이름

Comatching Service Backend

## 소개

이 프로젝트는 FastAPI를 기반으로 하는 매칭 서비스의 백엔드입니다. 사용자 정보를 CSV 파일로 관리하고, RabbitMQ를 통해 메시지를 송수신하며, 비동기적으로 매칭 요청과 사용자 CRUD 작업을 처리합니다.

## 목차

- [프로젝트 구조](#프로젝트-구조)
- [시작하기](#시작하기)
  - [필수 조건](#필수-조건)
  - [설치](#설치)
- [환경 설정](#환경-설정)
- [실행 방법](#실행-방법)
- [사용법](#사용법)

## 프로젝트 구조

```markdown
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── recommend.py
│   ├── consumers/
│   │   ├── __init__.py
│   │   ├── match_request_consumer.py
│   │   └── user_crud_consumer.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py
├── .env
├── requirements.txt
└── README.md

```

- **app/**: FastAPI 애플리케이션의 메인 디렉토리입니다.
    - **main.py**: 애플리케이션의 진입점입니다.
    - **config.py**: 환경 변수를 관리합니다.
    - **routes/**: API 엔드포인트를 관리합니다.
    - **consumers/**: RabbitMQ 메시지 큐 컨슈머를 관리합니다.
    - **utils/**: 유틸리티 함수들을 모아놓은 디렉토리입니다.
- **.env**: 환경 변수를 설정하는 파일입니다.
- **requirements.txt**: 필요한 패키지들이 명시되어 있습니다.
- **README.md**: 프로젝트에 대한 설명서입니다.

## 시작하기

### 필수 조건

- Python 3.7 이상
- RabbitMQ 서버
- 필요한 패키지 설치를 위한 `pip`

### 설치

1. **프로젝트 클론**
    
    ```bash
    git clone https://github.com/yourusername/yourproject.git
    cd yourproject
    ```
    
2. **가상 환경 생성 및 활성화 (선택 사항)**
    
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows의 경우 venv\Scripts\activate
    ```
    
3. **필요한 패키지 설치**
    
    ```bash
    pip install -r requirements.txt
    ```
    

## 환경 설정

프로젝트의 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가합니다:

```
CSV_FILE_PATH=/home/ads_lj/comatching/v6/ai_example.csv
RABBITMQ_URL=amqp://user:comatching12%40%40@100.115.125.32:5672/
RABBITMQ_USERNAME=user
RABBITMQ_PASSWORD=comatching12@@
RABBITMQ_HOST=100.115.125.32
RABBITMQ_PORT=5672
```

- `CSV_FILE_PATH`: 사용자 데이터를 저장하는 CSV 파일의 경로
- `RABBITMQ_URL`: RabbitMQ 서버의 연결 URL
- `RABBITMQ_USERNAME`, `RABBITMQ_PASSWORD`: RabbitMQ 서버의 인증 정보
- `RABBITMQ_HOST`, `RABBITMQ_PORT`: RabbitMQ 서버의 호스트와 포트 정보

## 실행 방법

애플리케이션을 실행하려면 다음 명령어를 사용하세요:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

- `-host`: 애플리케이션이 바인딩될 호스트를 지정합니다.
- `-port`: 애플리케이션이 바인딩될 포트를 지정합니다.
