import sqlite3
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kiwi.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Conversas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabela de Mensagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            model_tag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Autenticação
def register_user(username, password):
    username = username.strip()
    if not username or not password:
        return None, "Nome de usuário e senha são obrigatórios."
    if len(username) < 3:
        return None, "O nome de usuário deve ter pelo menos 3 caracteres."
    if len(password) < 4:
        return None, "A senha deve ter pelo menos 4 caracteres."
        
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        pw_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pw_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "username": username}, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, "Este nome de usuário já está em uso."
    except Exception as e:
        conn.close()
        return None, f"Erro ao criar conta: {str(e)}"

def authenticate_user(username, password):
    username = username.strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not check_password_hash(row["password_hash"], password):
        return None, "Usuário ou senha incorretos."
        
    return {"id": row["id"], "username": row["username"]}, None

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"]}
    return None

# Gerenciamento de Conversas
def create_conversation(user_id, title="Nova Conversa", model="gemini-3.5-flash-lite"):
    conv_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, user_id, title, model) VALUES (?, ?, ?, ?)",
        (conv_id, user_id, title, model)
    )
    conn.commit()
    conn.close()
    return {"id": conv_id, "title": title, "model": model}

def get_user_conversations(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, model, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_conversation(conv_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, model, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
        (conv_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_conversation_messages(conv_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, sender, content, model_tag, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conv_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_message(conv_id, sender, content, model_tag=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, sender, content, model_tag) VALUES (?, ?, ?, ?)",
        (conv_id, sender, content, model_tag)
    )
    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,)
    )
    conn.commit()
    conn.close()

def update_conversation_title_if_default(conv_id, first_message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM conversations WHERE id = ?", (conv_id,))
    row = cursor.fetchone()
    if row and row["title"] == "Nova Conversa":
        # Gera título compacto a partir da mensagem
        new_title = first_message.strip()[:32]
        if len(first_message.strip()) > 32:
            new_title += "..."
        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conv_id))
        conn.commit()
    conn.close()

def delete_conversation(conv_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def rename_conversation(conv_id, user_id, new_title):
    new_title = new_title.strip()
    if not new_title:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?",
        (new_title, conv_id, user_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0
