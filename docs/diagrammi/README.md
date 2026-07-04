# Diagrammi UML (immagini per il report)

Immagini PNG (300 dpi circa) dei diagrammi UML del progetto, pronte da inserire
nel report tecnico. Sono generate dai sorgenti Mermaid presenti nei file
Markdown della cartella `docs/`: modificando il sorgente e rigenerando le
immagini si mantiene tutto allineato.

| Immagine | Diagramma UML | Vista 4+1 | Sorgente |
|---|---|---|---|
| `uml-01-use-case.png` | Casi d'Uso | Scenari (+1) | `docs/02-use-case.md` |
| `uml-02-er-schema.png` | Entità-Relazione (dati persistenti) | Logica (dati) | `docs/03-er-schema.md` |
| `uml-03-sequence-ingest.png` | Sequenza — ingest telemetria e realtime | Processo | `docs/04-sequence.md` |
| `uml-04-sequence-login.png` | Sequenza — autenticazione JWT | Processo | `docs/04-sequence.md` |
| `uml-05-sequence-config.png` | Sequenza — configurazione remota device | Processo | `docs/04-sequence.md` |
| `uml-06-class-diagram.png` | Classi (entità + servizi) | Logica | `docs/06-classi-attivita.md` |
| `uml-07-activity-alert.png` | Attività — valutazione soglie e alert | Processo | `docs/06-classi-attivita.md` |
| `architettura-dataflow.png` | Architettura (data flow) — non UML, di supporto | Sviluppo/Fisica | `docs/05-architettura.md` |

## Come rigenerare le immagini

I sorgenti Mermaid sono nei file `.md` di `docs/`. Per rigenerare i PNG si usa
[`@mermaid-js/mermaid-cli`](https://github.com/mermaid-js/mermaid-cli):

```bash
# esempio: rigenerare il diagramma delle classi
npx @mermaid-js/mermaid-cli -i docs/06-classi-attivita.md -o docs/diagrammi/classi.png -b white -s 3
```

In alternativa i diagrammi si vedono già renderizzati aprendo i file `.md` su
GitHub, che supporta Mermaid nativamente.
