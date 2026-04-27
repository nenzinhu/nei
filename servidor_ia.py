import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import google.auth
from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
from ultralytics import YOLO
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
import io

app = Flask(__name__)
CORS(app) 

# Configuração Vertex AI (Autenticação sem chave no código)
try:
    # Tenta obter credenciais e projeto automaticamente do ambiente
    credentials, project_id = google.auth.default()
    vertexai.init(project=project_id, location="us-central1")
    model_gemini = GenerativeModel("gemini-1.5-flash-002")
    print(f"VERTEX AI: Autenticado no projeto {project_id}")
except Exception as e:
    print(f"AVISO: Falha na autenticação Vertex AI: {e}")
    print("Execute 'gcloud auth application-default login' no terminal.")
    model_gemini = None

# Caminhos dos modelos locais
model_pecas_path = 'modelo_seguros.pt'
repo_dano = "beingamit99/car_damage_detection"

# DICIONÁRIOS DE TRADUÇÃO
TRADUCAO_PECAS = {
    "hood": "Capô",
    "front_bumper": "Para-choque Dianteiro",
    "rear_bumper": "Para-choque Traseiro",
    "headlight": "Farol",
    "headlamp": "Farol",
    "damaged headlight": "Farol Danificado",
    "damaged hood": "Capô Danificado",
    "damaged bumper": "Para-choque Danificado",
    "damaged door": "Porta Danificada",
    "fender": "Paralama",
    "door": "Porta",
    "mirror": "Retrovisor",
    "windshield": "Para-brisa",
    "wheel": "Roda/Pneu",
    "trunk": "Porta-malas",
    "grille": "Grade Frontal"
}

TRADUCAO_DANOS = {
    0: "Rachadura (Crack)",
    1: "Arranhão (Scratch)",
    2: "Pneu Furado (Tire Flat)",
    3: "Amassado (Dent)",
    4: "Vidro Quebrado (Glass Shatter)",
    5: "Lanterna/Farol Quebrado (Lamp Broken)"
}

print("---")
print("INICIANDO SISTEMA DE IA EM PORTUGUÊS - PMRV-SC")
try:
    modelo_pecas = YOLO(model_pecas_path)
    proc_dano = AutoImageProcessor.from_pretrained(repo_dano)
    mod_dano = AutoModelForImageClassification.from_pretrained(repo_dano)
    print("SISTEMA PRONTO: http://127.0.0.1:5000")
    print("---")
except Exception as e:
    print(f"ERRO: {e}")

@app.route('/analisar_dano', methods=['POST'])
def analisar_dano():
    if 'foto' not in request.files:
        return jsonify({"erro": "Nenhuma foto enviada"}), 400
    
    arquivo = request.files['foto']
    caminho_temp = "temp_analise.jpg"
    arquivo.save(caminho_temp)
    
    try:
        # 1. Peças (com tradução)
        res_pecas = modelo_pecas.predict(caminho_temp, conf=0.25, verbose=False)
        pecas_pt = []
        for r in res_pecas:
            for b in r.boxes:
                label_en = modelo_pecas.names[int(b.cls[0])].lower()
                # Busca tradução ou usa o original se não encontrar
                pecas_pt.append(TRADUCAO_PECAS.get(label_en, label_en.capitalize()))
        
        # 2. Tipo de Dano (com tradução)
        img = Image.open(caminho_temp).convert("RGB")
        inputs = proc_dano(images=img, return_tensors="pt")
        with torch.no_grad():
            outputs = mod_dano(**inputs)
        
        tipo_idx = outputs.logits.argmax(-1).item()
        dano_pt = TRADUCAO_DANOS.get(tipo_idx, "Dano não identificado")

        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
            
        return jsonify({
            "sucesso": True,
            "dano_detectado": dano_pt,
            "pecas_afetadas": list(set(pecas_pt))
        })
    except Exception as e:
        if os.path.exists(caminho_temp): os.remove(caminho_temp)
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/vertex_analisar_sinistro', methods=['POST'])
def vertex_analisar_sinistro():
    # ... (mantenho o código anterior de análise de imagem)

@app.route('/gerar_narrativa', methods=['POST'])
def gerar_narrativa():
    # ... (código existente)

@app.route('/ocr_placa', methods=['POST'])
def ocr_placa():
    if not model_gemini:
        return jsonify({"sucesso": False, "erro": "Vertex AI não autenticado"}), 503
    
    if 'foto' not in request.files:
        return jsonify({"erro": "Nenhum frame enviado"}), 400
    
    try:
        arquivo = request.files['foto']
        img_bytes = arquivo.read()
        image_part = Part.from_data(data=img_bytes, mime_type="image/jpeg")
        
        prompt = """
        Extraia APENAS o texto da placa de veículo visível nesta imagem. 
        Retorne no formato: ABC1D23 (sem espaços ou traços).
        Se não houver placa visível ou legível, retorne 'ERRO'.
        Ignore qualquer outro texto na imagem.
        """
        
        response = model_gemini.generate_content([prompt, image_part])
        texto_placa = response.text.strip().upper().replace(" ", "").replace("-", "")
        
        if "ERRO" in texto_placa or len(texto_placa) < 7:
            return jsonify({"sucesso": False, "mensagem": "Placa não detectada"})
            
        return jsonify({
            "sucesso": True,
            "placa": texto_placa
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
