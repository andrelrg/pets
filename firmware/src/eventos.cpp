#include "eventos.h"

#include <ArduinoJson.h>

String lerEvento(const char* json, size_t tamanho, Evento& ev) {
  JsonDocument doc;
  DeserializationError e = deserializeJson(doc, json, tamanho);
  if (e) return String("JSON inválido: ") + e.c_str();
  if (!doc.is<JsonObject>()) return "o corpo precisa ser um objeto JSON";
  if (!doc["evento"].is<const char*>()) return "campo \"evento\" é obrigatório";

  ev = Evento{};
  ev.tipo = doc["evento"].as<const char*>();
  ev.detalhe = doc["detalhe"] | "";
  ev.pet = doc["pet"] | "auto";
  ev.tarefa = doc["tarefa"] | "";
  ev.silencioso = doc["silencioso"] | false;
  ev.limiteS = doc["limite"] | 0;

  String p = doc["prioridade"] | "normal";
  ev.prioridade = p == "alta" ? Prioridade::Alta : p == "baixa" ? Prioridade::Baixa : Prioridade::Normal;

  if (!doc["valor"].isNull()) {
    ev.temValor = true;
    ev.valor = constrain(doc["valor"].as<float>(), 0.0f, 100.0f);
  }
  return "";
}

const char* nomePrioridade(Prioridade p) {
  switch (p) {
    case Prioridade::Alta: return "alta";
    case Prioridade::Baixa: return "baixa";
    default: return "normal";
  }
}
