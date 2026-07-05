import { StyleSheet } from 'react-native';

// Palette dei colori usati dai componenti quando il colore dipende da uno
// stato a runtime (es. connesso/non connesso, valore normale/fuori norma) e
// non può quindi essere fissato in uno stile statico. Evita di scrivere
// valori esadecimali direttamente nella logica dei componenti.
export const colors = {
  // Colore di accento e colore primario (icone, pulsanti)
  accent: '#4FC3F7',
  primary: '#81D4FA',
  // Placeholder dei campi di testo
  placeholder: '#A0AAB2',

  // Colore del testo/valore in base allo stato del sensore
  valueMuted: '#A0AAB2',
  valueBad: '#E57373',
  valueGood: '#66BB6A',

  // Stato "critico" (banner, gravità allarme)
  danger: '#C62828',
  dangerBg: '#FFEBEE',
  dangerBorder: '#EF9A9A',
  dangerDot: '#EF5350',

  // Stato "attenzione" (parametri fuori norma, batteria scarica)
  warning: '#B85C24',
  warningBg: '#FFF2E8',
  warningBorder: '#FFD4B5',
  warningDot: '#FB8C42',

  // Stato "regolare"
  success: '#2E7D46',
  successBg: '#EAF7EE',
  successBorder: '#B7E0BF',
  successDot: '#66BB6A',

  // Stato "informativo" (verifica in corso)
  info: '#2C6E8F',
  infoBg: '#EAF6FD',
  infoBorder: '#B7DDF3',
  infoDot: '#4FC3F7',

  // Stato "neutro" (sensore staccato, segnale assente, in attesa)
  neutralBg: '#ECEFF1',
  neutralBorder: '#CFD8DC',
  neutralDot: '#B0BEC5',
  neutralDotAlt: '#90A4AE',
  neutralText: '#607D8B',
  neutralTextAlt: '#546E7A',

  // Chip di stato connessione
  connOn: '#66BB6A',
  connOnText: '#2E7D46',
  connOnAlt: '#8BD4A0',
  connOff: '#B0BEC5',
  connOffText: '#78909C',

  // Icone della barra di navigazione
  navActive: '#3A506B',
  navInactive: '#95A5A6',
};

const styles = StyleSheet.create({
  // Sfondo morbido chiaro moderno
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  containerCenter: {
    flex: 1,
    backgroundColor: '#F8F9FA',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },

  // Titoli sobri ed eleganti (Blu petrolio opaco desaturato)
  logo: {
    color: '#3A506B',
    fontSize: 32,
    fontWeight: '800',
    textAlign: 'center',
  },
  subtitle: {
    color: '#7F8C8D',
    textAlign: 'center',
    marginBottom: 36,
    marginTop: 6,
    fontSize: 15,
  },

  // Input arrotondati smussati a 16px
  input: {
    backgroundColor: '#FFFFFF',
    color: '#2C3E50',
    borderColor: '#E2E8F0',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
    fontSize: 15,
  },

  // Bottone principale
  btn: {
    backgroundColor: '#81D4FA',
    borderRadius: 16,
    padding: 16,
    marginTop: 8,
    alignItems: 'center',
  },
  btnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
  link: {
    color: '#4FC3F7',
    textAlign: 'center',
    fontWeight: '600',
    marginTop: 18,
    fontSize: 14,
  },
  // Contenitore del link "Registrati"/"Accedi": aggiunge un'area di tocco
  // comoda (padding) attorno al testo, invece di lasciare il
  // TouchableOpacity senza alcuno stile proprio.
  linkBtn: {
    paddingVertical: 10,
    paddingHorizontal: 8,
    alignItems: 'center',
  },

  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 10,
    paddingBottom: 2,
  },
  header: {
    color: '#3A506B',
    fontSize: 26,
    fontWeight: '800',
  },
  status: {
    color: '#7F8C8D',
    marginTop: 4,
    marginBottom: 16,
    fontSize: 13,
    paddingHorizontal: 24,
  },

  // Card arrotondate, pulite (bordo sottile su tutti i lati)
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 22,
    marginBottom: 14,
    marginHorizontal: 24,
    borderWidth: 0.5,
    borderColor: '#ECF0F3',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 2,
  },
  label: {
    color: '#7F8C8D',
    fontSize: 14,
    fontWeight: '600',
  },
  big: {
    fontSize: 48,
    fontWeight: '800',
    marginTop: 4,
  },
  unit: {
    fontSize: 18,
    color: '#95A5A6',
    fontWeight: '500',
  },
  // Piccolo testo sotto il valore che mostra l'intervallo nominale
  rangeHint: {
    color: '#B0BEC5',
    fontSize: 11,
    marginTop: 6,
  },

  // Riga informativa della batteria del dispositivo (sotto le card dei
  // parametri). Riprende lo stile di `rangeHint` e ne fissa i margini in
  // modo statico, così da non lasciare valori di layout scritti direttamente
  // nel componente.
  batteryLine: {
    paddingHorizontal: 24,
    marginTop: 12,
  },

  // Sezioni dello storico
  section: {
    color: '#3A506B',
    fontSize: 18,
    fontWeight: '700',
    marginTop: 16,
    marginBottom: 12,
    paddingHorizontal: 24,
  },
  muted: {
    color: '#95A5A6',
    paddingHorizontal: 24,
    fontSize: 14,
  },

  // Card degli allarmi (pulite, senza bordo laterale)
  alert: {
    backgroundColor: '#FFFFFF',
    borderWidth: 0.5,
    borderColor: '#ECF0F3',
    padding: 14,
    borderRadius: 14,
    marginBottom: 10,
    marginHorizontal: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 1,
  },
  alertKind: {
    // Stesso stile testuale delle scritte della Home (es. "Frequenza
    // respiratoria"): stessa dimensione e peso, così l'app resta coerente.
    fontWeight: '600',
    fontSize: 14,
    marginBottom: 3,
  },
  alertMsg: {
    color: '#34495E',
    fontSize: 14,
  },
  alertTime: {
    color: '#A0AAB2',
    fontSize: 11,
    marginTop: 4,
  },

  // Overlay e card generici usati da tutti i modali dell'app
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(44, 62, 80, 0.5)',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  modalCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
  },
  // Barra di navigazione inferiore (4 icone)
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    paddingTop: 8,
    paddingBottom: 8,
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 4,
  },

  // --- Registrazione: età (stepper) e sesso ---

  // Piccola etichetta sopra un gruppo di campi (es. "Età del bambino")
  fieldLabel: {
    color: '#7F8C8D',
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 8,
    marginLeft: 4,
  },

  // Riga di uno stepper: etichetta a sinistra, comandi a destra
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFFFFF',
    borderColor: '#E2E8F0',
    borderWidth: 1,
    borderRadius: 16,
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginBottom: 10,
  },
  stepperLabel: {
    color: '#2C3E50',
    fontSize: 15,
    fontWeight: '600',
  },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepBtn: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: '#81D4FA',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBtnDisabled: {
    backgroundColor: '#E2E8F0',
  },
  stepBtnText: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '800',
    lineHeight: 24,
  },
  stepValue: {
    minWidth: 44,
    textAlign: 'center',
    color: '#2C3E50',
    fontSize: 18,
    fontWeight: '700',
    marginHorizontal: 6,
  },

  // Riepilogo testuale dell'età scelta (es. "3 anni e 4 mesi")
  ageHint: {
    color: '#0E7C86',
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 14,
    marginLeft: 4,
  },

  // Selettore sesso: due opzioni affiancate
  sexRow: {
    flexDirection: 'row',
    marginBottom: 14,
  },
  sexOption: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderColor: '#E2E8F0',
    borderWidth: 1,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    marginRight: 10,
  },
  sexOptionActive: {
    backgroundColor: '#E1F5FE',
    borderColor: '#4FC3F7',
  },
  sexOptionText: {
    color: '#7F8C8D',
    fontSize: 15,
    fontWeight: '600',
  },
  sexOptionTextActive: {
    color: '#0E7C86',
    fontWeight: '700',
  },

  // --- Barra di navigazione a schede ---
  // Icona (Ionicons) sopra l'indicatore e l'etichetta della scheda.
  navIconVector: {
    marginBottom: 3,
  },
  // Piccolo indicatore sopra l'etichetta della scheda attiva.
  navIndicator: {
    height: 3,
    width: 22,
    borderRadius: 2,
    backgroundColor: 'transparent',
    marginBottom: 6,
  },
  navIndicatorActive: {
    backgroundColor: '#4FC3F7',
  },
  navText: {
    fontSize: 13,
    color: '#95A5A6',
    fontWeight: '600',
  },
  navTextActive: {
    color: '#3A506B',
    fontWeight: '800',
  },

  // --- Pallino sulla scheda Allarmi quando ci sono allarmi non letti ---
  navLabelWrap: {
    position: 'relative',
  },
  navBadge: {
    position: 'absolute',
    top: -3,
    right: -11,
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: '#EF5350',
  },

  // --- Profilo: solo il cerchio con l'iniziale (nessun banner) ---
  profileAvatarWrap: {
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 6,
  },
  // --- Profilo: cerchio con l'iniziale del paziente ---
  avatar: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: '#EAF6FD',
    borderWidth: 4,
    borderColor: '#F1F9FE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#4FC3F7',
    fontSize: 32,
    fontWeight: '800',
  },
  profileName: {
    color: '#3A506B',
    fontSize: 20,
    fontWeight: '800',
    marginTop: 14,
    textAlign: 'center',
  },
  // Piccola intestazione di sezione, tono tenue
  softSection: {
    color: '#90A4AE',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.3,
    marginTop: 20,
    marginBottom: 8,
    paddingHorizontal: 28,
  },

  // Card leggera (senza bordo colorato) con righe etichetta/valore
  softCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    marginHorizontal: 24,
    paddingHorizontal: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 1,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F4F8',
  },
  infoRowLast: {
    borderBottomWidth: 0,
  },
  infoLabel: {
    color: '#7F8C8D',
    fontSize: 14,
    fontWeight: '600',
  },
  infoValue: {
    color: '#2C3E50',
    fontSize: 15,
    fontWeight: '700',
  },
  statusDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    marginRight: 8,
  },

  // Tasto Esci delicato: contorno morbido invece del riempimento pieno
  logoutSoftBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#F3C9C9',
    borderRadius: 16,
    paddingVertical: 15,
    marginHorizontal: 24,
    marginTop: 26,
    alignItems: 'center',
  },
  logoutSoftText: {
    color: '#E88A8A',
    fontSize: 15,
    fontWeight: '700',
  },
  logoutCaption: {
    color: '#B0BEC5',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 10,
  },

  // --- Home: chip stato connessione ---
  connChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 5,
    paddingHorizontal: 11,
    borderRadius: 999,
  },
  connChipOn: {
    backgroundColor: '#E9F7EE',
  },
  connChipOff: {
    backgroundColor: '#ECEFF1',
  },
  connDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  connChipText: {
    fontSize: 12,
    fontWeight: '700',
  },

  // --- Home: banner di stato riassuntivo ---
  statusHero: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 18,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginHorizontal: 24,
    marginBottom: 14,
  },
  statusHeroDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 12,
  },
  statusHeroTitle: {
    fontSize: 15,
    fontWeight: '800',
  },
  statusHeroSub: {
    color: '#7F8C8D',
    fontSize: 12,
    marginTop: 2,
  },

  // --- Home: intestazione card + etichetta Normale/Fuori norma ---
  metricHeadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  metricChip: {
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: 999,
  },
  metricChipGood: {
    backgroundColor: '#E9F7EE',
  },
  metricChipBad: {
    backgroundColor: '#FDECEA',
  },
  metricChipText: {
    fontSize: 11,
    fontWeight: '700',
  },

  // --- Home: card affiancate (respiratoria e temperatura) ---
  halfRow: {
    flexDirection: 'row',
    marginHorizontal: 24,
    marginTop: 2,
  },
  halfCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    borderWidth: 0.5,
    borderColor: '#ECF0F3',
    padding: 16,
    marginRight: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 1,
  },
  halfLabel: {
    color: '#7F8C8D',
    fontSize: 13,
    fontWeight: '600',
    lineHeight: 17,
    // Riserva l'altezza di due righe: così "Frequenza respiratoria" (che va
    // a capo) e "Temperatura" (una riga) restano allineate, e i due valori
    // sotto partono dalla stessa altezza.
    minHeight: 34,
  },
  halfBig: {
    fontSize: 26,
    fontWeight: '800',
    marginTop: 6,
  },
  halfUnit: {
    fontSize: 12,
    color: '#95A5A6',
    fontWeight: '500',
  },
  halfRange: {
    color: '#B0BEC5',
    fontSize: 11,
    marginTop: 5,
  },

  // --- Home: storico come mini-tabella ---
  histCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    marginHorizontal: 24,
    paddingHorizontal: 16,
    paddingVertical: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.03,
    shadowRadius: 6,
    elevation: 1,
  },
  histHeadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F4F8',
  },
  histHead: {
    color: '#B0BEC5',
    fontSize: 10,
    fontWeight: '700',
    flex: 1,
  },
  histRight: {
    textAlign: 'right',
  },
  histRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: '#F7F9FB',
  },
  histRowLast: {
    borderBottomWidth: 0,
  },
  histTime: {
    color: '#7F8C8D',
    fontSize: 12,
    flex: 1,
  },
  histVal: {
    color: '#2C3E50',
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
  },

  // --- Tasto info nel banner di stato ---
  infoBtn: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: 'rgba(255,255,255,0.75)',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 10,
  },
  infoBtnText: {
    fontSize: 16,
    fontWeight: '800',
    fontStyle: 'italic',
  },

  // --- Modale generico: scroll + titolo + pulsanti ---
  modalScroll: {
    maxHeight: 420,
  },
  modalTitle: {
    color: '#3A506B',
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 4,
  },
  modalIntro: {
    color: '#7F8C8D',
    fontSize: 13,
    marginBottom: 14,
    lineHeight: 18,
  },
  modalBtn: {
    backgroundColor: '#81D4FA',
    borderRadius: 16,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 18,
  },
  modalBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  // Riga di due pulsanti (Annulla / Salva) nel form di modifica
  modalBtnRow: {
    flexDirection: 'row',
    marginTop: 18,
  },
  modalGhostBtn: {
    flex: 1,
    backgroundColor: '#ECEFF1',
    borderRadius: 16,
    paddingVertical: 14,
    alignItems: 'center',
    marginRight: 8,
  },
  modalGhostText: {
    color: '#7F8C8D',
    fontSize: 15,
    fontWeight: '700',
  },
  // Pulsante "Modifica profilo" nella scheda Profilo
  editBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#B3E5FC',
    borderRadius: 16,
    paddingVertical: 14,
    marginHorizontal: 24,
    marginTop: 22,
    alignItems: 'center',
  },
  editBtnText: {
    color: '#2C6E8F',
    fontSize: 15,
    fontWeight: '700',
  },

  // --- Pagina range: tabella per fascia d'età ---
  bandHeadRow: {
    flexDirection: 'row',
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F4F8',
  },
  bandHead: {
    color: '#B0BEC5',
    fontSize: 11,
    fontWeight: '700',
  },
  bandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 11,
    paddingHorizontal: 8,
    borderRadius: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F7F9FB',
  },
  bandRowActive: {
    backgroundColor: '#EAF6FD',
    borderBottomColor: 'transparent',
  },
  bandName: {
    color: '#2C3E50',
    fontSize: 13,
    fontWeight: '700',
    flex: 1.2,
  },
  bandVal: {
    color: '#34495E',
    fontSize: 13,
    flex: 1,
    textAlign: 'center',
  },
  tempNote: {
    color: '#7F8C8D',
    fontSize: 12,
    marginTop: 12,
    lineHeight: 17,
  },

  // --- Allarmi: pulsante guida primo soccorso ---
  guideBtn: {
    backgroundColor: '#EAF6FD',
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginHorizontal: 24,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  guideBtnTitle: {
    color: '#2C6E8F',
    fontSize: 14,
    fontWeight: '800',
  },
  guideBtnSub: {
    color: '#5B9BB8',
    fontSize: 12,
    marginTop: 2,
  },
  guideBtnArrow: {
    color: '#4FC3F7',
    fontSize: 22,
    fontWeight: '800',
    marginLeft: 12,
  },

  // --- Guida primo soccorso: contenuto ---
  guideSection: {
    marginTop: 14,
  },
  guideSectionTitle: {
    color: '#3A506B',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 6,
  },
  guideStepRow: {
    flexDirection: 'row',
    marginBottom: 7,
  },
  guideBullet: {
    color: '#4FC3F7',
    fontSize: 14,
    fontWeight: '800',
    marginRight: 8,
    lineHeight: 20,
  },
  guideStep: {
    color: '#34495E',
    fontSize: 13,
    flex: 1,
    lineHeight: 20,
  },
  guideEmergency: {
    backgroundColor: '#FFEBEE',
    borderRadius: 14,
    padding: 14,
    marginTop: 16,
  },
  guideEmergencyTitle: {
    color: '#C62828',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 6,
  },
  guideEmergencyText: {
    color: '#8E3B3B',
    fontSize: 13,
    lineHeight: 19,
  },
  guideDisclaimer: {
    color: '#95A5A6',
    fontSize: 11,
    fontStyle: 'italic',
    marginTop: 14,
    lineHeight: 16,
  },

  // --- Utility di layout generiche ---
  // Riempie lo spazio disponibile: usato al posto di style={{ flex: 1 }} inline.
  flexFill: {
    flex: 1,
  },
  // Contenuto scrollabile delle schede Home/Allarmi.
  tabContent: {
    paddingBottom: 24,
  },
  // Contenuto scrollabile della scheda Profilo (leggermente più alto in fondo).
  tabContentProfile: {
    paddingBottom: 28,
  },
  // Contenuto dello ScrollView della schermata di login: centra il form.
  loginScrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  // Colonna "Ora" nello storico letture (intestazione e righe).
  histTimeCol: {
    flex: 1.3,
  },
  // Colonne della tabella dei valori normali per fascia d'età.
  bandHeadName: {
    flex: 1.2,
  },
  bandHeadVal: {
    flex: 1,
    textAlign: 'center',
  },
  // Variante del pulsante di modale a metà larghezza, usata quando è
  // affiancato a un pulsante secondario (es. Annulla / Salva).
  modalBtnHalf: {
    flex: 1,
    marginTop: 0,
    marginLeft: 8,
  },
});

// Stili della schermata di splash mostrata all'avvio, mentre l'app verifica
// se esiste una sessione salvata.
export const splashStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
    justifyContent: 'center',
    alignItems: 'center',
  },
  badge: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#EAF6FD',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 22,
  },
  logo: {
    color: '#3A506B',
    fontSize: 34,
    fontWeight: '800',
    letterSpacing: 1,
  },
  tagline: {
    color: '#7F8C8D',
    fontSize: 14,
    marginTop: 8,
    fontWeight: '500',
  },
  loader: {
    marginTop: 30,
  },
});

export default styles;