import {submitOnce} from './mutations.mjs';

const page = document.body.dataset.page;
let user, csrf, snapshot, busy = false, reconciled = false;
const $ = selector => document.querySelector(selector);
const messages = {
  invalid_credentials: 'Meno alebo heslo nie je správne.',
  unauthorized: 'Prihlásenie vypršalo. Prihláste sa znova.',
  forbidden: 'Na túto operáciu nemáte oprávnenie.',
  csrf_invalid: 'Bezpečnostný token vypršal. Obnovte stránku a skúste znova.',
  client_mismatch: 'Rezerváciu môžete vytvoriť iba pre seba.',
  training_not_found: 'Tréning sa nenašiel. Obnovte rozvrh.',
  reservation_not_found: 'Rezervácia sa nenašla.',
  training_started: 'Tréning sa už začal. Rezervácia ani prvé zrušenie už nie sú možné.',
  duplicate_reservation: 'Na tento tréning už máte rezerváciu.',
  membership_inactive: 'Na novú rezerváciu potrebujete aktívne členstvo.',
  capacity_full: 'Tento tréning je už plný. Vyberte si iný termín.',
  storage_unavailable: 'Údaje sú dočasne nedostupné. Skúste ich obnoviť.',
  internal_error: 'Operáciu sa nepodarilo dokončiť. Obnovte údaje.',
  validation: 'Skontrolujte zadané údaje.',
  network: 'Výsledok požiadavky sa nepodarilo overiť. Načítavam aktuálne údaje; rezerváciu automaticky neopakujem.'
};

function notice(text, error = false) {
  const box = $('#message');
  box.textContent = text;
  box.className = 'message ' + (error ? 'message-error' : 'message-success');
  box.hidden = false;
  if (error) { box.tabIndex = -1; box.focus(); }
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {...options, credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf || '', ...options.headers}});
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) throw Object.assign(new Error(), {code: body?.error?.code || (response.status === 422 ? 'validation' : 'internal_error')});
    return body;
  } catch (error) {
    if (error.code) throw error;
    throw Object.assign(new Error(), {code: 'network'});
  } finally { clearTimeout(timer); }
}

const time = value => new Intl.DateTimeFormat('sk-SK', {timeZone: 'Europe/Bratislava', hour: '2-digit', minute: '2-digit'}).format(new Date(value));
const date = value => new Intl.DateTimeFormat('sk-SK', {timeZone: 'Europe/Bratislava', weekday: 'long', day: 'numeric', month: 'long'}).format(new Date(value));
const started = training => Date.parse(training.starts_at) <= Date.now();
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function action(label, onClick, disabled = false, quiet = false) {
  const button = element('button', 'button ' + (quiet ? 'button-outline' : 'button-primary'), label);
  button.disabled = disabled || busy || !reconciled;
  button.addEventListener('click', onClick);
  return button;
}

function trainingCard(training) {
  const card = element('article', 'training-card');
  const past = started(training);
  const top = element('div', 'card-top');
  top.append(element('span', 'date-label', date(training.starts_at)), element('span', 'pill ' + (past ? 'pill-muted' : ''), past ? 'MINULÝ TRÉNING' : training.moja_rezervacia_id ? 'REZERVOVANÉ' : training.volne_miesta ? 'VOĽNÉ MIESTA' : 'OBSADENÉ'));
  card.append(top, element('div', 'training-time', time(training.starts_at) + ' — ' + time(training.ends_at)), element('h3', '', training.aktivita), element('p', 'training-details', training.trener + ' · ' + training.priestor));
  const capacity = element('div', 'capacity');
  capacity.append(element('span', '', 'Voľné miesta'), element('strong', '', `${training.volne_miesta} / ${training.kapacita}`));
  const meter = element('meter', 'capacity-meter');
  meter.min = 0; meter.max = training.kapacita; meter.value = training.obsadene;
  meter.setAttribute('aria-label', `Obsadené miesta: ${training.obsadene} z ${training.kapacita}`);
  card.append(capacity, meter);
  if (user.role === 'client') {
    let label = 'Rezervovať miesto ↗', disabled = false;
    if (past) { label = 'Tréning sa už začal'; disabled = true; }
    else if (training.moja_rezervacia_id) { label = 'Miesto je vaše ✓'; disabled = true; }
    else if (snapshot.membership?.stav !== 'active') { label = 'Potrebné aktívne členstvo'; disabled = true; }
    else if (!training.volne_miesta) { label = 'Tréning je plný'; disabled = true; }
    card.append(action(label, () => mutate('POST', '/reservations', {id_klienta: user.id, id_treningu: training.id_treningu}), disabled));
  } else card.append(element('p', 'muted', 'Prehľad trénera · iba na čítanie'));
  return card;
}

function render() {
  if (!snapshot) return;
  if (page === 'schedule') {
    const membership = $('#membership');
    if (user.role === 'trainer') membership.textContent = 'Prístup trénera · Rozvrh iba na čítanie. Správa centra je mimo ukážky.';
    else {
      const labels = {active: 'Aktívne členstvo', pending: 'Členstvo čaká na aktiváciu alebo začiatok platnosti', expired: 'Členstvo vypršalo'};
      membership.textContent = snapshot.membership ? labels[snapshot.membership.stav] + (snapshot.membership.stav === 'active' ? ' · Platné do ' + date(snapshot.membership.valid_until) : '') : 'Nemáte evidované členstvo';
      membership.classList.toggle('membership-inactive', snapshot.membership?.stav !== 'active');
    }
    const future = snapshot.trainings.filter(training => !started(training));
    const past = snapshot.trainings.filter(started);
    $('#trainings').replaceChildren(...future.map(trainingCard));
    if (!future.length) $('#trainings').append(element('p', 'empty', 'Momentálne nie sú naplánované ďalšie tréningy.'));
    $('#trainings').setAttribute('aria-busy', 'false');
    $('#training-count').textContent = `${future.length} termíny`;
    $('#past-section').hidden = !past.length;
    $('#past-trainings').replaceChildren(...past.map(trainingCard));
  }
  if (page === 'reservations') {
    const cards = snapshot.reservations.map(reservation => {
      const training = reservation.training;
      const row = element('article', 'reservation-row');
      const info = element('div', 'reservation-info');
      const past = started(training), cancelled = reservation.stav === 'cancelled';
      info.append(element('span', 'date-label', date(training.starts_at) + ' · ' + time(training.starts_at)), element('h2', '', training.aktivita), element('p', 'muted', training.trener + ' · ' + training.priestor), element('small', 'muted', `Rezervácia č. ${reservation.id_rezervacie}`));
      const side = element('div', 'reservation-side');
      side.append(element('span', 'pill ' + (cancelled || past ? 'pill-muted' : ''), cancelled ? 'ZRUŠENÁ' : past ? 'POTVRDENÁ · MINULÝ TRÉNING' : 'POTVRDENÁ'));
      if (!cancelled && !past) side.append(action('Zrušiť rezerváciu', () => mutate('DELETE', `/reservations/${reservation.id_rezervacie}`), false, true));
      if (cancelled) side.append(element('small', 'muted', 'Miesto bolo uvoľnené.'));
      row.append(info, side); return row;
    });
    $('#reservations').replaceChildren(...cards);
    if (!cards.length) $('#reservations').append(element('div', 'empty', 'Zatiaľ nemáte žiadne rezervácie. Vyberte si tréning v rozvrhu.'));
    $('#reservations').setAttribute('aria-busy', 'false');
  }
}

async function refresh() {
  reconciled = false;
  render();
  const [trainings, membership, reservations] = await Promise.all([
    api('/trainings'), user.role === 'client' ? api('/memberships/current') : null,
    user.role === 'client' ? api('/reservations') : null
  ]);
  snapshot = {trainings: trainings.items, membership: membership?.membership, reservations: reservations?.items || []};
  reconciled = true;
  render();
}

async function mutate(method, path, body) {
  if (busy || !reconciled) return;
  busy = true; render();
  notice('Spracúvam požiadavku…');
  const outcome = await submitOnce(() => api(path, {method, ...(body ? {body: JSON.stringify(body)} : {})}), refresh);
  busy = false; render();
  if (!outcome.reconciled) notice('Aktuálny stav sa nepodarilo načítať. Ďalšia rezervácia je zablokovaná, kým neobnovíte údaje. Požiadavku automaticky neopakujem.', true);
  else if (!outcome.ok) notice(messages[outcome.error.code] || messages.internal_error, true);
  else notice(method === 'POST' ? 'Miesto je vaše. Rezervácia bola potvrdená.' : 'Rezervácia je zrušená. Miesto sme uvoľnili.');
}

async function boot() {
  try {
    const session = await api('/session');
    user = session.user; csrf = session.csrf_token;
    if (page === 'login') {
      $('#login-submit').disabled = false;
      $('#login-submit').textContent = 'Prihlásiť sa ↗';
      $('#login-form').addEventListener('submit', async event => {
        event.preventDefault();
        const button = $('#login-submit'); button.disabled = true; button.textContent = 'Prihlasujem…';
        try {
          const result = await api('/login', {method: 'POST', body: JSON.stringify({username: $('#username').value, password: $('#password').value})});
          window.location.assign(result.user.role === 'trainer' ? '/staff' : '/schedule');
        } catch (error) { notice(messages[error.code] || messages.internal_error, true); button.disabled = false; button.textContent = 'Prihlásiť sa ↗'; }
      });
      return;
    }
    if (!user) { window.location.assign('/login'); return; }
    $('#logout').addEventListener('click', async () => {
      $('#logout').disabled = true;
      try { await api('/logout', {method: 'POST'}); window.location.assign('/login'); }
      catch (error) { notice(messages[error.code] || messages.internal_error, true); $('#logout').disabled = false; }
    });
    if ($('#refresh')) $('#refresh').addEventListener('click', async () => {
      if (busy) return;
      busy = true; $('#refresh').disabled = true;
      try { await refresh(); notice('Údaje sú aktuálne.'); }
      catch (error) { notice(messages[error.code] || messages.internal_error, true); }
      finally { busy = false; $('#refresh').disabled = false; render(); }
    });
    if (page !== 'staff') await refresh();
  } catch (error) { notice(messages[error.code] || messages.internal_error, true); }
}

boot();
