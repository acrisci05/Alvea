import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { login, register } from "../api";

export default function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function handle(action) {
    if (!username || !password) return Alert.alert("Inserisci username e password");
    setBusy(true);
    try {
      if (action === "register") await register(username, password);
      const { access_token } = await login(username, password);
      onLogin(access_token);
    } catch (e) {
      Alert.alert("Errore", e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>Alvea</Text>
      <Text style={styles.subtitle}>Monitoraggio respiratorio e cardiaco · asma pediatrico</Text>
      <TextInput style={styles.input} placeholder="Username" autoCapitalize="none"
        placeholderTextColor="#8da" value={username} onChangeText={setUsername} />
      <TextInput style={styles.input} placeholder="Password" secureTextEntry
        placeholderTextColor="#8da" value={password} onChangeText={setPassword} />
      <TouchableOpacity style={styles.btn} disabled={busy} onPress={() => handle("login")}>
        <Text style={styles.btnText}>{busy ? "..." : "Accedi"}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => handle("register")}>
        <Text style={styles.link}>Crea un nuovo account</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B132B", justifyContent: "center", padding: 28 },
  logo: { color: "#fff", fontSize: 32, fontWeight: "800", textAlign: "center" },
  subtitle: { color: "#9bb", textAlign: "center", marginBottom: 32, marginTop: 4 },
  input: { backgroundColor: "#1C2541", color: "#fff", borderRadius: 12, padding: 14, marginBottom: 12 },
  btn: { backgroundColor: "#5BC0BE", borderRadius: 12, padding: 16, marginTop: 8 },
  btnText: { color: "#0B132B", textAlign: "center", fontWeight: "700", fontSize: 16 },
  link: { color: "#5BC0BE", textAlign: "center", marginTop: 18 },
});
