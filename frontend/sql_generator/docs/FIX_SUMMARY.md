# Correzione Bug SQL Display

## Problema Identificato
Il SQL formattato appariva per un attimo e poi scompariva quando il flag "Show SQL" era attivo.

## Causa del Problema
Il messaggio AI veniva renderizzato SOLO se aveva contenuto testuale (`msg.content.trim()`) o era in processing (`msg.isProcessing`).

Quando il backend inviava solo `SQL_FORMATTED` senza altro contenuto testuale, il messaggio aveva:
- `content: ""` (vuoto)
- `formattedSql: "SELECT ..."` (presente)
- `isProcessing: false`

La condizione di rendering alla linea 560 era:
```javascript
(msg.content.trim() || msg.isProcessing) ? (
```

Questa condizione restituiva `false` quando il contenuto era vuoto e non era in processing, quindi l'intero blocco del messaggio AI non veniva renderizzato, anche se aveva SQL formattato da mostrare.

## Soluzione Implementata
Aggiornata la condizione di rendering per includere anche messaggi che hanno SQL formattato o spiegazione:

```javascript
(msg.content.trim() || msg.isProcessing || msg.formattedSql || msg.sqlExplanation) ? (
```

Ora il messaggio AI viene renderizzato se ha almeno uno di:
- Contenuto testuale
- È in processing  
- SQL formattato
- Spiegazione SQL

## File Modificato
- `/app/chat/page.tsx` - Linea 560

## Test della Correzione

1. Apri http://localhost:3008
2. Abilita "Show SQL" nella sidebar
3. Invia una domanda
4. Il SQL dovrebbe apparire e rimanere visibile
5. Toggle del flag dovrebbe mostrare/nascondere il SQL immediatamente
6. La spiegazione dovrebbe funzionare correttamente come prima

## Risultato
✅ Il SQL ora rimane visibile quando il flag è attivo
✅ Il toggle dei flag funziona correttamente per entrambi SQL e spiegazione
✅ I dati vengono sempre generati dal backend indipendentemente dai flag
✅ L'utente ha controllo completo sulla visualizzazione