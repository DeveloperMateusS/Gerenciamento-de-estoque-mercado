# admin.py
import socket
import json
import sys

# Função para enviar um comando e receber a resposta
def send_command(sock, command_dict):
    try:
        json_string = json.dumps(command_dict)
        sock.sendall(json_string.encode())
        
        resposta_raw = sock.recv(4096).decode()
        return json.loads(resposta_raw)
        
    except socket.error as e:
        print(f"*** Erro de rede: {e} ***")
        return None
    except json.JSONDecodeError:
        print("*** Erro: Servidor enviou resposta inválida ***")
        return None

def main():
    HOST = input("Digite o IP do servidor (ex: 127.0.0.1): ")
    PORT = 5050

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print(f"--- Conectado ao servidor {HOST}:{PORT} como ADMIN ---")
        print("Use os comandos:")
        print("  SET <produto> <quantidade>   (Ex: SET maca 50)")
        print("  SAIR                         (Para fechar)")
        print("-" * 50)
    except socket.error as e:
        print(f"Não foi possível conectar: {e}")
        return

    while True:
        try:
            # Pede o comando ao admin
            user_input = input("Admin > ").strip()
            if not user_input:
                continue

            parts = user_input.split()
            cmd = parts[0].upper()

            if cmd == "SAIR":
                send_command(sock, {"tipo": "SAIR"})
                break # Sai do loop while
            
            elif cmd == "SET" and len(parts) == 3:
                # Comando para definir estoque
                produto = parts[1].lower()
                try:
                    quantidade = int(parts[2])
                    
                    # Monta o comando JSON
                    comando = {
                        "tipo": "SET_ESTOQUE",
                        "payload": {
                            "produto": produto,
                            "quantidade": quantidade
                        }
                    }
                    
                    # Envia e imprime a resposta
                    resposta = send_command(sock, comando)
                    if resposta:
                        print(f"Servidor: {resposta.get('payload', {}).get('mensagem')}")
                        
                except ValueError:
                    print("Erro: A quantidade deve ser um número.")
            
            else:
                print("Comando inválido. Use: SET <produto> <quantidade> ou SAIR")

        except KeyboardInterrupt:
            # Se o admin der Ctrl+C
            send_command(sock, {"tipo": "SAIR"})
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            break

    sock.close()
    print("--- Desconectado do servidor ---")

if __name__ == "__main__":
    main()