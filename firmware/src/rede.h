// Wi-Fi (portal de configuração), mDNS (pets.local) e a API HTTP do simulador:
//   POST /evento   corpo JSON (ver eventos.h)     -> 202 {"ok": true}
//   GET  /         status                          -> {"pets": [...], "fila": n, ...}
#pragma once

#include <functional>

#include "eventos.h"

using AoReceber = std::function<void(const Evento&)>;
using AoStatus = std::function<String()>;

void redeIniciar(AoReceber receber, AoStatus status);
void redeAtualizar();
void redeEsquecerWifi();  // apaga a rede salva e reinicia no portal
String redeDescricao();
