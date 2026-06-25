import { StyleSheet } from 'react-native';


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

  // Monitor Header con riga titolo + pulsante logout
  monitorHeader: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  header: {
    color: '#3A506B',
    fontSize: 26,
    fontWeight: '800',
  },
  // Pulsante logout a freccia
  logoutBtn: {
    padding: 4,
  },
  logoutText: {
    color: '#3A506B',
    fontSize: 28,
    fontWeight: '300',
    lineHeight: 30,
  },
  status: {
    color: '#7F8C8D',
    marginTop: 4,
    marginBottom: 16,
    fontSize: 13,
  },

  // Banner EMERGENZA cardiaca (rosso intenso)
  bannerEmergency: {
    backgroundColor: '#FFEBEE',
    borderColor: '#EF5350',
    borderWidth: 2,
    padding: 16,
    borderRadius: 16,
    marginHorizontal: 24,
    marginBottom: 10,
  },
  bannerEmergencyText: {
    color: '#C62828',
    fontWeight: '800',
    textAlign: 'center',
    fontSize: 14,
  },

  // Banner ALLERTA FEBBRE (arancione)
  bannerFever: {
    backgroundColor: '#FFF8E1',
    borderColor: '#FFB300',
    borderWidth: 1,
    padding: 14,
    borderRadius: 16,
    marginHorizontal: 24,
    marginBottom: 10,
  },
  bannerFeverText: {
    color: '#E65100',
    fontWeight: '700',
    textAlign: 'center',
    fontSize: 13,
  },

  // Banner sensore staccato (giallo tenue — come da requisiti)
  banner: {
    backgroundColor: '#FFEBEE',
    borderColor: '#FFCDD2',
    borderWidth: 1,
    padding: 14,
    borderRadius: 16,
    marginHorizontal: 24,
    marginBottom: 16,
  },
  bannerText: {
    color: '#EF5350',
    fontWeight: '700',
    textAlign: 'center',
    fontSize: 13,
  },

  // Card arrotondate con bordo azzurro a sinistra
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 22,
    marginBottom: 14,
    marginHorizontal: 24,
    borderLeftWidth: 5,
    borderLeftColor: '#81D4FA',
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

  // Card degli allarmi
  alert: {
    backgroundColor: '#FFFFFF',
    borderLeftWidth: 4,
    borderLeftColor: '#FFCC80',
    padding: 14,
    borderRadius: 14,
    marginBottom: 10,
    marginHorizontal: 24,
    elevation: 1,
  },
  alertCrit: {
    borderLeftColor: '#EF5350',
  },
  // Alert "risolto" (gravita INFO dal firmware): verde invece di
  // arancione/rosso, per distinguere visivamente una buona notizia da
  // un nuovo problema.
  alertInfo: {
    borderLeftColor: '#66BB6A',
  },
  alertKind: {
    color: '#7F8C8D',
    fontWeight: '700',
    fontSize: 11,
    marginBottom: 2,
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

  // Storico letture
  historyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginHorizontal: 24,
    marginBottom: 6,
    borderRadius: 12,
    elevation: 1,
  },
  historyTime: {
    color: '#7F8C8D',
    fontSize: 12,
    flex: 1,
  },
  historyVal: {
    color: '#2C3E50',
    fontSize: 13,
    fontWeight: '600',
    flex: 1,
    textAlign: 'right',
  },
  // Variante compatta di historyVal, usata quando la riga storico mostra
  // piu' di due valori numerici (bpm, respirazione, temperatura, batteria)
  historyValSmall: {
    color: '#2C3E50',
    fontSize: 11,
    fontWeight: '600',
    flex: 1,
    textAlign: 'right',
  },

  // Modal di configurazione device (Punto 8 dei requisiti)
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
});

export default styles;
