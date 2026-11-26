// Motor: fila de falas, prioridades, tarefa em andamento e estados de fundo.
// Mesma lógica do simulador (sim/app.py). Nesta fase ainda não há tela: a
// duração de cada fala é estimada e o estado aparece no LED e na serial.
#pragma once

#include <Arduino.h>
#include <vector>

#include "eventos.h"

// Pets e papéis. Provisório: depois virá dos assets gerados (LittleFS).
struct PetInfo {
  const char* id;
  const char* papel;  // alerta | progresso | ambos
};

struct Fala {
  String pet;
  String evento;
  String detalhe;
  Prioridade prioridade;
};

struct Tarefa {
  bool ativa = false;
  String nome;
  bool temValor = false;
  float valor = 0;
  uint32_t atualizadaEm = 0; // millis() do último progresso
  uint32_t limiteMs = 0;     // sem progresso por mais que isso -> alerta "parado"
  uint32_t concluidaEm = 0;  // millis(); 0 = em andamento
  bool parada = false;       // alerta de "sem progresso" já foi dado
};

enum class Estado : uint8_t { Idle, Pensando, Dormindo, Falando };

class Motor {
 public:
  Motor(const PetInfo* pets, size_t n, uint32_t dormirMs = 120000, uint32_t paradoMs = 600000);

  void receber(const Evento& ev, uint32_t agora);
  void atualizar(uint32_t agora);
  void pularFala(uint32_t agora);  // botão A

  Estado estado() const;
  const Fala* falaAtual() const { return temAtual_ ? &atual_ : nullptr; }
  uint32_t inicioFala() const { return inicioFala_; }
  size_t tamanhoFila() const { return fila_.size(); }
  const Tarefa& tarefa() const { return tarefa_; }
  String statusJson() const;

 private:
  std::vector<const PetInfo*> destinatarios(const Evento& ev) const;
  void iniciar(const Fala& f, uint32_t agora);
  void encerrar();

  const PetInfo* pets_;
  size_t nPets_;
  uint32_t dormirMs_;
  uint32_t paradoMs_;
  std::vector<Fala> fila_;
  Fala atual_;
  bool temAtual_ = false;
  uint32_t inicioFala_ = 0, fimFala_ = 0;
  uint32_t ultimaAtividade_ = 0;
  Tarefa tarefa_;
};

const char* nomeEstado(Estado e);
