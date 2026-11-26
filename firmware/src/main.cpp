// pets — firmware (fase 0: só a placa)
//
// Recebe eventos pelo Wi-Fi (POST http://pets.local:8765/evento) e pela serial
// (uma linha JSON por evento), mantém a fila com prioridades como o simulador
// e mostra o estado no LED da placa. A tela entra na próxima fase.
//
// Comandos na serial (115200): JSON de evento | status | wifi-esquecer | ajuda

#include <Arduino.h>

#include "eventos.h"
#include "led.h"
#include "motor.h"
#include "placa.h"
#include "rede.h"

static const PetInfo PETS[] = {
    {"nala", "progresso"},
    {"simba", "alerta"},
};

static Motor motor(PETS, sizeof(PETS) / sizeof(PETS[0]));
static Led led(PINO_LED);

static void receber(const Evento& ev) {
  Serial.printf("[evento] %s \"%s\" pet=%s prioridade=%s%s\n", ev.tipo.c_str(), ev.detalhe.c_str(),
                ev.pet.c_str(), nomePrioridade(ev.prioridade), ev.silencioso ? " (silencioso)" : "");
  motor.receber(ev, millis());
}

static void ajuda() {
  Serial.println(
      "Comandos:\n"
      "  {\"evento\": \"erro\", \"detalhe\": \"...\"}   envia um evento (mesmo JSON da API)\n"
      "  status          estado, fila e rede\n"
      "  wifi-esquecer   apaga a rede salva e abre o portal de configuração\n"
      "  ajuda           esta mensagem");
}

static void comandoSerial(String linha) {
  linha.trim();
  if (!linha.length()) return;
  if (linha[0] == '{') {
    Evento ev;
    String erro = lerEvento(linha.c_str(), linha.length(), ev);
    if (erro.length()) Serial.printf("[erro] %s\n", erro.c_str());
    else receber(ev);
  } else if (linha == "status") {
    Serial.printf("[status] %s\n[rede] %s\n", motor.statusJson().c_str(), redeDescricao().c_str());
  } else if (linha == "wifi-esquecer") {
    redeEsquecerWifi();
  } else {
    ajuda();
  }
}

static void lerSerial() {
  static String buffer;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      comandoSerial(buffer);
      buffer = "";
    } else if (buffer.length() < 1024) {
      buffer += c;
    }
  }
}

// Botão A: pula a fala atual. (Botão B: modo silencioso, quando houver som.)
static void lerBotoes(uint32_t agora) {
  static bool antes = false;
  static uint32_t mudou = 0;
  bool apertado = digitalRead(PINO_BOTAO_A) == LOW;
  if (apertado != antes && agora - mudou > 30) {  // debounce
    mudou = agora;
    antes = apertado;
    if (apertado) motor.pularFala(agora);
  }
}

static void atualizarLed(uint32_t agora) {
  const Fala* f = motor.falaAtual();
  switch (motor.estado()) {
    case Estado::Falando: led.tocar(padraoDoEvento(f->evento), agora); break;
    case Estado::Pensando: led.tocar(PadraoLed::Pensando, agora); break;
    case Estado::Dormindo: led.tocar(PadraoLed::Apagado, agora); break;
    default: led.tocar(PadraoLed::Respirando, agora); break;
  }
  led.atualizar(agora);
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.printf("\n=== pets %s · %s ===\n", VERSAO, PLACA_NOME);

  pinMode(PINO_BOTAO_A, INPUT_PULLUP);
  pinMode(PINO_BOTAO_B, INPUT_PULLUP);
  led.iniciar();
  redeIniciar(receber, [] { return motor.statusJson(); });
  ajuda();
}

void loop() {
  uint32_t agora = millis();
  redeAtualizar();
  lerSerial();
  lerBotoes(agora);
  motor.atualizar(agora);
  atualizarLed(agora);
  delay(5);
}
