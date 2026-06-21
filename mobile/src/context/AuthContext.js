// src/context/AuthContext.js
//
// Gestisce autenticazione e sessione del caregiver, replicando a livello
// concettuale POST /register e POST /login (OAuth2 password flow + JWT)
// della Tabella 2. In modalita' simulata (default) gli account vivono in
// memoria + AsyncStorage sul dispositivo, senza alcuna richiesta di rete.
//
// Include anche un accesso rapido al profilo "Medico Pneumologo/Pediatra"
// (Relazione, Sez. 4.1), utile per navigare la vista multi-paziente senza
// dover modellare un secondo flusso di registrazione completo.

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { isSimulated, api } from '../services/dataSource';

const AuthContext = createContext(null);

const STORAGE_KEY_SESSION = '@alvea/session';
const STORAGE_KEY_ACCOUNTS = '@alvea/accounts';

// Account demo preconfigurato per consentire un accesso immediato senza
// dover compilare il form di registrazione.
const DEMO_ACCOUNT = {
  email: 'caregiver@alvea.demo',
  password: 'demo1234',
  name: 'Account demo',
  childName: 'Sofia',
  ageBand: 'prescolare',
  role: 'caregiver',
};

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null); // { email, name, role, childName, ageBand, token? }
  const [accounts, setAccounts] = useState({ [DEMO_ACCOUNT.email]: DEMO_ACCOUNT });
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  // Ripristina sessione e account salvati localmente all'avvio dell'app.
  useEffect(() => {
    (async () => {
      try {
        const [storedSession, storedAccounts] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEY_SESSION),
          AsyncStorage.getItem(STORAGE_KEY_ACCOUNTS),
        ]);
        if (storedAccounts) {
          setAccounts((prev) => ({ ...prev, ...JSON.parse(storedAccounts) }));
        }
        if (storedSession) {
          setSession(JSON.parse(storedSession));
        }
      } catch (e) {
        // Storage non disponibile (es. primo avvio): si procede con i default.
      } finally {
        setIsReady(true);
      }
    })();
  }, []);

  async function persistAccounts(nextAccounts) {
    setAccounts(nextAccounts);
    try {
      await AsyncStorage.setItem(STORAGE_KEY_ACCOUNTS, JSON.stringify(nextAccounts));
    } catch (e) {
      // Persistenza best-effort: non blocca il flusso applicativo.
    }
  }

  async function persistSession(nextSession) {
    setSession(nextSession);
    try {
      if (nextSession) {
        await AsyncStorage.setItem(STORAGE_KEY_SESSION, JSON.stringify(nextSession));
      } else {
        await AsyncStorage.removeItem(STORAGE_KEY_SESSION);
      }
    } catch (e) {
      // Persistenza best-effort.
    }
  }

  async function register({ name, email, password, childName, ageBand }) {
    setError(null);
    const normalizedEmail = email.trim().toLowerCase();

    if (!name || !normalizedEmail || !password || !childName) {
      const msg = 'Compila tutti i campi per completare la registrazione.';
      setError(msg);
      throw new Error(msg);
    }
    if (password.length < 6) {
      const msg = 'La password deve contenere almeno 6 caratteri.';
      setError(msg);
      throw new Error(msg);
    }
    if (accounts[normalizedEmail]) {
      const msg = 'Esiste già un account con questa email. Accedi invece di registrarti.';
      setError(msg);
      throw new Error(msg);
    }

    if (!isSimulated) {
      // Percorso reale: POST /register sul backend FastAPI.
      await api.registerCaregiver({ name, email: normalizedEmail, password });
    }

    const newAccount = {
      email: normalizedEmail,
      password,
      name,
      childName,
      ageBand,
      role: 'caregiver',
    };
    await persistAccounts({ ...accounts, [normalizedEmail]: newAccount });
    await persistSession(newAccount);
    return newAccount;
  }

  async function login({ email, password }) {
    setError(null);
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password) {
      const msg = 'Inserisci email e password.';
      setError(msg);
      throw new Error(msg);
    }

    if (!isSimulated) {
      // Percorso reale: POST /login (OAuth2 password flow) -> token JWT.
      const result = await api.loginCaregiver({ email: normalizedEmail, password });
      const nextSession = { email: normalizedEmail, role: 'caregiver', token: result.access_token };
      await persistSession(nextSession);
      return nextSession;
    }

    const account = accounts[normalizedEmail];
    if (!account || account.password !== password) {
      const msg = 'Credenziali non valide. Verifica email e password, oppure registrati.';
      setError(msg);
      throw new Error(msg);
    }
    await persistSession(account);
    return account;
  }

  /** Accesso rapido al profilo Medico (Relazione, Sez. 4.1), senza un
   * secondo flusso di registrazione: utile per demo e revisione didattica. */
  function loginAsMedico() {
    const medicoSession = {
      email: 'medico@alvea.demo',
      name: 'Dott.ssa R. Iacoviello',
      role: 'medico',
    };
    persistSession(medicoSession);
    return medicoSession;
  }

  async function logout() {
    await persistSession(null);
  }

  const value = useMemo(
    () => ({
      session,
      isReady,
      error,
      isAuthenticated: !!session,
      isSimulated,
      register,
      login,
      loginAsMedico,
      logout,
      clearError: () => setError(null),
    }),
    [session, isReady, error, accounts]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve essere usato dentro un AuthProvider');
  return ctx;
}
