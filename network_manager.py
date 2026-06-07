# network_manager.py

import socket
import threading
import queue
import time
import json 

class NetworkManager:
    def __init__(self, host, port, max_players, game_instance):
        self.host = host
        self.port = port
        self.max_players = max_players
        self.game_instance = game_instance 
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_players)
        print(f"Server: listening on {self.host}:{self.port}")
        
        self.clients = {} 
        self.player_id_counter = 1 
        self.input_queue = queue.Queue() 

        self.accept_thread = threading.Thread(target=self._accept_connections)
        self.accept_thread.daemon = True 
        self.client_handler_threads = []

    def start_server(self): 
        self.accept_thread.start()
        print("Server: Accept connections thread started.")

    def _accept_connections(self):
        print("Server: Waiting for client connections...")
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Server: Accepted connection from {addr}")
                
                # Biarkan 1 slot untuk pemain lokal (ID 0)
                # Jika total remote players sudah mencapai MAX_PLAYERS - 1, tolak koneksi
                if len(self.clients) >= self.max_players - 1: 
                    print(f"Server: Connection from {addr} rejected: Max remote players reached ({len(self.clients)} remote players).")
                    client_socket.close()
                    continue

                client_thread = threading.Thread(target=self._handle_client, args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
                self.client_handler_threads.append(client_thread)
                print(f"Server: Started handler thread for {addr}.")

            except Exception as e:
                print(f"Server: Error accepting connection: {e}")
                break 

    def _handle_client(self, client_socket, addr):
        current_player_id = None
        buffer = "" 
        print(f"Server: Handler for {addr} starting.") # Baris ini sekarang akan di-follow oleh logging lebih detail

        while True:
            try:
                # Menerima data dalam bentuk byte, lalu decode
                data = client_socket.recv(1024) 
                if not data:
                    print(f"Server: Client {addr} (ID:{current_player_id}) disconnected gracefully.")
                    break # Keluar dari loop, lakukan cleanup
                
                # Decode data setelah memastikan tidak kosong
                decoded_data = data.decode('utf-8')
                buffer += decoded_data
                print(f"Server: Raw data received from {addr}: '{decoded_data.strip()}'") # Log raw data

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    print(f"Server: Processing line from {addr}: '{line.strip()}'") # Log baris yang diproses

                    try:
                        message = json.loads(line)
                        print(f"Server: Parsed message from {addr}: {message}") # Log pesan yang sudah diparsing
                        
                        if message.get("command") == "CLIENT_READY" and current_player_id is None:
                            player_id = self.player_id_counter
                            self.player_id_counter += 1
                            self.clients[player_id] = client_socket 
                            current_player_id = player_id 

                            player_name = message.get("name", f"Player {player_id} (Remote)")
                            start_x = 300 + (player_id * 70) 
                            start_y = 300
                            
                            # --- TANGANI POTENSIAL ERROR SAAT MENAMBAHKAN PEMAIN KE GAME ---
                            try:
                                self.game_instance.add_player(current_player_id, start_x, start_y, "assets/meme4.png", player_name)
                                print(f"Game: Player {current_player_id} ('{player_name}') added to game state.")
                                self.send_to_client(client_socket, {"command": "SET_ID", "id": current_player_id})
                                print(f"Server: Sent SET_ID ({current_player_id}) to {addr}.")
                            except Exception as add_player_e:
                                print(f"Server: ERROR adding player {current_player_id} ('{player_name}') to game state (likely missing sprite 'assets/meme4.png' or other Player init issue): {add_player_e}")
                                # Jika gagal menambah pemain, tutup koneksi untuk klien ini
                                client_socket.close()
                                if current_player_id in self.clients:
                                    del self.clients[current_player_id] # Bersihkan dari daftar klien
                                self.player_id_counter -= 1 # Kembalikan ID jika tidak berhasil digunakan
                                break # Keluar dari loop penanganan klien
                            # --- Akhir penanganan error add_player ---

                        elif current_player_id is not None:
                            self.input_queue.put((current_player_id, message)) 
                            # print(f"Server: Added input from {current_player_id}: {message.get('command')}") # Terlalu verbose
                        else:
                            print(f"Server: Received command '{message.get('command')}' from {addr} before CLIENT_READY. Message: {message}")

                    except json.JSONDecodeError as jde:
                        print(f"Server: Invalid JSON from client {addr} (Line: '{line.strip()}'): {jde}")
                        # Jika JSON terus-menerus tidak valid, putuskan koneksi klien ini
                        break 
                    except KeyError as ke:
                        print(f"Server: Missing expected key in JSON message from {addr}: {ke}. Message: {message}")
                        break
                    except Exception as inner_e: # Tangani error lain saat memproses pesan JSON
                        print(f"Server: UNEXPECTED ERROR processing message from {addr}: {inner_e}. Message: {message}")
                        break
            except ConnectionResetError:
                print(f"Server: Client {addr} (ID:{current_player_id}) connection reset (disconnected forcefully).")
                break
            except Exception as e:
                print(f"Server: Generic error in client handler for {addr} (ID:{current_player_id if current_player_id else 'unknown'}): {e}")
                break
        
        # --- CLEANUP SETELAH DISKONEKSI (baik karena error atau klien menutup) ---
        print(f"Server: Handler for {addr} stopping. Cleaning up...")
        if current_player_id is not None: # Pastikan ID sudah ditetapkan sebelum mencoba menghapus
            if current_player_id in self.clients:
                del self.clients[current_player_id]
                print(f"Server: Removed client {current_player_id} from active sockets list.")
            
            # Panggil game_instance untuk menghapus pemain dari game state
            self.game_instance.remove_player(current_player_id)
            print(f"Server: Signaled game instance to remove player {current_player_id}.")
        else:
            print(f"Server: Client {addr} disconnected before ID assignment. No player to remove from game.")

        client_socket.close()

    def send_to_client(self, client_socket, message_dict):
        try:
            message = json.dumps(message_dict) + '\n'
            client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Server: Error sending message to client: {e}")

    def get_network_input(self):
        inputs = []
        while not self.input_queue.empty():
            inputs.append(self.input_queue.get())
        return inputs

    def shutdown(self):
        print("Server: Shutting down network manager...")
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
        except OSError as e:
            print(f"Server: Error during server socket shutdown: {e}")