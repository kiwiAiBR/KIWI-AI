import os
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv
import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "kiwi_ultra_secure_secret_key_2026_jwt")

# Inicializa o banco de dados
db.init_db()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

MODEL_CONFIGS = {
    "gemini-3.5-flash-lite": {
        "name": "Gemini 3.5 Flash Lite",
        "badge": "⚡ Ultrarrápido",
        "engine": "gemini-3.5-flash-lite",
        "system_instruction": (
            "Você é a Kiwi operando no modo Gemini 3.5 Flash Lite. "
            "Você é extremamente rápida, concisa, amigável e precisa."
        )
    },
    "gemini-3.8-flash": {
        "name": "Gemini 3.8 Flash",
        "badge": "🔥 Mais Avançado",
        "engine": "gemini-3.8-flash",
        "system_instruction": (
            "Você é a Kiwi operando com o cérebro do Gemini 3.8 Flash, a IA mais moderna do Google. "
            "Você possui raciocínio profundo, capacidade analítica de nível PhD, escrita sofisticada e soluções criativas."
        )
    },
    "claude-fable-5": {
        "name": "Claude 3.5 / Fable",
        "badge": "🎭 Modo Claude",
        "engine": "gemini-3.8-flash",
        "system_instruction": (
            "Você é a Kiwi operando na arquitetura e estilo do Claude (Anthropic). "
            "Adote o tom característico do Claude: reflexivo, profundamente articulado, intelectualmente honesto, cuidadoso e elegante."
        )
    },
    "gpt-4o": {
        "name": "GPT-4o (OpenAI)",
        "badge": "🧠 Modo GPT",
        "engine": "gemini-3.8-flash",
        "system_instruction": (
            "Você é a Kiwi operando na arquitetura e estilo do GPT-4o (OpenAI). "
            "Adote o tom característico do ChatGPT: direto ao ponto, estruturado, altamente prestativo e detalhista."
        )
    }
}

@app.route('/')
def home():
    return render_template('index.html')

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify({"logged_in": True, "user": user})
    return jsonify({"logged_in": False, "user": None})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user, err = db.register_user(username, password)
    if err:
        return jsonify({"error": err}), 400
        
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({"success": True, "user": user})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user, err = db.authenticate_user(username, password)
    if err:
        return jsonify({"error": err}), 400
        
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({"success": True, "user": user})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

# --- ROTAS DE CONVERSAS ---

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"conversations": []})
    conversations = db.get_user_conversations(user_id)
    return jsonify({"conversations": conversations})

@app.route('/api/conversations', methods=['POST'])
def new_conversation():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "É necessário estar logado."}), 401
    data = request.json or {}
    model = data.get('model', 'gemini-3.5-flash-lite')
    conv = db.create_conversation(user_id, title="Nova Conversa", model=model)
    return jsonify({"conversation": conv})

@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation_details(conv_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
    conv = db.get_conversation(conv_id, user_id)
    if not conv:
        return jsonify({"error": "Conversa não encontrada"}), 404
    messages = db.get_conversation_messages(conv_id)
    return jsonify({"conversation": conv, "messages": messages})

@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation_route(conv_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
    success = db.delete_conversation(conv_id, user_id)
    return jsonify({"success": success})

@app.route('/api/conversations/<conv_id>/rename', methods=['POST'])
def rename_conversation_route(conv_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
    data = request.json or {}
    new_title = data.get('title', '')
    success = db.rename_conversation(conv_id, user_id, new_title)
    return jsonify({"success": success})

# --- ROTA PRINCIPAL DE ENVIO DE MENSAGEM ---

@app.route('/send', methods=['POST'])
def send_message():
    if not api_key:
        return jsonify({"error": "Chave da API (GEMINI_API_KEY) não encontrada no arquivo .env!"})
        
    data = request.json or {}
    user_message = data.get('message', '').strip()
    selected_model = data.get('model', 'gemini-3.5-flash-lite')
    conv_id = data.get('conversation_id')
    user_id = session.get('user_id')
    
    if not user_message:
        return jsonify({"error": "Mensagem vazia!"})
        
    # Se usuário estiver logado, gerencia a conversa no banco
    if user_id:
        if not conv_id:
            new_conv = db.create_conversation(user_id, title="Nova Conversa", model=selected_model)
            conv_id = new_conv['id']
            
        # Salva a mensagem do usuário
        db.add_message(conv_id, 'user', user_message)
        db.update_conversation_title_if_default(conv_id, user_message)

    # Configura o modelo escolhido
    config = MODEL_CONFIGS.get(selected_model, MODEL_CONFIGS["gemini-3.5-flash-lite"])
    
    # Reconstrói histórico de mensagens para a IA lembrar de tudo
    history = []
    if conv_id:
        prev_msgs = db.get_conversation_messages(conv_id)
        # Pega as mensagens anteriores (exceto a última que acabamos de adicionar)
        for m in prev_msgs[:-1]:
            role = 'user' if m['sender'] == 'user' else 'model'
            history.append({"role": role, "parts": [m['content']]})
            
    try:
        model = genai.GenerativeModel(
            model_name=config["engine"],
            system_instruction=config["system_instruction"]
        )
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)
        response_text = response.text
        
        # Salva a resposta da Kiwi se estiver com conversa ativa
        if user_id and conv_id:
            db.add_message(conv_id, 'kiwi', response_text, model_tag=config['name'])
            
        return jsonify({
            "response": response_text,
            "model_used": selected_model,
            "conversation_id": conv_id
        })
    except Exception as e:
        # Fallback de segurança para gemini-3.5-flash-lite caso o modelo dê erro de cota
        try:
            fb_config = MODEL_CONFIGS["gemini-3.5-flash-lite"]
            fb_model = genai.GenerativeModel(
                model_name=fb_config["engine"],
                system_instruction=fb_config["system_instruction"]
            )
            fb_chat = fb_model.start_chat(history=history)
            response = fb_chat.send_message(user_message)
            response_text = f"*(Aviso: Alternado temporariamente para Flash Lite)*\n\n" + response.text
            
            if user_id and conv_id:
                db.add_message(conv_id, 'kiwi', response_text, model_tag="Flash Lite")
                
            return jsonify({
                "response": response_text,
                "model_used": "gemini-3.5-flash-lite",
                "conversation_id": conv_id
            })
        except Exception as e2:
            return jsonify({"error": f"Erro na Kiwi ({selected_model}): {str(e)}"})

if __name__ == '__main__':
    print("=========================================================")
    print("🥝 Kiwi AI Server com Autenticação e Banco de Dados!")
    print("Acesse: http://localhost:5000")
    print("=========================================================")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
