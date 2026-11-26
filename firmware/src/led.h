// Luz de aviso: um padrão de brilho para cada evento/estado (LED da placa, PWM).
#pragma once

#include <Arduino.h>

enum class PadraoLed : uint8_t { Apagado, Respirando, Pensando, Erro, Aviso, Sucesso, Marco, Deploy, Info };

PadraoLed padraoDoEvento(const String& evento);

class Led {
 public:
  explicit Led(int pino) : pino_(pino) {}
  void iniciar();
  void tocar(PadraoLed p, uint32_t agora);  // reinicia só se mudou
  void atualizar(uint32_t agora);

 private:
  void escrever(uint8_t brilho);
  int pino_;
  PadraoLed padrao_ = PadraoLed::Apagado;
  uint32_t inicio_ = 0;
};
