# servidor.py
import socket
import threading
import json

# --- (ESTRUTURA DE DADOS PRINCIPAL) ---
# O estoque agora está dividido em dois:
estoque_disponivel = {
    "banana": 10,
    "uva": 20,
    "leite": 5,
    "pao": 15
}
# Dicionário para rastrear o "carrinho" de cada cliente (conexão)
reservas_por_cliente = {}

lock = threading.Lock()  # O lock agora protege AMBAS as estruturas

HOST = "0.0.0.0"
PORT = 5050

def handle_client(conn, addr):
    print(f"[NOVA CONEXAO] {addr} conectado.")
    
    # --- (NOVO) ---
    # Cria um "carrinho" vazio para este cliente
    with lock:
        reservas_por_cliente[conn] = {}
        
    try:
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break 

            print(f"[{addr}] Enviou: {data}")

            try:
                # --- (MUDANÇA) ---
                # Passamos 'conn' para que a função saiba QUEM está pedindo
                response_json = process_json_command(data, conn) 
            except Exception as e:
                print(f"*** ERRO NO SERVIDOR: {e} ***")
                response_data = {"tipo": "ERRO_GERAL", "payload": {"mensagem": "Erro interno no servidor."}}
                response_json = json.dumps(response_data)
            
            conn.sendall(response_json.encode())
            
            try:
                if json.loads(data).get("tipo") == "SAIR":
                    break
            except Exception:
                pass

    except ConnectionResetError:
        print(f"[{addr}] Ligação perdida abruptamente.")
    except Exception as e:
        print(f"[{addr}] Erro de rede: {e}")
    finally:
        # --- (NOVO E CRÍTICO) ---
        # Bloco de limpeza: Se o cliente desconectar,
        # devolve todos os seus itens reservados ao estoque.
        with lock:
            carrinho_abandonado = reservas_por_cliente.pop(conn, {}) # Pega o carrinho e remove da lista
            if carrinho_abandonado:
                print(f"[{addr}] Desconectado. Devolvendo itens ao estoque...")
                for produto, quantidade in carrinho_abandonado.items():
                    if produto in estoque_disponivel:
                        estoque_disponivel[produto] += quantidade
                    else:
                        # Caso o admin tenha removido o produto enquanto estava reservado
                        estoque_disponivel[produto] = quantidade 
                print(f"[{addr}] Itens devolvidos: {carrinho_abandonado}")
        
        conn.close()
        print(f"[DESCONECTADO] {addr}")

# --- (MUDANÇA) ---
# A função agora recebe 'conn' para saber qual "carrinho" usar
def process_json_command(json_string, conn):
    """Processa um comando JSON e retorna uma resposta JSON (string)."""
    
    try:
        msg = json.loads(json_string)
        cmd_tipo = msg.get("tipo")
        payload = msg.get("payload", {})
    except json.JSONDecodeError:
        resp = {"tipo": "RESPOSTA_ERRO", "payload": {"mensagem": "Comando JSON inválido."}}
        return json.dumps(resp)

    # --- (LÓGICA DOS COMANDOS) ---

    if cmd_tipo == "GET_ESTOQUE":
        with lock:
            # Retorna o estoque DISPONÍVEL
            resp = {"tipo": "ESTOQUE_ATUAL", "payload": estoque_disponivel.copy()}
        return json.dumps(resp)

    # --- (NOVO COMANDO) ---
    elif cmd_tipo == "GET_MINHAS_RESERVAS":
        with lock:
            # Retorna o carrinho do cliente específico
            carrinho_cliente = reservas_por_cliente.get(conn, {})
            resp = {"tipo": "MINHAS_RESERVAS", "payload": carrinho_cliente.copy()}
        return json.dumps(resp)

    elif cmd_tipo == "RESERVAR":
        produto = payload.get("produto")
        try:
            quantidade = int(payload.get("quantidade", 0))
        except ValueError:
            quantidade = 0

        if not produto or quantidade <= 0:
            resp = {"tipo": "RESPOSTA_RESERVA", "payload": {"status": "ERRO", "mensagem": "Pedido inválido."}}
            return json.dumps(resp)

        with lock:
            produto = produto.lower() 
            if produto not in estoque_disponivel:
                resp = {"tipo": "RESPOSTA_RESERVA", "payload": {"status": "ERRO", "mensagem": f"Produto '{produto}' não existe."}}
            
            elif estoque_disponivel[produto] < quantidade:
                msg_erro = f"Estoque insuficiente. Temos apenas {estoque_disponivel[produto]} '{produto}'."
                resp = {"tipo": "RESPOSTA_RESERVA", "payload": {"status": "ERRO", "mensagem": msg_erro}}
            
            else:
                # --- (LÓGICA ATUALIZADA) ---
                # 1. Tira do estoque disponível
                estoque_disponivel[produto] -= quantidade
                # 2. Adiciona ao carrinho do cliente
                carrinho_cliente = reservas_por_cliente[conn]
                carrinho_cliente[produto] = carrinho_cliente.get(produto, 0) + quantidade
                
                msg_sucesso = f"Reserva de {quantidade} '{produto}' efetuada com sucesso!"
                resp = {"tipo": "RESPOSTA_RESERVA", "payload": {"status": "SUCESSO", "mensagem": msg_sucesso}}
        
        return json.dumps(resp)

    elif cmd_tipo == "CANCELAR_RESERVA":
        produto = payload.get("produto")
        try:
            quantidade = int(payload.get("quantidade", 0))
        except ValueError:
            quantidade = 0

        if not produto or quantidade <= 0:
            resp = {"tipo": "RESPOSTA_CANCELAMENTO", "payload": {"status": "ERRO", "mensagem": "Pedido de cancelamento inválido."}}
            return json.dumps(resp)
        
        with lock:
            produto = produto.lower()
            carrinho_cliente = reservas_por_cliente[conn]
            quantidade_reservada = carrinho_cliente.get(produto, 0)

            # --- (VALIDAÇÃO PRINCIPAL) ---
            # O cliente tem o que quer cancelar?
            if quantidade > quantidade_reservada:
                msg_erro = f"Cancelamento falhou. Você só tem {quantidade_reservada} '{produto}' reservados."
                resp = {"tipo": "RESPOSTA_CANCELAMENTO", "payload": {"status": "ERRO", "mensagem": msg_erro}}
            
            else:
                # --- (LÓGICA ATUALIZADA) ---
                # 1. Tira do carrinho do cliente
                carrinho_cliente[produto] -= quantidade
                if carrinho_cliente[produto] == 0:
                    del carrinho_cliente[produto] # Limpa o carrinho se zerar
                
                # 2. Devolve ao estoque disponível
                estoque_disponivel[produto] += quantidade
                
                msg_sucesso = f"Cancelamento de {quantidade} '{produto}' efetuado. Estoque agora: {estoque_disponivel[produto]}"
                resp = {"tipo": "RESPOSTA_CANCELAMENTO", "payload": {"status": "SUCESSO", "mensagem": msg_sucesso}}
        
        return json.dumps(resp)
    
    elif cmd_tipo == "SET_ESTOQUE":
        produto = payload.get("produto")
        try:
            quantidade = int(payload.get("quantidade", 0))
        except ValueError:
            quantidade = 0

        if not produto or quantidade < 0:
            resp = {"tipo": "RESPOSTA_ADMIN", "payload": {"status": "ERRO", "mensagem": "Pedido admin inválido."}}
            return json.dumps(resp)

        with lock:
            produto = produto.lower() 
            # Admin agora mexe no ESTOQUE DISPONÍVEL
            estoque_disponivel[produto] = quantidade
            mensagem = f"Estoque disponível de '{produto}' definido para {quantidade}."
            
            if produto not in estoque_disponivel:
                 mensagem = f"Novo produto '{produto}' criado com {quantidade} unidades."
            
            resp = {"tipo": "RESPOSTA_ADMIN", "payload": {"status": "SUCESSO", "mensagem": mensagem}}
            
        return json.dumps(resp)

    elif cmd_tipo == "SAIR":
        return json.dumps({"tipo": "BYE"})

    else:
        resp = {"tipo": "RESPOSTA_ERRO", "payload": {"mensagem": "Tipo de comando desconhecido."}}
        return json.dumps(resp)

def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.settimeout(1.0) 
    
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVIDOR] Mercadinho rodando em {HOST}:{PORT}")

    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
            
            except socket.timeout:
                pass 
            
    except KeyboardInterrupt:
        print("\n[DESLIGANDO] Recebido Ctrl+C. A desligar...")
        
    finally:
        server.close()
        print("[SERVIDOR DESLIGADO]")

if __name__ == "__main__":
    start()