import os
from dotenv import load_dotenv

load_dotenv()

CSV_FILE_PATH= os.getenv('CSV_FILE_PATH')
ML_FILE_PATH = os.getenv('ML_FILE_PATH')
ML_BE_URL = os.getenv('ML_BE_URL')
ML_BE_PORT = os.getenv('ML_BE_PORT')

RABBITMQ_URL = os.getenv('RABBITMQ_URL')
RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT'))
