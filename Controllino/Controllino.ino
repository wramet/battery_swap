#include <Controllino.h>

const int numSwitches = 10; // Total number of limit switches and relays
int digitalInputPins[numSwitches] = {CONTROLLINO_A0, CONTROLLINO_A1, CONTROLLINO_A2, CONTROLLINO_A3, CONTROLLINO_A4, CONTROLLINO_A5, CONTROLLINO_A6, CONTROLLINO_A7, CONTROLLINO_A8, CONTROLLINO_A9};
bool currentStates[numSwitches];
bool previousStates[numSwitches];
unsigned long lastDebounceTime[numSwitches]; // Last time the output pin was toggled
unsigned long debounceDelay = 50; // The debounce time in milliseconds
unsigned long relayActivationTimes[numSwitches]; // Array to store the start time of relay activation
int relayActivationDuration = 100; // Duration for which the relay remains activated in milliseconds
int lastActivatedSwitch = -1; // To remember the last activated switch

void setup() {
    Serial.begin(9600); // Initialize serial communication

    for (int i = 0; i < numSwitches; i++) {
        pinMode(digitalInputPins[i], INPUT); // Use INPUT for external pull-down
        previousStates[i] = digitalRead(digitalInputPins[i]);
        lastDebounceTime[i] = 0;

        pinMode(CONTROLLINO_R0 + i, OUTPUT);
        digitalWrite(CONTROLLINO_R0 + i, LOW); // Ensure relays are off at startup
    }
}

void loop() {
    if (Serial.available() > 0) {
        handleClient();
    }

    checkLimitSwitches();
    updateRelayStates();
}

void handleClient() {
    String message = Serial.readStringUntil('\n');

    if (message.startsWith("Trigger Relay ")) {
        int relayNum = message.substring(14).toInt();
        triggerRelay(relayNum);
        Serial.print("Triggered Relay ");
        Serial.print(relayNum);
        Serial.println(" successfully");
    } else {
        Serial.println("Invalid command: " + message);
    }
}

void checkLimitSwitches() {
    for (int i = 0; i < numSwitches; i++) {
        bool reading = digitalRead(digitalInputPins[i]);
        if (reading != previousStates[i]) {
            lastDebounceTime[i] = millis();
        }

        if ((millis() - lastDebounceTime[i]) > debounceDelay) {
            // ตรวจสอบการเปลี่ยนแปลงสถานะ ไม่ว่าจะเป็นการกดหรือปล่อย
            if (reading != currentStates[i]) {
                currentStates[i] = reading;
                sendSwitchActivation(i, reading); // ส่งสถานะใหม่พร้อมการแจ้งเตือน
            }
        }
        previousStates[i] = reading;
    }
}


void sendSwitchActivation(int switchNum, bool activated) {
    if (activated) {
        Serial.print("Limit switch ");
        Serial.print(switchNum);
        Serial.println(" activated");
    } else{
      Serial.print("");
    }
}

void triggerRelay(int relayNum) {
    if (relayNum >= 0 && relayNum < numSwitches) {
        digitalWrite(CONTROLLINO_R0 + relayNum, HIGH);
        relayActivationTimes[relayNum] = millis();
    }else{
      Serial.println("Relay number out of range");
    }
}

void updateRelayStates() {
    unsigned long currentMillis = millis();

    for (int i = 0; i < numSwitches; i++) {
        if (digitalRead(CONTROLLINO_R0 + i) == HIGH && (currentMillis - relayActivationTimes[i] >= relayActivationDuration)) {
            digitalWrite(CONTROLLINO_R0 + i, LOW);
        }
    }
}
