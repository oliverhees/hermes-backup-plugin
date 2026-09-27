/**
 * Hermes Backup - Desktop-Halfte.
 *
 * Eigenstaendiges Plugin (unified package: plugin.yaml + dashboard/ + desktop/,
 * siehe website/docs/developer-guide/desktop-plugin-sdk.md "One package, both
 * SDKs"). Spricht sein eigenes Backend an: ~/.hermes/plugins/hermes-backup/
 * dashboard/plugin_api.py, gemountet unter /api/plugins/hermes-backup/.
 *
 * Reines ESM, wird uncompiliert geladen. Oberflaeche ueber jsx()-Aufrufe,
 * keine JSX-Syntax. Vorbild: der Hub selbst (aiianer-hermes-extensions),
 * aus dessen "Backups"-Tab dieses Plugin am 2026-09-27 ausgekoppelt wurde.
 */

import * as ReactModule from 'react'
import * as HermesSdk from '@hermes/plugin-sdk'

const React = ReactModule.default ?? ReactModule
const { useEffect, useState } = ReactModule

const jsx = (type, props = {}, key) => React.createElement(type, { ...props, key })
const jsxs = jsx

const { host, ROUTES_AREA, SIDEBAR_NAV_AREA } = HermesSdk

const ID = 'hermes-backup'
const PATH = '/hermes-backup'

function BackupPage(ctx) {
  const [backup, setBackup] = useState(null)
  const [backupArchives, setBackupArchives] = useState([])
  const [restorePlan, setRestorePlan] = useState(null)
  const [restoreText, setRestoreText] = useState('')
  const [restoreAcknowledged, setRestoreAcknowledged] = useState(false)
  const [backupTarget, setBackupTarget] = useState('')
  const [backupSchedule, setBackupSchedule] = useState('manual')
  const [backupTime, setBackupTime] = useState('02:00')
  const [backupWeekday, setBackupWeekday] = useState(0)
  const [backupBrowser, setBackupBrowser] = useState(null)
  const [backupBusy, setBackupBusy] = useState(false)

  const aktionen = {
    backupStatus: () => ctx.rest('/status'),
    backupSettings: body => ctx.rest('/settings', { method: 'PUT', body }),
    backupBrowse: body => ctx.rest('/browse', { method: 'POST', body }),
    backupArchives: () => ctx.rest('/archives'),
    backupRestorePrepare: body => ctx.rest('/restore/prepare', { method: 'POST', body }),
    backupRestoreConfirm: body => ctx.rest('/restore/confirm', { method: 'POST', body }),
    backupRun: () => ctx.rest('/run', { method: 'POST', body: {} })
  }

  const refreshBackup = () => Promise.all([aktionen.backupStatus(), aktionen.backupArchives()]).then(([result, archives]) => {
    setBackup(result)
    setBackupArchives(archives.archives || [])
    if (!backupTarget && result.targetDir) setBackupTarget(result.targetDir)
    setBackupSchedule(result.schedule || 'manual')
    setBackupTime(result.scheduleTime || '02:00')
    setBackupWeekday(Number.isInteger(result.scheduleWeekday) ? result.scheduleWeekday : 0)
    return result
  })

  useEffect(() => {
    refreshBackup().catch(() => setBackup({ state: 'failed', lastErrorCode: 'STATUS_UNAVAILABLE' }))
  }, [])

  const browseBackup = path => {
    setBackupBusy(true)
    aktionen.backupBrowse({ path }).then(setBackupBrowser).catch(() => setBackupBrowser({ error: 'Ordner konnte nicht geöffnet werden.' })).finally(() => setBackupBusy(false))
  }
  const prepareRestore = name => {
    setBackupBusy(true)
    aktionen.backupRestorePrepare({ name }).then(plan => { setRestorePlan(plan); setRestoreText(''); setRestoreAcknowledged(false) }).finally(() => setBackupBusy(false))
  }
  const confirmRestore = () => {
    if (!restorePlan || restoreText !== restorePlan.confirmationText || !restoreAcknowledged) return
    setBackupBusy(true)
    aktionen.backupRestoreConfirm({ name: restorePlan.name, confirmationToken: restorePlan.confirmationToken, confirmationText: restoreText, acknowledged: true }).then(() => { setRestorePlan(null); return refreshBackup() }).finally(() => setBackupBusy(false))
  }
  const saveBackup = () => {
    setBackupBusy(true)
    aktionen.backupSettings({ enabled: backupSchedule !== 'manual', target_dir: backupTarget, schedule: backupSchedule, scheduleTime: backupTime, scheduleWeekday: backupWeekday, retention: { enabled: false, keep: 5 } })
      .then(result => { setBackup(result); setBackupBrowser(null) }).finally(() => setBackupBusy(false))
  }
  const runBackup = () => {
    setBackupBusy(true); aktionen.backupRun().then(setBackup).finally(() => setBackupBusy(false))
  }

  return jsxs('div', { className: 'min-w-0 w-full max-w-6xl overflow-x-hidden p-4 sm:p-6 lg:p-8 space-y-5', children: [
    jsx('p', { className: 'text-xs uppercase tracking-widest text-accent', children: 'AIIANER BACKUP-AUSSENPOSTEN' }),
    jsx('h2', { className: 'text-xl font-semibold', children: 'Backups · lokal und außerhalb von Hermes' }),
    jsx('p', { className: 'break-words whitespace-normal text-sm leading-5 opacity-70', children: 'Deine Daten verlassen diesen Rechner nicht. Wähle den Zielordner einfach aus — innerhalb von HERMES_HOME ist absichtlich gesperrt.' }),
    jsxs('div', { className: 'space-y-2', children: [
      jsx('label', { className: 'text-xs font-medium opacity-75', children: 'Speicherort' }),
      jsxs('div', { className: 'flex gap-2', children: [
        jsx('input', { className: 'min-w-0 flex-1 rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm', value: backupTarget, placeholder: '/home/deinname/Backups', onChange: event => setBackupTarget(event.target.value) }),
        jsx('button', { className: 'shrink-0 rounded-md border border-white/15 px-3 py-2 text-xs', disabled: backupBusy, onClick: () => browseBackup(backupTarget || undefined), children: 'Ordner auswählen' })
      ] })
    ] }),
    backupBrowser ? jsxs('div', { className: 'rounded-md border border-white/15 bg-white/[0.03] p-3 space-y-2', children: [
      backupBrowser.error ? jsx('p', { className: 'text-xs text-red-300', children: backupBrowser.error }) : jsxs(React.Fragment, { children: [
        jsxs('div', { className: 'flex flex-wrap items-center gap-2', children: [
          jsx('button', { className: 'rounded border border-white/15 px-2 py-1 text-xs', disabled: !backupBrowser.parent || backupBusy, onClick: () => browseBackup(backupBrowser.parent), children: '← Hoch' }),
          jsx('button', { className: 'rounded border border-accent/60 px-2 py-1 text-xs text-accent', disabled: backupBusy, onClick: () => { setBackupTarget(backupBrowser.path); setBackupBrowser(null) }, children: 'Diesen Ordner wählen' }),
          jsx('span', { className: 'min-w-0 break-all text-[11px] opacity-60', children: backupBrowser.path })
        ] }),
        backupBrowser.directories && backupBrowser.directories.length ? jsx('div', { className: 'grid max-h-52 grid-cols-1 gap-1 overflow-auto sm:grid-cols-2', children: backupBrowser.directories.map(folder => jsx('button', { className: 'truncate rounded px-2 py-1 text-left text-xs hover:bg-white/10', onClick: () => browseBackup(folder.path), children: `📁 ${folder.name}` }, folder.path)) }) : jsx('p', { className: 'text-xs opacity-60', children: 'Keine Unterordner. Du kannst diesen Ordner direkt wählen.' })
      ] })
    ] }) : null,
    jsx('p', { className: 'break-words whitespace-normal text-xs leading-5 opacity-70', children: 'Hier stellst du die automatische Backup-Routine ein. Nach dem Speichern legt Hermes einen eigenen Zeitplan an. Ohne Zielordner wird nichts ausgeführt.' }),
    jsx('p', { className: 'break-words whitespace-normal text-xs leading-5 text-amber-200/75', children: 'Backup beim Schließen von Hermes ist in V1 noch nicht verfügbar. Diese Option folgt erst mit einem verlässlichen App-Shutdown-Hook.' }),
    jsxs('div', { className: 'grid gap-3 rounded-md border border-white/10 p-3 sm:grid-cols-3', children: [
      jsxs('label', { className: 'min-w-0 space-y-1 text-xs', children: [jsx('span', { className: 'font-medium opacity-75', children: 'Automatisches Backup' }), jsx('select', { className: 'w-full min-w-0 rounded border border-white/15 bg-background px-2 py-2 text-foreground', style: { colorScheme: 'dark' }, value: backupSchedule, onChange: event => setBackupSchedule(event.target.value), children: [jsx('option', { className: 'bg-background text-foreground', value: 'manual', children: 'Aus · nur manuell' }), jsx('option', { className: 'bg-background text-foreground', value: 'daily', children: 'Täglich' }), jsx('option', { className: 'bg-background text-foreground', value: 'weekly', children: 'Wöchentlich' })] })] }),
      jsxs('label', { className: 'space-y-1 text-xs', children: [jsx('span', { className: 'font-medium opacity-75', children: 'Uhrzeit' }), jsx('input', { className: 'w-full rounded border border-white/15 bg-black/20 px-2 py-2', type: 'time', value: backupTime, disabled: backupSchedule === 'manual', onChange: event => setBackupTime(event.target.value) })] }),
      backupSchedule === 'weekly' ? jsxs('label', { className: 'space-y-1 text-xs', children: [jsx('span', { className: 'font-medium opacity-75', children: 'Wochentag' }), jsx('select', { className: 'w-full rounded border border-white/15 bg-black/20 px-2 py-2', value: backupWeekday, onChange: event => setBackupWeekday(Number(event.target.value)), children: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'].map((name, day) => jsx('option', { value: day, children: name }, day)) })] }) : jsx('div', { className: 'text-xs self-end opacity-55', children: backupSchedule === 'daily' ? 'Läuft jeden Tag zur gewählten Uhrzeit.' : 'Manuelle Sicherungen bleiben jederzeit möglich.' })
    ] }),
    jsxs('div', { className: 'flex gap-2 flex-wrap', children: [
      jsx('button', { className: 'rounded-md border border-accent px-3 py-2 text-xs', disabled: backupBusy || !backupTarget, onClick: saveBackup, children: backupBusy ? 'Arbeite ...' : 'Speicherort & Plan sichern' }),
      jsx('button', { className: 'rounded-md border border-white/15 px-3 py-2 text-xs', disabled: backupBusy || !(backup && backup.configured), onClick: runBackup, children: 'Jetzt sichern' }),
      jsx('button', { className: 'rounded-md border border-white/15 px-3 py-2 text-xs', disabled: backupBusy, onClick: () => refreshBackup(), children: 'Status aktualisieren' })
    ] }),
    backup ? jsxs('div', { className: 'space-y-1 text-xs opacity-75', children: [
      jsx('p', { children: `Status: ${backup.state}${backup.lastErrorCode ? ` · Backup: ${backup.lastErrorCode}` : ''}${backup.scheduleErrorCode ? ` · Zeitplan: ${backup.scheduleErrorCode}` : ''}` }),
      backup.lastArchive ? jsx('p', { children: `Letztes Archiv: ${backup.lastArchive.name} · ${backup.lastArchive.fileCount || '?'} Dateien` }) : null,
      jsx('p', { children: `${backup.archiveCount || 0} veröffentlichte Archive im Zielordner.` })
    ] }) : jsx('div', { className: 'h-12 animate-pulse rounded-lg bg-white/10' }),
    jsxs('div', { className: 'rounded-md border border-white/10 p-3', children: [
      jsx('h3', { className: 'text-sm font-medium', children: 'Laufprotokoll' }),
      backup && backup.history && backup.history.length ? jsx('div', { className: 'mt-2 space-y-1 text-xs', children: backup.history.map((entry, index) => jsx('p', { className: entry.state === 'success' ? 'text-emerald-300' : 'text-red-300', children: `${entry.state === 'success' ? '✓' : '✕'} ${new Date(entry.at).toLocaleString('de-DE')} · ${entry.state === 'success' ? (entry.archive && entry.archive.name ? entry.archive.name : 'Sicherung erfolgreich') : (entry.errorCode || 'Fehler')}` }, `${entry.at}-${index}`)) }) : jsx('p', { className: 'mt-2 text-xs opacity-60', children: 'Noch kein Backup-Lauf protokolliert.' })
    ] }),
    jsxs('div', { className: 'rounded-md border border-white/10 p-3 space-y-2', children: [
      jsx('h3', { className: 'text-sm font-medium', children: 'Verfügbare Backups' }),
      backupArchives.length ? jsx('div', { className: 'space-y-2', children: backupArchives.map(archive => jsxs('div', { className: 'flex flex-wrap items-center justify-between gap-2 border-t border-white/10 pt-2 first:border-t-0 first:pt-0', children: [
        jsxs('div', { className: 'min-w-0', children: [jsx('p', { className: 'truncate text-xs font-medium', children: archive.name }), jsx('p', { className: 'text-[11px] opacity-60', children: `${new Date(archive.modified).toLocaleString('de-DE')} · ${(archive.bytes / 1024 / 1024).toFixed(1)} MB` })] }),
        jsx('button', { className: 'rounded border border-amber-300/60 px-2 py-1 text-xs text-amber-200', disabled: backupBusy || archive.valid === false, onClick: () => prepareRestore(archive.name), children: archive.valid === false ? 'Ungültig' : 'Wiederherstellen' })
      ] }, archive.name)) }) : jsx('p', { className: 'text-xs opacity-60', children: 'Noch keine fertigen Backups im Zielordner.' })
    ] }),
    restorePlan ? jsxs('div', { className: 'rounded-md border border-red-400/50 bg-red-950/20 p-3 space-y-2', children: [
      jsx('h3', { className: 'text-sm font-medium text-red-200', children: 'Wiederherstellung bestätigen' }),
      jsx('p', { className: 'text-xs text-red-100/80', children: restorePlan.warning }),
      jsx('p', { className: 'break-all rounded bg-black/20 p-2 font-mono text-xs', children: restorePlan.confirmationText }),
      jsx('input', { className: 'w-full rounded border border-red-300/40 bg-black/20 px-2 py-2 text-xs', value: restoreText, placeholder: 'Bestätigung exakt eintippen', onChange: event => setRestoreText(event.target.value) }),
      jsx('label', { className: 'flex items-start gap-2 text-xs', children: [jsx('input', { type: 'checkbox', checked: restoreAcknowledged, onChange: event => setRestoreAcknowledged(event.target.checked) }), jsx('span', { children: 'Ich weiß, dass bestehende Hermes-Daten überschrieben werden können.' })] }),
      jsxs('div', { className: 'flex gap-2', children: [jsx('button', { className: 'rounded border border-red-300 bg-red-500/20 px-3 py-2 text-xs text-red-100', disabled: backupBusy || restoreText !== restorePlan.confirmationText || !restoreAcknowledged, onClick: confirmRestore, children: 'Import mit Überschreiben ausführen' }), jsx('button', { className: 'rounded border border-white/15 px-3 py-2 text-xs', disabled: backupBusy, onClick: () => setRestorePlan(null), children: 'Abbrechen' })] })
    ] }) : null,
    jsxs('div', { className: 'rounded-md border border-white/10 p-3 space-y-2', children: [
      jsx('h3', { className: 'text-sm font-medium', children: 'Restore-Anleitung' }),
      jsx('p', { className: 'text-xs opacity-75', children: '1. Wähle oben ein gültiges Archiv. 2. Lies die Warnung und tippe den exakten Bestätigungssatz ein. 3. Setze die Checkbox und starte den Import. Hermes muss danach gegebenenfalls neu gestartet werden.' }),
      jsx('p', { className: 'text-xs opacity-60', children: 'Alternativ im Terminal: hermes import /vollständiger/pfad/zu/deinem-backup.zip. Für das Überschreiben bestehender Daten verwendet der Assistent den offiziellen Importpfad mit --force.' })
    ] }),
    jsx('p', { className: 'text-xs text-amber-300/80', children: 'Wiederherstellung überschreibt möglicherweise bestehende Hermes-Daten. Sie wird niemals automatisch ausgeführt.' })
  ] })
}

export default {
  id: ID,
  name: 'Hermes Backup',
  register(ctx) {
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: PATH },
        render: () => jsx(BackupPage, { ctx })
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        data: { path: PATH, label: 'Backups', codicon: 'archive' }
      }
    ])
  }
}
