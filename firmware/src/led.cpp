#include "led.h"

#include <math.h>

static const int CANAL = 0;

PadraoLed padraoDoEvento(const String& e) {
  if (e == "erro") return PadraoLed::Erro;
  if (e == "aviso" || e == "pendente" || e == "parado") return PadraoLed::Aviso;
  if (e == "sucesso") return PadraoLed::Sucesso;
  if (e == "marco") return PadraoLed::Marco;
  if (e == "deploy") return PadraoLed::Deploy;
  return PadraoLed::Info;
}

void Led::iniciar() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(pino_, 5000, 8);
#else
  ledcSetup(CANAL, 5000, 8);
  ledcAttachPin(pino_, CANAL);
#endif
  escrever(0);
}

void Led::escrever(uint8_t brilho) {
  // Correção de gama: o olho percebe brilho de forma não linear.
  uint32_t v = (uint32_t)brilho * brilho / 255;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(pino_, v);
#else
  ledcWrite(CANAL, v);
#endif
}

void Led::tocar(PadraoLed p, uint32_t agora) {
  if (p == padrao_) return;
  padrao_ = p;
  inicio_ = agora;
}

// Piscadas: n pulsos de `on` ms separados por `off`, depois pausa; repete.
static bool piscadas(uint32_t t, int n, uint32_t on, uint32_t off, uint32_t pausa) {
  uint32_t ciclo = n * (on + off) + pausa;
  uint32_t x = t % ciclo;
  if (x >= n * (on + off)) return false;
  return (x % (on + off)) < on;
}

void Led::atualizar(uint32_t agora) {
  uint32_t t = agora - inicio_;
  float b = 0;
  switch (padrao_) {
    case PadraoLed::Apagado: b = 0; break;
    case PadraoLed::Respirando:  // bem fraquinho, ciclo de 4 s
      b = 0.12f * (0.5f - 0.5f * cosf(t * 2 * PI / 4000));
      break;
    case PadraoLed::Pensando:  // um "blip" a cada 2 s
      b = (t % 2000) < 90 ? 0.5f : 0;
      break;
    case PadraoLed::Erro: b = piscadas(t, 3, 80, 80, 450) ? 1 : 0; break;
    case PadraoLed::Aviso: b = piscadas(t, 2, 160, 160, 700) ? 1 : 0; break;
    case PadraoLed::Info: b = (t % 1200) < 120 ? 0.7f : 0; break;
    case PadraoLed::Sucesso:  // respiração forte e lenta
      b = 0.5f - 0.5f * cosf(t * 2 * PI / 1400);
      break;
    case PadraoLed::Marco:  // batimento duplo (tum-tum)
      b = piscadas(t, 2, 110, 140, 800) ? 1 : 0;
      break;
    case PadraoLed::Deploy: {  // contagem regressiva acelerando... e decolou (aceso)
      uint32_t x = t % 3000;
      if (x < 2200) {
        float periodo = 400 - x * 0.15f;
        b = fmodf(x, periodo) < periodo * 0.4f ? 1 : 0;
      } else {
        b = 1;
      }
      break;
    }
  }
  escrever((uint8_t)(constrain(b, 0.0f, 1.0f) * 255));
}
