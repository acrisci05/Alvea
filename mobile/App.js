import React, { useEffect, useState } from "react";
import { StatusBar, View, ActivityIndicator } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import LoginScreen from "./src/screens/LoginScreen";
import MonitorScreen from "./src/screens/MonitorScreen";

const TOKEN_KEY = "alvea_token";

export default function App() {
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // All'avvio: ripristina la sessione salvata (login persistente).
  useEffect(() => {
    AsyncStorage.getItem(TOKEN_KEY)
      .then((saved) => { if (saved) setToken(saved); })
      .finally(() => setLoading(false));
  }, []);

  async function handleLogin(t) {
    await AsyncStorage.setItem(TOKEN_KEY, t);
    setToken(t);
  }

  async function handleLogout() {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: "#0B132B", justifyContent: "center" }}>
        <StatusBar barStyle="light-content" />
        <ActivityIndicator size="large" color="#5BC0BE" />
      </View>
    );
  }

  return (
    <>
      <StatusBar barStyle="light-content" />
      {token
        ? <MonitorScreen token={token} onLogout={handleLogout} />
        : <LoginScreen onLogin={handleLogin} />}
    </>
  );
}
