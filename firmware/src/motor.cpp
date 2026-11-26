#include "motor.h"

#include <ArduinoJson.h>
#include <algorithm>

// Evento -> papel do pet que responde quando pet = "auto" (igual ao simulador).
static const char* papelDoEvento(const String& evento) {
  if (evento == "erro" || evento == "aviso" || evento == "pendente" || evento == "deploy" || evento == "parado")
    return "alerta";
  return "progresso";
}

// Sem tela ainda: estima quanto a fala duraria (reação + digitação + leitura).
static uint32_t duracaoFala(const Fala& f) {
  const uint32_t caracteres = f.detalhe.length() + 24;  // ~ frase do pet em volta do detalhe
  return 1500 + caracteres * 31 + 1400 + caracteres * 35;
}

Motor::Motor(const PetInfo* pets, size_t n, uint32_t dormirMs, uint32_t paradoMs)
    : pets_(pets), nPets_(n), dormirMs_(dormirMs), paradoMs_(paradoMs) {}

std::vector<const PetInfo*> Motor::destinatarios(const Evento& ev) const {
  std::vector<const PetInfo*> r;
  if (ev.pet == "ambos") {
    for (size_t i = 0; i < nPets_; i++) r.push_back(&pets_[i]);
    return r;
  }
  if (ev.pet != "auto") {
    for (size_t i = 0; i < nPets_; i++)
      if (ev.pet == pets_[i].id) r.push_back(&pets_[i]);
  } else {
    const char* papel = papelDoEvento(ev.tipo);
    for (size_t i = 0; i < nPets_ && r.empty(); i++)
      if (!strcmp(pets_[i].papel, papel) || !strcmp(pets_[i].papel, "ambos")) r.push_back(&pets_[i]);
  }
  if (r.empty() && nPets_) r.push_back(&pets_[0]);
  return r;
}

void Motor::receber(const Evento& entrada, uint32_t agora) {
  ultimaAtividade_ = agora;
  Evento ev = entrada;

  if (ev.tipo == "progresso") {
    tarefa_ = Tarefa{};
    tarefa_.ativa = true;
    tarefa_.nome = ev.tarefa.length() ? ev.tarefa : (ev.detalhe.length() ? ev.detalhe : String("tarefa"));
    tarefa_.temValor = ev.temValor;
    tarefa_.valor = ev.valor;
    tarefa_.atualizadaEm = agora;
    tarefa_.limiteMs = ev.limiteS ? ev.limiteS * 1000 : paradoMs_;
    if (ev.temValor && ev.valor >= 100) {
      // 100% = conclusão: vira um "sucesso" (comemora e fala, se não for silencioso).
      tarefa_.concluidaEm = agora;
      ev.tipo = "sucesso";
      ev.detalhe = tarefa_.nome;
      Serial.printf("[tarefa] %s concluída!\n", tarefa_.nome.c_str());
    } else {
      Serial.printf("[tarefa] %s %s\n", tarefa_.nome.c_str(),
                    ev.temValor ? (String(ev.valor, 0) + "%").c_str() : "...");
    }
  } else if (ev.tipo == "sucesso" && tarefa_.ativa && !tarefa_.concluidaEm) {
    if (tarefa_.temValor) tarefa_.valor = 100;
    tarefa_.concluidaEm = agora;
    Serial.printf("[tarefa] %s concluída!\n", tarefa_.nome.c_str());
  }
  if (ev.silencioso) return;  // só o painel

  std::vector<Fala> novas;
  for (auto* p : destinatarios(ev)) novas.push_back({p->id, ev.tipo, ev.detalhe, ev.prioridade});

  if (ev.prioridade == Prioridade::Alta) {
    // Interrompe a fala atual e passa na frente do resto.
    fila_.insert(fila_.begin(), novas.begin(), novas.end());
    if (temAtual_) Serial.printf("[interrompe] %s\n", atual_.pet.c_str());
    encerrar();
  } else {
    fila_.insert(fila_.end(), novas.begin(), novas.end());
    std::stable_sort(fila_.begin(), fila_.end(),
                     [](const Fala& a, const Fala& b) { return a.prioridade > b.prioridade; });
  }
}

void Motor::iniciar(const Fala& f, uint32_t agora) {
  atual_ = f;
  temAtual_ = true;
  inicioFala_ = agora;
  fimFala_ = agora + duracaoFala(f);
  Serial.printf("[fala] %s · %s · \"%s\" (%s)\n", f.pet.c_str(), f.evento.c_str(), f.detalhe.c_str(),
                nomePrioridade(f.prioridade));
}

void Motor::encerrar() { temAtual_ = false; }

void Motor::pularFala(uint32_t agora) {
  if (!temAtual_) return;
  Serial.printf("[pula] %s\n", atual_.pet.c_str());
  encerrar();
  ultimaAtividade_ = agora;
}

void Motor::atualizar(uint32_t agora) {
  if (tarefa_.ativa && tarefa_.concluidaEm && agora - tarefa_.concluidaEm > 10000) {
    tarefa_.ativa = false;
  } else if (tarefa_.ativa && !tarefa_.concluidaEm && !tarefa_.parada &&
             agora - tarefa_.atualizadaEm > tarefa_.limiteMs) {
    // Muito tempo sem progresso: o pet de alerta avisa (uma vez por tarefa parada).
    tarefa_.parada = true;
    Evento ev;
    ev.tipo = "parado";
    uint32_t minutos = max<uint32_t>(1, (agora - tarefa_.atualizadaEm + 30000) / 60000);
    ev.detalhe = tarefa_.nome + ", " + String(minutos) + " min sem progresso";
    receber(ev, agora);
  }

  if (temAtual_ && (int32_t)(agora - fimFala_) >= 0) {
    Serial.printf("[fim] %s\n", atual_.pet.c_str());
    encerrar();
    ultimaAtividade_ = agora;
  }
  if (!temAtual_ && !fila_.empty()) {
    Fala f = fila_.front();
    fila_.erase(fila_.begin());
    iniciar(f, agora);
  }
}

Estado Motor::estado() const {
  if (temAtual_) return Estado::Falando;
  if (millis() - ultimaAtividade_ >= dormirMs_) return Estado::Dormindo;
  if (tarefa_.ativa && !tarefa_.concluidaEm && !tarefa_.parada) return Estado::Pensando;
  return Estado::Idle;
}

String Motor::statusJson() const {
  JsonDocument doc;
  JsonArray pets = doc["pets"].to<JsonArray>();
  for (size_t i = 0; i < nPets_; i++) pets.add(pets_[i].id);
  doc["fila"] = fila_.size();
  doc["estado"] = nomeEstado(estado());
  if (temAtual_) {
    doc["falando"]["pet"] = atual_.pet;
    doc["falando"]["evento"] = atual_.evento;
    doc["falando"]["detalhe"] = atual_.detalhe;
  }
  if (tarefa_.ativa) {
    doc["tarefa"]["nome"] = tarefa_.nome;
    if (tarefa_.temValor) doc["tarefa"]["valor"] = tarefa_.valor;
    doc["tarefa"]["situacao"] = tarefa_.concluidaEm ? "concluida" : tarefa_.parada ? "parada" : "andamento";
  }
  String s;
  serializeJson(doc, s);
  return s;
}

const char* nomeEstado(Estado e) {
  switch (e) {
    case Estado::Falando: return "falando";
    case Estado::Pensando: return "pensando";
    case Estado::Dormindo: return "dormindo";
    default: return "idle";
  }
}
