# Arquitetura e operação

## Fluxo do pedido

1. O Gateway valida o formato e encaminha o `POST` para Pedidos.
2. Pedidos grava o pedido, o primeiro histórico e `pedido.criado` na outbox.
3. O publicador envia o evento ao exchange `pedidos.eventos`.
4. Estoque trava os produtos consultados, reserva tudo ou recusa tudo e publica o resultado.
5. Pagamentos recebe apenas reservas bem-sucedidas. O token fictício `RECUSAR` simula um pagamento
   não autorizado, enquanto `APROVAR` segue pelo fluxo de aprovação.
6. Pedidos atualiza o estado. Estoque confirma a baixa ou devolve a reserva em caso de recusa.

As filas são duráveis, as mensagens são persistentes e os acknowledgements só ocorrem depois do
processamento. Se um consumidor cair antes do ack, a mensagem volta para a fila. Como isso produz
entrega pelo menos uma vez, cada serviço mantém `eventos_processados` e ignora identificadores já
vistos.

## Outbox e falhas

A alteração de negócio e o evento são gravados na mesma transação PostgreSQL. Um worker busca a
outbox, coloca um bloqueio com prazo curto e publica no RabbitMQ. Se a publicação falhar, o prazo
expira e outra tentativa pega o registro. O campo `publicado_em` encerra o ciclo.

Esse desenho evita o caso em que o pedido fica salvo mas o processo cai antes de publicar o evento.
O MVP não implementa dead-letter queue nem reconciliação administrativa, esses itens ficam como
evolução para uma operação real.

## Telemetria

- Métricas HTTP trazem volume, status e histograma de duração por serviço.
- Métricas de negócio contam pedidos, pagamentos e resultados do estoque.
- Logs saem em JSON e incluem `trace_id` e `span_id` quando existe span ativo.
- Traces usam W3C Trace Context. O contexto é injetado nos cabeçalhos das mensagens e recuperado
  pelo consumidor, mantendo a mesma linha de investigação entre HTTP e RabbitMQ.
- Prometheus avalia alertas de serviço indisponível e erro HTTP acima de 5%.

O painel provisionado no Grafana reúne taxa, p95, respostas e logs. O Explore do Grafana permite
abrir traces no Tempo e procurar o mesmo identificador no Loki.

## Implantação e escala

Os quatro Deployments usam rolling update com `maxUnavailable: 0` e `maxSurge: 1`. Readiness evita
tráfego precoce, liveness reinicia um processo travado. PDB preserva ao menos uma réplica do Gateway
e de Pedidos durante manutenção voluntária.

O HPA varia de duas a seis réplicas quando a média de CPU ultrapassa 70%. Como todos os serviços
declaram requests, a métrica tem uma base estável. Para o consumo do RabbitMQ, a próxima evolução é
KEDA com tamanho da fila, que representa a pressão de trabalho melhor que CPU.

## Limites conscientes

PostgreSQL e RabbitMQ têm uma réplica no MVP. Isso demonstra volumes e StatefulSets, mas não oferece
alta disponibilidade. Em produção, use backups testados e serviços gerenciados. O token de pagamento
é fictício, uma integração real deve usar tokenização do provedor, TLS, rotação de secrets, timeout,
circuit breaker e regras de PCI DSS.
