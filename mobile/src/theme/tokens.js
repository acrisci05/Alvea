// src/theme/tokens.js
//
// Design system condiviso da tutte le schermate. Tema CHIARO: stessa identita'
// visiva e logica clinica della demo (verde/ambra/rosso per gli stati, blu
// polvere per i dati neutri), ora su superfici chiare in stile "cartella
// clinica / referto cartaceo" invece che navy scuro.

export const colors = {
  // superfici
  paper: '#FAF8F3',      // sfondo principale (era navy)
  surface: '#FFFFFF',    // card/superfici elevate (era navySoft)
  surfaceMuted: '#F1EDE3', // superfici secondarie leggermente piu' scure della carta

  // testo
  ink: '#1A2433',        // testo principale (era ivory)
  inkDim: 'rgba(26,36,51,0.58)', // testo secondario (era textDim)

  // stati clinici (toni piu' scuri/saturi per restare leggibili su sfondo chiaro)
  sage: '#1F6E5C',
  sageBg: '#E2F1EC',
  sageText: '#1F6E5C',
  amber: '#B5601F',
  amberBg: '#FBEBDA',
  amberText: '#9A4F17',
  brick: '#9C2E2E',
  brickBg: '#FAE4E4',
  brickText: '#8C2424',

  dust: '#3D5A75',        // dati neutri / grafici (FR)
  pink: '#B4567E',         // dati neutri / grafici (BPM)

  line: '#E8E2D3',         // bordi/separatori
  lineStrong: '#D8D0BC',

  // retro-compatibilita' con nomi usati nei componenti esistenti
  navy: '#FAF8F3',
  navySoft: '#FFFFFF',
  ivory: '#1A2433',
  ivoryDim: '#F1EDE3',
  textDim: 'rgba(26,36,51,0.58)',
  sageDim: '#E2F1EC',
  amberDim: '#FBEBDA',
  brickDim: '#FAE4E4',
};

export const fonts = {
  // Fraunces e IBM Plex Mono sono caricati come Google Fonts via expo-font
  // (vedi App.js). Se i font non sono ancora caricati, React Native ricade
  // automaticamente sul font di sistema.
  display: 'Fraunces_600SemiBold',
  body: 'Inter_400Regular',
  bodyMedium: 'Inter_500Medium',
  bodySemibold: 'Inter_600SemiBold',
  mono: 'PlexMono_400Regular',
};

export const spacing = (n) => n * 4;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
};

export function severityPalette(severity) {
  switch (severity) {
    case 'critical':
    case 'CRITICAL':
      return { bg: colors.brickBg, text: colors.brickText, accent: colors.brick };
    case 'warning':
    case 'WARNING':
      return { bg: colors.amberBg, text: colors.amberText, accent: colors.amber };
    case 'info':
    case 'INFO':
      return { bg: colors.sageBg, text: colors.sageText, accent: colors.sage };
    default:
      return { bg: colors.sageBg, text: colors.sageText, accent: colors.sage };
  }
}

// Ombra leggera per le card su sfondo chiaro (sostituisce l'effetto "bordo
// luminoso su navy" del tema scuro: su carta chiara serve un'elevazione
// sottile per distinguere le superfici bianche dallo sfondo).
export const cardShadow = {
  shadowColor: '#1A2433',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.06,
  shadowRadius: 8,
  elevation: 2,
};


