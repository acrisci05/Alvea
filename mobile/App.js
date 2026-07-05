import React, { useState, useEffect } from "react";
import { View, Text, ActivityIndicator } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import * as SecureStore from "expo-secure-store";
import LoginScreen from "./src/LoginScreen";
import MonitorScreen from "./src/MonitorScreen";
import { splashStyles, colors } from "./src/style";


const SESSION_TOKEN_KEY = "alvea_token";
const SESSION_DEVICE_KEY = "alvea_device_id";
const SESSION_USER_KEY = "alvea_username";

export default function App() {
  const [token, setToken] = useState(null);
  const [deviceId, setDeviceId] = useState(null);
  const [username, setUsername] = useState(null);
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    async function prepare() {
      try {
        const savedToken = await SecureStore.getItemAsync(SESSION_TOKEN_KEY);
        const savedDeviceId = await SecureStore.getItemAsync(SESSION_DEVICE_KEY);
        const savedUser = await SecureStore.getItemAsync(SESSION_USER_KEY);
        if (savedToken && savedDeviceId) {
          setToken(savedToken);
          setDeviceId(savedDeviceId);
          setUsername(savedUser);
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

  const handleLogin = async (newToken, newDeviceId, newUsername) => {
    try {
      await SecureStore.setItemAsync(SESSION_TOKEN_KEY, newToken);
      await SecureStore.setItemAsync(SESSION_DEVICE_KEY, newDeviceId);
      if (newUsername)
        await SecureStore.setItemAsync(SESSION_USER_KEY, newUsername);
    } catch (e) {
      console.warn("Impossibile salvare la sessione:", e);
    }
    setToken(newToken);
    setDeviceId(newDeviceId);
    setUsername(newUsername || null);
  };

  const handleLogout = async () => {
    try {
      await SecureStore.deleteItemAsync(SESSION_TOKEN_KEY);
      await SecureStore.deleteItemAsync(SESSION_DEVICE_KEY);
      await SecureStore.deleteItemAsync(SESSION_USER_KEY);
    } catch (e) {
      console.warn("Errore durante il logout:", e);
    }
    setToken(null);
    setDeviceId(null);
    setUsername(null);
  };

  if (showSplash) {
    return (
      <SafeAreaProvider>
        <View style={splashStyles.container}>
          <View style={splashStyles.badge}>
            <Ionicons name="heart" size={36} color={colors.accent} />
          </View>
          <Text style={splashStyles.logo}>Alvea</Text>
          <Text style={splashStyles.tagline}>Monitoraggio pediatrico</Text>
          <ActivityIndicator
            size="small"
            color={colors.primary}
            style={splashStyles.loader}
          />
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
          username={username}
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