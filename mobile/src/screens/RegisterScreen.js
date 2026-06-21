// src/screens/RegisterScreen.js
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
import AgeBandSelector from '../components/AgeBandSelector';
import { colors, fonts, radius, cardShadow } from '../theme/tokens';

export default function RegisterScreen({ navigation }) {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [childName, setChildName] = useState('');
  const [ageBand, setAgeBand] = useState('prescolare');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await register({ name, email, password, childName, ageBand });
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.screen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Crea il tuo account</Text>
        <Text style={styles.subtitle}>
          Registrazione caregiver — corrisponde a POST /register nell'architettura del backend.
        </Text>

        <View style={styles.card}>
          <Field label="Nome caregiver">
            <TextInput style={styles.input} value={name} onChangeText={setName} placeholder="es. Maria Rossi" placeholderTextColor="rgba(26,36,51,0.32)" />
          </Field>

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
              placeholder="minimo 6 caratteri"
              placeholderTextColor="rgba(26,36,51,0.32)"
              secureTextEntry
            />
          </Field>

          <Field label="Nome del bambino">
            <TextInput style={styles.input} value={childName} onChangeText={setChildName} placeholder="es. Sofia" placeholderTextColor="rgba(26,36,51,0.32)" />
          </Field>

          <Field label="Fascia d'età del bambino">
            <AgeBandSelector value={ageBand} onChange={setAgeBand} />
            <Text style={styles.note}>
              Adatta i range nominali di riferimento per età (Relazione, Tabella 3). Le soglie di
              warning/critico effettivamente applicate restano quelle statiche validate (Sez. 5.2).
            </Text>
          </Field>

          <Pressable style={styles.submitBtn} onPress={handleSubmit} disabled={submitting}>
            <Text style={styles.submitText}>
              {submitting ? 'Creazione account…' : 'Crea account e registra il device'}
            </Text>
          </Pressable>

          {error ? <Text style={styles.error}>{error}</Text> : null}
        </View>

        <Pressable style={styles.linkRow} onPress={() => navigation.navigate('Login')}>
          <Text style={styles.linkText}>Hai già un account? Accedi</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({ label, children }) {
  return (
    <View style={{ marginBottom: 18 }}>
      <Text style={styles.fieldLabel}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.navy },
  scrollContent: { padding: 24, paddingTop: 56, paddingBottom: 48 },
  title: { fontFamily: fonts.display, fontSize: 24, color: colors.ivory, fontWeight: '600', marginBottom: 6 },
  subtitle: { fontSize: 12.5, color: colors.textDim, lineHeight: 18, marginBottom: 22 },
  card: {
    backgroundColor: colors.navySoft, borderWidth: 1, borderColor: colors.line,
    borderRadius: radius.lg, padding: 22, ...cardShadow,
  },
  fieldLabel: {
    fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5,
    color: colors.textDim, fontFamily: fonts.bodySemibold, marginBottom: 7,
  },
  input: {
    backgroundColor: colors.navy, borderWidth: 1, borderColor: colors.line,
    borderRadius: 9, color: colors.ivory, fontFamily: fonts.body,
    fontSize: 14, paddingHorizontal: 13, paddingVertical: 11,
  },
  note: { fontSize: 10.5, color: colors.textDim, marginTop: 8, lineHeight: 15 },
  submitBtn: {
    backgroundColor: colors.ivory, borderRadius: 10, paddingVertical: 13,
    alignItems: 'center', marginTop: 4,
  },
  submitText: { color: colors.navy, fontFamily: fonts.bodySemibold, fontSize: 14, fontWeight: '700' },
  error: { color: colors.brickText, fontSize: 12, marginTop: 10 },
  linkRow: { marginTop: 20, alignItems: 'center' },
  linkText: { color: colors.textDim, fontSize: 12.5, fontFamily: fonts.body },
});
