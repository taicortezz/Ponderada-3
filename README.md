# BDD e Engenharia de Integração - Ponderada 3

## Objetivo

Este projeto implementa um fluxo simples de integração como código dentro do contexto da ASIS Tax Tech.

Aqui está descrito  o caminho que um arquivo fiscal faz dentro da plataforma. Primeiro, um sistema cliente envia o arquivo para a ASIS. Em seguida, a plataforma devolve um identificador para esse envio. Com esse identificador, o cliente passa a consultar o andamento do processamento até que ele termine. Quando o processamento é concluído, o cliente consulta o resultado final. O projeto mostra esse fluxo e também como verificar se ele está funcionando dentro das regras de tempo, versão, protocolo e tratamento de erros.

O fluxo escolhido foi:

**upload de arquivo fiscal -> consulta de status por polling -> consulta de resultado**

## Estrutura de integração

### Camadas

1. **Cliente/ERP**
   - Sistema que envia o arquivo fiscal para processamento.

2. **API ASIS**
   - Recebe o upload e expõe os endpoints de consulta.

3. **Serviço de processamento assíncrono**
   - Processa o arquivo fiscal após o upload.

4. **Serviço de resultado**
   - Retorna o resultado do processamento concluído.

### Módulos e componentes

- **Módulo de upload**
  - Envia o arquivo para a API.

- **Módulo de polling**
  - Consulta o status do processo até a conclusão.

- **Módulo de resultado**
  - Busca o resultado final do processo.

- **Módulo de autenticação**
  - Usa `account-key` e `app-key`.

- **Módulo de controle de qualidade**
  - Valida SLA, protocolo, versão e exceções.

### Serviços

- `POST /api/v1/upload`
- `GET /api/v1/processo/{id}`
- `GET /api/v1/resultado/processo/{id}`

### Hardware

- máquina cliente ou ERP do usuário;
- servidor em nuvem onde a API ASIS está hospedada.

### Software

- Python 3;
- API REST sobre HTTPS;
- mensagens em JSON;
- autenticação por dupla chave.

### Processo

1. o cliente envia um arquivo fiscal;
2. a API retorna um `process_id`;
3. o cliente consulta o status do processo;
4. quando o status for concluído, o cliente consulta o resultado.

## Controle de qualidade da integração

| Item | Definição |
| --- | --- |
| Tempo do upload | até 5 segundos |
| Tempo da consulta | até 5 segundos |
| Protocolo | HTTPS/REST |
| Versão | v1 |
| Autenticação | `account-key` e `app-key` |
| Falhas transitórias | tolerância de até 4 falhas no polling |
| Exceções tratadas | autenticação, processo inexistente e timeout |

## Como o controle foi codificado

O arquivo `asis_integration_flow.py` implementa:

- o fluxo de upload, polling e resultado;
- validação dos endpoints na versão `v1`;
- uso do protocolo `HTTPS/REST` como contrato da integração;
- verificação de SLA de tempo para upload e consulta;
- tratamento das exceções principais da integração.

## Arquivos do projeto

- `asis_integration_flow.py`: fluxo de integração da ASIS;
- `tests/test_asis_integration_flow.py`: testes automatizados;
- `README.md`: documentação da atividade.

## Testes implementados

Os testes verificam:

1. fluxo de sucesso;
2. protocolo e versão da integração;
3. autenticação por chaves;
4. tolerância a falha transitória no polling;
5. tratamento de processo inexistente;
6. tratamento de timeout por violação de SLA.

## Como executar

Na raiz do repositório, execute:

`python -m unittest discover -s Ponderada-3/tests -v`