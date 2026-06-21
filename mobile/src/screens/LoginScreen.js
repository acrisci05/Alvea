// src/screens/LoginScreen.js
import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { colors, fonts, radius, cardShadow } from '../theme/tokens';

export default function LoginScreen({ navigation }) {
  const { login, loginAsMedico } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await login({ email, password });
      // La navigazione verso l'app principale avviene automaticamente:
      // RootNavigator osserva isAuthenticated e cambia stack.
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.brandRow}>
          <View style={styles.brandMark}>
            <Text style={styles.brandMarkText}>A</Text>
          </View>
          <View>
            <Text style={styles.brandTitle}>Alvea</Text>
            <Text style={styles.brandSub}>accesso caregiver</Text>
          </View>
        </View>

        <View style={styles.card}>
          <View style={styles.hint}>
            <Text style={styles.hintText}>
              Demo locale: nessun backend reale connesso. Usa{' '}
              <Text style={styles.code}>caregiver@alvea.demo</Text> /{' '}
              <Text style={styles.code}>demo1234</Text>, oppure registrati.
            </Text>
          </View>

          <Field label="Email">
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="nome@esempio.it"
              placeholderTextColor="rgba(26,36,51,0.32)"
              autoCapitalize="none"
              keyboardType="email-address"
            />
          </Field>

          <Field label="Password">
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor="rgba(26,36,51,0.32)"
              secureTextEntry
            />
          </Field>

          <Pressable style={styles.submitBtn} onPress={handleSubmit} disabled={submitting}>
            <Text style={styles.submitText}>{submitting ? 'Accesso in corso…' : 'Accedi'}</Text>
          </Pressable>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable style={styles.linkRow} onPress={() => navigation.navigate('Register')}>
            <Text style={styles.linkText}>Non hai un account? Registrati</Text>
          </Pressable>
        </View>

        <Pressable style={styles.medicoLink} onPress={loginAsMedico}>
          <Text style={styles.medicoLinkText}>Accedi come Medico Pneumologo/Pediatra →</Text>
        </Pressable>

        <Text style={styles.footnote}>
          Alvea è un prototipo didattico (Academy Medical Wearable Devices, A.A. 2025/2026). Login
          e registrazione sono simulati in questa demo.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({ label, children }) {
  return (
    <View style={{ marginBottom: 16 }}>
      <Text style={styles.fieldLabel}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy },
  scrollContent: { padding: 24, paddingTop: 64, paddingBottom: 48, flexGrow: 1, justifyContent: 'center' },
  brandRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 14, marginBottom: 32 },
  brandMark: {
    width: 44, height: 44, borderRadius: 11,
    backgroundColor: colors.sage, alignItems: 'center', justifyContent: 'center',
  },
  brandMarkText: { color: colors.navy, fontFamily: fonts.display, fontSize: 20, fontWeight: '700' },
  brandTitle: { fontFamily: fonts.display, fontSize: 28, color: colors.ivory, fontWeight: '600' },
  brandSub: { fontFamily: fonts.mono, fontSize: 12, color: colors.textDim, marginTop: 2 },
  card: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 22, ...cardShadow,
  },
  hint: {
    backgroundColor: colors.navy, borderWidth: 1, borderColor: colors.line,
    borderStyle: 'dashed', borderRadius: 8, padding: 10, marginBottom: 16,
  },
  hintText: { fontSize: 11.5, color: colors.textDim, lineHeight: 17 },
  code: { fontFamily: fonts.mono, color: colors.ivory },
  fieldLabel: {
    fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5,
    color: colors.textDim, fontFamily: fonts.bodySemibold, marginBottom: 7,
  },
  input: {
    backgroundColor: colors.navy, borderWidth: 1, borderColor: colors.line,
    borderRadius: 9, color: colors.ivory, fontFamily: fonts.body,
    fontSize: 14, paddingHorizontal: 13, paddingVertical: 11,
  },
  submitBtn: {
    backgroundColor: colors.ivory, borderRadius: 10, paddingVertical: 13,
    alignItems: 'center', marginTop: 6,
  },
  submitText: { color: colors.navy, fontFamily: fonts.bodySemibold, fontSize: 14, fontWeight: '700' },
  error: { color: colors.brickText, fontSize: 12, marginTop: 10 },
  linkRow: { marginTop: 16, alignItems: 'center' },
  linkText: { color: colors.textDim, fontSize: 12.5, fontFamily: fonts.body },
  medicoLink: { marginTop: 18, alignItems: 'center' },
  medicoLinkText: { color: colors.dust, fontSize: 12.5, fontFamily: fonts.bodyMedium },
  footnote: {
    fontSize: 11, color: colors.textDim, textAlign: 'center', lineHeight: 16,
    marginTop: 28, paddingHorizontal: 12,
  },
});
