import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import * as SecureStore from "expo-secure-store";
import LoginScreen from "./src/LoginScreen";
import MonitorScreen from "./src/MonitorScreen";


const SESSION_TOKEN_KEY = "alvea_token";
const SESSION_DEVICE_KEY = "alvea_device_id";

export default function App() {
  const [token, setToken] = useState(null);
  const [deviceId, setDeviceId] = useState(null);
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    async function prepare() {
      try {
        const savedToken = await SecureStore.getItemAsync(SESSION_TOKEN_KEY);
        const savedDeviceId = await SecureStore.getItemAsync(SESSION_DEVICE_KEY);
        if (savedToken && savedDeviceId) {
          setToken(savedToken);
          setDeviceId(savedDeviceId);
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      } catch (e) {
        console.warn("Errore ripristino sessione:", e);
      } finally {
        setShowSplash(false);
      }
    }
    prepare();
  }, []);

  const handleLogin = async (newToken, newDeviceId) => {
    try {
      await SecureStore.setItemAsync(SESSION_TOKEN_KEY, newToken);
      await SecureStore.setItemAsync(SESSION_DEVICE_KEY, newDeviceId);
    } catch (e) {
      console.warn("Impossibile salvare la sessione:", e);
    }
    setToken(newToken);
    setDeviceId(newDeviceId);
  };

  const handleLogout = async () => {
    try {
      await SecureStore.deleteItemAsync(SESSION_TOKEN_KEY);
      await SecureStore.deleteItemAsync(SESSION_DEVICE_KEY);
    } catch (e) {
      console.warn("Errore durante il logout:", e);
    }
    setToken(null);
    setDeviceId(null);
  };

  if (showSplash) {
    return (
      <SafeAreaProvider>
        <View style={splash.container}>
          <Text style={splash.logo}>Alvea</Text>
          <Text style={splash.tagline}>Monitoraggio pediatrico</Text>
        </View>
      </SafeAreaProvider>
    );
  }

  if (token && deviceId) {
    return (
      <SafeAreaProvider>
        <MonitorScreen
          token={token}
          deviceId={deviceId}
          onLogout={handleLogout}
        />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <LoginScreen onLogin={handleLogin} />
    </SafeAreaProvider>
  );
}

const splash = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#3A506B",
    justifyContent: "center",
    alignItems: "center",
  },
  logo: {
    color: "#FFFFFF",
    fontSize: 42,
    fontWeight: "800",
    letterSpacing: 2,
  },
  tagline: {
    color: "#81D4FA",
    fontSize: 15,
    marginTop: 10,
    fontWeight: "500",
  },
});