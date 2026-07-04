import React, { useState } from "react";
import {
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import * as SecureStore from "expo-secure-store";
import { loginUser, registerUser } from "./api"; // Nomi corretti delle funzioni
import { PATIENT_INFO_KEY } from "./config";
import styles from "./style";


export default function LoginScreen({ onLogin }) {
  // "login" mostra solo username/password. "register" mostra anche i dati
  // anagrafici minimi del paziente (Punto 9 dei requisiti: scheda paziente
  // - dati anagrafici), che vengono salvati insieme a username/password.
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [patientName, setPatientName] = useState("");
  const [ageYears, setAgeYears] = useState("");
  const [ageMonths, setAgeMonths] = useState("");
  const [busy, setBusy] = useState(false);

  const isRegisterMode = mode === "register";

  // Passa alla schermata di registrazione, ripulendo eventuali residui
  // della sessione di login precedente (la password non va mai riusata
  // tra le due modalità senza che l'utente la riscriva).
  function goToRegister() {
    setPassword("");
    setMode("register");
  }

  function goToLogin() {
    setPassword("");
    setMode("login");
  }

  async function handleRegister() {
    if (!username || !password)
      return Alert.alert("Attenzione", "Inserisci username e password");
    if (!patientName.trim())
      return Alert.alert("Attenzione", "Inserisci il nome del paziente");

    const yearsNum = ageYears === "" ? 0 : parseInt(ageYears, 10);
    const monthsNum = ageMonths === "" ? 0 : parseInt(ageMonths, 10);
    if (
      Number.isNaN(yearsNum) || Number.isNaN(monthsNum) ||
      yearsNum < 0 || monthsNum < 0 || monthsNum > 11
    ) {
      return Alert.alert(
        "Attenzione",
        "Età non valida: usa anni interi (≥ 0) e mesi tra 0 e 11"
      );
    }

    setBusy(true);
    try {
      const patientInfo = {
        patient_name: patientName.trim(),
        age_years: yearsNum,
        age_months: monthsNum,
      };
      await registerUser(username, password, patientInfo);
      // Persistiamo i dati anagrafici localmente: in DEMO_MODE non esiste
      // un vero backend che li conservi, e anche con un backend reale è
      // utile per mostrarli subito in MonitorScreen senza un'altra chiamata.
      try {
        await SecureStore.setItemAsync(PATIENT_INFO_KEY, JSON.stringify(patientInfo));
      } catch (storageError) {
        console.warn("Impossibile salvare i dati anagrafici:", storageError);
      }
      Alert.alert(
        "Registrazione completata",
        "Ora puoi accedere con le tue credenziali.",
        [{ text: "OK", onPress: goToLogin }]
      );
    } catch (e) {
      Alert.alert("Errore", e.message || "Registrazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin() {
    if (!username || !password)
      return Alert.alert("Attenzione", "Inserisci username e password");
    setBusy(true);
    try {
      // Il backend restituisce { access_token, device_id, role } dell'utente
      const { access_token, device_id, role } = await loginUser(username, password);
      onLogin(access_token, device_id, role);
    } catch (e) {
      // Errore reale mostrato all'utente — nessun fallback con token finto
      Alert.alert("Accesso negato", e.message || "Credenziali non valide.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <SafeAreaView style={styles.containerCenter}>
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, justifyContent: "center" }}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.logo}>Alvea</Text>
          <Text style={styles.subtitle}>
            {isRegisterMode
              ? "Crea l'account del paziente"
              : "Monitoraggio pediatrico e prevenzione dell'asma"}
          </Text>

          <TextInput
            style={styles.input}
            placeholder="Username"
            autoCapitalize="none"
            placeholderTextColor="#A0AAB2"
            value={username}
            onChangeText={setUsername}
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            secureTextEntry
            placeholderTextColor="#A0AAB2"
            value={password}
            onChangeText={setPassword}
          />

          {/* Dati anagrafici del paziente, richiesti solo in registrazione */}
          {isRegisterMode && (
            <>
              <TextInput
                style={styles.input}
                placeholder="Nome del paziente"
                placeholderTextColor="#A0AAB2"
                value={patientName}
                onChangeText={setPatientName}
              />
              <TextInput
                style={styles.input}
                placeholder="Età — anni"
                placeholderTextColor="#A0AAB2"
                keyboardType="number-pad"
                value={ageYears}
                onChangeText={setAgeYears}
              />
              <TextInput
                style={styles.input}
                placeholder="Età — mesi (0-11)"
                placeholderTextColor="#A0AAB2"
                keyboardType="number-pad"
                value={ageMonths}
                onChangeText={setAgeMonths}
              />
            </>
          )}

          <TouchableOpacity
            style={styles.btn}
            disabled={busy}
            onPress={isRegisterMode ? handleRegister : handleLogin}
          >
            <Text style={styles.btnText}>
              {busy
                ? (isRegisterMode ? "Registrazione in corso..." : "Accesso in corso...")
                : (isRegisterMode ? "Registrati" : "Accedi")}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkBtn}
            disabled={busy}
            onPress={isRegisterMode ? goToLogin : goToRegister}
          >
            <Text style={styles.link}>
              {isRegisterMode
                ? "Hai già un account? Accedi"
                : "Registrati"}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

