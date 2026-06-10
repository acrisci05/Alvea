import React, { useState } from "react";
import { StatusBar } from "react-native";
import LoginScreen from "./src/screens/LoginScreen";
import MonitorScreen from "./src/screens/MonitorScreen";

export default function App() {
  const [token, setToken] = useState(null);
  return (
    <>
      <StatusBar barStyle="light-content" />
      {token ? <MonitorScreen token={token} /> : <LoginScreen onLogin={setToken} />}
    </>
  );
}
