# 🛒 Gerenciamento de Estoque de Mercado (Projeto de Redes)

Projeto acadêmico desenvolvido para a disciplina de Redes de Computadores da Universidade de Brasília (UnB).

O objetivo é implementar uma aplicação na arquitetura Cliente-Servidor e desenvolver um protocolo de aplicação customizado para, em seguida, analisar seu funcionamento e tráfego com o Wireshark.

## 🏛️ Arquitetura

A aplicação simula o gerenciamento de estoque de um mercado e é dividida em três componentes principais:

1.  **`servidor.py` (O Servidor Central):**
    * Gerencia o estado centralizado do estoque (`estoque_disponivel`).
    * Controla "carrinhos de reserva" individuais para cada cliente conectado.
    * Utiliza `threading` para lidar com múltiplas conexões de clientes simultaneamente.
    * Responsável por processar todos os comandos do protocolo.

2.  **`cliente_gui.py` (O Consumidor):**
    * Interface gráfica (GUI) desenvolvida com `Tkinter`.
    * Permite ao usuário visualizar o estoque disponível e seu "carrinho" de reservas.
    * Pode enviar comandos de `RESERVAR` e `CANCELAR_RESERVA`.
    * Possui um *loop* de atualização automática para sincronizar com o servidor.

3.  **`admin.py` (O Administrador):**
    * Cliente de linha de comando (CLI) para fins administrativos.
    * Permite ao administrador adicionar novos produtos e definir/atualizar a quantidade de itens no estoque em tempo real (comando `SET_ESTOCKE`).

## 📡 Protocolo de Aplicação (JSON sobre TCP)

Para a comunicação entre cliente e servidor, foi definido um protocolo de aplicação customizado que utiliza mensagens no formato **JSON** sobre **TCP** (`socket.SOCK_STREAM`).

O `tipo` da mensagem define o comando a ser executado:

| Comando | Origem | Destino | Descrição |
| :--- | :--- | :--- | :--- |
| `GET_ESTOQUE` | Cliente | Servidor | Solicita a lista atual de estoque disponível. |
| `GET_MINHAS_RESERVAS` | Cliente | Servidor | Solicita o "carrinho" de itens do cliente. |
| `RESERVAR` | Cliente | Servidor | Move um item do estoque para o carrinho do cliente. |
| `CANCELAR_RESERVA` | Cliente | Servidor | Move um item do carrinho do cliente de volta para o estoque. |
| `SET_ESTOQUE` | Admin | Servidor | Adiciona um novo produto ou atualiza sua quantidade no estoque. |
| `SAIR` | Cliente/Admin | Servidor | Informa o servidor sobre a desconexão. |

### Exemplo de Mensagem (Carga Útil):
```json
{
  "tipo": "RESERVAR",
  "payload": {
    "produto": "banana",
    "quantidade": 5
  }
}