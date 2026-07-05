import React, { useState } from "react";
import {
  Text,
  TextInput,
  TouchableOpacity,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  View,
} from "react-native";
import { SafeAreaView } from 'react-native-safe-area-context';
import * as SecureStore from "expo-secure-store";
import { loginUser, registerUser } from "./api";
import { patientInfoKeyFor } from "./config";
import styles, { colors } from "./style";


// Limiti dell'età
const MAX_YEARS = 18;
const MAX_MONTHS = 11;

// Testo sintetico dell'età (es. "3 anni e 4 mesi").
function ageLabel(years, months) {
  const y = `${years} ${years === 1 ? "anno" : "anni"}`;
  const m = `${months} ${months === 1 ? "mese" : "mesi"}`;
  if (years === 0) return m;
  if (months === 0) return y;
  return `${y} e ${m}`;
}

export default function LoginScreen({ onLogin }) {
  // "login" mostra solo username/password. "register" mostra anche i dati anagrafici minimi del paziente.
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [patientName, setPatientName] = useState("");
  const [ageYears, setAgeYears] = useState(0);
  const [ageMonths, setAgeMonths] = useState(0);
  const [sex, setSex] = useState("");      // "M" | "F"
  const [busy, setBusy] = useState(false);

  const isRegisterMode = mode === "register";

  // Passa alla schermata di registrazione, ripulendo eventuali residui della sessione di login precedente.
  function goToRegister() {
    setPassword("");
    setConfirmPassword("");
    setMode("register");
  }

  function goToLogin() {
    setPassword("");
    setConfirmPassword("");
    setMode("login");
  }

  // Incremento/decremento con limiti, usati dai due stepper.
  function changeYears(delta) {
    setAgeYears((v) => Math.min(MAX_YEARS, Math.max(0, v + delta)));
  }
  function changeMonths(delta) {
    setAgeMonths((v) => Math.min(MAX_MONTHS, Math.max(0, v + delta)));
  }

  async function handleRegister() {
    if (!username || !password)
      return Alert.alert("Attenzione", "Inserisci username e password");
    if (password.length < 6)
      return Alert.alert("Attenzione", "La password deve avere almeno 6 caratteri");
    if (password !== confirmPassword)
      return Alert.alert("Attenzione", "Le due password non coincidono");
    if (!patientName.trim())
      return Alert.alert("Attenzione", "Inserisci il nome del paziente");
    if (!sex)
      return Alert.alert("Attenzione", "Seleziona il sesso del bambino");

    setBusy(true);
    try {
      const patientInfo = {
        patient_name: patientName.trim(),
        sex,                      // "M" | "F"
        age_years: ageYears,
        age_months: ageMonths,
      };
      await registerUser(username, password, patientInfo);
      try {
        await SecureStore.setItemAsync(
          patientInfoKeyFor(username),
          JSON.stringify(patientInfo)
        );
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
      const { access_token, device_id, username: loggedUser, patientInfo: loggedPatient } =
        await loginUser(username, password);
      const finalUser = loggedUser || username;
      if (loggedPatient) {
        try {
          const key = patientInfoKeyFor(finalUser);
          const existing = await SecureStore.getItemAsync(key);
          if (!existing)
            await SecureStore.setItemAsync(key, JSON.stringify(loggedPatient));
        } catch (storageError) {
          console.warn("Impossibile salvare i dati anagrafici:", storageError);
        }
      }
      onLogin(access_token, device_id, finalUser);
    } catch (e) {
      Alert.alert("Accesso negato", e.message || "Credenziali non valide.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.flexFill}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <SafeAreaView style={styles.containerCenter}>
        <ScrollView
          contentContainerStyle={styles.loginScrollContent}
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
            placeholder="Username genitore"
            autoCapitalize="none"
            placeholderTextColor={colors.placeholder}
            value={username}
            onChangeText={setUsername}
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            secureTextEntry
            placeholderTextColor={colors.placeholder}
            value={password}
            onChangeText={setPassword}
          />

          {/* Dati anagrafici del paziente, richiesti solo in registrazione */}
          {isRegisterMode && (
            <>
              <TextInput
                style={styles.input}
                placeholder="Conferma password"
                secureTextEntry
                placeholderTextColor={colors.placeholder}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
              />

              <TextInput
                style={styles.input}
                placeholder="Nome del paziente"
                placeholderTextColor={colors.placeholder}
                value={patientName}
                onChangeText={setPatientName}
              />

              {/* --- Età (anni e mesi) --- */}
              <Text style={styles.fieldLabel}>Età del bambino</Text>

              <View style={styles.stepperRow}>
                <Text style={styles.stepperLabel}>Anni</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity
                    style={[styles.stepBtn, ageYears === 0 && styles.stepBtnDisabled]}
                    onPress={() => changeYears(-1)}
                    disabled={ageYears === 0}
                  >
                    <Text style={styles.stepBtnText}>-</Text>
                  </TouchableOpacity>
                  <Text style={styles.stepValue}>{ageYears}</Text>
                  <TouchableOpacity
                    style={[styles.stepBtn, ageYears === MAX_YEARS && styles.stepBtnDisabled]}
                    onPress={() => changeYears(1)}
                    disabled={ageYears === MAX_YEARS}
                  >
                    <Text style={styles.stepBtnText}>+</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <View style={styles.stepperRow}>
                <Text style={styles.stepperLabel}>Mesi</Text>
                <View style={styles.stepper}>
                  <TouchableOpacity
                    style={[styles.stepBtn, ageMonths === 0 && styles.stepBtnDisabled]}
                    onPress={() => changeMonths(-1)}
                    disabled={ageMonths === 0}
                  >
                    <Text style={styles.stepBtnText}>-</Text>
                  </TouchableOpacity>
                  <Text style={styles.stepValue}>{ageMonths}</Text>
                  <TouchableOpacity
                    style={[styles.stepBtn, ageMonths === MAX_MONTHS && styles.stepBtnDisabled]}
                    onPress={() => changeMonths(1)}
                    disabled={ageMonths === MAX_MONTHS}
                  >
                    <Text style={styles.stepBtnText}>+</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <Text style={styles.ageHint}>{ageLabel(ageYears, ageMonths)}</Text>

              {/* --- Sesso: selettore a due opzioni --- */}
              <Text style={styles.fieldLabel}>Sesso</Text>
              <View style={styles.sexRow}>
                <TouchableOpacity
                  style={[styles.sexOption, sex === "M" && styles.sexOptionActive]}
                  onPress={() => setSex("M")}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.sexOptionText, sex === "M" && styles.sexOptionTextActive]}>
                    Maschio
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.sexOption, sex === "F" && styles.sexOptionActive]}
                  onPress={() => setSex("F")}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.sexOptionText, sex === "F" && styles.sexOptionTextActive]}>
                    Femmina
                  </Text>
                </TouchableOpacity>
              </View>
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