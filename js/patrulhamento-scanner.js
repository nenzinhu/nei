/**
 * Módulo: Scanner Tático de Placas (Inovação Vertex)
 * Reconhecimento de placas por vídeo em tempo real para patrulhamento em lote.
 */

let SCANNER_STREAM = null;
let SCANNER_INTERVAL = null;
let SCANNER_PLACAS_DETECTADAS = new Set();

/**
 * Inicializa ou encerra o scanner de vídeo.
 */
async function scanner_toggle(ativo) {
    const video = document.getElementById('pat_scanner_video');
    const status = document.getElementById('pat_scanner_status');

    if (!ativo) {
        if (SCANNER_STREAM) {
            SCANNER_STREAM.getTracks().forEach(track => track.stop());
            SCANNER_STREAM = null;
        }
        clearInterval(SCANNER_INTERVAL);
        if (status) status.textContent = 'SCANNER DESATIVADO';
        return;
    }

    try {
        SCANNER_STREAM = await navigator.mediaDevices.getUserMedia({
            video: { 
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        video.srcObject = SCANNER_STREAM;
        
        if (status) status.textContent = 'SCANNER ATIVO - BUSCANDO...';
        
        // Inicia o ciclo de captura (a cada 2.5 segundos para não sobrecarregar o servidor/Vertex)
        SCANNER_INTERVAL = setInterval(scanner_processarFrame, 2500);

    } catch (err) {
        console.error('Erro ao acessar câmera:', err);
        alert('Não foi possível acessar a câmera para o scanner tático.');
    }
}

/**
 * Captura um frame do vídeo e envia para OCR na IA.
 */
async function scanner_processarFrame() {
    const video = document.getElementById('pat_scanner_video');
    const canvas = document.getElementById('pat_scanner_canvas');
    const status = document.getElementById('pat_scanner_status');
    
    if (!video || video.paused || video.ended) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Converte para Blob (JPEG) para envio
    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('foto', blob, 'frame.jpg');

        try {
            if (status) status.textContent = '🔍 PROCESSANDO...';
            
            const response = await fetch('http://127.0.0.1:5000/ocr_placa', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.sucesso && data.placa) {
                const placa = data.placa;
                
                if (!SCANNER_PLACAS_DETECTADAS.has(placa)) {
                    SCANNER_PLACAS_DETECTADAS.add(placa);
                    if (status) {
                        status.textContent = `✅ PLACA: ${placa}`;
                        status.className = 'absolute bottom-2 left-2 bg-green-600 text-white text-[10px] px-2 py-1 rounded-full font-bold animate-bounce';
                        setTimeout(() => {
                            status.className = 'absolute bottom-2 left-2 bg-blue-600 text-white text-[10px] px-2 py-1 rounded-full font-bold';
                            status.textContent = 'BUSCANDO PRÓXIMA...';
                        }, 2000);
                    }
                    
                    // Notificação sonora tática (opcional)
                    scanner_notificarSucesso();
                    
                    // Adiciona automaticamente ao lote de patrulhamento
                    scanner_adicionarAoLote(placa);
                } else {
                    if (status) status.textContent = `🔁 PLACA JÁ NO LOTE: ${placa}`;
                }
            } else {
                if (status) status.textContent = 'AGUARDANDO PLACA...';
            }
        } catch (e) {
            console.error('Erro OCR:', e);
            if (status) status.textContent = '❌ IA OFFLINE';
        }
    }, 'image/jpeg', 0.8);
}

/**
 * Integra com o módulo de patrulhamento para salvar a placa.
 */
function scanner_adicionarAoLote(placa) {
    const areaPlacas = document.getElementById('pat_lote_placas');
    if (areaPlacas) {
        const atual = areaPlacas.value.trim();
        const novasPlacas = atual ? atual + '\n' + placa : placa;
        areaPlacas.value = novasPlacas;
        
        // Dispara o evento de input para atualizar os contadores do módulo original
        areaPlacas.dispatchEvent(new Event('input'));
        
        console.log(`[TÁTICO] Placa ${placa} adicionada ao lote.`);
    }
}

function scanner_notificarSucesso() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // Nota A5
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        
        gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.1);
    } catch (e) {}
}

window.scanner_toggle = scanner_toggle;
