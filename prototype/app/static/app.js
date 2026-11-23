import {submitOnce} from './mutations.mjs';

const page = document.body.dataset.page;
let user, csrf, snapshot, busy = false, reconciled = false;
const $ = selector => document.querySelector(selector);
const messages = {
  invalid_credentials: 'Meno alebo heslo nie je správne.',
  username_taken: 'Toto používateľské meno sa už používa.',
  already_signed_in: 'Už ste prihlásení.',
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
  account_not_found: 'Účet sa nenašiel.',
  account_changed: 'Účet sa medzitým zmenil.',
  client_role_fixed: 'Klientskemu účtu nemožno priradiť zamestnaneckú rolu.',
  last_active_admin: 'Aspoň jeden administrátor musí zostať aktívny.',
  future_reservation: 'Účet má potvrdenú rezerváciu na budúci tréning. Klient ju môže najprv zrušiť.',
  future_training_assignment: 'Tréner má pridelený budúci tréning.',
  network: 'Výsledok požiadavky sa nepodarilo overiť. Načítavam aktuálne údaje; rezerváciu automaticky neopakujem.'
};
const roleLabels = {client: 'Klient', trainer: 'Tréner', reception: 'Recepcia', admin: 'Administrátor'};
const statusLabels = {active: 'Aktívny', disabled: 'Deaktivovaný'};

function signIn() {
  user = csrf = snapshot = null;
  $('#main').replaceChildren($('#message'));
  $('.account')?.remove();
  window.location.replace('/login');
}

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
    if (!response.ok) {
      const code = body?.error?.code || (response.status === 422 ? 'validation' : 'internal_error');
      if (code === 'unauthorized' && page !== 'login' && page !== 'register') signIn();
      throw Object.assign(new Error(), {code});
    }
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
  }
  return card;
}

function render() {
  if (!snapshot) return;
  if (page === 'schedule') {
    const membership = $('#membership');
    if (user.role !== 'client') membership.textContent = 'Rozvrh a obsadenosť · iba na čítanie';
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
  if (!user) return;
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
  if (!user) return;
  busy = false; render();
  if (!outcome.reconciled) notice('Aktuálny stav sa nepodarilo načítať. Ďalšia rezervácia je zablokovaná, kým neobnovíte údaje. Požiadavku automaticky neopakujem.', true);
  else if (!outcome.ok) notice(messages[outcome.error.code] || messages.internal_error, true);
  else notice(method === 'POST' ? 'Miesto je vaše. Rezervácia bola potvrdená.' : 'Rezervácia je zrušená. Miesto sme uvoľnili.');
}

function setupRegistration() {
  const form = $('#registration-form');
  const button = form.querySelector('button');
  const password = $('#password');
  button.disabled = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    button.disabled = true;
    try {
      await api('/api/account/registration', {method: 'POST', body: JSON.stringify({
        username: $('#username').value, display_name: $('#display-name').value, password: password.value
      })});
      form.hidden = true;
      notice('Účet je vytvorený. Prihláste sa zvoleným menom a heslom.');
      form.nextElementSibling.querySelector('a').focus();
    } catch (error) {
      if (error.code === 'network') {
        notice('Výsledok registrácie sa nepodarilo overiť. Skúste sa prihlásiť zvoleným menom a heslom.', true);
      } else {
        notice(messages[error.code] || messages.internal_error, true);
        button.disabled = false;
      }
    } finally {
      password.value = '';
    }
  });
}

async function setupProfile() {
  const form = $('#profile-form');
  const button = form.querySelector('button');
  const name = $('#display-name');
  const profile = await api('/api/account/profile');
  name.value = profile.display_name;
  name.disabled = false;
  button.disabled = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    button.disabled = true;
    name.readOnly = true;
    try {
      const updated = await api('/api/account/profile', {method: 'PUT', body: JSON.stringify({display_name: name.value})});
      name.value = updated.display_name;
      notice('Zobrazované meno bolo uložené.');
    } catch (error) {
      const uncertain = 'Výsledok uloženia sa nepodarilo overiť. Obnovte stránku a skontrolujte uložené meno.';
      notice(error.code === 'network' ? uncertain : messages[error.code] || messages.internal_error, true);
    } finally {
      name.readOnly = false;
      button.disabled = false;
    }
  });
}

function setupAdmin() {
  const path = '/api/admin/accounts';
  const form = $('#staff-form'), refreshButton = $('#accounts-refresh'), list = $('#accounts-list');
  const fields = form.querySelector('fieldset');
  let available = false, pending = false;

  function setAvailability() {
    fields.disabled = pending || !available;
    refreshButton.disabled = pending;
    list.querySelectorAll('button, select').forEach(control => {
      control.disabled = fields.disabled;
    });
  }

  function card(account) {
    const row = element('article', 'admin-account');
    row.dataset.accountId = account.id;
    row.append(element('h3', '', account.display_name),
      element('p', 'muted', `@${account.username} · ${roleLabels[account.role]}`),
      element('p', 'admin-status', statusLabels[account.status]));
    const actions = element('div', 'admin-actions');
    const nextStatus = account.status === 'active' ? 'disabled' : 'active';
    const state = element('button', 'button button-outline', nextStatus === 'disabled' ? 'Deaktivovať' : 'Aktivovať');
    state.addEventListener('click', () => save(`${path}/${account.id}/status`, 'PUT',
      {status: nextStatus, expected_version: account.version}, account.id));
    actions.append(state);
    if (account.role !== 'client') {
      const roleForm = element('form', 'admin-role');
      const select = element('select');
      select.id = `role-${account.id}`;
      const label = element('label', '', 'Nová rola');
      label.htmlFor = select.id;
      for (const role of ['trainer', 'reception', 'admin']) {
        const option = element('option', '', roleLabels[role]);
        option.value = role;
        select.append(option);
      }
      select.value = account.role;
      const submit = element('button', 'button button-outline', 'Uložiť rolu');
      roleForm.append(label, select, submit);
      roleForm.addEventListener('submit', event => {
        event.preventDefault();
        save(`${path}/${account.id}/role`, 'PUT',
          {role: select.value, expected_version: account.version}, account.id);
      });
      actions.append(roleForm);
    }
    row.append(actions);
    return row;
  }

  async function load() {
    available = false;
    setAvailability();
    list.setAttribute('aria-busy', 'true');
    try {
      const {items} = await api(path);
      list.replaceChildren(...items.map(card));
      if (!items.length) list.append(element('p', 'empty', 'Zoznam účtov je prázdny.'));
      available = true;
      return items;
    } finally {
      list.setAttribute('aria-busy', 'false');
      setAvailability();
    }
  }

  async function reload() {
    if (pending) return;
    pending = true;
    try {
      await load();
      notice('Zoznam účtov je aktuálny.');
    } catch (error) {
      if (!user) return;
      list.replaceChildren();
      notice('Zoznam sa nepodarilo načítať. Použite tlačidlo Obnoviť zoznam.', true);
    } finally {
      pending = false;
      setAvailability();
    }
  }

  async function save(url, method, data, id) {
    if (pending || !available) return;
    pending = true;
    setAvailability();
    try {
      const account = await api(url, {method, body: JSON.stringify(data)});
      if (account.id === user?.id && (account.status === 'disabled' || account.role !== user.role)) {
        signIn();
        return;
      }
      const existing = list.querySelector(`[data-account-id="${account.id}"]`);
      if (existing) existing.replaceWith(card(account));
      else list.append(card(account));
      if (method === 'POST') form.reset();
      notice(method === 'POST' ? 'Účet zamestnanca bol vytvorený.' : 'Údaje účtu sú uložené.');
    } catch (error) {
      if (!user) return;
      if (['network', 'internal_error', 'storage_unavailable', 'account_changed', 'account_not_found'].includes(error.code)) {
        try {
          const items = await load();
          const current = items.find(account => id ? account.id === id : account.username === data.username);
          const state = current
            ? `Aktuálny stav @${current.username} · ${statusLabels[current.status]} · ${roleLabels[current.role]}.`
            : 'Účet sa v aktuálnom zozname nenašiel.';
          const matches = current && (!data.role || current.role === data.role) &&
            (!data.status || current.status === data.status);
          const comparison = matches ? 'Požadovaná rola alebo stav zodpovedá zoznamu.' : 'Skontrolujte údaje pred ďalšou zmenou.';
          const failure = error.code === 'network' ? 'Výsledok požiadavky sa nepodarilo overiť.' : messages[error.code];
          notice(`${failure} ${state} ${comparison}`, true);
        } catch {
          if (user) {
            list.replaceChildren();
            notice('Výsledok sa nepodarilo overiť. Pred ďalšou zmenou obnovte zoznam účtov.', true);
          }
        }
      } else {
        notice(messages[error.code] || messages.internal_error, true);
      }
    } finally {
      form.elements.password.value = '';
      pending = false;
      setAvailability();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    save(path, 'POST', Object.fromEntries(new FormData(form)));
  });
  refreshButton.addEventListener('click', reload);
  return reload();
}

async function boot() {
  try {
    const session = await api('/session');
    user = session.user; csrf = session.csrf_token;
    if (page === 'register') {
      setupRegistration();
      return;
    }
    if (page === 'login') {
      $('#login-submit').disabled = false;
      $('#login-submit').textContent = 'Prihlásiť sa ↗';
      $('#login-form').addEventListener('submit', async event => {
        event.preventDefault();
        const button = $('#login-submit'); button.disabled = true; button.textContent = 'Prihlasujem…';
        try {
          const result = await api('/login', {method: 'POST', body: JSON.stringify({username: $('#username').value, password: $('#password').value})});
          window.location.assign(result.user.role === 'client' ? '/schedule' : '/staff');
        } catch (error) { notice(messages[error.code] || messages.internal_error, true); button.disabled = false; button.textContent = 'Prihlásiť sa ↗'; }
      });
      return;
    }
    if (!user) { signIn(); return; }
    $('#logout').addEventListener('click', async () => {
      $('#logout').disabled = true;
      try { await api('/logout', {method: 'POST'}); window.location.assign('/login'); }
      catch (error) {
        if (error.code === 'csrf_invalid') {
          try {
            if (!(await api('/session')).user) { signIn(); return; }
          } catch {}
        }
        if (user) { notice(messages[error.code] || messages.internal_error, true); $('#logout').disabled = false; }
      }
    });
    if (page === 'profile') {
      await setupProfile();
      return;
    }
    if (page === 'admin') {
      await setupAdmin();
      return;
    }
    const refreshButton = $('#refresh');
    if (refreshButton) refreshButton.addEventListener('click', async () => {
      if (busy) return;
      busy = true; refreshButton.disabled = true;
      try { await refresh(); notice('Údaje sú aktuálne.'); }
      catch (error) { notice(messages[error.code] || messages.internal_error, true); }
      finally { busy = false; refreshButton.disabled = false; render(); }
    });
    if (page !== 'staff') await refresh();
  } catch (error) {
    if (error.code === 'unauthorized') return;
    const accountPage = page === 'register' || page === 'profile';
    const message = accountPage && error.code === 'network'
      ? 'Stránku sa nepodarilo načítať. Obnovte ju a skúste znova.'
      : messages[error.code] || messages.internal_error;
    notice(message, true);
  }
}

boot();
