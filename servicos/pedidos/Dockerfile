FROM python:3.14.7-slim AS construtor
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.14.7-slim AS execucao
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/pycache
RUN groupadd --gid 10001 aplicacao && useradd --uid 10001 --gid aplicacao --no-create-home aplicacao
COPY --from=construtor /opt/venv /opt/venv
WORKDIR /app
COPY --chown=aplicacao:aplicacao comum /app/comum
COPY --chown=aplicacao:aplicacao servicos /app/servicos
USER 10001:10001
EXPOSE 8001
CMD ["uvicorn", "servicos.pedidos.app:app", "--host", "0.0.0.0", "--port", "8001"]
