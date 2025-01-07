FROM continuumio/anaconda3:latest

WORKDIR /app

# (1) 환경 파일이 있다면 복사 후 환경 생성
COPY environment.yml .
RUN conda env create -f environment.yml

# (2) 소스 복사
COPY . .

# (3) CMD 시점에 conda.sh를 source + 환경 활성
CMD ["/bin/bash"]
