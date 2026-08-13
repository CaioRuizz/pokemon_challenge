# Container para rodar a otimização evolutiva (scripts/evolve_policy.py) continuamente.
# NÃO embute o engine licenciado (vendor/cg/) na imagem — ele é buscado em
# tempo de execução via scripts/fetch_official.sh, usando credenciais do
# Kaggle montadas como secret/volume (ver deploy/README.md e
# docs/06-riscos-questoes-abertas.md item 3 sobre a licença restrita).
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY agent/ agent/
COPY scripts/ scripts/
COPY data/ data/
COPY eval/ eval/
COPY docs/ docs/

RUN pip install --no-cache-dir kaggle cma numpy

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
