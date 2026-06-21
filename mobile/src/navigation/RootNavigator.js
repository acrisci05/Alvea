// src/navigation/RootNavigator.js
import React from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, View, Pressable } from 'react-native';

import { useAuth } from '../context/AuthContext';
import { TelemetryProvider } from '../context/TelemetryContext';

import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import CaregiverHomeScreen from '../screens/CaregiverHomeScreen';
import HistoryScreen from '../screens/HistoryScreen';
import AlertsScreen from '../screens/AlertsScreen';
import MedicoPatientListScreen from '../screens/MedicoPatientListScreen';
import MedicoPatientDetailScreen from '../screens/MedicoPatientDetailScreen';

import { colors, fonts } from '../theme/tokens';

const AuthStack = createNativeStackNavigator();
const CaregiverTabs = createBottomTabNavigator();
const MedicoStack = createNativeStackNavigator();

const navTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.navy,
    card: colors.navySoft,
    text: colors.ivory,
    border: colors.line,
    primary: colors.dust,
  },
};

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
    </AuthStack.Navigator>
  );
}

function LogoutButton() {
  const { logout } = useAuth();
  return (
    <Pressable onPress={logout} style={{ paddingHorizontal: 14 }}>
      <Text style={{ color: colors.ivory, fontFamily: fonts.bodyMedium, fontSize: 13 }}>Esci</Text>
    </Pressable>
  );
}

function CaregiverNavigator() {
  return (
    <CaregiverTabs.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.navy },
        headerTitleStyle: { color: colors.ivory, fontFamily: fonts.display },
        headerShadowVisible: false,
        headerRight: () => <LogoutButton />,
        tabBarStyle: { backgroundColor: colors.navySoft, borderTopColor: colors.line },
        tabBarActiveTintColor: colors.ivory,
        tabBarInactiveTintColor: colors.textDim,
        tabBarLabelStyle: { fontFamily: fonts.bodyMedium, fontSize: 11 },
      }}
    >
      <CaregiverTabs.Screen name="Home" component={CaregiverHomeScreen} options={{ title: 'Alvea' }} />
      <CaregiverTabs.Screen name="Alerts" component={AlertsScreen} options={{ title: 'Allerte' }} />
      <CaregiverTabs.Screen name="History" component={HistoryScreen} options={{ title: 'Storico' }} />
    </CaregiverTabs.Navigator>
  );
}

function MedicoNavigator() {
  return (
    <MedicoStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.navy },
        headerTitleStyle: { color: colors.ivory, fontFamily: fonts.display },
        headerShadowVisible: false,
        headerTintColor: colors.ivory,
        headerRight: () => <LogoutButton />,
      }}
    >
      <MedicoStack.Screen name="MedicoPatientList" component={MedicoPatientListScreen} options={{ title: 'Pazienti' }} />
      <MedicoStack.Screen
        name="MedicoPatientDetail"
        component={MedicoPatientDetailScreen}
        options={({ route }) => ({ title: 'Scheda paziente' })}
      />
    </MedicoStack.Navigator>
  );
}

export default function RootNavigator() {
  const { isAuthenticated, isReady, session } = useAuth();

  if (!isReady) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.navy, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: colors.textDim, fontFamily: fonts.mono }}>Caricamento…</Text>
      </View>
    );
  }

  return (
    <NavigationContainer theme={navTheme}>
      {!isAuthenticated ? (
        <AuthNavigator />
      ) : (
        <TelemetryProvider>
          {session.role === 'medico' ? <MedicoNavigator /> : <CaregiverNavigator />}
        </TelemetryProvider>
      )}
    </NavigationContainer>
  );
}
