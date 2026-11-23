import {bratislavaWall, instantChoices, offsetLabel, trainingTime} from './training-times.mjs';

const path = '/api/trainer/schedule';
const recoveryPrefix = 'pohyb.training-create.';
const uncertain = new Set(['network', 'internal_error', 'storage_unavailable']);
const errors = {
  training_changed: 'Tréning sa medzitým zmenil. Skontrolujte aktuálne údaje.',
  training_started: 'Tréning sa už začal a nedá sa upraviť.',
  training_start_not_future: 'Začiatok tréningu musí byť v budúcnosti.',
  trainer_overlap: 'V tomto čase už máte naplánovaný iný tréning.',
  room_overlap: 'Priestor je v tomto čase obsadený.',
  training_details_locked: 'Tréning má históriu rezervácií. Môžete zmeniť iba kapacitu.',
  capacity_below_occupancy: 'Kapacita nesmie byť nižšia ako počet potvrdených rezervácií.',
  activity_not_found: 'Vybraná aktivita sa nenašla.',
  room_not_found: 'Vybraný priestor sa nenašiel.',
  activity_inactive: 'Vybraná aktivita už nie je aktívna.',
  room_inactive: 'Vybraný priestor už nie je aktívny.',
  create_request_conflict: 'Tento identifikátor vytvorenia už patrí inej požiadavke.',
  trainer_link_required: 'Váš účet musí administrátor prepojiť s aktívnym záznamom trénera.'
};

export function clearTrainingRecovery() {
  try {
    for (const key of Object.keys(sessionStorage)) {
      if (key.startsWith(recoveryPrefix)) sessionStorage.removeItem(key);
    }
  } catch {
    // Block creation on the editor if recovery storage is unavailable.
  }
}

export async function setupTrainerSchedule({accountId, api, element, notice, messages}) {
  const byId = id => document.getElementById('training-' + id);
  const form = byId('form'), list = byId('editor-list'), refreshButton = byId('refresh');
  const createButton = byId('new'), recovery = byId('recovery');
  const verify = byId('verify'), abandon = byId('abandon');
  const fields = form.elements;
  const fieldset = form.querySelector('fieldset');
  let snapshot, target, pending, pendingEdit, key, busy = false, available = false;
  const date = new Intl.DateTimeFormat('sk-SK', {
    timeZone: 'Europe/Bratislava', dateStyle: 'medium'
  });

  function controls() {
    createButton.hidden = !snapshot || !!pending;
    createButton.disabled = !available || busy || !snapshot?.activities.length || !snapshot?.rooms.length;
    recovery.hidden = !snapshot || !pending;
    fieldset.disabled = !available || busy || !!pending;
    verify.disabled = abandon.disabled = !available || busy;
    refreshButton.disabled = busy;
    list.querySelectorAll('button').forEach(button => { button.disabled = !available || busy || !!pending; });
  }

  function assignChoices(select, choices, selectedId, assignedLabel) {
    const empty = new Option('Vyberte možnosť', '');
    select.replaceChildren(empty, ...choices.map(choice => new Option(choice.name, choice.id)));
    if (selectedId && !choices.some(choice => choice.id === selectedId)) {
      select.append(new Option(assignedLabel + ' (neaktívne)', selectedId));
    }
    select.value = selectedId || '';
  }

  function updateTime(name, original) {
    const input = fields[name], select = fields[name + 'Offset'];
    const choices = instantChoices(input.value);
    select.replaceChildren(new Option('Vyberte posun', ''), ...choices.map(choice =>
      new Option(offsetLabel(choice.offset), choice.instant)));
    const originalChoice = choices.find(choice =>
      original && Date.parse(choice.instant) === Math.floor(Date.parse(original) / 1000) * 1000);
    select.value = originalChoice?.instant ?? '';
    const ambiguous = choices.length > 1;
    byId(name + '-choice').hidden = !ambiguous;
    select.required = ambiguous;
    input.setCustomValidity(input.value && !choices.length ? 'Tento čas v Bratislave neexistuje.' : '');
  }

  function readTime(name) {
    const original = target?.[name === 'start' ? 'starts_at' : 'ends_at'];
    if (target?.has_reservation_history) return original;
    const choices = instantChoices(fields[name].value);
    const selected = choices.length === 1 ? choices[0].instant : fields[name + 'Offset'].value;
    if (original && Date.parse(selected) === Math.floor(Date.parse(original) / 1000) * 1000) return original;
    return selected;
  }

  function openEditor(training) {
    target = training;
    form.reset();
    const locked = !!training?.has_reservation_history;
    byId('form-title').textContent = training ? 'Upraviť tréning' : 'Nový tréning';
    byId('trainer').textContent = snapshot.trainer.name;
    byId('lock').hidden = !locked;
    assignChoices(fields.activity, snapshot.activities, training?.activity_id, training?.aktivita);
    assignChoices(fields.room, snapshot.rooms, training?.room_id, training?.priestor);
    fields.activity.disabled = fields.room.disabled = locked;
    fields.capacity.value = training?.capacity ?? '';
    fields.capacity.min = Math.max(1, training?.obsadene ?? 0);
    for (const [name, original] of [['start', training?.starts_at], ['end', training?.ends_at]]) {
      fields[name].value = original ? bratislavaWall(original) : '';
      fields[name].readOnly = locked;
      fields[name + 'Offset'].disabled = locked;
      updateTime(name, original);
    }
    form.hidden = false;
    (locked ? fields.capacity : fields.activity).focus();
  }

  function card(training) {
    const row = element('article', 'admin-account');
    const edit = element('button', 'button button-outline', 'Upraviť tréning');
    edit.addEventListener('click', () => openEditor(training));
    row.append(element('h3', '', training.aktivita), element('p', 'muted', training.priestor),
      element('p', '', date.format(new Date(training.starts_at)) + ', ' + trainingTime(training)),
      element('p', '', `Obsadené: ${training.obsadene} / ${training.capacity} · Voľné: ${training.volne_miesta}`), edit);
    return row;
  }

  function reconcileEdit() {
    if (!pendingEdit) return;
    const {id, data} = pendingEdit;
    pendingEdit = null;
    const current = snapshot.items.find(training => training.id_treningu === id);
    if (!current) {
      notice('Tréning už nie je v zozname. Výsledok uloženia sa nepodarilo overiť.', true);
      return;
    }
    const normalize = value => value.replace(/(?:\.(\d+))?Z$/, (_, fraction = '') =>
      '.' + fraction.padEnd(6, '0') + 'Z');
    const matches = ['activity_id', 'room_id', 'capacity'].every(name => current[name] === data[name]) &&
      ['starts_at', 'ends_at'].every(name => normalize(current[name]) === normalize(data[name]));
    notice(`Aktuálna verzia ${current.version}. ${matches ? 'Aktuálne údaje zodpovedajú požadovanej zmene.' :
      'Aktuálne údaje sa líšia od požadovanej zmeny.'}`);
  }

  async function load() {
    available = false;
    controls();
    list.setAttribute('aria-busy', 'true');
    try {
      snapshot = await api(path);
      key = recoveryPrefix + accountId + '.' + snapshot.trainer.id;
      try {
        pending = JSON.parse(sessionStorage.getItem(key));
      } catch {
        pending = null;
      }
      list.replaceChildren(...snapshot.items.map(card));
      if (!snapshot.items.length) list.append(element('p', 'empty', 'Nemáte žiadne budúce tréningy.'));
      form.hidden = true;
      available = true;
      return true;
    } catch (error) {
      snapshot = null;
      form.hidden = true;
      list.replaceChildren();
      notice(errors[error.code] || 'Tréningy sa nepodarilo načítať. Použite tlačidlo Obnoviť tréningy.', true);
      return false;
    } finally {
      list.setAttribute('aria-busy', 'false');
      controls();
    }
  }

  function clearPending() {
    sessionStorage.removeItem(key);
    pending = null;
  }

  async function save(method, data, id) {
    if (busy || !available) return;
    busy = true;
    controls();
    try {
      await api(id ? `${path}/${id}` : path, {method, body: JSON.stringify(data)});
      if (method === 'POST') clearPending();
      if (await load()) notice(method === 'POST' ? 'Tréning bol zverejnený.' : 'Tréning bol uložený.');
      else notice('Tréning bol uložený. Zoznam sa nepodarilo obnoviť.', true);
    } catch (error) {
      if (error.code === 'unauthorized') return;
      if (uncertain.has(error.code)) {
        if (method === 'PUT') pendingEdit = {id, data};
        if (await load()) {
          if (pendingEdit) reconcileEdit();
          else notice('Výsledok treba overiť. Použite tlačidlo Overiť vytvorenie.', true);
        }
      } else {
        if (method === 'POST' && !['trainer_link_required', 'forbidden', 'csrf_invalid'].includes(error.code)) {
          clearPending();
        }
        if (await load()) notice(errors[error.code] || messages[error.code] || messages.internal_error, true);
      }
    } finally {
      busy = false;
      controls();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (busy || !available || pending) return;
    const data = {
      activity_id: Number(fields.activity.value), room_id: Number(fields.room.value),
      starts_at: readTime('start'), ends_at: readTime('end'), capacity: Number(fields.capacity.value)
    };
    if (target) {
      save('PUT', {...data, expected_version: target.version}, target.id_treningu);
      return;
    }
    const intent = {...data, request_id: crypto.randomUUID()};
    try {
      sessionStorage.setItem(key, JSON.stringify(intent));
    } catch {
      notice('Prehliadač nemôže uložiť identifikátor na overenie. Tréning sa neodoslal.', true);
      return;
    }
    pending = intent;
    save('POST', intent);
  });
  for (const name of ['start', 'end']) {
    fields[name].addEventListener('input', () => updateTime(name));
  }
  createButton.addEventListener('click', () => openEditor(null));
  byId('discard').addEventListener('click', () => { form.hidden = true; controls(); });
  verify.addEventListener('click', () => { if (pending) save('POST', pending); });
  abandon.addEventListener('click', () => { clearPending(); controls(); });
  refreshButton.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    try {
      if (await load()) {
        if (pendingEdit) reconcileEdit();
        else notice('Zoznam tréningov je aktuálny.');
      }
    } finally {
      busy = false;
      controls();
    }
  });
  return load();
}
