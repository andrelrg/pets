#include "rede.h"

#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiManager.h>

#include "placa.h"

static WiFiManager wm;
static WebServer servidor(PORTA_HTTP);
static AoReceber receber_;
static AoStatus status_;
static bool conectado = false;

static void responder(int codigo, const String& json) {
  servidor.sendHeader("Access-Control-Allow-Origin", "*");
  servidor.send(codigo, "application/json; charset=utf-8", json);
}

static void postEvento() {
  const String& corpo = servidor.arg("plain");
  Evento ev;
  String erro = lerEvento(corpo.c_str(), corpo.length(), ev);
  if (erro.length()) {
    erro.replace("\"", "'");
    return responder(400, "{\"erro\": \"" + erro + "\"}");
  }
  receber_(ev);
  responder(202, "{\"ok\": true}");
}

void redeIniciar(AoReceber receber, AoStatus status) {
  receber_ = receber;
  status_ = status;

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(NOME_REDE);
  // Não bloqueia: sem Wi-Fi configurado, o portal fica aberto e a serial segue funcionando.
  wm.setConfigPortalBlocking(false);
  wm.setTitle("pets");
  if (wm.autoConnect(REDE_CONFIG)) {
    Serial.println("[wifi] conectando com a rede salva...");
  } else {
    Serial.printf("[wifi] sem rede salva: conecte-se à rede \"%s\" para configurar\n", REDE_CONFIG);
  }

  servidor.on("/evento", HTTP_POST, postEvento);
  servidor.on("/", HTTP_GET, [] { responder(200, status_()); });
  servidor.onNotFound([] { responder(404, "{\"erro\": \"use POST /evento\"}"); });
}

void redeAtualizar() {
  wm.process();
  if (!conectado && WiFi.status() == WL_CONNECTED) {
    conectado = true;
    servidor.begin();
    if (MDNS.begin(NOME_REDE)) MDNS.addService("http", "tcp", PORTA_HTTP);
    Serial.printf("[wifi] conectado: http://%s.local:%d  (IP %s)\n", NOME_REDE, PORTA_HTTP,
                  WiFi.localIP().toString().c_str());
  } else if (conectado && WiFi.status() != WL_CONNECTED) {
    conectado = false;
    Serial.println("[wifi] conexão perdida, tentando de novo...");
  }
  if (conectado) servidor.handleClient();
}

void redeEsquecerWifi() {
  Serial.println("[wifi] esquecendo a rede salva e reiniciando...");
  wm.resetSettings();
  delay(200);
  ESP.restart();
}

String redeDescricao() {
  if (WiFi.status() == WL_CONNECTED)
    return String("http://") + NOME_REDE + ".local:" + PORTA_HTTP + " (IP " + WiFi.localIP().toString() + ")";
  return String("desconectado (portal: rede \"") + REDE_CONFIG + "\")";
}
