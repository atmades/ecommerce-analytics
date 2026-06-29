from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass(frozen=True)
class Config:
    project_id: str
    gcs_bucket: str
    bq_dataset: str

    @classmethod
    def from_env(cls) -> "Config":
        missing = []
        for key in ["GCP_PROJECT_ID", "GCS_BUCKET", "BQ_DATASET"]:
            if not os.getenv(key):
                missing.append(key)
        if missing:
            raise EnvironmentError(
                f"Отсутствуют переменные окружения: {', '.join(missing)}\n"
                f"Проверь файл .env"
            )
        return cls(
            project_id=os.environ["GCP_PROJECT_ID"],
            gcs_bucket=os.environ["GCS_BUCKET"],
            bq_dataset=os.environ["BQ_DATASET"],
        )

config = Config.from_env()
