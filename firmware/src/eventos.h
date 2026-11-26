// Eventos recebidos (HTTP ou serial): mesmo JSON do simulador.
//   {"evento": "erro", "detalhe": "3 testes falharam", "pet": "auto",
//    "prioridade": "normal", "valor": 60, "silencioso": false, "tarefa": "...", "limite": 600}
#pragma once

#include <Arduino.h>

enum class Prioridade : uint8_t { Baixa = 0, Normal = 1, Alta = 2 };

struct Evento {
  String tipo;               // erro | aviso | sucesso | progresso | pendente | marco | deploy | info
  String detalhe;
  String pet = "auto";       // id do pet, "auto" (pelo papel) ou "ambos"
  Prioridade prioridade = Prioridade::Normal;
  bool temValor = false;     // progresso 0-100
  float valor = 0;
  bool silencioso = false;   // só atualiza o painel, sem fala
  String tarefa;             // nome da tarefa (progresso); padrão = detalhe
  uint32_t limiteS = 0;      // progresso: s sem novo progresso até o alerta "parado" (0 = padrão)
};

// Lê o JSON em `ev`. Devolve "" se deu certo, ou a mensagem de erro.
String lerEvento(const char* json, size_t tamanho, Evento& ev);

const char* nomePrioridade(Prioridade p);
