import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


def requisitar(caminho: str, metodo: str = "GET", corpo: dict | None = None) -> dict:
    dados = json.dumps(corpo).encode() if corpo else None
    requisicao = urllib.request.Request(
        f"{BASE}{caminho}",
        data=dados,
        method=metodo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(requisicao, timeout=10) as resposta:
        return json.load(resposta)


def main() -> int:
    entrada = {
        "cliente_id": "smoke-test",
        "token_pagamento": "tok_aprovado",
        "itens": [{"sku": "SKU-CAMISETA", "quantidade": 1, "preco_unitario": "79.90"}],
    }
    criado = requisitar("/api/v1/pedidos", "POST", entrada)
    for _ in range(30):
        pedido = requisitar(f"/api/v1/pedidos/{criado['id']}")
        if pedido["estado"] == "CONFIRMADO":
            print(f"Pedido {criado['id']} confirmado com sucesso")
            return 0
        if pedido["estado"] == "CANCELADO":
            print(f"Pedido cancelado: {pedido['motivo_cancelamento']}", file=sys.stderr)
            return 1
        time.sleep(1)
    print("O pedido não terminou dentro do tempo esperado", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as erro:
        print(f"A API não respondeu: {erro}", file=sys.stderr)
        raise SystemExit(1) from erro
