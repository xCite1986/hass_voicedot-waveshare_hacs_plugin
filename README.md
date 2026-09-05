# VoiceDot Waveshare — Home Assistant Integration

Bindet [VoiceDot](https://github.com/xCite1986/voicedot-waveshare)-Geräte in
Home Assistant ein: automatische Erkennung im Netzwerk, ein Gerät je VoiceDot,
Sensoren, Einstellungen und ein Dienst für Ansagen.

Mehrere VoiceDots werden unterstützt — jeder wird über seine Chip-ID eindeutig
zugeordnet, ein Wechsel der IP-Adresse ist also unkritisch.

---

## Installation

### HACS

1. HACS → **Integrationen** → Menü oben rechts → **Benutzerdefinierte Repositories**
2. URL `https://github.com/xCite1986/hass_voicedot-waveshare_hacs_plugin`,
   Kategorie **Integration**
3. „VoiceDot Waveshare" installieren, Home Assistant neu starten

### Manuell

Den Ordner `custom_components/voicedot` nach `config/custom_components/`
kopieren und Home Assistant neu starten.

---

## Einrichtung

VoiceDot meldet sich per mDNS als `_voicedot._tcp` an. Home Assistant findet
das Gerät dadurch von selbst — die Meldung erscheint unter
**Einstellungen → Geräte & Dienste**, bestätigen genügt.

Alternativ **Integration hinzufügen → VoiceDot Waveshare** und den Hostnamen
eintragen, etwa `voicedot.local`.

> Voraussetzung ist Firmware **v0.7.0** oder neuer — ältere Stände melden weder
> den mDNS-Dienst noch die Geräte-ID.

### Adresse ändern

Bei der Erkennung wird bevorzugt der **mDNS-Name** übernommen
(`voicedotone.local`) — der überlebt einen Wechsel der IP-Adresse. Kann Home
Assistant `.local` nicht auflösen, was in Containern ohne Host-Netzwerk
vorkommt, wird automatisch auf die IP-Adresse zurückgefallen.

Nachträglich ändern lässt sich das über **Einstellungen → Geräte & Dienste →
VoiceDot → Konfigurieren**. Die Adresse wird vor dem Speichern geprüft, und die
Integration lädt sich danach selbst neu.

Wird ein bereits eingerichteter VoiceDot erneut per mDNS gemeldet, aktualisiert
die Integration die hinterlegte Adresse von selbst — ein mit IP angelegter
Eintrag wandert dadurch mit der Zeit auf den Namen.

---

## Entitäten

Pro Gerät entstehen:

### Firmware-Update

Eine `update`-Entitaet zeigt installierte und verfuegbare Version und bietet
den Installieren-Knopf. Die Versionen kommen aus dem Zwischenspeicher des
Geraets, nicht direkt von GitHub: unangemeldet erlaubt deren API 60 Anfragen
pro Stunde und Adresse, und diese Integration fragt alle zehn Sekunden ab.

Vor dem Installieren holt die Integration einmal eine frische Liste, dann
startet das Geraet neu und installiert. Nach etwa einer Minute meldet es sich
mit der neuen Version zurueck.

### Sensoren

| Entität | Inhalt |
|---|---|
| Status | `idle`, `listening`, `thinking`, `speaking`, `error` |
| **Wecker** | Zeitstempel des nächsten Weckens, sonst leer |
| **Timer** | Zeitstempel des Ablaufs, sonst leer |
| **Gruppen** | Anzahl der angelegten Gruppen |
| Radio | laufender Sender oder `aus` |
| Lautstärke-Anhebung | dB, die der Umgebungslärm gerade zulegt |
| Nachbar-VoiceDots | wie viele andere Geräte sich melden |
| Leuchtring | aktuelle Phase des LED-Rings |
| Letzte Frage | Transkript der letzten Aufnahme |
| Letzte Antwort | Antwort des Assistenten |
| Stichwort | aktuell aktives Wake-Word |
| Erkennungen | Zähler seit dem Start |
| Rauschboden | dBFS, laufend nachgeführt |
| Profil | Tag oder Nacht |
| Laufzeit, Freier Heap, Heap-Minimum, WLAN-Signal | Diagnose |

Der vollständige Text von Frage und Antwort steht im Attribut `full_text` —
der Zustand selbst ist in Home Assistant auf 255 Zeichen begrenzt.

**Wecker und Timer sind Zeitstempel**, keine Restzeiten: damit lässt sich in
einer Automation direkt auf den Zeitpunkt triggern, und die Oberfläche zählt
von selbst herunter. Weckzeit, Weckton, Briefing und die Restsekunden stehen
zusätzlich in den Attributen.

Das Gerät meldet die *verbleibenden* Sekunden, der Zeitpunkt wird also alle
zehn Sekunden neu ausgerechnet und läge jedesmal eine Sekunde daneben.
Abweichungen unter fünf Sekunden werden deshalb verworfen — ein laufender
Timer behält das Ende, das er bekommen hat, statt den Verlauf mit
Sekundensprüngen zu füllen.

### Steuerung

| Entität | Funktion |
|---|---|
| Lautstärke | 0–100 % |
| Sprechtempo | 75–135 % |
| Wake-Word | ein/aus |
| Stichwort | Auswahl aus den Modellen der Partition |
| Assist-Pipeline | Auswahl aus den Pipelines in Home Assistant |
| Ansage nach Wake-Word, Automatisches Satzende, Rückfragen fortsetzen, Tag/Nacht-Profil, Markdown entfernen | ein/aus |
| Lautstärke nach Umgebungslärm, Selbst nach Updates sehen, Aushandlung mit anderen VoiceDots | ein/aus |
| **Wecker täglich** | ein/aus |
| Assist starten, Ansage anhören, Ansagen erzeugen, Lautsprecher testen, Neu starten | Aktionen |
| **Wecker löschen, Timer löschen, Briefing sprechen** | Aktionen |

---

## Dienst `voicedot.announce`

```yaml
action: voicedot.announce
target:
  device_id: <dein VoiceDot>
data:
  text: "DING DONG! Es hat geläutet"
```

Ohne Ziel sprechen **alle** bekannten VoiceDots — praktisch für eine Türklingel.

Beispiel für eine Automation:

```yaml
alias: Türklingel ansagen
triggers:
  - trigger: state
    entity_id: binary_sensor.tuerklingel
    to: "on"
actions:
  - action: voicedot.announce
    data:
      text: "DING DONG! Es hat geläutet"
```

Die Sprachausgabe erzeugt VoiceDot über die TTS-Engine der eingestellten
Assist-Pipeline, die Ansage klingt also wie der Assistent selbst.

---

## Wecker, Timer und Briefing

Beides läuft **auf dem Gerät**, nicht in Home Assistant: der Wecker klingelt
auch dann, wenn HA gerade neu startet oder das Netz weg ist. Die Integration
zeigt den Zustand und kann stellen und löschen.

```yaml
action: voicedot.set_alarm
target:
  device_id: <dein VoiceDot>
data:
  time: "06:45"
  daily: true
```

```yaml
action: voicedot.start_timer
target:
  device_id: <dein VoiceDot>
data:
  duration: "00:10:00"
```

Dazu `voicedot.clear_alarm` und `voicedot.clear_timer`, beide ohne Felder.

`voicedot.speak_briefing` lässt das Morning Briefing sofort abfragen und
sprechen. Ohne eigenen Text nimmt das Gerät die Anweisung, die in seinem
Webinterface hinterlegt ist — das Briefing ist **kein fester Text, sondern
eine Aufgabe an die Assist-Pipeline**, das Sprachmodell holt sich Wetter und
Kalender selbst.

```yaml
action: voicedot.speak_briefing
target:
  device_id: <dein VoiceDot>
data:
  text: "Fasse die Termine von morgen kurz zusammen."
```

Gestellt wird sonst per Sprache am Gerät („stelle den Wecker auf sieben Uhr
dreißig", „stelle den Timer auf zehn Minuten", „wie lange noch?"). Weckton und
Timer-Ton werden im Webinterface des Geräts gewählt, weil dort auch die Klänge
liegen.

**Gruppen** („schalte im Obergeschoß das Licht aus") wertet das Gerät selbst
aus; die Integration zeigt sie nur an. Gepflegt werden sie im Webinterface,
weil dort die Entitätensuche sitzt.

---

## Wie es arbeitet

Die Integration fragt alle 10 Sekunden `/api/status` und `/api/config` ab
(`local_polling`). Es gibt keine Cloud-Abhängigkeit und keinen MQTT-Broker;
gesteuert wird ausschließlich über die REST-Endpunkte des Geräts.

Nach jeder Änderung wird sofort neu abgefragt, damit die Oberfläche nicht
hinterherhinkt.

---

## Grenzen

- Die Geräte-API ist **unauthentifiziert**. VoiceDot und Home Assistant
  gehören ins selbe vertrauenswürdige Netz.
- Die Erkennung braucht mDNS im Netz. Bei getrennten VLANs oder blockiertem
  Multicast hilft die manuelle Eingabe.
- Änderungen, die im Webinterface des Geräts vorgenommen werden, erscheinen
  hier mit bis zu 10 Sekunden Verzögerung.
- Wecker und Timer lassen sich hier stellen und löschen, aber ihre Klänge nur
  im Webinterface auswählen — die Liste der Klänge liegt hinter einem eigenen
  Endpunkt und wäre bei jeder Abfrage mitzuladen.
- Gruppen werden angezeigt, aber nicht bearbeitet.
