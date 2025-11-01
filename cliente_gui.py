# cliente_gui.py
import socket
import tkinter as tk
from tkinter import simpledialog, messagebox, Listbox, END
import json  # Importante: usaremos JSON

# --- Classe NetworkClient (Sem alterações) ---
class NetworkClient:
    def __init__(self):
        self.client_socket = None

    def connect(self, host, port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            return True
        except socket.error as e:
            messagebox.showerror("Erro de Rede", f"Não foi possível ligar ao servidor: {e}")
            return None

    def send_command(self, command_dict):
        try:
            json_string = json.dumps(command_dict)
            self.client_socket.sendall(json_string.encode())
            
            if command_dict.get("tipo") == "SAIR":
                self.client_socket.close()
                return {"tipo": "BYE"}

            resposta_raw = self.client_socket.recv(4096).decode()
            if not resposta_raw:
                messagebox.showerror("Erro de Rede", "O servidor desligou a ligação.")
                return None

            return json.loads(resposta_raw)

        except socket.error as e:
            messagebox.showerror("Erro de Rede", f"Ligação perdida: {e}")
            return None
        except json.JSONDecodeError:
            messagebox.showerror("Erro de Protocolo", "O servidor enviou uma resposta JSON inválida.")
            return None
            
    def close(self):
        if self.client_socket:
            self.send_command({"tipo": "SAIR"})


# --- Configuração da Interface Gráfica (GUI) ---
class App:
    def __init__(self, root):
        self.network = NetworkClient()
        self.root = root
        self.root.title("Mercadinho - Cliente")
        self.root.geometry("600x400") # Janela mais larga
        
        self.is_running = True 

        self.status_label = tk.Label(root, text="Por favor, ligue-se ao servidor.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Frame da Lista Estoque (Esquerda) ---
        list_frame = tk.Frame(main_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="Estoque Disponível:").pack(anchor=tk.W)
        
        scrollbar_estoque = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.estoque_listbox = Listbox(list_frame, yscrollcommand=scrollbar_estoque.set, height=15)
        scrollbar_estoque.config(command=self.estoque_listbox.yview)
        
        scrollbar_estoque.pack(side=tk.RIGHT, fill=tk.Y)
        self.estoque_listbox.pack(fill=tk.BOTH, expand=True)
        # Evento de clique para o botão Reservar
        self.estoque_listbox.bind("<<ListboxSelect>>", self.on_select_estoque)


        # --- Frame dos Botões (Centro) ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Button(button_frame, text="Atualizar Listas", command=self.atualizar_listas).pack(fill=tk.X)
        self.btn_reservar = tk.Button(button_frame, text="Reservar", command=self.reservar_produto, bg="#4CAF50", fg="white", state=tk.DISABLED)
        self.btn_reservar.pack(fill=tk.X, pady=5)
        
        self.btn_cancelar = tk.Button(button_frame, text="Cancelar", command=self.cancelar_reserva, bg="#F44336", fg="white", state=tk.DISABLED)
        self.btn_cancelar.pack(fill=tk.X, pady=5)


        # --- (NOVO) Frame Minhas Reservas (Direita) ---
        reservas_frame = tk.Frame(main_frame)
        reservas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(reservas_frame, text="Minhas Reservas:").pack(anchor=tk.W)
        
        scrollbar_reservas = tk.Scrollbar(reservas_frame, orient=tk.VERTICAL)
        self.reservas_listbox = Listbox(reservas_frame, yscrollcommand=scrollbar_reservas.set, height=15)
        scrollbar_reservas.config(command=self.reservas_listbox.yview)
        
        scrollbar_reservas.pack(side=tk.RIGHT, fill=tk.Y)
        self.reservas_listbox.pack(fill=tk.BOTH, expand=True)
        # Evento de clique para o botão Cancelar
        self.reservas_listbox.bind("<<ListboxSelect>>", self.on_select_reserva)


        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.ligar_ao_servidor()

    def ligar_ao_servidor(self):
        host = simpledialog.askstring("Ligar ao Servidor", "Digite o IP do servidor:", initialvalue="127.0.0.1")
        if not host:
            self.root.destroy()
            return

        is_connected = self.network.connect(host, 5050)
        
        if is_connected:
            self.status_label.config(text="Ligado a " + host)
            self.auto_atualizar_loop()
        else:
            self.root.destroy()

    def auto_atualizar_loop(self):
        if not self.is_running:
            return 
        self.atualizar_listas() # Função wrapper
        self.root.after(3000, self.auto_atualizar_loop) # Atualiza a cada 3 seg

    # --- Funções de Lógica ---
    
    def atualizar_listas(self):
        """Pede ao servidor o estoque E as reservas."""
        self.atualizar_lista_estoque()
        self.atualizar_lista_reservas()
    
    def atualizar_lista_estoque(self):
        comando = {"tipo": "GET_ESTOQUE"}
        resposta = self.network.send_command(comando)
        if resposta is None: return

        if resposta.get("tipo") == "ESTOQUE_ATUAL":
            self.estoque_listbox.delete(0, END)
            estoque = resposta.get("payload", {})
            if not estoque or all(v == 0 for v in estoque.values()):
                self.estoque_listbox.insert(END, "Estoque vazio.")
                return

            for produto, qtd in estoque.items():
                if qtd > 0: # Só mostra itens com estoque > 0
                    self.estoque_listbox.insert(END, f"{produto}: {qtd} un.")
        else:
            messagebox.showerror("Erro", f"Resposta inesperada do servidor: {resposta}")

    def atualizar_lista_reservas(self):
        comando = {"tipo": "GET_MINHAS_RESERVAS"}
        resposta = self.network.send_command(comando)
        if resposta is None: return
        
        if resposta.get("tipo") == "MINHAS_RESERVAS":
            self.reservas_listbox.delete(0, END)
            reservas = resposta.get("payload", {})
            if not reservas:
                self.reservas_listbox.insert(END, "Nenhum item reservado.")
                return

            for produto, qtd in reservas.items():
                self.reservas_listbox.insert(END, f"{produto}: {qtd} un.")
        else:
            messagebox.showerror("Erro", f"Resposta inesperada do servidor: {resposta}")
            
    # --- (NOVO) Funções de seleção ---
    def on_select_estoque(self, event):
        # Habilita o botão reservar e desabilita o cancelar
        if self.estoque_listbox.curselection():
            self.btn_reservar.config(state=tk.NORMAL)
            self.btn_cancelar.config(state=tk.DISABLED)
            # Limpa seleção da outra lista
            self.reservas_listbox.selection_clear(0, END)

    def on_select_reserva(self, event):
        # Habilita o botão cancelar e desabilita o reservar
        if self.reservas_listbox.curselection():
            self.btn_cancelar.config(state=tk.NORMAL)
            self.btn_reservar.config(state=tk.DISABLED)
            # Limpa seleção da outra lista
            self.estoque_listbox.selection_clear(0, END)
            
    # ---
    
    def _obter_produto_selecionado(self, listbox):
        """Função auxiliar para pegar o nome do produto de uma listbox."""
        try:
            indice_selecionado = listbox.curselection()[0]
            linha_texto = listbox.get(indice_selecionado)
            produto = linha_texto.split(":")[0].strip()
            return produto
        except IndexError:
            return None

    def reservar_produto(self):
        produto = self._obter_produto_selecionado(self.estoque_listbox)
        if produto is None: return
        
        quantidade = simpledialog.askinteger("Reservar Produto", 
                                             f"Qual a quantidade de '{produto}' que quer reservar?",
                                             minvalue=1)
        if not quantidade or quantidade <= 0: return 

        comando = {"tipo": "RESERVAR", "payload": {"produto": produto, "quantidade": quantidade}}
        resposta = self.network.send_command(comando)
        if resposta is None: return
        
        if resposta.get("tipo") == "RESPOSTA_RESERVA":
            payload = resposta.get("payload", {})
            status = payload.get("status")
            mensagem = payload.get("mensagem")
            
            if status == "SUCESSO":
                messagebox.showinfo("Sucesso", mensagem)
                self.atualizar_listas() # Atualiza ambas as listas
            else:
                messagebox.showerror("Erro de Reserva", mensagem)
        else:
             messagebox.showerror("Erro", f"Resposta inesperada do servidor: {resposta}")

    def cancelar_reserva(self):
        produto = self._obter_produto_selecionado(self.reservas_listbox)
        if produto is None: return
        
        quantidade = simpledialog.askinteger("Cancelar Reserva", 
                                             f"Qual a quantidade de '{produto}' que quer devolver/cancelar?",
                                             minvalue=1)
        if not quantidade or quantidade <= 0: return

        comando = {"tipo": "CANCELAR_RESERVA", "payload": {"produto": produto, "quantidade": quantidade}}
        resposta = self.network.send_command(comando)
        if resposta is None: return
        
        if resposta.get("tipo") == "RESPOSTA_CANCELAMENTO":
            payload = resposta.get("payload", {})
            status = payload.get("status")
            mensagem = payload.get("mensagem")
            
            if status == "SUCESSO":
                messagebox.showinfo("Sucesso", mensagem)
                self.atualizar_listas() # Atualiza ambas as listas
            else:
                messagebox.showerror("Erro de Cancelamento", mensagem)
        else:
             messagebox.showerror("Erro", f"Resposta inesperada do servidor: {resposta}")
    
    def ao_fechar(self):
        self.is_running = False 
        print("A fechar a ligação...")
        self.network.close()
        self.root.destroy()

# --- Iniciar a Aplicação ---
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()