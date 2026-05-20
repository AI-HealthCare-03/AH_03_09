FROM python:3.13-slim

WORKDIR /app

# 1. uv 설치
RUN pip install uv --no-cache-dir

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'app' 그룹만 설치합니다.
RUN uv sync --group ai --no-dev --frozen

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ./ai_worker ./ai_worker

# 5. AI 워커 실행
CMD ["uv", "run", "python", "-m", "ai_worker.main"]
